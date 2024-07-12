import numpy as np
import argparse
from collections import deque
from gym import spaces
import copy
import envs.create_maze_env

def create_random_point():
    # 定义各个合法区域及其面积
    areas = [
        ((0, 0, 20, 8), 160),               # 左下角矩形
        ((16, 8, 20, 20), 48),         # 右边竖直长条
        ((0, 16, 16, 20), 64)        # 上边横条
    ]
    
    # 计算总面积
    total_area = 272
    
    # 根据面积随机选择一个区域
    r = np.random.uniform(0, total_area)
    cumulative_area = 0
    for ((x1, y1, x2, y2), area) in areas:
        cumulative_area += area
        if r < cumulative_area:
            # 在选择的区域内生成点
            return np.random.uniform((x1, y1), (x2, y2))
        
def get_goal_sample_fn(env_name, evaluate):
    if env_name in ["AntMaze", "PointMaze", "AntMazeStochastic", "2Rooms", "3Rooms", "4Rooms"]:
        if evaluate:
            return lambda: np.array([0., 16.])
        else:
            # return lambda: np.random.uniform((-4, -4), (20, 20))
            # return lambda: np.random.uniform((0, 0), (20, 20))
            return lambda: create_random_point()
    elif env_name == 'AntMazeSparse' or env_name == 'PointMazeSparse':
        return lambda: np.array([2., 9.])
    elif env_name == 'AntPush':
        return lambda: np.array([0., 19.])
    elif env_name == 'AntFall':
        return lambda: np.array([0., 27., 4.5])
    elif env_name in ['AntMazeCam', "2RoomsCam"]:
        if evaluate:
            return lambda: np.array([0., 16.])
        else:
            return lambda: np.random.uniform((-4, -4), (20, 20))
    else:
        assert False, 'Unknown env'


def get_reward_fn(env_name):
    if env_name in ['AntMaze', 'AntPush', 'PointMaze', 'AntMazeStochastic', "2Rooms", "3Rooms", "4Rooms"]:
        return lambda obs, goal: -np.sum(np.square(obs[:2] - goal)) ** 0.5
    elif env_name == 'AntMazeSparse' or env_name == 'PointMazeSparse':
        return lambda obs, goal: float(np.sum(np.square(obs[:2] - goal)) ** 0.5 < 1)
    elif env_name == 'AntFall':
        return lambda obs, goal: -np.sum(np.square(obs[:3] - goal)) ** 0.5
    elif env_name in ['AntMazeCam', "2RoomsCam"]:
        return lambda obs, goal: -np.sum(np.square(obs[:2] - goal)) ** 0.5
    else:
        assert False, 'Unknown env'


def get_success_fn(env_name):
    if env_name in ['AntMaze', 'AntPush', 'AntFall', 'PointMaze', 'AntMazeStochastic', "2Rooms", "3Rooms", "4Rooms"]:
        return lambda reward: reward > -5.0
    elif env_name == 'AntMazeSparse' or env_name == 'PointMazeSparse':
        return lambda reward: reward > 1e-6
    elif env_name in ['AntMazeCam', "2RoomsCam"]:
        return lambda reward: reward > -5.0
    else:
        assert False, 'Unknown env'


class GatherEnv(object):

    def __init__(self, base_env, env_name):
        self.base_env = base_env
        self.env_name = env_name
        self.evaluate = False
        self.count = 0

    def seed(self, seed):
        self.base_env.seed(seed)

    def reset(self):
        obs = self.base_env.reset()
        self.count = 0
        return {
            'observation': obs.copy(),
            'achieved_goal': obs[:2],
            'desired_goal': None,
        }

    def step(self, a):
        obs, reward, done, info = self.base_env.step(a)
        self.count += 1
        next_obs = {
            'observation': obs.copy(),
            'achieved_goal': obs[:2],
            'desired_goal': None,
        }
        return next_obs, reward, done or self.count >= 500, info

    @property
    def action_space(self):
        return self.base_env.action_space


class EnvWithGoal(object):

    def __init__(self, base_env, env_name):
        self.base_env = base_env
        self.env_name = env_name
        self.evaluate = False
        self.reward_fn = get_reward_fn(env_name)
        self.success_fn = get_success_fn(env_name)
        self.goal = None
        self.distance_threshold = 5 if env_name in ['AntMaze', 'AntPush', 'AntFall', 'AntMazeCam', '2RoomsCam', 'MazeStochastic', "2Rooms", "3Rooms", "4Rooms"] else 1
        if env_name in ['AntMazeCam']:
            self.cam = False 
            self.alt_base_env = envs.create_maze_env.create_maze_env('AntMaze', 2)
        if env_name in ['2RoomsCam']:
            self.cam = False 
            self.alt_base_env = envs.create_maze_env.create_maze_env('2Rooms', 2)
        
        self.count = 0
        self.early_stop = False if env_name in ['AntMaze', 'AntPush', 'AntFall', 'AntMazeCam', '2RoomsCam', 'MazeStochastic', 'PointMaze', "2Rooms", "3Rooms", "4Rooms"] else True
        self.early_stop_flag = False
        self.history = []
        self.past = []

    def seed(self, seed):
        self.base_env.seed(seed)

    def reset(self):
        # self.viewer_setup()
        self.history = []
        self.past = []
        self.early_stop_flag = False
        self.goal_sample_fn = get_goal_sample_fn(self.env_name, self.evaluate)
        if self.env_name in ['AntMazeStochastic']:
            self.alt_base_env = envs.create_maze_env.create_maze_env('AntMazeStochastic', 2)
            self.base_env = self.alt_base_env
        
        obs = self.base_env.reset()    
        self.past.append(obs)
        self.count = 0
        self.goal = self.goal_sample_fn()
        self.desired_goal = self.goal if self.env_name in ['AntMaze', 'AntPush', 'AntFall', 'AntMazeCam', '2RoomsCam', 'AntMazeStochastic', 'PointMaze', "2Rooms", "3Rooms", "4Rooms"] else None
        if self.env_name in ['AntMazeCam', '2RoomsCam']:
            self.cam = False 
            self.alt_base_env.reset()
        return {
            'observation': obs.copy(),
            'achieved_goal': obs[:2],
            'desired_goal': self.desired_goal,
        }

    def step(self, a):
        self.history.append(a)
        if self.env_name in ['AntMaze', 'AntPush', 'AntFall', 'AntMazeStochastic', 'PointMaze', "2Rooms", "3Rooms", "4Rooms"]:
            obs, _, done, info = self.base_env.step(a)
            reward = self.reward_fn(obs, self.goal)

        elif self.env_name in ['AntMazeCam', '2RoomsCam']:
            ori = self.base_env.get_ori()
            obs = self.base_env._get_obs()
            if 16 <= obs[0] <= 20 and obs[1] <= 8 and -1 <= ori <= 0 and not self.cam:
                # ant looks at the camera
                self.cam = True
                t = self.base_env.t 
                self.alt_base_env.t = t
                self.alt_base_env.copy_state(obs[:15], obs[15:29])
                obs, _, done, info = self.alt_base_env.step(a)
            elif self.cam:
                obs, _, done, info = self.alt_base_env.step(a)
            else:
                obs, _, done, info = self.base_env.step(a)

            reward = self.reward_fn(obs, self.goal)
        elif self.env_name in ['AntMazeStochastic']:
            obs, _, done, info = self.base_env.step(a)
            reward = self.reward_fn(obs, self.goal)
            # move the block to a new location with a normal probability
            # self.base_env.pi

        if self.early_stop and self.success_fn(reward):
            self.early_stop_flag = True
        self.count += 1
        done = self.early_stop_flag and self.count % 10 == 0
        next_obs = {
            'observation': obs.copy(),
            'achieved_goal': obs[:2],
            'desired_goal': self.desired_goal,
        }
        return next_obs, reward, done or self.count >= 500, info

    def render(self, mode, width, height, camera_name):
        return self.base_env.render(mode=mode, width=width, height=height, camera_name=camera_name)

    @property
    def action_space(self):
        return self.base_env.action_space
