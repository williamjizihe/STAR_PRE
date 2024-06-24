import torch
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter

import time
import os
import numpy as np
import pandas as pd
from math import ceil
from collections import defaultdict

import star.utils as utils
import star.agents as agents
from star.models import ANet, ForwardModel, StochasticForwardModel
from envs import EnvWithGoal, GatherEnv
from envs.create_maze_env import create_maze_env
from envs.create_gather_env import create_gather_env
import imageio
import logging
import yaml

import csv
from star.chat import ChatGenerator

"""
HIRO part adapted from
https://github.com/bhairavmehta95/data-efficient-hrl/blob/master/hiro/train_hiro.py
"""

def evaluate_policy(env, env_name, manager_policy, controller_policy,
                    calculate_controller_reward, ctrl_rew_scale,
                    manager_propose_frequency=10, eval_idx=0, eval_episodes=5):
    print("Starting evaluation number {}...".format(eval_idx))
    env.evaluate = True
    # video_dir = "Videos"

    # if not os.path.exists(video_dir):
    #     os.makedirs(video_dir)
    # video_path = os.path.join(video_dir, f"video_{env_name}_hrac_{eval_idx}.mp4")

    with torch.no_grad():
        avg_reward = 0.
        avg_controller_rew = 0.
        global_steps = 0
        goals_achieved = 0
        for eval_ep in range(eval_episodes):
            obs = env.reset()

            goal = obs["desired_goal"]
            state = obs["observation"]

            done = False
            step_count = 0
            env_goals_achieved = 0

            # video_writer = None
            # if eval_ep == 4:
            #     video_writer = imageio.get_writer(video_path, fps=30)

            while not done:
                if step_count % manager_propose_frequency == 0:
                    subgoal = manager_policy.sample_goal(state, goal)

                step_count += 1
                global_steps += 1
                action = controller_policy.select_action(state, subgoal, evaluation=True)
                new_obs, reward, done, _ = env.step(action)
                if env_name != "AntGather" and env.success_fn(reward):
                    env_goals_achieved += 1
                    goals_achieved += 1
                    done = True

                goal = new_obs["desired_goal"]
                new_state = new_obs["observation"]

                subgoal = controller_policy.subgoal_transition(state, subgoal, new_state)

                avg_reward += reward
                avg_controller_rew += calculate_controller_reward(state, subgoal, new_state, ctrl_rew_scale)

                state = new_state

            #     if video_writer is not None:
            #         data_rgb = env.render(mode='rgb_array', width=512, height=512, camera_name="top_down")
            #         video_writer.append_data(data_rgb)

            # if video_writer is not None:
            #     video_writer.close()

        avg_reward /= eval_episodes
        avg_controller_rew /= global_steps
        avg_step_count = global_steps / eval_episodes
        avg_env_finish = goals_achieved / eval_episodes

        print("---------------------------------------")
        print("Evaluation over {} episodes:\nAvg Ctrl Reward: {:.3f}".format(eval_episodes, avg_controller_rew))
        if env_name == "AntGather":
            print("Avg reward: {:.1f}".format(avg_reward))
        else:
            print("Goals achieved: {:.1f}%".format(100*avg_env_finish))
        print("Avg Steps to finish: {:.1f}".format(avg_step_count))
        print("---------------------------------------")

        env.evaluate = False
        return avg_reward, avg_controller_rew, avg_step_count, avg_env_finish

def evaluate_policy_star(env, env_name, goal_dim, grid, boss_policy, manager_policy, controller_policy,
                    calculate_controller_reward, ctrl_rew_scale, boss_propose_frequency=30,
                    manager_propose_frequency=10, eval_idx=0, eval_episodes=5, save_goals=False, total_timesteps=0, logging=None):
    print("Starting evaluation number {}...".format(eval_idx))
    env.evaluate = True
    avg_visits = np.zeros(len(boss_policy.G))
    resolution = 50
    g_low = [0, 0]
    g_high = [20, 20]

    if not os.path.exists("./results/partitions"):
        os.makedirs("./results/partitions")
    if not os.path.exists("./results/transition"):
        os.makedirs("./results/transition")
    
    # video_dir = "Videos"
    # if not os.path.exists(video_dir):
    #     os.makedirs(video_dir)
    
    # # Set the video path
    # video_path = os.path.join(video_dir, f"video_{env_name}_star_{eval_idx}.mp4")
    # video_writer = None

    with torch.no_grad():
        avg_reward = 0.
        avg_controller_rew = 0.
        global_steps = 0
        goals_achieved = 0
        visits_matrix = np.zeros((len(boss_policy.G), len(boss_policy.G)))
        last_region = 0
        next_region = 0
        for eval_ep in range(eval_episodes):
            visits = np.zeros((len(boss_policy.G)))
            obs = env.reset()
            goal = obs["desired_goal"]
            if goal is not None:
                goal_partition = boss_policy.identify_goal(goal)
            else:
                goal_partition = None

            state = obs["observation"]
            new_state = state
            start_state = state
            start_partition_idx = boss_policy.identify_partition(state)
            visits[start_partition_idx] += 1
            last_region = start_partition_idx
            start_partition = np.array(boss_policy.G[start_partition_idx].inf + boss_policy.G[start_partition_idx].sup)
            done = False
            step_count = 0
            env_goals_achieved = 0
            
             # Initialize video writer only for the 4th episode
            # if eval_ep == 4:
            #     video_writer = imageio.get_writer(video_path, fps=30)
            boss_policy.last_partition_idx = None
            while not done:
                if step_count % boss_propose_frequency == 0:
                    start_partition_idx = boss_policy.identify_partition(state)
                    start_partition = np.array(boss_policy.G[start_partition_idx].inf + boss_policy.G[start_partition_idx].sup)
                    visits[start_partition_idx] += 1
                    # target_partition_idx = boss_policy.select_partition(start_partition_idx, epsilon=0, goal=goal)
                    try:
                        target_partition_idx = boss_policy.select_partition_chat(state, start_partition_idx, goal, start_partition_idx) - 1
                    except Exception as e:
                        target_partition_idx = boss_policy.select_partition(state, start_partition_idx, goal)
                        if logging:
                            logging.error("Error in evaluation: {}".format(e))
                    if target_partition_idx == goal_partition and goal_dim == goal.shape[0]:
                        target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[i]-1 for i in range(goal_dim)], sup=[goal[i]+1 for i in range(goal_dim)])
                    elif target_partition_idx == goal_partition and goal_dim != goal.shape[0]:
                        target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[0]-1, goal[1]-1]+boss_policy.G[goal_partition].inf[2:], sup=[goal[0]+1, goal[1]+1]+boss_policy.G[goal_partition].sup[2:])
                    else:
                        target_partition_interval = boss_policy.G[target_partition_idx]
                    target_partition = np.array(target_partition_interval.inf + target_partition_interval.sup)

                if step_count % manager_propose_frequency == 0:
                    # subgoal = manager_policy.sample_goal(state, np.concatenate((target_partition, goal)))
                    subgoal = manager_policy.sample_goal(state, target_partition)
                    # subgoal = np.clip(subgoal, g_low, g_high)
                    x = max(min(int((subgoal[0] - g_low[0]) / (g_high[0] - g_low[0]) * resolution),resolution),0)
                    y = max(min(int((subgoal[1] - g_low[1]) / (g_high[1] - g_low[1]) * resolution),resolution),0)
                    grid[y, x] += 1
                step_count += 1
                global_steps += 1
                action = controller_policy.select_action(state, subgoal, evaluation=True)
                new_obs, reward, done, _ = env.step(action)
                if env_name != "AntGather" and env.success_fn(reward):
                    env_goals_achieved += 1
                    goals_achieved += 1
                    done = True

                goal = new_obs["desired_goal"]
                new_state = new_obs["observation"]
                next_region = boss_policy.identify_partition(new_state)
                if last_region != next_region:
                    visits_matrix[last_region, next_region] += 1
                last_region = next_region
                
                subgoal = controller_policy.subgoal_transition(state, subgoal, new_state)
                
                x = max(min(int((subgoal[0] - g_low[0]) / (g_high[0] - g_low[0]) * resolution),resolution),0)
                y = max(min(int((subgoal[1] - g_low[1]) / (g_high[1] - g_low[1]) * resolution),resolution),0)
                grid[y, x] += 1

                avg_reward += reward
                avg_controller_rew += calculate_controller_reward(state, subgoal, new_state, ctrl_rew_scale)

                state = new_state

                # Save frame to video only during the 4th episode
                # if video_writer is not None:
                #     data_rgb = env.render(mode='rgb_array', width=512, height=512, camera_name="top_down")
                #     video_writer.append_data(data_rgb)

            # Close video writer if it was used for the 4th episode
            # if video_writer is not None:
            #     video_writer.close()
            #     video_writer = None  # Reset for safety
            final_partition_idx = boss_policy.identify_partition(state)
            visits[final_partition_idx] += 1
            avg_visits += visits

        avg_visits /= eval_episodes
        adjacency_list = []
        for row in enumerate(visits_matrix):
            adjacency_list.append([i+1 for i, x in enumerate(row[1]) if x > 0])
        
        # if eval_idx in [200, 400, 600]:
        if eval_idx % 5 == 0: # Save the partitions every 5 evaluations
            with open("{}/{}_{}_BossPartitions.pth".format('./results/partitions', env_name, total_timesteps), 'w', encoding='UTF8') as f:
            # create the csv writer
                writer = csv.writer(f)
                writer.writerow([total_timesteps, eval_idx])
                writer.writerow(avg_visits)
                for i in range(len(boss_policy.G)):
                    # write a row to the csv file
                    writer.writerow(boss_policy.G[i].inf + boss_policy.G[i].sup)
            f.close()
            
            with open("{}/{}_{}_TransitionMatrix.pth".format('./results/transition', env_name, total_timesteps), 'w', encoding='UTF8') as f:
            # create the csv writer
                writer = csv.writer(f)
                writer.writerow([total_timesteps, eval_idx])
                for i in range(len(boss_policy.G)):
                    writer.writerow(visits_matrix[i])
            f.close()

        avg_reward /= eval_episodes
        avg_controller_rew /= global_steps
        avg_step_count = global_steps / eval_episodes
        avg_env_finish = goals_achieved / eval_episodes

        print("---------------------------------------")
        print("Evaluation over {} episodes:\nAvg Ctrl Reward: {:.3f}".format(eval_episodes, avg_controller_rew))
        if env_name == "AntGather":
            print("Avg reward: {:.1f}".format(avg_reward))
        else:
            print("Goals achieved: {:.1f}%".format(100*avg_env_finish))
        print("Avg Steps to finish: {:.1f}".format(avg_step_count))
        print("---------------------------------------")

        env.evaluate = False
        return avg_reward, avg_controller_rew, avg_step_count, avg_env_finish, grid, adjacency_list

def evaluate_policy_gara(env, env_name, goal_dim, grid, boss_policy, controller_policy,
                    calculate_controller_reward, ctrl_rew_scale, boss_propose_frequency=30,
                    eval_idx=0, eval_episodes=5):
    print("Starting evaluation number {}...".format(eval_idx))
    env.evaluate = True
    resolution = 24
    g_low = [-4, -4]
    g_high = [20, 20]
    # print(boss_policy.Q[:,3,:])
    with torch.no_grad():
        avg_reward = 0.
        avg_controller_rew = 0.
        global_steps = 0
        goals_achieved = 0
        for eval_ep in range(eval_episodes):
            obs = env.reset()
            goal = obs["desired_goal"]
            if goal is not None:
                goal_partition = boss_policy.identify_goal(goal)
            else:
                goal_partition = None

            state = obs["observation"]
            new_state = state
            start_state = state
            start_partition_idx = boss_policy.identify_partition(state)
            start_partition = np.array(boss_policy.G[start_partition_idx].inf + boss_policy.G[start_partition_idx].sup)
            done = False
            step_count = 0
            env_goals_achieved = 0
            while not done:
                if step_count % boss_propose_frequency == 0:
                    start_partition_idx = boss_policy.identify_partition(state)
                    start_partition = np.array(boss_policy.G[start_partition_idx].inf + boss_policy.G[start_partition_idx].sup)
                    target_partition_idx = boss_policy.select_partition(start_partition_idx, epsilon=0, goal=goal)
                    if target_partition_idx == goal_partition and goal_dim == goal.shape[0]:
                        target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[i]-1 for i in range(goal_dim)], sup=[goal[i]+1 for i in range(goal_dim)])
                    elif target_partition_idx == goal_partition and goal_dim != goal.shape[0]:
                        target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[0]-1, goal[1]-1]+boss_policy.G[goal_partition].inf[2:], sup=[goal[0]+1, goal[1]+1]+boss_policy.G[goal_partition].sup[2:])
                    else:
                        target_partition_interval = boss_policy.G[target_partition_idx]
                    target_partition = np.array(target_partition_interval.inf + target_partition_interval.sup)

                    partition_center = np.array([(target_partition_interval.inf[0] + target_partition_interval.sup[0]) / 2,
                        (target_partition_interval.inf[1] + target_partition_interval.sup[1]) / 2])
                    subgoal = partition_center

                step_count += 1
                global_steps += 1
                action = controller_policy.select_action(state, subgoal, evaluation=True)
                new_obs, reward, done, _ = env.step(action)
                if env_name != "AntGather" and env.success_fn(reward):
                    env_goals_achieved += 1
                    goals_achieved += 1
                    done = True

                goal = new_obs["desired_goal"]
                new_state = new_obs["observation"]

                subgoal = controller_policy.subgoal_transition(state, subgoal, new_state)
                
                avg_reward += reward
                avg_controller_rew += calculate_controller_reward(state, subgoal, new_state, ctrl_rew_scale)

                state = new_state

        avg_reward /= eval_episodes
        avg_controller_rew /= global_steps
        avg_step_count = global_steps / eval_episodes
        avg_env_finish = goals_achieved / eval_episodes

        print("---------------------------------------")
        print("Evaluation over {} episodes:\nAvg Ctrl Reward: {:.3f}".format(eval_episodes, avg_controller_rew))
        if env_name == "AntGather":
            print("Avg reward: {:.1f}".format(avg_reward))
        else:
            print("Goals achieved: {:.1f}%".format(100*avg_env_finish))
        print("Avg Steps to finish: {:.1f}".format(avg_step_count))
        print("---------------------------------------")

        env.evaluate = False
        return avg_reward, avg_controller_rew, avg_step_count, avg_env_finish, grid

def evaluate_policy_hiro(env, env_name, grid, boss_policy, manager_policy, controller_policy,
                    calculate_controller_reward, ctrl_rew_scale, boss_propose_frequency=50,
                    manager_propose_frequency=10, eval_idx=0, eval_episodes=5):
    print("Starting evaluation number {}...".format(eval_idx))
    env.evaluate = True
    resolution = 24
    g_low = [-4, -4]
    g_high = [20, 20]
    with torch.no_grad():
        avg_reward = 0.
        avg_reward_manager = [0]*len(boss_policy.G)
        avg_controller_rew = 0.
        global_steps = 0
        goals_achieved = 0
        for eval_ep in range(eval_episodes):
            obs = env.reset()
            goal = obs["desired_goal"]
            goal_partition = boss_policy.identify_partition(goal)
            state = obs["observation"]
            start_state = state
            start_partition_idx = boss_policy.identify_partition(state)
            start_partition = np.array(boss_policy.G[start_partition_idx].inf + boss_policy.G[start_partition_idx].sup)
            done = False
            step_count = 0
            env_goals_achieved = 0
            while not done:
                if step_count % boss_propose_frequency == 0:
                    start_partition_idx = boss_policy.identify_partition(state)
                    start_partition = np.array(boss_policy.G[start_partition_idx].inf + boss_policy.G[start_partition_idx].sup)
                    # target_partition_idx = boss_policy.select_partition(start_partition_idx, epsilon=0, goal=goal)
                    # target_partition = np.array(boss_policy.G[target_partition_idx].inf + boss_policy.G[target_partition_idx].sup)
                    target_partition_idx, target_partition_interval = handcrafted_planning(goal, goal_partition, start_partition_idx, boss_policy)
                    target_partition = np.array(target_partition_interval.inf + target_partition_interval.sup)


                if step_count % manager_propose_frequency == 0:
                    # subgoal = manager_policy.sample_goal(state, np.concatenate((target_partition, goal)))
                    subgoal = manager_policy.sample_goal(state, goal)
                    # subgoal = np.clip(subgoal, g_low, g_high)
                    x = max(min(int((subgoal[0] - g_low[0]) / (g_high[0] - g_low[0]) * resolution),resolution),0)
                    y = max(min(int((subgoal[1] - g_low[1]) / (g_high[1] - g_low[1]) * resolution),resolution),0)
                    grid[y, x] += 1
                step_count += 1
                global_steps += 1
                action = controller_policy.select_action(state, subgoal, evaluation=True)
                new_obs, reward, done, _ = env.step(action)
                if env_name != "AntGather" and env.success_fn(reward):
                    env_goals_achieved += 1
                    goals_achieved += 1
                    done = True

                goal = new_obs["desired_goal"]
                new_state = new_obs["observation"]

                subgoal = controller_policy.subgoal_transition(state, subgoal, new_state)

                avg_reward += reward
                avg_controller_rew += calculate_controller_reward(state, subgoal, new_state, ctrl_rew_scale)

                state = new_state

        avg_reward /= eval_episodes
        avg_controller_rew /= global_steps
        avg_step_count = global_steps / eval_episodes
        avg_env_finish = goals_achieved / eval_episodes

        print("---------------------------------------")
        print("Evaluation over {} episodes:\nAvg Ctrl Reward: {:.3f}".format(eval_episodes, avg_controller_rew))
        if env_name == "AntGather":
            print("Avg reward: {:.1f}".format(avg_reward))
        else:
            print("Goals achieved: {:.1f}%".format(100*avg_env_finish))
        print("Avg Steps to finish: {:.1f}".format(avg_step_count))
        print("---------------------------------------")

        env.evaluate = False
        return avg_reward, avg_controller_rew, avg_step_count, avg_env_finish, grid

def get_reward_function(dims, absolute_goal=False, binary_reward=False):
    if absolute_goal and binary_reward:
        def controller_reward(z, subgoal, next_z, scale):
            z = z[:dims]
            next_z = next_z[:dims]
            reward = float(np.linalg.norm(subgoal - next_z, axis=-1) <= 1.414) * scale
            return reward
    elif absolute_goal:
        def controller_reward(z, subgoal, next_z, scale):
            z = z[:dims]
            next_z = next_z[:dims]
            reward = -np.linalg.norm(subgoal - next_z, axis=-1) * scale
            return reward
    elif binary_reward:
        def controller_reward(z, subgoal, next_z, scale):
            z = z[:dims]
            next_z = next_z[:dims]
            reward = float(np.linalg.norm(z + subgoal - next_z, axis=-1) <= 1.414) * scale
            return reward
    elif type(dims) == list:
        def controller_reward(z, subgoal, next_z, scale):
            z = z[dims]
            next_z = next_z[dims]
            reward = -np.linalg.norm(z + subgoal - next_z, axis=-1) * scale
            return reward
    else:
        def controller_reward(z, subgoal, next_z, scale):
            z = z[:dims]
            next_z = next_z[:dims]
            reward = -np.linalg.norm(z + subgoal - next_z, axis=-1) * scale
            return reward

    return controller_reward

def get_manager_reward(subgoal, target_partition):
    partition_center = np.array([(target_partition.inf[0] + target_partition.sup[0]) / 2,
                        (target_partition.inf[1] + target_partition.sup[1]) / 2])
    reward = -np.sum(np.square(subgoal[:2] - partition_center)) ** 0.5

    return reward

def update_amat_and_train_anet(n_states, adj_mat, state_list, state_dict, a_net, traj_buffer,
        optimizer_r, controller_goal_dim, device, args, episode_num, state_dims=None):
    for traj in traj_buffer.get_trajectory():
        for i in range(len(traj)):
            for j in range(1, min(args.manager_propose_freq, len(traj) - i)):
                if state_dims:
                    s1 = tuple(np.round(traj[i][state_dims]).astype(np.int32))
                    s2 = tuple(np.round(traj[i+j][state_dims]).astype(np.int32))
                else:
                    s1 = tuple(np.round(traj[i][:controller_goal_dim]).astype(np.int32))
                    s2 = tuple(np.round(traj[i+j][:controller_goal_dim]).astype(np.int32))
                if s1 not in state_list:
                    state_list.append(s1)
                    state_dict[s1] = n_states
                    n_states += 1
                if s2 not in state_list:
                    state_list.append(s2)
                    state_dict[s2] = n_states
                    n_states += 1
                adj_mat[state_dict[s1], state_dict[s2]] = 1
                adj_mat[state_dict[s2], state_dict[s1]] = 1
    print("Explored states: {}".format(n_states))
    flags = np.ones((30, 30))
    for s in state_list:
        flags[int(s[0]), int(s[1])] = 0
    print(flags)
    if not args.load_adj_net:
        print("Training adjacency network...")
        utils.train_adj_net(a_net, state_list, adj_mat[:n_states, :n_states],
                            optimizer_r, args.r_margin_pos, args.r_margin_neg,
                            n_epochs=args.r_training_epochs, batch_size=args.r_batch_size,
                            device=device, verbose=False)

        if args.save_models:
            r_filename = os.path.join("./models", "{}_{}_a_network.pth".format(args.env_name, args.algo))
            torch.save(a_net.state_dict(), r_filename)
            print("----- Adjacency network {} saved. -----".format(episode_num))

    traj_buffer.reset()

    return n_states

def handcrafted_planning(goal, goal_partition_idx, start_partition_idx, boss_policy):
    if goal_partition_idx < start_partition_idx:
        target_partition_idx = start_partition_idx - 1
        target_partition = boss_policy.G[target_partition_idx]
    elif goal_partition_idx > start_partition_idx:
        target_partition_idx = start_partition_idx + 1
        target_partition = boss_policy.G[target_partition_idx]
    else:
        target_partition = utils.ndInterval(2, inf=[goal[0]-1, goal[1]-1], sup=[goal[0]+1, goal[1]+1])
        target_partition_idx = goal_partition_idx
    
    return target_partition_idx, target_partition

def run_hrac(args):
    start_algo = time.time()
    if not os.path.exists("./results"):
        os.makedirs("./results")
    if not os.path.exists("./time"):
        os.makedirs("./time")
    if args.save_models and not os.path.exists("./models"):
        os.makedirs("./models")
    if not os.path.exists(args.log_dir):
        os.makedirs(args.log_dir)
    if not os.path.exists(os.path.join(args.log_dir, args.algo)):
        os.makedirs(os.path.join(args.log_dir, args.algo))
    output_dir = os.path.join(args.log_dir, args.algo)
    print("Logging in {}".format(output_dir))

    if args.env_name == "AntGather":
        env = GatherEnv(create_gather_env(args.env_name, args.seed), args.env_name)
        env.seed(args.seed)   
    elif args.env_name in ["AntMaze", "AntMazeSparse", "AntPush", "AntFall", "AntMazeCam", "PointMaze", "AntMazeStochastic"]:
        env = EnvWithGoal(create_maze_env(args.env_name, args.seed), args.env_name)
        env.seed(args.seed)
    else:
        raise NotImplementedError

    if args.env_name in ["AntMaze", "PointMaze", "AntMazeStochastic"]:
        state_dims = None
    elif args.env_name in ["AntMazeCam"]:
        state_dims = [0,1,3,4,5]
    elif args.env_name in ["AntFall"]:    
        state_dims = [0,1,2]
    else:
        state_dims = None

    if state_dims:
        low = np.array((-10, -10, -0.5, -1, -1, -1, -1,
                -0.5, -0.3, -0.5, -0.3, -0.5, -0.3, -0.5, -0.3,-5,-5,-5,
                -8,-8,-7,-8,-7,-8,-9,-8,-9,-8,-7,0.0000))
    else:
        low = np.array((-10, -10, -0.5, -1, -1, -1, -1,
                    -0.5, -0.3, -0.5, -0.3, -0.5, -0.3, -0.5, -0.3))
    
    
    max_action = float(env.action_space.high[0])
    policy_noise = 0.2
    noise_clip = 0.5
    high = -low
    man_scale = (high - low) / 2
    if state_dims:
        new_man_scale = man_scale[state_dims]   
    else:
        new_man_scale = man_scale 

    if state_dims:
        controller_goal_dim = len(state_dims)
    elif args.env_name == "AntFall":
        controller_goal_dim = 3
    else:
        controller_goal_dim = 2
        
    if args.absolute_goal:
        man_scale[0] = 30
        man_scale[1] = 30
        no_xy = False
    else:
        no_xy = True
    action_dim = env.action_space.shape[0]

    obs = env.reset()

    goal = obs["desired_goal"]
    state = obs["observation"]

    writer = SummaryWriter(log_dir=os.path.join(args.log_dir, args.algo))
    torch.cuda.set_device(args.gid)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    file_name = "{}_{}_{}_{}".format(args.env_name, args.algo, args.exp, args.seed)
    output_data = {"frames": [], "reward": [], "dist": []}    

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    state_dim = state.shape[0]
    if args.env_name in ["AntMaze", "AntPush", "AntFall", "AntMazeCam", "PointMaze"]:
        goal_dim = goal.shape[0]
    else:
        goal_dim = 0

    states_l = state
    states_u = state
    
    controller_policy = agents.Controller(
        state_dim=state_dim,
        goal_dim=controller_goal_dim,
        action_dim=action_dim,
        max_action=max_action,
        actor_lr=args.ctrl_act_lr,
        critic_lr=args.ctrl_crit_lr,
        no_xy=no_xy,
        absolute_goal=args.absolute_goal,
        policy_noise=policy_noise,
        noise_clip=noise_clip
    )

    manager_policy = agents.Manager(
        state_dim=state_dim,
        goal_dim=goal_dim,
        action_dim=controller_goal_dim,
        actor_lr=args.man_act_lr,
        critic_lr=args.man_crit_lr,
        candidate_goals=args.candidate_goals,
        correction=not args.no_correction,
        scale=new_man_scale,
        goal_loss_coeff=args.goal_loss_coeff,
        absolute_goal=args.absolute_goal
    )

    if state_dims:
        calculate_controller_reward = get_reward_function(
            state_dims, absolute_goal=args.absolute_goal, binary_reward=args.binary_int_reward)
    else:
        calculate_controller_reward = get_reward_function(
            controller_goal_dim, absolute_goal=args.absolute_goal, binary_reward=args.binary_int_reward)

    if args.noise_type == "ou":
        man_noise = utils.OUNoise(state_dim, sigma=args.man_noise_sigma)
        ctrl_noise = utils.OUNoise(action_dim, sigma=args.ctrl_noise_sigma)

    elif args.noise_type == "normal":
        man_noise = utils.NormalNoise(sigma=args.man_noise_sigma)
        ctrl_noise = utils.NormalNoise(sigma=args.ctrl_noise_sigma)

    manager_buffer = utils.ReplayBuffer(maxsize=args.man_buffer_size)
    controller_buffer = utils.ReplayBuffer(maxsize=args.ctrl_buffer_size)

    # Initialize adjacency matrix and adjacency network
    n_states = 0
    state_list = []
    state_dict = {}
    adj_mat = np.diag(np.ones(1500, dtype=np.uint8))
    # adj_mat = np.diag(np.ones(5000, dtype=np.uint8))
    traj_buffer = utils.TrajectoryBuffer(capacity=args.traj_buffer_size)
    a_net = ANet(controller_goal_dim, args.r_hidden_dim, args.r_embedding_dim)
    if args.load_adj_net:
        print("Loading adjacency network...")
        a_net.load_state_dict(torch.load("./models/a_network.pth"))
    a_net.to(device)
    optimizer_r = optim.Adam(a_net.parameters(), lr=args.lr_r)

    if args.load:
        try:
            manager_policy.load("./models")
            controller_policy.load("./models")
            print("Loaded successfully.")
            just_loaded = True
        except Exception as e:
            just_loaded = False
            print(e, "Loading failed.")
    else:
        just_loaded = False

    # Logging Parameters
    total_timesteps = 0
    timesteps_since_eval = 0
    timesteps_since_manager = 0
    episode_timesteps = 0
    timesteps_since_subgoal = 0
    episode_num = 0
    done = True
    evaluations = []
    compute_time = {'reach_time':[], 'algo_time':[], 'percentage':[]}
    duration = 0

    # Train
    while total_timesteps < args.max_timesteps:
        if done:
            if total_timesteps != 0 and not just_loaded:
                if episode_num % 10 == 0:
                    print("Episode {}".format(episode_num))
                # Train controller
                ctrl_act_loss, ctrl_crit_loss = controller_policy.train(controller_buffer, episode_timesteps,
                    batch_size=args.ctrl_batch_size, discount=args.ctrl_discount, tau=args.ctrl_soft_sync_rate)
                if episode_num % 10 == 0:
                    print("Controller actor loss: {:.3f}".format(ctrl_act_loss))
                    print("Controller critic loss: {:.3f}".format(ctrl_crit_loss))
                writer.add_scalar("data/controller_actor_loss", ctrl_act_loss, total_timesteps)
                writer.add_scalar("data/controller_critic_loss", ctrl_crit_loss, total_timesteps)

                writer.add_scalar("data/controller_ep_rew", episode_reward, total_timesteps)
                writer.add_scalar("data/manager_ep_rew", manager_transition[4], total_timesteps)

                # Train manager
                if timesteps_since_manager >= args.train_manager_freq:
                    timesteps_since_manager = 0
                    r_margin = (args.r_margin_pos + args.r_margin_neg) / 2

                    man_act_loss, man_crit_loss, man_goal_loss = manager_policy.train(controller_policy,
                        manager_buffer, ceil(episode_timesteps/args.train_manager_freq),
                        batch_size=args.man_batch_size, discount=args.man_discount, tau=args.man_soft_sync_rate,
                        a_net=a_net, r_margin=r_margin)
                    
                    writer.add_scalar("data/manager_actor_loss", man_act_loss, total_timesteps)
                    writer.add_scalar("data/manager_critic_loss", man_crit_loss, total_timesteps)
                    writer.add_scalar("data/manager_goal_loss", man_goal_loss, total_timesteps)

                    if episode_num % 10 == 0:
                        print("Manager actor loss: {:.3f}".format(man_act_loss))
                        print("Manager critic loss: {:.3f}".format(man_crit_loss))
                        print("Manager goal loss: {:.3f}".format(man_goal_loss))

                # Evaluate
                if timesteps_since_eval >= args.eval_freq:
                    timesteps_since_eval = 0
                    start_eval = time.time()
                    avg_ep_rew, avg_controller_rew, avg_steps, avg_env_finish =\
                        evaluate_policy(env, args.env_name, manager_policy, controller_policy,
                            calculate_controller_reward, args.ctrl_rew_scale, args.manager_propose_freq,
                            len(evaluations))
                    end_eval = time.time()
                    duration_eval = end_eval - start_eval

                    writer.add_scalar("eval/avg_ep_rew", avg_ep_rew, total_timesteps)
                    writer.add_scalar("eval/avg_controller_rew", avg_controller_rew, total_timesteps)

                    evaluations.append([avg_ep_rew, avg_controller_rew, avg_steps])
                    output_data["frames"].append(total_timesteps)
                    if args.env_name == "AntGather":
                        output_data["reward"].append(avg_ep_rew)
                    else:
                        output_data["reward"].append(avg_env_finish)
                        writer.add_scalar("eval/avg_steps_to_finish", avg_steps, total_timesteps)
                        writer.add_scalar("eval/perc_env_goal_achieved", avg_env_finish, total_timesteps)
                    output_data["dist"].append(-avg_controller_rew)

                    if args.save_models:
                        controller_policy.save("./models", args.env_name, args.algo)
                        manager_policy.save("./models", args.env_name, args.algo)

                if traj_buffer.full():
                    start = time.time()
                    n_states = update_amat_and_train_anet(n_states, adj_mat, state_list, state_dict, a_net, traj_buffer,
                        optimizer_r, controller_goal_dim, device, args, episode_num, state_dims)
                    end = time.time()
                    end_algo = end
                    duration += end - start
                    duration_algo = (end_algo - start_algo) - duration_eval
                    compute_time['reach_time'].append(duration)
                    compute_time['algo_time'].append(duration_algo)
                    compute_time['percentage'].append(duration / duration_algo)
                    time_df = pd.DataFrame(compute_time)
                    time_df.to_csv(os.path.join("./time", file_name+".csv"), float_format="%.4f", index=False)

                if len(manager_transition[-2]) != 1:                    
                    manager_transition[1] = state
                    manager_transition[5] = float(True)
                    manager_buffer.add(manager_transition)

            obs = env.reset()
            goal = obs["desired_goal"]
            state = obs["observation"]
            traj_buffer.create_new_trajectory()
            traj_buffer.append(state)
            done = False
            episode_reward = 0
            episode_timesteps = 0
            just_loaded = False
            episode_num += 1

            subgoal = manager_policy.sample_goal(state, goal)
            
            if not args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[state_dims], max_action=man_scale[state_dims])
            elif not args.absolute_goal and not state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[:controller_goal_dim], max_action=man_scale[:controller_goal_dim])
            elif args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[state_dims])
            else: 
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[:controller_goal_dim])

            timesteps_since_subgoal = 0
            manager_transition = [state, None, goal, subgoal, 0, False, [state], []]

        action = controller_policy.select_action(state, subgoal)
        action = ctrl_noise.perturb_action(action, -max_action, max_action)
        action_copy = action.copy()

        next_tup, manager_reward, done, _ = env.step(action_copy)

        manager_transition[4] += manager_reward * args.man_rew_scale
        manager_transition[-1].append(action)

        next_goal = next_tup["desired_goal"]
        next_state = next_tup["observation"]

        manager_transition[-2].append(next_state)
        traj_buffer.append(next_state)

        controller_reward = calculate_controller_reward(state, subgoal, next_state, args.ctrl_rew_scale)
        subgoal = controller_policy.subgoal_transition(state, subgoal, next_state)

        controller_goal = subgoal
        episode_reward += controller_reward

        if args.inner_dones:
            ctrl_done = done or timesteps_since_subgoal % args.manager_propose_freq == 0
        else:
            ctrl_done = done

        controller_buffer.add(
            (state, next_state, controller_goal, action, controller_reward, float(ctrl_done), [], []))
        
        state = next_state
        goal = next_goal

        episode_timesteps += 1
        total_timesteps += 1
        timesteps_since_eval += 1
        timesteps_since_manager += 1
        timesteps_since_subgoal += 1

        states_l = np.min((state, states_l), axis=0)
        states_u = np.max((state, states_u), axis=0)

        if timesteps_since_subgoal % args.manager_propose_freq == 0:
            manager_transition[1] = state
            manager_transition[5] = float(done)

            manager_buffer.add(manager_transition)
            subgoal = manager_policy.sample_goal(state, goal)

            if not args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[state_dims], max_action=man_scale[state_dims])
            elif not args.absolute_goal and not state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[:controller_goal_dim], max_action=man_scale[:controller_goal_dim])
            elif args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[state_dims])
            else: 
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[:controller_goal_dim])

            timesteps_since_subgoal = 0
            manager_transition = [state, None, goal, subgoal, 0, False, [state], []]

    # Final evaluation
    start_eval = time.time()
    avg_ep_rew, avg_controller_rew, avg_steps, avg_env_finish = evaluate_policy(
        env, args.env_name, manager_policy, controller_policy, calculate_controller_reward,
        args.ctrl_rew_scale, args.manager_propose_freq, len(evaluations))
    end_eval = time.time()
    duration_eval = end_eval - start_eval

    evaluations.append([avg_ep_rew, avg_controller_rew, avg_steps])
    output_data["frames"].append(total_timesteps)
    if args.env_name == 'AntGather':
        output_data["reward"].append(avg_ep_rew)
    else:
        output_data["reward"].append(avg_env_finish)
    output_data["dist"].append(-avg_controller_rew)

    if args.save_models:
        controller_policy.save("./models", args.env_name, args.algo)
        manager_policy.save("./models", args.env_name, args.algo)

    writer.close()

    end_algo = end
    duration += end - start
    duration_algo = (end_algo - start_algo) - duration_eval
    compute_time['reach_time'].append(duration)
    compute_time['algo_time'].append(duration_algo)
    compute_time['percentage'].append(duration / duration_algo)
    time_df = pd.DataFrame(compute_time)
    time_df.to_csv(os.path.join("./time", file_name+".csv"), float_format="%.4f", index=False)

    output_df = pd.DataFrame(output_data)
    output_df.to_csv(os.path.join("./results", file_name+".csv"), float_format="%.4f", index=False)
    # l_bound = pd.DataFrame(states_l)
    # l_bound.to_csv(os.path.join("./results", "states_l"+".csv"), float_format="%.4f", index=False)
    # u_bound = pd.DataFrame(states_u)
    # u_bound.to_csv(os.path.join("./results", "states_u"+".csv"), float_format="%.4f", index=False)
    print("Training finished.")

def run_star(args):
    start_algo = time.time()
    # system_prompt = "In this task, You are a navigation assistant, helping agent to reach the goal. Based on the data, determine the most appropriate region for the agent to explore next, avoiding obstacles."
    
    
    # 配置日志
    logging.basicConfig(filename=f'logging_{args.env_name}_{args.algo}_LLAMA3.log',  # 日志文件名
                        filemode='a',  # 'a' 为追加模式（默认），'w' 为覆盖模式
                        level=logging.INFO,  # 日志级别
                        format='%(asctime)s - %(levelname)s - %(message)s')  # 日志格式
    if not os.path.exists("./results"):
        os.makedirs("./results")
    if args.save_models and not os.path.exists("./models"):
        os.makedirs("./models")
    if not os.path.exists("./time"):
        os.makedirs("./time")
    if not os.path.exists(args.log_dir):
        os.makedirs(args.log_dir)
    if not os.path.exists(os.path.join(args.log_dir, args.algo)):
        os.makedirs(os.path.join(args.log_dir, args.algo))
    output_dir = os.path.join(args.log_dir, args.algo)
    print("Logging in {}".format(output_dir))

    if args.env_name == "AntGather":
        env = GatherEnv(create_gather_env(args.env_name, args.seed), args.env_name)
        env.seed(args.seed)   
    elif args.env_name in ["AntMaze", "AntMazeSparse", "AntPush", "AntFall", "AntMazeCam", "PointMaze", "AntMazeStochastic", "2Rooms", "2RoomsCam", "3Rooms", "4Rooms"]:
        env = EnvWithGoal(create_maze_env(args.env_name, args.seed), args.env_name)
        env.seed(args.seed)
    else:
        raise NotImplementedError

    if args.env_name in ["AntMaze", "AntMazeStochastic", "2Rooms", "3Rooms", "4Rooms"]:
        state_dims = None
    elif args.env_name in ["AntMazeCam", "2RoomsCam"]:
        state_dims = [0,1,3,4,5]
    elif args.env_name in ["AntFall"]:    
        state_dims = [0,1,2]
    else:
        state_dims = None
    if state_dims:
        low = np.array((-10, -10, -0.5, -1, -1, -1, -1,
                -0.5, -0.3, -0.5, -0.3, -0.5, -0.3, -0.5, -0.3,-5,-5,-5,
                -8,-8,-7,-8,-7,-8,-9,-8,-9,-8,-7,0.0000))
    else:
        low = np.array((-10, -10, -0.5, -1, -1, -1, -1,
                    -0.5, -0.3, -0.5, -0.3, -0.5, -0.3, -0.5, -0.3))
        
    max_action = float(env.action_space.high[0])
    policy_noise = 0.2
    noise_clip = 0.5
    high = -low

    man_scale = (high - low) / 2
    if state_dims:
        new_man_scale = man_scale[state_dims]   
    else:
        new_man_scale = man_scale 

    epsilon = args.boss_eps
    
    if state_dims:
        controller_goal_dim = len(state_dims)
    elif args.env_name == "AntFall":
        controller_goal_dim = 3
    else:
        controller_goal_dim = 2

    if args.absolute_goal:
        man_scale[0] = 30
        man_scale[1] = 30
        no_xy = False
    else:
        no_xy = True
    action_dim = env.action_space.shape[0]

    obs = env.reset()

    goal = obs["desired_goal"]
    state = obs["observation"]

    writer = SummaryWriter(log_dir=os.path.join(args.log_dir, args.algo))
    torch.cuda.set_device(args.gid)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    file_name = "{}_{}_{}_{}".format(args.env_name, args.algo, args.exp, args.seed)
    output_data = {"frames": [], "reward": [], "dist": []}    

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    state_dim = state.shape[0]
    if args.env_name in ["AntMaze", "AntPush", "AntFall", "AntMazeCam", "2RoomsCam", "AntMazeStochastic", "2Rooms", "3Rooms", "4Rooms", "PointMaze"] and not state_dims:
        goal_dim = goal.shape[0]
        goal_cond = True
    elif args.env_name in ["AntMaze", "AntPush", "AntFall", "AntMazeCam", "2RoomsCam", "AntMazeStochastic", "2Rooms", "3Rooms", "4Rooms", "PointMaze"] and state_dims:
        goal_dim = len(state_dims)
        goal_cond = True
    elif state_dims:
        goal_dim = len(state_dims)
        goal_cond = True
    else:
        goal_dim = args.boss_region_dim
        goal_cond = False

    g_low = [0, 0]
    g_high = [20, 20]
    
    if args.env_name in ["AntMaze", "AntMazeCam", "2RoomsCam", "AntMazeStochastic", "2Rooms", "3Rooms", "4Rooms", "PointMaze"] and state_dims:
        G_init = [utils.ndInterval(goal_dim, inf=[0,0]+list(low[state_dims[2:]]), sup=[8,8]+list(high[state_dims[2:]])),
                utils.ndInterval(goal_dim, inf=[8,0]+list(low[state_dims[2:]]), sup=[20,8]+list(high[state_dims[2:]])),
                utils.ndInterval(goal_dim, inf=[8,8]+list(low[state_dims[2:]]), sup=[20,20]+list(high[state_dims[2:]])),
                utils.ndInterval(goal_dim, inf=[0,8]+list(low[state_dims[2:]]), sup=[8,20]+list(high[state_dims[2:]]))
                ]
    elif args.env_name in ["AntMaze", "AntMazeCam", "2RoomsCam", "AntMazeStochastic", "2Rooms", "3Rooms", "4Rooms", "PointMaze"] and not state_dims:
        G_init = [utils.ndInterval(goal_dim, inf=[0,0], sup=[8,8]),
                utils.ndInterval(goal_dim, inf=[8,0], sup=[20,8]),
                utils.ndInterval(goal_dim, inf=[8,8], sup=[20,20]),
                utils.ndInterval(goal_dim, inf=[0,8], sup=[8,20])
                ]
    elif args.env_name in ["AntPush"]:
        G_init = [utils.ndInterval(goal_dim, inf=[-8,0], sup=[20,8]),
                utils.ndInterval(goal_dim, inf=[-8,0], sup=[20,8]),
                utils.ndInterval(goal_dim, inf=[8,8], sup=[20,16]),
                utils.ndInterval(goal_dim, inf=[0,8], sup=[8,16]),
                utils.ndInterval(goal_dim, inf=[0,16], sup=[8,20]),
                ]
        
    elif args.env_name in ["AntFall"] and state_dims:
        G_init = [utils.ndInterval(goal_dim, inf=[-8,0,0], sup=[4,16,5]),
                utils.ndInterval(goal_dim, inf=[4,0,0], sup=[16,16,5]),
                utils.ndInterval(goal_dim, inf=[-8,16,0], sup=[4,32,5]),
                utils.ndInterval(goal_dim, inf=[4,16,0], sup=[16,32,5])
                ]
        
    resolution = 50
    grid = np.zeros((resolution, resolution))
    # Choose mode
    if args.env_name in ["AntMaze", "AntPush", "AntFall", "AntMazeCam", "2Rooms", "3Rooms", "4Rooms", "PointMaze"]:
        mode = "deterministic"
    elif args.env_name in ["AntMazeStochastic"]:
        mode = "stochastic"

    boss_policy = agents.Boss(
        G_init=G_init,
        state_dim=state_dim,
        goal_dim=goal_dim,
        policy=args.boss_policy,
        reachability_algorithm=args.reach_algo,
        goal_cond=goal_cond,
        mem_capacity=args.boss_batch_size,
        mode=mode)
    
    controller_policy = agents.Controller(
        state_dim=state_dim,
        goal_dim=controller_goal_dim,
        action_dim=action_dim,
        max_action=max_action,
        actor_lr=args.ctrl_act_lr,
        critic_lr=args.ctrl_crit_lr,
        no_xy=no_xy,
        absolute_goal=args.absolute_goal,
        policy_noise=policy_noise,
        noise_clip=noise_clip
    )

    manager_policy = agents.Manager(
        state_dim=state_dim,
        goal_dim=2*goal_dim,
        action_dim=controller_goal_dim,
        actor_lr=args.man_act_lr,
        critic_lr=args.man_crit_lr,
        candidate_goals=args.candidate_goals,
        correction=not args.no_correction,
        scale=new_man_scale,
        goal_loss_coeff=args.goal_loss_coeff,
        absolute_goal=args.absolute_goal,
        partitions=True
    )

    if state_dims:
        calculate_controller_reward = get_reward_function(
            state_dims, absolute_goal=args.absolute_goal, binary_reward=args.binary_int_reward)
    else:
        calculate_controller_reward = get_reward_function(
            controller_goal_dim, absolute_goal=args.absolute_goal, binary_reward=args.binary_int_reward)
        
    if args.noise_type == "ou":
        man_noise = utils.OUNoise(state_dim, sigma=args.man_noise_sigma)
        ctrl_noise = utils.OUNoise(action_dim, sigma=args.ctrl_noise_sigma)

    elif args.noise_type == "normal":
        man_noise = utils.NormalNoise(sigma=args.man_noise_sigma)
        ctrl_noise = utils.NormalNoise(sigma=args.ctrl_noise_sigma)

    boss_buffer = utils.PartitionBuffer(maxsize=args.boss_buffer_size)
    manager_buffer = utils.ReplayBuffer(maxsize=args.man_buffer_size)
    controller_buffer = utils.ReplayBuffer(maxsize=args.ctrl_buffer_size)

    # Initialize forward model
    if args.env_name in ["AntMaze", "AntPush", "AntFall", "AntMazeCam", "2Rooms", "3Rooms", "4Rooms", "PointMaze"]:
        fwd_model = ForwardModel(state_dims, 2*goal_dim, args.fwd_hidden_dim, args.lr_fwd)
    elif args.env_name in ["AntMazeStochastic"]:
        fwd_model = StochasticForwardModel(state_dims, 2*goal_dim, args.fwd_hidden_dim, args.lr_fwd)
    else:
        raise NotImplementedError
    
    if args.load_fwd_model:
        fwd_model.load("./models", args.loaded_env_name, args.algo)
        print("Loaded Forward Model")
    
    
    if args.load:
        try:
            boss_policy.load("./models", args.loaded_env_name, args.algo)
            manager_policy.load("./models", args.loaded_env_name, args.algo)
            controller_policy.load("./models", args.loaded_env_name, args.algo)
            print("Loaded successfully.")
            just_loaded = True
        except Exception as e:
            just_loaded = False
            print(e, "Loading failed.")
    else:
        just_loaded = False

    # Logging Parameters
    total_timesteps = 0
    timesteps_since_eval = 0
    timesteps_since_boss = 0
    timesteps_since_manager = 0
    episode_timesteps = 0
    timesteps_since_partition = 0
    timesteps_since_subgoal = 0
    timesteps_since_map = 0
    episode_num = 0
    done = True
    fwd_errors = defaultdict(lambda: [])
    boss_reward = -100
    compute_time = {'reach_time':[], 'algo_time':[], 'percentage':[]}
    duration = 0
    evaluations = []
    manager_ep_rew = 0
    if not os.path.exists("./results/Regions"):
        os.makedirs("./results/Regions")
    adjacency_list = None
    
    # Train
    while total_timesteps < args.max_timesteps:
        if done:
            if total_timesteps != 0 and not just_loaded:
                if episode_num % 10 == 0:
                    print("Episode {}".format(episode_num))
                # Train controller
                ctrl_act_loss, ctrl_crit_loss = controller_policy.train(controller_buffer, episode_timesteps,
                    batch_size=args.ctrl_batch_size, discount=args.ctrl_discount, tau=args.ctrl_soft_sync_rate)
                # if episode_num % 10 == 0:
                #     print("Controller actor loss: {:.3f}".format(ctrl_act_loss))
                #     print("Controller critic loss: {:.3f}".format(ctrl_crit_loss))
                writer.add_scalar("data/controller_actor_loss", ctrl_act_loss, total_timesteps)
                writer.add_scalar("data/controller_critic_loss", ctrl_crit_loss, total_timesteps)

                writer.add_scalar("data/controller_ep_rew", episode_reward, total_timesteps)
                writer.add_scalar("data/manager_ep_rew", manager_ep_rew, total_timesteps)
                manager_ep_rew = 0

                # Train manager
                if timesteps_since_manager >= args.train_manager_freq:
                    timesteps_since_manager = 0
                    r_margin = (args.r_margin_pos + args.r_margin_neg) / 2

                    man_act_loss, man_crit_loss, man_goal_loss = manager_policy.train(controller_policy,
                        manager_buffer, ceil(episode_timesteps/args.train_manager_freq),
                        batch_size=args.man_batch_size, discount=args.man_discount, tau=args.man_soft_sync_rate,
                        a_net=None, r_margin=r_margin)
                    
                    writer.add_scalar("data/manager_actor_loss", man_act_loss, total_timesteps)
                    writer.add_scalar("data/manager_critic_loss", man_crit_loss, total_timesteps)
                    writer.add_scalar("data/manager_goal_loss", man_goal_loss, total_timesteps)

                    # if episode_num % 10 == 0:
                    #     print("Manager actor loss: {:.3f}".format(man_act_loss))
                    #     print("Manager critic loss: {:.3f}".format(man_crit_loss))
                    #     print("Manager goal loss: {:.3f}".format(man_goal_loss))
                
                # Train Boss
                if timesteps_since_boss >= args.train_boss_freq:
                    timesteps_since_boss = 0
                    if len(boss_buffer) >= args.boss_buffer_min_size:
                        for goal_pair in transition_list:
                            Gs = np.array(boss_policy.G[goal_pair[0]].inf + boss_policy.G[goal_pair[0]].sup)
                            Gt = np.array(boss_policy.G[goal_pair[1]].inf + boss_policy.G[goal_pair[1]].sup)
                            utils.train_forward_model(fwd_model, boss_buffer, Gs, Gt, n_epochs=args.fwd_training_epochs, \
                                                    batch_size=args.fwd_batch_size, device=device, verbose=False) 
                        
                            fwd_errors[(goal_pair[0], goal_pair[1])].append(fwd_model.measure_error(boss_buffer, args.fwd_batch_size, goal_pair[0], goal_pair[1]))
                    
                            if len(fwd_errors[(goal_pair[0], goal_pair[1])]) > 1 and fwd_errors[(goal_pair[0], goal_pair[1])][-1] - fwd_errors[(goal_pair[0], goal_pair[1])][-2] < 0.001:
                                start = time.time()
                                boss_policy.train(fwd_model, goal, [goal_pair], args.boss_buffer_min_size, batch_size=args.boss_batch_size, replay_buffer=boss_buffer, tau1=args.tau1, tau2=args.tau2)
                                end = time.time()
                                end_algo = end
                                duration += end - start
                                if duration > 0.0001:
                                    duration_algo = (end_algo - start_algo) - duration_eval
                                    compute_time['reach_time'].append(duration)
                                    compute_time['algo_time'].append(duration_algo)
                                    compute_time['percentage'].append(duration / duration_algo)
                                    time_df = pd.DataFrame(compute_time)
                                    time_df.to_csv(os.path.join("./time", file_name+".csv"), float_format="%.4f", index=False)

                    writer.add_scalar("data/Boss_nbr_part", len(boss_policy.G), total_timesteps)
                    writer.add_scalar("data/Boss_eps", epsilon, total_timesteps)

                if episode_num % 10 == 0:
                    print("Controller actor loss: {:.3f}".format(ctrl_act_loss))
                    print("Controller critic loss: {:.3f}".format(ctrl_crit_loss))
                    print("Manager actor loss: {:.3f}".format(man_act_loss))
                    print("Manager critic loss: {:.3f}".format(man_crit_loss))
                    print("Manager goal loss: {:.3f}".format(man_goal_loss))
                    print("Boss partitions number : {:.3f}".format(len(boss_policy.G)))
                    print("Boss epsilon: {:.3f}".format(epsilon))

                # Evaluate
                if timesteps_since_eval >= args.eval_freq:
                    timesteps_since_eval = 0
                    start_eval = time.time()
                    avg_ep_rew, avg_controller_rew, avg_steps, avg_env_finish, grid, adjacency_list = evaluate_policy_star(env, args.env_name, goal_dim, grid, boss_policy, manager_policy, controller_policy,
                            calculate_controller_reward, args.ctrl_rew_scale, args.boss_propose_freq, args.manager_propose_freq,
                            len(evaluations), total_timesteps=total_timesteps)
                    end_eval = time.time()
                    duration_eval = end_eval - start_eval

                    writer.add_scalar("eval/avg_ep_rew", avg_ep_rew, total_timesteps)
                    writer.add_scalar("eval/avg_controller_rew", avg_controller_rew, total_timesteps)

                    evaluations.append([avg_ep_rew, avg_controller_rew, avg_steps])
                    output_data["frames"].append(total_timesteps)
                    if args.env_name == "AntGather":
                        output_data["reward"].append(avg_ep_rew)
                    else:
                        output_data["reward"].append(avg_env_finish)
                        writer.add_scalar("eval/avg_steps_to_finish", avg_steps, total_timesteps)
                        writer.add_scalar("eval/perc_env_goal_achieved", avg_env_finish, total_timesteps)
                    output_data["dist"].append(-avg_controller_rew)

                    if args.save_models:
                        fwd_model.save("./models", args.env_name, args.algo)
                        controller_policy.save("./models", args.env_name, args.algo)
                        manager_policy.save("./models", args.env_name, args.algo)
                        boss_policy.save("./models", args.env_name, args.algo)

                # Heatmap
                # if timesteps_since_map >= 5e5:
                    # utils.manager_mapping(grid, g_low, g_high, 'maps/manager_gara_mapping'+ str(total_timesteps / 5e5 ) + '.png' )
                    # grid = np.zeros((resolution, resolution))
                    # boss_policy.save("./partitions", args.env_name , total_timesteps / 5e5 )
                    # timesteps_since_map = 0
                
                if [start_partition_idx, target_partition_idx] not in transition_list:
                    transition_list.append([start_partition_idx, target_partition_idx])
                boss_policy.high_steps[(start_partition_idx, target_partition_idx)] += 1
                boss_buffer.add((start_state, start_partition, state, reached_partition, manager_reward, boss_reward))
                
                if len(manager_transition[-2]) != 1:                    
                    manager_transition[1] = state
                    manager_transition[5] = float(True)
                    manager_buffer.add(manager_transition)

            if total_timesteps > 0:
                boss_policy.policy_update(start_partition_idx, target_partition_idx, reached_partition_idx, boss_reward, done, goal, args.boss_discount_factor, args.boss_alpha)
            
            obs = env.reset()
            goal = obs["desired_goal"]
            if goal_cond:
                goal_partition = boss_policy.identify_goal(goal)
            else:
                goal_partition = None

            transition_list = []
            state = obs["observation"]
            start_state = state
            start_partition_idx = boss_policy.identify_partition(state)
            start_partition = np.array(boss_policy.G[start_partition_idx].inf + boss_policy.G[start_partition_idx].sup)
            prev_start_partition_idx = start_partition_idx
            prev_start_partition = start_partition
            done = False
            episode_reward = 0
            episode_timesteps = 0
            just_loaded = False
            episode_num += 1
            
            # target_partition_idx = boss_policy.select_partition(start_partition_idx, epsilon=0, goal=goal)
            # Here we ask LLM to propose a target partition
            try:
                boss_policy.last_partition_idx = None
                target_partition_idx = boss_policy.select_partition_chat(state, start_partition_idx, goal, logging=logging) - 1
            except Exception as e:
                logging.error(e)
                target_partition_idx = boss_policy.select_partition(start_partition_idx, epsilon=0, goal=goal)
            # logging.info(f"STAR: {target_partition_idx+1}")
            ###
            if target_partition_idx == goal_partition and goal_dim == goal.shape[0]:
                target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[i]-1 for i in range(goal_dim)], sup=[goal[i]+1 for i in range(goal_dim)])
            elif target_partition_idx == goal_partition and goal_dim != goal.shape[0]:
                target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[0]-1, goal[1]-1]+boss_policy.G[goal_partition].inf[2:], sup=[goal[0]+1, goal[1]+1]+boss_policy.G[goal_partition].sup[2:])
            else:
                target_partition_interval = boss_policy.G[target_partition_idx]
            target_partition = np.array(target_partition_interval.inf + target_partition_interval.sup)
            prev_target_partition_idx = target_partition_idx
            prev_target_partition = target_partition

            subgoal = manager_policy.sample_goal(state, target_partition)

            if not args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[state_dims], max_action=man_scale[state_dims])
            elif not args.absolute_goal and not state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[:controller_goal_dim], max_action=man_scale[:controller_goal_dim])
            elif args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[state_dims])
            else: 
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[:controller_goal_dim])

            timesteps_since_subgoal = 0
            manager_transition = [state, None, target_partition, subgoal, 0, False, [state], []]

        action = controller_policy.select_action(state, subgoal)
        action = ctrl_noise.perturb_action(action, -max_action, max_action)
        action_copy = action.copy()

        next_tup, ext_reward, done, _ = env.step(action_copy)

        next_goal = next_tup["desired_goal"]
        next_state = next_tup["observation"]

        controller_reward = calculate_controller_reward(state, subgoal, next_state, args.ctrl_rew_scale)
        if state_dims:
            manager_reward = 4 * get_manager_reward(next_state[state_dims], target_partition_interval)
        else:    
            manager_reward = 4 * get_manager_reward(next_state[:2], target_partition_interval)
        boss_reward = max(ext_reward, boss_reward)

        reached_partition_idx = boss_policy.identify_partition(state)
        reached_partition = np.array(boss_policy.G[reached_partition_idx].inf + boss_policy.G[reached_partition_idx].sup)
        if transition_list and total_timesteps > args.boss_propose_freq and total_timesteps % args.boss_propose_freq != 0:
            s = controller_buffer.storage[0][-args.boss_propose_freq - 1]
            if reached_partition_idx == prev_target_partition_idx:
                boss_buffer.add((s, prev_start_partition, state, reached_partition, manager_reward, boss_reward))
                boss_policy.high_steps[(prev_start_partition_idx, reached_partition_idx)] += 1

        manager_transition[4] += manager_reward * args.man_rew_scale
        manager_transition[-1].append(action)

        manager_transition[-2].append(next_state)

        subgoal = controller_policy.subgoal_transition(state, subgoal, next_state)

        controller_goal = subgoal
        episode_reward += controller_reward

        if args.inner_dones: 
            ctrl_done = done or timesteps_since_subgoal % args.manager_propose_freq == 0
        else:
            ctrl_done = done

        controller_buffer.add(
            (state, next_state, controller_goal, action, controller_reward, float(ctrl_done), [], []))

        state = next_state
        goal = next_goal

        episode_timesteps += 1
        total_timesteps += 1
        timesteps_since_eval += 1
        timesteps_since_boss += 1
        timesteps_since_partition += 1
        timesteps_since_manager += 1
        timesteps_since_subgoal += 1
        timesteps_since_map += 1

        if timesteps_since_partition % args.boss_propose_freq == 0:
            boss_policy.policy_update(start_partition_idx, target_partition_idx, reached_partition_idx, boss_reward, done, goal, args.boss_discount_factor, args.boss_alpha)
            prev_start_partition_idx = start_partition_idx
            prev_start_partition = start_partition
            prev_target_partition_idx = target_partition_idx  
            prev_target_partition = target_partition
            epsilon *= args.boss_eps_decay
            epsilon = max(epsilon, args.boss_eps_min)
            boss_buffer.add((start_state, start_partition, state, reached_partition, manager_reward, boss_reward))
            start_state = state
            start_partition_idx = boss_policy.identify_partition(state)
            start_partition = np.array(boss_policy.G[start_partition_idx].inf + boss_policy.G[start_partition_idx].sup)
            
            # target_partition_idx = boss_policy.select_partition(start_partition_idx, epsilon, goal)
            # Here we ask LLM to propose a target partition
            try:
                target_partition_idx = boss_policy.select_partition_chat(state, start_partition_idx, goal, logging=logging) - 1
            except Exception as e:
                logging.error(e)
                target_partition_idx = boss_policy.select_partition(start_partition_idx, epsilon=0, goal=goal)
                
            if target_partition_idx == goal_partition and goal_dim == goal.shape[0]:
                target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[i]-1 for i in range(goal_dim)], sup=[goal[i]+1 for i in range(goal_dim)])
            elif target_partition_idx == goal_partition and goal_dim != goal.shape[0]:
                target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[0]-1, goal[1]-1]+boss_policy.G[goal_partition].inf[2:], sup=[goal[0]+1, goal[1]+1]+boss_policy.G[goal_partition].sup[2:])
            else:
                target_partition_interval = boss_policy.G[target_partition_idx]
            target_partition = np.array(target_partition_interval.inf + target_partition_interval.sup)

            timesteps_since_partition = 0
            if [start_partition_idx, target_partition_idx] not in transition_list:
                transition_list.append([start_partition_idx, target_partition_idx]) 
            boss_policy.high_steps[(start_partition_idx, target_partition_idx)] += 1   
            boss_reward = -100
        if timesteps_since_subgoal % args.manager_propose_freq == 0:
            manager_transition[1] = state
            manager_transition[5] = float(done)        
            
            manager_buffer.add(manager_transition)
            subgoal = manager_policy.sample_goal(state, target_partition)

            if not args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[state_dims], max_action=man_scale[state_dims])
            elif not args.absolute_goal and not state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[:controller_goal_dim], max_action=man_scale[:controller_goal_dim])
            elif args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[state_dims])
            else: 
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[:controller_goal_dim])

            manager_ep_rew = manager_transition[4]
            timesteps_since_subgoal = 0
            manager_transition = [state, None, target_partition, subgoal, 0, False, [state], []]
    
    # Final evaluation
    start_eval = time.time()
    avg_ep_rew, avg_controller_rew, avg_steps, avg_env_finish, grid, adjacency_list = evaluate_policy_star(
        env, args.env_name, goal_dim, grid, boss_policy, manager_policy, controller_policy, calculate_controller_reward,
        args.ctrl_rew_scale, args.boss_propose_freq, args.manager_propose_freq, len(evaluations))
    end_eval = time.time()
    duration_eval = end_eval - start_eval

    utils.manager_mapping(grid, g_low, g_high, 'manager_gara_mapping.png')
    evaluations.append([avg_ep_rew, avg_controller_rew, avg_steps])
    output_data["frames"].append(total_timesteps)
    if args.env_name == 'AntGather':
        output_data["reward"].append(avg_ep_rew)
    else:
        output_data["reward"].append(avg_env_finish)
    output_data["dist"].append(-avg_controller_rew)

    if args.save_models:
        fwd_model.save("./models", args.env_name, args.algo)
        controller_policy.save("./models", args.env_name, args.algo)
        manager_policy.save("./models", args.env_name, args.algo)
        boss_policy.save("./models", args.env_name, args.algo)

    writer.close()
    # duration_algo = (end_algo - start_algo) - duration_eval
    # compute_time['reach_time'].append(duration)
    # compute_time['algo_time'].append(duration_algo)
    # compute_time['percentage'].append(duration / duration_algo)
    time_df = pd.DataFrame(compute_time)
    time_df.to_csv(os.path.join("./time", file_name+".csv"), float_format="%.4f", index=False)

    output_df = pd.DataFrame(output_data)
    output_df.to_csv(os.path.join("./results", file_name+".csv"), float_format="%.4f", index=False)
    print("Training finished.")

def run_hiro(args):
    start_algo = time.time()
    if not os.path.exists("./results"):
        os.makedirs("./results")
    if args.save_models and not os.path.exists("./models"):
        os.makedirs("./models")
    if not os.path.exists("./time"):
        os.makedirs("./time")
    if not os.path.exists(args.log_dir):
        os.makedirs(args.log_dir)
    if not os.path.exists(os.path.join(args.log_dir, args.algo)):
        os.makedirs(os.path.join(args.log_dir, args.algo))
    output_dir = os.path.join(args.log_dir, args.algo)
    print("Logging in {}".format(output_dir))

    if args.env_name == "AntGather":
        env = GatherEnv(create_gather_env(args.env_name, args.seed), args.env_name)
        env.seed(args.seed)   
    elif args.env_name in ["AntMaze", "AntMazeSparse", "AntPush", "AntFall", "AntMazeCam", "PointMaze", "AntMazeStochastic"]:
        env = EnvWithGoal(create_maze_env(args.env_name, args.seed), args.env_name)
        env.seed(args.seed)
    else:
        raise NotImplementedError

    if args.env_name in ["AntMaze", "PointMaze", "AntMazeStochastic"]:
        state_dims = None
    elif args.env_name in ["AntMazeCam"]:
        state_dims = [0,1,3,4,5]
    elif args.env_name in ["AntFall"]:    
        state_dims = [0,1,2]
    else:
        state_dims = None
    if state_dims:
        low = np.array((-10, -10, -0.5, -1, -1, -1, -1,
                -0.5, -0.3, -0.5, -0.3, -0.5, -0.3, -0.5, -0.3,-5,-5,-5,
                -8,-8,-7,-8,-7,-8,-9,-8,-9,-8,-7,0.0000))
    else:
        low = np.array((-10, -10, -0.5, -1, -1, -1, -1,
                    -0.5, -0.3, -0.5, -0.3, -0.5, -0.3, -0.5, -0.3))
    
    
    max_action = float(env.action_space.high[0])
    policy_noise = 0.2
    noise_clip = 0.5
    high = -low
    man_scale = (high - low) / 2
    if state_dims:
        new_man_scale = man_scale[state_dims]   
    else:
        new_man_scale = man_scale 

    if state_dims:
        controller_goal_dim = len(state_dims)
    elif args.env_name == "AntFall":
        controller_goal_dim = 3
    else:
        controller_goal_dim = 2
        
    if args.absolute_goal:
        man_scale[0] = 30
        man_scale[1] = 30
        no_xy = False
    else:
        no_xy = True
    action_dim = env.action_space.shape[0]

    obs = env.reset()

    goal = obs["desired_goal"]
    state = obs["observation"]

    writer = SummaryWriter(log_dir=os.path.join(args.log_dir, args.algo))
    torch.cuda.set_device(args.gid)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    file_name = "{}_{}_{}_{}".format(args.env_name, args.algo, args.exp, args.seed)
    output_data = {"frames": [], "reward": [], "dist": []}    

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    state_dim = state.shape[0]
    if args.env_name in ["AntMaze", "AntPush", "AntFall", "AntMazeCam", "PointMaze"]:
        goal_dim = goal.shape[0]
    else:
        goal_dim = 0

    states_l = state
    states_u = state
    
    controller_policy = agents.Controller(
        state_dim=state_dim,
        goal_dim=controller_goal_dim,
        action_dim=action_dim,
        max_action=max_action,
        actor_lr=args.ctrl_act_lr,
        critic_lr=args.ctrl_crit_lr,
        no_xy=no_xy,
        absolute_goal=args.absolute_goal,
        policy_noise=policy_noise,
        noise_clip=noise_clip
    )

    manager_policy = agents.Manager(
        state_dim=state_dim,
        goal_dim=goal_dim,
        action_dim=controller_goal_dim,
        actor_lr=args.man_act_lr,
        critic_lr=args.man_crit_lr,
        candidate_goals=args.candidate_goals,
        correction=not args.no_correction,
        scale=new_man_scale,
        goal_loss_coeff=args.goal_loss_coeff,
        absolute_goal=args.absolute_goal
    )

    if state_dims:
        calculate_controller_reward = get_reward_function(
            state_dims, absolute_goal=args.absolute_goal, binary_reward=args.binary_int_reward)
    else:
        calculate_controller_reward = get_reward_function(
            controller_goal_dim, absolute_goal=args.absolute_goal, binary_reward=args.binary_int_reward)

    if args.noise_type == "ou":
        man_noise = utils.OUNoise(state_dim, sigma=args.man_noise_sigma)
        ctrl_noise = utils.OUNoise(action_dim, sigma=args.ctrl_noise_sigma)

    elif args.noise_type == "normal":
        man_noise = utils.NormalNoise(sigma=args.man_noise_sigma)
        ctrl_noise = utils.NormalNoise(sigma=args.ctrl_noise_sigma)

    manager_buffer = utils.ReplayBuffer(maxsize=args.man_buffer_size)
    controller_buffer = utils.ReplayBuffer(maxsize=args.ctrl_buffer_size)

    # Initialize adjacency matrix and adjacency network
    n_states = 0
    state_list = []
    state_dict = {}
    adj_mat = np.diag(np.ones(1500, dtype=np.uint8))
    traj_buffer = utils.TrajectoryBuffer(capacity=args.traj_buffer_size)
    a_net = ANet(controller_goal_dim, args.r_hidden_dim, args.r_embedding_dim)
    if args.load_adj_net:
        print("Loading adjacency network...")
        a_net.load_state_dict(torch.load("./models/a_network.pth"))
    a_net.to(device)
    optimizer_r = optim.Adam(a_net.parameters(), lr=args.lr_r)

    if args.load:
        try:
            manager_policy.load("./models")
            controller_policy.load("./models")
            print("Loaded successfully.")
            just_loaded = True
        except Exception as e:
            just_loaded = False
            print(e, "Loading failed.")
    else:
        just_loaded = False

    # Logging Parameters
    total_timesteps = 0
    timesteps_since_eval = 0
    timesteps_since_manager = 0
    episode_timesteps = 0
    timesteps_since_subgoal = 0
    episode_num = 0
    done = True
    evaluations = []
    compute_time = {'algo_time':[]}
    duration = 0
    
    # Train
    while total_timesteps < args.max_timesteps:
        if done:
            if total_timesteps != 0 and not just_loaded:
                if episode_num % 10 == 0:
                    print("Episode {}".format(episode_num))
                # Train controller
                ctrl_act_loss, ctrl_crit_loss = controller_policy.train(controller_buffer, episode_timesteps,
                    batch_size=args.ctrl_batch_size, discount=args.ctrl_discount, tau=args.ctrl_soft_sync_rate)
                if episode_num % 10 == 0:
                    print("Controller actor loss: {:.3f}".format(ctrl_act_loss))
                    print("Controller critic loss: {:.3f}".format(ctrl_crit_loss))
                writer.add_scalar("data/controller_actor_loss", ctrl_act_loss, total_timesteps)
                writer.add_scalar("data/controller_critic_loss", ctrl_crit_loss, total_timesteps)

                writer.add_scalar("data/controller_ep_rew", episode_reward, total_timesteps)
                writer.add_scalar("data/manager_ep_rew", manager_transition[4], total_timesteps)

                # Train manager
                if timesteps_since_manager >= args.train_manager_freq:
                    timesteps_since_manager = 0
                    r_margin = (args.r_margin_pos + args.r_margin_neg) / 2

                    man_act_loss, man_crit_loss, man_goal_loss = manager_policy.train(controller_policy,
                        manager_buffer, ceil(episode_timesteps/args.train_manager_freq),
                        batch_size=args.man_batch_size, discount=args.man_discount, tau=args.man_soft_sync_rate,
                        a_net=a_net, r_margin=r_margin)
                    
                    writer.add_scalar("data/manager_actor_loss", man_act_loss, total_timesteps)
                    writer.add_scalar("data/manager_critic_loss", man_crit_loss, total_timesteps)
                    writer.add_scalar("data/manager_goal_loss", man_goal_loss, total_timesteps)

                    if episode_num % 10 == 0:
                        print("Manager actor loss: {:.3f}".format(man_act_loss))
                        print("Manager critic loss: {:.3f}".format(man_crit_loss))
                        print("Manager goal loss: {:.3f}".format(man_goal_loss))

                # Evaluate
                if timesteps_since_eval >= args.eval_freq:
                    timesteps_since_eval = 0
                    start_eval = time.time()
                    avg_ep_rew, avg_controller_rew, avg_steps, avg_env_finish =\
                        evaluate_policy(env, args.env_name, manager_policy, controller_policy,
                            calculate_controller_reward, args.ctrl_rew_scale, args.manager_propose_freq,
                            len(evaluations))
                    end_eval = time.time()
                    end_algo = time.time()
                    duration_eval = end_eval - start_eval
                    duration_algo = (end_algo - start_algo) - duration_eval
                    compute_time['algo_time'].append(duration_algo)
                    time_df = pd.DataFrame(compute_time)
                    time_df.to_csv(os.path.join("./time", file_name+".csv"), float_format="%.4f", index=False)

                    writer.add_scalar("eval/avg_ep_rew", avg_ep_rew, total_timesteps)
                    writer.add_scalar("eval/avg_controller_rew", avg_controller_rew, total_timesteps)

                    evaluations.append([avg_ep_rew, avg_controller_rew, avg_steps])
                    output_data["frames"].append(total_timesteps)
                    if args.env_name == "AntGather":
                        output_data["reward"].append(avg_ep_rew)
                    else:
                        output_data["reward"].append(avg_env_finish)
                        writer.add_scalar("eval/avg_steps_to_finish", avg_steps, total_timesteps)
                        writer.add_scalar("eval/perc_env_goal_achieved", avg_env_finish, total_timesteps)
                    output_data["dist"].append(-avg_controller_rew)

                    if args.save_models:
                        controller_policy.save("./models", args.env_name, args.algo)
                        manager_policy.save("./models", args.env_name, args.algo)

                if len(manager_transition[-2]) != 1:                    
                    manager_transition[1] = state
                    manager_transition[5] = float(True)
                    manager_buffer.add(manager_transition)

            obs = env.reset()
            goal = obs["desired_goal"]
            state = obs["observation"]
            traj_buffer.create_new_trajectory()
            traj_buffer.append(state)
            done = False
            episode_reward = 0
            episode_timesteps = 0
            just_loaded = False
            episode_num += 1

            subgoal = manager_policy.sample_goal(state, goal)
            
            if not args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[state_dims], max_action=man_scale[state_dims])
            elif not args.absolute_goal and not state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[:controller_goal_dim], max_action=man_scale[:controller_goal_dim])
            elif args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[state_dims])
            else: 
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[:controller_goal_dim])

            timesteps_since_subgoal = 0
            manager_transition = [state, None, goal, subgoal, 0, False, [state], []]

        action = controller_policy.select_action(state, subgoal)
        action = ctrl_noise.perturb_action(action, -max_action, max_action)
        action_copy = action.copy()

        next_tup, manager_reward, done, _ = env.step(action_copy)

        manager_transition[4] += manager_reward * args.man_rew_scale
        manager_transition[-1].append(action)

        next_goal = next_tup["desired_goal"]
        next_state = next_tup["observation"]

        manager_transition[-2].append(next_state)
        traj_buffer.append(next_state)

        controller_reward = calculate_controller_reward(state, subgoal, next_state, args.ctrl_rew_scale)
        subgoal = controller_policy.subgoal_transition(state, subgoal, next_state)

        controller_goal = subgoal
        episode_reward += controller_reward

        if args.inner_dones:
            ctrl_done = done or timesteps_since_subgoal % args.manager_propose_freq == 0
        else:
            ctrl_done = done

        controller_buffer.add(
            (state, next_state, controller_goal, action, controller_reward, float(ctrl_done), [], []))
        
        state = next_state
        goal = next_goal

        episode_timesteps += 1
        total_timesteps += 1
        timesteps_since_eval += 1
        timesteps_since_manager += 1
        timesteps_since_subgoal += 1

        states_l = np.min((state, states_l), axis=0)
        states_u = np.max((state, states_u), axis=0)

        if timesteps_since_subgoal % args.manager_propose_freq == 0:
            manager_transition[1] = state
            manager_transition[5] = float(done)

            manager_buffer.add(manager_transition)
            subgoal = manager_policy.sample_goal(state, goal)

            if not args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[state_dims], max_action=man_scale[state_dims])
            elif not args.absolute_goal and not state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[:controller_goal_dim], max_action=man_scale[:controller_goal_dim])
            elif args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[state_dims])
            else: 
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[:controller_goal_dim])

            timesteps_since_subgoal = 0
            manager_transition = [state, None, goal, subgoal, 0, False, [state], []]

    # Final evaluation
    start_eval = time.time()
    avg_ep_rew, avg_controller_rew, avg_steps, avg_env_finish = evaluate_policy(
        env, args.env_name, manager_policy, controller_policy, calculate_controller_reward,
        args.ctrl_rew_scale, args.manager_propose_freq, len(evaluations))
    end_eval = time.time()
    duration_eval = end_eval - start_eval

    evaluations.append([avg_ep_rew, avg_controller_rew, avg_steps])
    output_data["frames"].append(total_timesteps)
    if args.env_name == 'AntGather':
        output_data["reward"].append(avg_ep_rew)
    else:
        output_data["reward"].append(avg_env_finish)
    output_data["dist"].append(-avg_controller_rew)

    if args.save_models:
        controller_policy.save("./models", args.env_name, args.algo)
        manager_policy.save("./models", args.env_name, args.algo)

    writer.close()

    end_algo = time.time()
    duration_algo = (end_algo - start_algo) - duration_eval
    compute_time['algo_time'].append(duration_algo)
    time_df = pd.DataFrame(compute_time)
    time_df.to_csv(os.path.join("./time", file_name+".csv"), float_format="%.4f", index=False)

    output_df = pd.DataFrame(output_data)
    output_df.to_csv(os.path.join("./results", file_name+".csv"), float_format="%.4f", index=False)
    l_bound = pd.DataFrame(states_l)
    l_bound.to_csv(os.path.join("./results", "states_l"+".csv"), float_format="%.4f", index=False)
    u_bound = pd.DataFrame(states_u)
    u_bound.to_csv(os.path.join("./results", "states_u"+".csv"), float_format="%.4f", index=False)
    print("Training finished.")

def run_gara(args):
    start_algo = time.time()
    if not os.path.exists("./results"):
        os.makedirs("./results")
    if args.save_models and not os.path.exists("./models"):
        os.makedirs("./models")
    if not os.path.exists("./time"):
        os.makedirs("./time")
    if not os.path.exists(args.log_dir):
        os.makedirs(args.log_dir)
    if not os.path.exists(os.path.join(args.log_dir, args.algo)):
        os.makedirs(os.path.join(args.log_dir, args.algo))
    output_dir = os.path.join(args.log_dir, args.algo)
    print("Logging in {}".format(output_dir))

    if args.env_name == "AntGather":
        env = GatherEnv(create_gather_env(args.env_name, args.seed), args.env_name)
        env.seed(args.seed)   
    elif args.env_name in ["AntMaze", "AntMazeSparse", "AntPush", "AntFall", "AntMazeCam", "PointMaze", "AntMazeStochastic"]:
        env = EnvWithGoal(create_maze_env(args.env_name, args.seed), args.env_name)
        env.seed(args.seed)
    else:
        raise NotImplementedError

    if args.env_name in ["AntMaze", "AntMazeStochastic"]:
        state_dims = None
    elif args.env_name in ["AntMazeCam"]:
        state_dims = [0,1,3,4,5]
    elif args.env_name in ["AntFall"]:    
        state_dims = [0,1,2]
    else:
        state_dims = None
    if state_dims:
        low = np.array((-10, -10, -0.5, -1, -1, -1, -1,
                -0.5, -0.3, -0.5, -0.3, -0.5, -0.3, -0.5, -0.3,-5,-5,-5,
                -8,-8,-7,-8,-7,-8,-9,-8,-9,-8,-7,0.0000))
    else:
        low = np.array((-10, -10, -0.5, -1, -1, -1, -1,
                    -0.5, -0.3, -0.5, -0.3, -0.5, -0.3, -0.5, -0.3))
        
    max_action = float(env.action_space.high[0])
    policy_noise = 0.2
    noise_clip = 0.5
    high = -low

    man_scale = (high - low) / 2
    if state_dims:
        new_man_scale = man_scale[state_dims]   
    else:
        new_man_scale = man_scale 

    epsilon = args.boss_eps
    
    if state_dims:
        controller_goal_dim = len(state_dims)
    elif args.env_name == "AntFall":
        controller_goal_dim = 3
    else:
        controller_goal_dim = 2

    if args.absolute_goal:
        man_scale[0] = 30
        man_scale[1] = 30
        no_xy = False
    else:
        no_xy = True
    action_dim = env.action_space.shape[0]

    obs = env.reset()

    goal = obs["desired_goal"]
    state = obs["observation"]

    writer = SummaryWriter(log_dir=os.path.join(args.log_dir, args.algo))
    torch.cuda.set_device(args.gid)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    file_name = "{}_{}_{}_{}".format(args.env_name, args.algo, args.exp, args.seed)
    output_data = {"frames": [], "reward": [], "dist": []}    

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    state_dim = state.shape[0]
    if args.env_name in ["AntMaze", "AntPush", "AntFall", "AntMazeCam", "AntMazeStochastic"] and not state_dims:
        goal_dim = goal.shape[0]
        goal_cond = True
    elif args.env_name in ["AntMaze", "AntPush", "AntFall", "AntMazeCam", "AntMazeStochastic"] and state_dims:
        goal_dim = len(state_dims)
        goal_cond = True
    elif state_dims:
        goal_dim = len(state_dims)
        goal_cond = True
    else:
        goal_dim = args.boss_region_dim
        goal_cond = False

    g_low = [0, 0]
    g_high = [20, 20]
    
    if args.env_name in ["AntMaze", "AntMazeCam", "AntMazeStochastic"] and state_dims:
        G_init = [utils.ndInterval(goal_dim, inf=[0,0]+list(low[state_dims[2:]]), sup=[8,8]+list(high[state_dims[2:]])),
                utils.ndInterval(goal_dim, inf=[8,0]+list(low[state_dims[2:]]), sup=[20,8]+list(high[state_dims[2:]])),
                utils.ndInterval(goal_dim, inf=[8,8]+list(low[state_dims[2:]]), sup=[20,20]+list(high[state_dims[2:]])),
                utils.ndInterval(goal_dim, inf=[0,8]+list(low[state_dims[2:]]), sup=[8,20]+list(high[state_dims[2:]]))
                ]
    elif args.env_name in ["AntMaze", "AntMazeCam", "AntMazeStochastic"] and not state_dims:
        G_init = [utils.ndInterval(goal_dim, inf=[0,0], sup=[8,8]),
                utils.ndInterval(goal_dim, inf=[8,0], sup=[20,8]),
                utils.ndInterval(goal_dim, inf=[8,8], sup=[20,20]),
                utils.ndInterval(goal_dim, inf=[0,8], sup=[8,20])
                ]
    elif args.env_name in ["AntPush"]:
        G_init = [utils.ndInterval(goal_dim, inf=[-8,0], sup=[20,8]),
                utils.ndInterval(goal_dim, inf=[-8,0], sup=[20,8]),
                utils.ndInterval(goal_dim, inf=[8,8], sup=[20,16]),
                utils.ndInterval(goal_dim, inf=[0,8], sup=[8,16]),
                utils.ndInterval(goal_dim, inf=[0,16], sup=[8,20]),
                ]
        
    elif args.env_name in ["AntFall"] and state_dims:
        G_init = [utils.ndInterval(goal_dim, inf=[-8,0,0], sup=[4,16,5]),
                utils.ndInterval(goal_dim, inf=[4,0,0], sup=[16,16,5]),
                utils.ndInterval(goal_dim, inf=[-8,16,0], sup=[4,32,5]),
                utils.ndInterval(goal_dim, inf=[4,16,0], sup=[16,32,5])
                ]
        
    resolution = 50
    grid = np.zeros((resolution, resolution))

    boss_policy = agents.Boss(
        G_init=G_init,
        state_dim=state_dim,
        goal_dim=goal_dim,
        policy=args.boss_policy,
        reachability_algorithm=args.reach_algo,
        goal_cond=goal_cond,
        mem_capacity=args.boss_batch_size)
    
    controller_policy = agents.Controller(
        state_dim=state_dim,
        goal_dim=controller_goal_dim,
        action_dim=action_dim,
        max_action=max_action,
        actor_lr=args.ctrl_act_lr,
        critic_lr=args.ctrl_crit_lr,
        no_xy=no_xy,
        absolute_goal=args.absolute_goal,
        policy_noise=policy_noise,
        noise_clip=noise_clip
    )

    if state_dims:
        calculate_controller_reward = get_reward_function(
            state_dims, absolute_goal=args.absolute_goal, binary_reward=args.binary_int_reward)
    else:
        calculate_controller_reward = get_reward_function(
            controller_goal_dim, absolute_goal=args.absolute_goal, binary_reward=args.binary_int_reward)
        
    if args.noise_type == "ou":
        man_noise = utils.OUNoise(state_dim, sigma=args.man_noise_sigma)
        ctrl_noise = utils.OUNoise(action_dim, sigma=args.ctrl_noise_sigma)

    elif args.noise_type == "normal":
        man_noise = utils.NormalNoise(sigma=args.man_noise_sigma)
        ctrl_noise = utils.NormalNoise(sigma=args.ctrl_noise_sigma)

    boss_buffer = utils.PartitionBuffer(maxsize=args.boss_buffer_size)
    manager_buffer = utils.ReplayBuffer(maxsize=args.man_buffer_size)
    controller_buffer = utils.ReplayBuffer(maxsize=args.ctrl_buffer_size)

    # Initialize forward model
    fwd_model = ForwardModel(state_dim, 2*goal_dim, args.fwd_hidden_dim, args.lr_fwd)
    if args.load_fwd_model:
        fwd_model.load("./models", args.env_name, args.algo)
        print("Loaded Forward Model")
    
    if args.load:
        try:
            boss_policy.load("./models")
            controller_policy.load("./models")
            print("Loaded successfully.")
            just_loaded = True
        except Exception as e:
            just_loaded = False
            print(e, "Loading failed.")
    else:
        just_loaded = False

    # Logging Parameters
    total_timesteps = 0
    timesteps_since_eval = 0
    timesteps_since_boss = 0
    timesteps_since_manager = 0
    episode_timesteps = 0
    timesteps_since_partition = 0
    timesteps_since_subgoal = 0
    timesteps_since_map = 0
    episode_num = 0
    done = True
    fwd_errors = defaultdict(lambda: [])
    boss_reward = -100
    compute_time = {'reach_time':[], 'algo_time':[], 'percentage':[]}
    duration = 0
    evaluations = []

    # Train
    while total_timesteps < args.max_timesteps:
        if done:
            if total_timesteps != 0 and not just_loaded:
                if episode_num % 10 == 0:
                    print("Episode {}".format(episode_num))
                # Train controller
                ctrl_act_loss, ctrl_crit_loss = controller_policy.train(controller_buffer, episode_timesteps,
                    batch_size=args.ctrl_batch_size, discount=args.ctrl_discount, tau=args.ctrl_soft_sync_rate)
                if episode_num % 10 == 0:
                    print("Controller actor loss: {:.3f}".format(ctrl_act_loss))
                    print("Controller critic loss: {:.3f}".format(ctrl_crit_loss))
                writer.add_scalar("data/controller_actor_loss", ctrl_act_loss, total_timesteps)
                writer.add_scalar("data/controller_critic_loss", ctrl_crit_loss, total_timesteps)

                writer.add_scalar("data/controller_ep_rew", episode_reward, total_timesteps)

                # Train Boss
                if timesteps_since_boss >= args.train_boss_freq:
                    timesteps_since_boss = 0
                    if len(boss_buffer) >= args.boss_buffer_min_size:
                        for goal_pair in transition_list:
                            Gs = np.array(boss_policy.G[goal_pair[0]].inf + boss_policy.G[goal_pair[0]].sup)
                            Gt = np.array(boss_policy.G[goal_pair[1]].inf + boss_policy.G[goal_pair[1]].sup)
                            utils.train_forward_model(fwd_model, boss_buffer, Gs, Gt, n_epochs=args.fwd_training_epochs, \
                                                    batch_size=args.fwd_batch_size, device=device, verbose=False) 
                        
                            fwd_errors[(goal_pair[0], goal_pair[1])].append(fwd_model.measure_error(boss_buffer, args.fwd_batch_size, goal_pair[0], goal_pair[1]))
                    
                            if len(fwd_errors[(goal_pair[0], goal_pair[1])]) > 1 and fwd_errors[(goal_pair[0], goal_pair[1])][-1] - fwd_errors[(goal_pair[0], goal_pair[1])][-2] < 0.001:
                                start = time.time()
                                boss_policy.train(fwd_model, goal, [goal_pair], args.boss_buffer_min_size, batch_size=args.boss_batch_size, replay_buffer=boss_buffer, tau1=args.tau1, tau2=args.tau2)
                                end = time.time()
                                end_algo = end
                                duration += end - start
                                if duration > 0.0001:
                                    duration_algo = (end_algo - start_algo) - duration_eval
                                    compute_time['reach_time'].append(duration)
                                    compute_time['algo_time'].append(duration_algo)
                                    compute_time['percentage'].append(duration / duration_algo)
                                    time_df = pd.DataFrame(compute_time)
                                    time_df.to_csv(os.path.join("./time", file_name+".csv"), float_format="%.4f", index=False)

                    writer.add_scalar("data/Boss_nbr_part", len(boss_policy.G), total_timesteps)
                    writer.add_scalar("data/Boss_eps", epsilon, total_timesteps)

                    if episode_num % 10 == 0:
                        print("Boss partitions number : {:.3f}".format(len(boss_policy.G)))
                        print("Boss epsilon: {:.3f}".format(epsilon))

                # Evaluate
                if timesteps_since_eval >= args.eval_freq:
                    timesteps_since_eval = 0
                    start_eval = time.time()
                    avg_ep_rew, avg_controller_rew, avg_steps, avg_env_finish, grid = evaluate_policy_gara(env, args.env_name, goal_dim, grid, boss_policy, controller_policy,
                            calculate_controller_reward, args.ctrl_rew_scale, args.boss_propose_freq, len(evaluations))
                    end_eval = time.time()
                    duration_eval = end_eval - start_eval

                    writer.add_scalar("eval/avg_ep_rew", avg_ep_rew, total_timesteps)
                    writer.add_scalar("eval/avg_controller_rew", avg_controller_rew, total_timesteps)

                    evaluations.append([avg_ep_rew, avg_controller_rew, avg_steps])
                    output_data["frames"].append(total_timesteps)
                    if args.env_name == "AntGather":
                        output_data["reward"].append(avg_ep_rew)
                    else:
                        output_data["reward"].append(avg_env_finish)
                        writer.add_scalar("eval/avg_steps_to_finish", avg_steps, total_timesteps)
                        writer.add_scalar("eval/perc_env_goal_achieved", avg_env_finish, total_timesteps)
                    output_data["dist"].append(-avg_controller_rew)

                    if args.save_models:
                        controller_policy.save("./models", args.env_name, args.algo)
                        boss_policy.save("./models", args.env_name, args.algo)
                
                if [start_partition_idx, target_partition_idx] not in transition_list:
                    transition_list.append([start_partition_idx, target_partition_idx])
                boss_policy.high_steps[(start_partition_idx, target_partition_idx)] += 1
                boss_buffer.add((start_state, start_partition, state, reached_partition, controller_reward, boss_reward))
                
            if total_timesteps > 0:
                boss_policy.policy_update(start_partition_idx, target_partition_idx, reached_partition_idx, boss_reward, done, goal, args.boss_discount_factor, args.boss_alpha)
            
            obs = env.reset()
            goal = obs["desired_goal"]
            if goal_cond:
                goal_partition = boss_policy.identify_goal(goal)
            else:
                goal_partition = None

            transition_list = []
            state = obs["observation"]
            start_state = state
            start_partition_idx = boss_policy.identify_partition(state)
            start_partition = np.array(boss_policy.G[start_partition_idx].inf + boss_policy.G[start_partition_idx].sup)
            prev_start_partition_idx = start_partition_idx
            prev_start_partition = start_partition
            done = False
            episode_reward = 0
            episode_timesteps = 0
            just_loaded = False
            episode_num += 1
            
            target_partition_idx = boss_policy.select_partition(start_partition_idx, epsilon=0, goal=goal)
            if target_partition_idx == goal_partition and goal_dim == goal.shape[0]:
                target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[i]-1 for i in range(goal_dim)], sup=[goal[i]+1 for i in range(goal_dim)])
            elif target_partition_idx == goal_partition and goal_dim != goal.shape[0]:
                target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[0]-1, goal[1]-1]+boss_policy.G[goal_partition].inf[2:], sup=[goal[0]+1, goal[1]+1]+boss_policy.G[goal_partition].sup[2:])
            else:
                target_partition_interval = boss_policy.G[target_partition_idx]
            target_partition = np.array(target_partition_interval.inf + target_partition_interval.sup)
            prev_target_partition_idx = target_partition_idx
            prev_target_partition = target_partition

            partition_center = np.array([(target_partition_interval.inf[0] + target_partition_interval.sup[0]) / 2,
                                (target_partition.inf[1] + target_partition.sup[1]) / 2])
            subgoal = partition_center

            if not args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[state_dims], max_action=man_scale[state_dims])
            elif not args.absolute_goal and not state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[:controller_goal_dim], max_action=man_scale[:controller_goal_dim])
            elif args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[state_dims])
            else: 
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[:controller_goal_dim])

            timesteps_since_subgoal = 0

        action = controller_policy.select_action(state, subgoal)
        action = ctrl_noise.perturb_action(action, -max_action, max_action)
        action_copy = action.copy()

        next_tup, ext_reward, done, _ = env.step(action_copy)

        next_goal = next_tup["desired_goal"]
        next_state = next_tup["observation"]

        controller_reward = calculate_controller_reward(state, subgoal, next_state, args.ctrl_rew_scale)
        boss_reward = max(ext_reward, boss_reward)

        reached_partition_idx = boss_policy.identify_partition(state)
        reached_partition = np.array(boss_policy.G[reached_partition_idx].inf + boss_policy.G[reached_partition_idx].sup)
        if transition_list and total_timesteps > args.boss_propose_freq and total_timesteps % args.boss_propose_freq != 0:
            s = controller_buffer.storage[0][-args.boss_propose_freq - 1]
            if reached_partition_idx == prev_target_partition_idx:
                boss_buffer.add((s, prev_start_partition, state, reached_partition, controller_reward, boss_reward))
                boss_policy.high_steps[(prev_start_partition_idx, reached_partition_idx)] += 1
    
        subgoal = controller_policy.subgoal_transition(state, subgoal, next_state)

        controller_goal = subgoal
        episode_reward += controller_reward

        if args.inner_dones: 
            ctrl_done = done or timesteps_since_subgoal % args.manager_propose_freq == 0
        else:
            ctrl_done = done

        controller_buffer.add(
            (state, next_state, controller_goal, action, controller_reward, float(ctrl_done), [], []))

        state = next_state
        goal = next_goal

        episode_timesteps += 1
        total_timesteps += 1
        timesteps_since_eval += 1
        timesteps_since_boss += 1
        timesteps_since_partition += 1
        timesteps_since_subgoal += 1
        timesteps_since_map += 1

        if timesteps_since_partition % args.boss_propose_freq == 0:
            boss_policy.policy_update(start_partition_idx, target_partition_idx, reached_partition_idx, boss_reward, done, goal, args.boss_discount_factor, args.boss_alpha)
            prev_start_partition_idx = start_partition_idx
            prev_start_partition = start_partition
            prev_target_partition_idx = target_partition_idx  
            prev_target_partition = target_partition
            epsilon *= args.boss_eps_decay
            epsilon = max(epsilon, args.boss_eps_min)
            boss_buffer.add((start_state, start_partition, state, reached_partition, controller_reward, boss_reward))
            start_state = state
            start_partition_idx = boss_policy.identify_partition(state)
            start_partition = np.array(boss_policy.G[start_partition_idx].inf + boss_policy.G[start_partition_idx].sup)
            
            target_partition_idx = boss_policy.select_partition(start_partition_idx, epsilon, goal)
            if target_partition_idx == goal_partition and goal_dim == goal.shape[0]:
                target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[i]-1 for i in range(goal_dim)], sup=[goal[i]+1 for i in range(goal_dim)])
            elif target_partition_idx == goal_partition and goal_dim != goal.shape[0]:
                target_partition_interval = utils.ndInterval(goal_dim, inf=[goal[0]-1, goal[1]-1]+boss_policy.G[goal_partition].inf[2:], sup=[goal[0]+1, goal[1]+1]+boss_policy.G[goal_partition].sup[2:])
            else:
                target_partition_interval = boss_policy.G[target_partition_idx]
            target_partition = np.array(target_partition_interval.inf + target_partition_interval.sup)

            if [start_partition_idx, target_partition_idx] not in transition_list:
                transition_list.append([start_partition_idx, target_partition_idx]) 
            boss_policy.high_steps[(start_partition_idx, target_partition_idx)] += 1   
            boss_reward = -100
        
            partition_center = np.array([(target_partition_interval.inf[0] + target_partition_interval.sup[0]) / 2,
                                (target_partition.inf[1] + target_partition.sup[1]) / 2])
            subgoal = partition_center

            if not args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[state_dims], max_action=man_scale[state_dims])
            elif not args.absolute_goal and not state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=-man_scale[:controller_goal_dim], max_action=man_scale[:controller_goal_dim])
            elif args.absolute_goal and state_dims:
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[state_dims])
            else: 
                subgoal = man_noise.perturb_action(subgoal,
                    min_action=np.zeros(controller_goal_dim), max_action=2*man_scale[:controller_goal_dim])
            
            timesteps_since_partition = 0

    # Final evaluation
    start_eval = time.time()
    avg_ep_rew, avg_controller_rew, avg_steps, avg_env_finish, grid = evaluate_policy_gara(
        env, args.env_name, goal_dim, grid, boss_policy, controller_policy, calculate_controller_reward,
        args.ctrl_rew_scale, args.boss_propose_freq, len(evaluations))
    end_eval = time.time()
    duration_eval = end_eval - start_eval

    evaluations.append([avg_ep_rew, avg_controller_rew, avg_steps])
    output_data["frames"].append(total_timesteps)
    if args.env_name == 'AntGather':
        output_data["reward"].append(avg_ep_rew)
    else:
        output_data["reward"].append(avg_env_finish)
    output_data["dist"].append(-avg_controller_rew)

    if args.save_models:
        controller_policy.save("./models", args.env_name, args.algo)
        boss_policy.save("./models", args.env_name, args.algo)

    writer.close()
    duration_algo = (end_algo - start_algo) - duration_eval
    compute_time['reach_time'].append(duration)
    compute_time['algo_time'].append(duration_algo)
    compute_time['percentage'].append(duration / duration_algo)
    time_df = pd.DataFrame(compute_time)
    time_df.to_csv(os.path.join("./time", file_name+".csv"), float_format="%.4f", index=False)

    output_df = pd.DataFrame(output_data)
    output_df.to_csv(os.path.join("./results", file_name+".csv"), float_format="%.4f", index=False)
    print("Training finished.")