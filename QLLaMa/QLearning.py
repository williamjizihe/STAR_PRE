# Copyright (c) Meta Platforms, Inc. and affiliates.
# This software may be used and distributed in accordance with the terms of the Llama 3 Community License Agreement.

import numpy as np
import random
from simpleMaze import Maze
from navigator import Boss
from utils import ndInterval

from llama import ChatGenerator
from tqdm import tqdm
class QLearningAgent:
    def __init__(self, maze, learning_rate=0.1, discount_factor=0.9, epsilon=0.1, chat_gen=None):
        self.maze = maze
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.q_table = np.zeros((*maze.maze.shape, 4))  # 4 actions: up, down, left, right
        self.actions = ['up', 'down', 'left', 'right']
        self.parameters = {'learning_rate': learning_rate, 'discount_factor': discount_factor, 'epsilon': epsilon}
        self.chat_gen = chat_gen
        
    def choose_action(self, state):
        if random.uniform(0, 1) < self.epsilon:
            return random.choice(self.actions)
        else:
            state_actions = self.q_table[state]
            return self.actions[np.argmax(state_actions)]
    
    def learn(self, state, action, reward, next_state):
        action_index = self.actions.index(action)
        predict = self.q_table[state][action_index]
        target = reward + self.discount_factor * np.max(self.q_table[next_state])
        self.q_table[state][action_index] += self.learning_rate * (target - predict)
    
    def train(self, episodes, max_steps, boss):
        for episode in tqdm(range(episodes)):
            state = self.maze.agent_position
            for step in range(max_steps):
                action = self.choose_action(state)
                if episode % 10 == 0 and self.chat_gen is not None:
                    maze_str = str(self.maze)
                    user_prompt = (
                        f"I am at position {state} , the goal is at position {self.maze.goal}.\n"
                        f"Here is the current maze(A: agent, G: goal):\n{maze_str}\n"
                        "Provide your answer in the following format without any additional text: <action>"
                    )
                    response = self.chat_gen(user_prompt)
                    if response in self.actions:
                        action = response
                    else:
                        print(f"Invalid action {response}.")
                
                self.maze.move_agent(action)
                next_state = self.maze.agent_position
                reward = self.get_reward(state, next_state)
                self.learn(state, action, reward, next_state)
                boss.count_visits(state, next_state)
                state = next_state
                if reward == 1:
                    # self.maze.display_maze()
                    self.maze.reset()
                    break
            if episode % 10 == 9:
                success_rate = self.evaluate()
                print(f'Episode: {episode}, Success rate: {success_rate}')
    
    def get_reward(self, state, next_state):
        # Define the reward function
        if next_state == self.maze.goal:
            return 1
        elif state == next_state:
            return -1
        else:
            return -0.01  # small penalty for each step taken

    def save_policy(self, filename):
        np.save(filename, self.q_table)
    
    def load_policy(self, filename):
        self.q_table = np.load(filename)
    
    def test(self):
        maze = self.maze.copy_maze()
        maze.reset()
        max_steps = 100
        step = 0
        state = maze.agent_position
        route = [state]
        while state != maze.goal:
            maze_str = str(maze)
            user_prompt = (
                f"I am at position {state} , the goal is at position {maze.goal}.\n"
                f"Here is the current maze(A: agent, G: goal, #: wall, _: empty space):\n{maze_str}\n"
                "Provide your answer in the following format without any additional text: <action>"
            )
            response = self.chat_gen(user_prompt)
            if response in self.actions:
                action = response
            else:
                raise ValueError(f"Invalid action {response}.")
            maze.move_agent(action)
            state = maze.agent_position
            route.append(state)
            step += 1
            print(maze)
            if step > max_steps:
                break
            if state == maze.goal:
                print(f"Congratulations! You have reached the goal in{step} steps.")
        return route
        
    def evaluate(self, num_evaluation=10):
        maze = self.maze.copy_maze()
        maze.reset()
        success = 0
        self.epsilon = 0
        max_steps = 100
        
        for _ in range(num_evaluation):
            step = 0
            state = maze.agent_position
            while state != maze.goal:
                action = self.choose_action(state)
                maze.move_agent(action)
                state = maze.agent_position
                step += 1
                if step > max_steps:
                    break
            if state == maze.goal:
                success += 1
            maze.reset()
        
        self.epsilon = self.parameters['epsilon']
        return success / num_evaluation
        
if __name__ == '__main__':
    system_prompt = "You are the navigation assistant for an agent. Your task is to select an action in left, right, up, down to avoid the wall and reach the goal."
    chat_gen = ChatGenerator(system_prompt=system_prompt, 
                             max_batch_size=4,
                             max_gen_len=256)
    
    maze = Maze(25, 25)
    # 设置迷宫墙壁
    maze.set_walls([(j, i) for i in range(0, 20) for j in range(8, 16)])
    # 设置迷宫围墙
    maze.set_walls([(0, j) for j in range(25)])
    maze.set_walls([(24, j) for j in range(25)])
    maze.set_walls([(i, 0) for i in range(25)])
    maze.set_walls([(i, 24) for i in range(25)])
    # 设置迷宫起点和终点
    maze.set_start((20, 5))
    maze.set_goal((5, 5))
    
    maze.save_maze()
    
    for _ in range(15):
        maze.move_agent('right')
        
    for _ in range(13):
        maze.move_agent('up')
    print(maze)
    user_prompt = (
        f"Here is the top-down view of the current maze, A represents the agent, G represents the goal, # represents the wall, and 0 represents the empty space.\n{maze}\n"
        # "Based on the maze, what action should the agent take to reach the goal?\n"
        "Based on the maze, plan a route for the agent to reach the goal.\n"
        # "Provide your answer in the following format without any additional text: <action>"
        "Provide your answer in the following format with explanation: <action> <action> <action> ..."
    )
    response = chat_gen(user_prompt)
    print(user_prompt)
    print(response)
    # agent = QLearningAgent(maze, chat_gen=chat_gen)
    # route = agent.test()
    
    # # [2, [0, 0], [8, 8]], [2, [8, 0], [20, 8]], [2, [8, 8], [20, 20]], [2, [0, 8], [8, 20]]
    # boss = Boss([ndInterval(2, [0, 0], [12, 20]), 
    #              ndInterval(2, [12, 0], [25, 20]), 
    #              ndInterval(2, [0, 20], [12, 25]), 
    #              ndInterval(2, [12, 20], [25, 25])])
    # agent.train(episodes=100, max_steps=100, boss=boss)
    # agent.save_policy('q_table.npy')
    
    # # save the visit matrix
    # with open('visit_matrix.txt', 'w') as f:
    #     for i in range(len(boss.visit_matrix)):
    #         f.write(' '.join(map(str, boss.visit_matrix[i])) + '\n')
        
    #     # write regions
    #     for i in range(len(boss.G)):
    #         f.write(str(boss.G[i].inf) + ' ' + str(boss.G[i].sup) + '\n')
    
    # # Test the learned policy
    # maze.reset()
    # testAgent = QLearningAgent(maze, learning_rate=0, discount_factor=0, epsilon=0)
    # testAgent.load_policy('q_table.npy')
    
    # # Save the route
    # route = []
    # state = maze.agent_position
    # route.append(state)
    # step, max_steps = 0, 100
    # while state != maze.goal:
    #     action = testAgent.choose_action(state)
    #     maze.move_agent(action)
    #     state = maze.agent_position
    #     route.append(state)
    #     step += 1
    #     if step > max_steps:
    #         break
    
    # print(maze)
    # # Draw the route
    # import matplotlib.pyplot as plt
    
    # # Draw the maze and route
    # fig, ax = maze.draw_maze()

    # # Draw route
    # route = np.array(route)
    # ax.plot(route[:, 1], maze.height - route[:, 0] - 1, color='blue', marker='o', linestyle='-')

    # plt.savefig('maze_route.png')
    # plt.show()