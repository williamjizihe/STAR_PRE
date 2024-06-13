import numpy as np
from matplotlib import pyplot as plt

class Maze:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.maze = np.zeros((height, width), dtype=int)
        self.agent_position = [0, 0]
        self.start = None
        self.goal = None
        self.save = None
    
    def set_walls(self, walls):
        if any([w[0] >= self.height or w[1] >= self.width for w in walls]):
            raise ValueError('Wall coordinates are out of bounds')
        for wall in walls:
            if self.goal is not None and wall == self.goal:
                raise ValueError('Wall cannot be set on the goal')
            self.maze[wall] = 1
    
    def set_agent(self, position):
        self.agent_position[0] = position[0]
        self.agent_position[1] = position[1]
    
    def set_start(self, position):
        if self.maze[position] == 1:
            raise ValueError('Start cannot be set on a wall')
        else:
            self.start = position
            self.agent_position = position
    
    def set_goal(self, position):
        if self.maze[position] == 1:
            raise ValueError('Goal cannot be set on a wall')
        else:
            self.goal = position
    
    def save_maze(self):
        self.save = {'maze': self.maze.copy(), 
                     'agent_position': self.agent_position, 
                     'start': self.start,
                     'goal': self.goal}
        
    def reset(self):
        if self.save is not None:
            self.maze = self.save['maze'].copy()
            self.agent_position = self.save['agent_position']
            self.goal = self.save['goal']
            self.start = self.save['start']
        else:
            raise ValueError('No saved state to reset to')
    
    def move_agent(self, action):
        new_position = self.agent_position
        if action == 'up' and self.agent_position[0] > 0:
            new_position = (self.agent_position[0] - 1, self.agent_position[1])
        elif action == 'down' and self.agent_position[0] < self.height - 1:
            new_position = (self.agent_position[0] + 1, self.agent_position[1])
        elif action == 'left' and self.agent_position[1] > 0:
            new_position = (self.agent_position[0], self.agent_position[1] - 1)
        elif action == 'right' and self.agent_position[1] < self.width - 1:
            new_position = (self.agent_position[0], self.agent_position[1] + 1)
        
        if self.maze[new_position] != 1:  # Check if new position is not a wall
            self.agent_position = new_position
    
    def copy_maze(self):
        maze = Maze(self.width, self.height)
        maze.maze = self.maze.copy()
        maze.agent_position = self.agent_position
        maze.start = self.start
        maze.goal = self.goal
        maze.save = self.save
        return maze
    
    def __str__(self):
        rows = []
        for i in range(self.height):
            row = []
            for j in range(self.width):
                if (i, j) == self.agent_position:
                    row.append('A')
                elif (i, j) == self.goal:
                    row.append('G')
                # elif (i, j) == self.start:
                #     row.append('S ')
                elif self.maze[i, j] == 0:
                    row.append('_')
                elif self.maze[i, j] == 1:
                    row.append('#')
                else:
                    row.append('X')
            rows.append(''.join(row).rstrip())
        return '\n'.join(rows)

    def draw_maze(self, show=False):
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_xlim(-0.5, self.width - 0.5)
        ax.set_ylim(-0.5, self.height - 0.5)
        ax.set_xticks(np.arange(-0.5, self.width, 1))
        ax.set_yticks(np.arange(-0.5, self.height, 1))
        ax.grid(True)

        # Draw walls
        # for (i, j) in zip(*np.where(self.maze == 1)):
        #     ax.add_patch(plt.Rectangle((j - 0.5, self.height - i - 0.5), 1, 1, color='black'))
        # Draw walls
        for (i, j) in zip(*np.where(self.maze == 1)):
            ax.add_patch(plt.Rectangle((j - 0.5, self.height - i - 1.5), 1, 1, color='black'))
        # Draw start and goal
        ax.add_patch(plt.Rectangle((self.start[1] - 0.5, self.height - self.start[0] - 1.5), 1, 1, color='green'))
        ax.add_patch(plt.Rectangle((self.goal[1] - 0.5, self.height - self.goal[0] - 1.5), 1, 1, color='red'))

        # Add coordinates text
        # for i in range(self.height):
        #     for j in range(self.width):
        #         ax.text(j, self.height - i - 1, f'({i},{j})', ha='center', va='center', color='black', fontsize=8)
        if show:
            plt.show()

        plt.draw()
        plt.savefig('maze.png')
        return fig, ax

if __name__ == '__main__':
    # 示例
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
    print(maze)
    
    maze.move_agent('down')
    print(maze)
    
    maze.draw_maze(True)
