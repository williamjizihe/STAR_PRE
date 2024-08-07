import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.utils.data as Data
import seaborn as sns
import matplotlib.pyplot as plt

import numpy as np
import copy
from collections import deque
from interval import interval
import json
import networkx as nx
import math

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')



# Multi dimensional intervals class
class ndInterval:
    """
    Class that creates arrays of intervals and extend interval methods across the array.
    """

    def __init__(self, n, inf=[], sup=[]):
        self.n = n
        self.inf = inf
        self.sup = sup
        if inf != [] and sup != []:
            self.interval = [interval[inf[i], sup[i]] for i in range(n)]
        else:
            self.interval = []

    def __contains__(self, item):
        # assert self.n == len(item)
        for i in range(self.n):
            if not item[i] in self.interval[i]:
                return False
        return True

    def dist(self, item):
        dist = 0
        for i in range(self.n):
            dist += abs(self.inf[i] - item[i])
        return dist
    
    def volume(self):
        volume = 1
        for i in range(self.n):
            volume *= self.sup[i] - self.inf[i]

        return volume

    def adjacency(self, B):
        """Checks for adjacent intervals that can be merged"""
        counter = self.n
        dim = -1
        for i in range(self.n):
            if self.inf[i] == B.inf[i] and self.sup[i] == B.sup[i]:
                counter -= 1
            elif self.sup[i] == B.inf[i] or self.inf[i] == B.sup[i]:
                dim = i
        if counter == 1:
            return dim
        else:
            return -1

    def merge(self, B, dim):
        """Merges two interval vectors across an appropriate dimension"""
        C = ndInterval(self.n, [], [])
        for i in range(C.n):
            if i != dim:
                C.sup.append(self.sup[i])
                C.inf.append(self.inf[i])
            else:
                C.sup.append(self.sup[i] * (self.sup[i] >= B.sup[i]) + B.sup[i] * (self.sup[i] < B.sup[i]))
                C.inf.append(self.inf[i] * (self.inf[i] <= B.inf[i]) + B.inf[i] * (self.inf[i] > B.inf[i]))

        C.interval = [interval[C.inf[i], C.sup[i]] for i in range(C.n)]
        return C

    def search_merge(list):
        """Searches for intervals that can be merged together and merges them"""
        change = True
        n = len(list)
        while change and len(list) > 1:
            for A in list:
                for B in list:
                    dim = A.adjacency(B)
                    if dim > -1:
                        C = A.merge(B, dim)
                        change = True
                        list.remove(A)
                        list.remove(B)
                        list.append(C)
                        n = len(list)
                        break
                if A not in list:
                    continue
            if len(list) == n:
                change = False
        
        return list

    def split(self, dims, lows=[], ups=[], split_value=dict()):
        """Splits an interval across a dimension"""
        if not dims:
            return [self]
        if lows == [] or ups == []:
            lows = self.inf
            ups = self.sup
        if dims:
            d = dims[0]
            lows1 = copy.deepcopy(lows)
            ups1 = copy.deepcopy(ups)
            if d not in split_value.keys():
                ups1[d] = lows[d] + ((ups[d] - lows[d]) / 2)
            else:
                ups1[d] = split_value[d]
            partition1 = ndInterval(self.n, inf=lows1, sup=ups1)
            list1 = partition1.split(dims[1:], lows1, ups1)

            lows2 = copy.deepcopy(lows1)
            if d not in split_value.keys():
                lows2[d] = lows[d] + ((ups[d] - lows[d]) / 2)
            else:
                lows2[d] = split_value[d]
            ups2 = copy.deepcopy(ups)
            partition2 = ndInterval(self.n, inf=lows2, sup=ups2)
            list2 = partition2.split(dims[1:], lows2, ups2)

            return list1 + list2

    def complement(self, subinterval):
        """Computes the complement of a sub interval inside the original interval"""
        complement = []
        for v in range(self.n):
            inf1 = copy.copy(self.inf)
            sup1 = copy.copy(self.sup)
            sup1[v] = subinterval.inf[v]
            if sup1[v] > inf1[v]:
                int1 = ndInterval(self.n, inf=inf1, sup=sup1)
                complement.append(int1)

            inf2 = copy.copy(self.inf)
            inf2[v] = subinterval.sup[v]
            sup2 = copy.copy(self.sup)
            if sup2[v] > inf2[v]:
                int2 = ndInterval(self.n, inf=inf2, sup=sup2)
                complement.append(int2)

        ndInterval.search_merge(complement)
        return ndInterval.remove_duplicates(complement)

    def intersection(self, interval):
        intersection_inf = list(np.maximum(self.inf, interval.inf))
        intersection_sup = list(np.minimum(self.sup, interval.sup))

        # Empty intersection
        if max(np.array(intersection_inf) > np.array(intersection_sup)):
            return []
        else:
            return [intersection_inf, intersection_sup]

    def remove_duplicates(interval_list):
        """Takes a list of intervals and eliminates duplicate intersections"""
        for i in range(len(interval_list)):
            partition1 = interval_list[i]
            for j in range(i+1,len(interval_list)):
                partition2 = interval_list[j]
                intersection = partition1.intersection(partition2)
                if intersection:
                    new_inf = []
                    new_sup = []
                    for v in range(partition2.n):
                        if partition2.inf[v] < intersection[0][v]:
                            new_sup += [intersection[0][v]]
                        else:
                            new_sup += [partition2.sup[v]]
                        if partition2.sup[v] > intersection[1][v]:
                            new_inf += [intersection[1][v]]
                        else:
                            new_inf += [partition2.inf[v]]
                    interval_list[j] = ndInterval(partition2.n, new_inf, new_sup)


        return interval_list

# Simple replay buffer
class ReplayBuffer(object):
    def __init__(self, maxsize=1e6):
        self.storage = [[] for _ in range(8)]
        self.maxsize = maxsize
        self.next_idx = 0

    def clear(self):
        self.storage = [[] for _ in range(8)]
        self.next_idx = 0

    # Expects tuples of (x, x', g, u, r, d, x_seq, a_seq)
    def add(self, data):
        self.next_idx = int(self.next_idx)
        if self.next_idx >= len(self.storage[0]):
            [array.append(datapoint) for array, datapoint in zip(self.storage, data)]
        else:
            [array.__setitem__(self.next_idx, datapoint) for array, datapoint in zip(self.storage, data)]

        self.next_idx = (self.next_idx + 1) % self.maxsize

    def sample(self, batch_size):
        if len(self.storage[0]) <= batch_size:
            ind = np.arange(len(self.storage[0]))
        else:
            ind = np.random.randint(0, len(self.storage[0]), size=batch_size)

        x, y, g, u, r, d, x_seq, a_seq = [], [], [], [], [], [], [], []          

        for i in ind: 
            X, Y, G, U, R, D, obs_seq, acts = (array[i] for array in self.storage)
            x.append(np.array(X, copy=False))
            y.append(np.array(Y, copy=False))
            g.append(np.array(G, copy=False))
            u.append(np.array(U, copy=False))
            r.append(np.array(R, copy=False))
            d.append(np.array(D, copy=False))

            # For off-policy goal correction
            x_seq.append(np.array(obs_seq, copy=False))
            a_seq.append(np.array(acts, copy=False))
        
        return np.array(x), np.array(y), np.array(g), \
            np.array(u), np.array(r).reshape(-1, 1), np.array(d).reshape(-1, 1), \
            x_seq, a_seq

    def save(self, file):
        np.savez_compressed(file, idx=np.array([self.next_idx]), x=self.storage[0],
                            y=self.storage[1], g=self.storage[2], u=self.storage[3],
                            r=self.storage[4], d=self.storage[5], xseq=self.storage[6],
                            aseq=self.storage[7])

    def load(self, file):
        with np.load(file) as data:
            self.next_idx = int(data['idx'][0])
            self.storage = [data['x'], data['y'], data['g'], data['u'], data['r'],
                            data['d'], data['xseq'], data['aseq']]
            self.storage = [list(l) for l in self.storage]

    def __len__(self):
        return len(self.storage[0])


class PartitionBuffer:
    def __init__(self, maxsize=1e6):
        self.storage = [[] for _ in range(6)]
        self.maxsize = maxsize
        self.next_idx = 0

    def clear(self):
        self.storage = [[] for _ in range(6)]
        self.next_idx = 0

    # Expects tuples of (x, x', g, u, r, d, x_seq, a_seq)
    def add(self, data):
        self.next_idx = int(self.next_idx)
        if self.next_idx >= len(self.storage[0]):
            [array.append(datapoint) for array, datapoint in zip(self.storage, data)]
        else:
            [array.__setitem__(self.next_idx, datapoint) for array, datapoint in zip(self.storage, data)]

        self.next_idx = (self.next_idx + 1) % self.maxsize

    def sample(self, batch_size):
        if len(self.storage[0]) <= batch_size:
            ind = np.arange(len(self.storage[0]))
        else:
            ind = np.random.randint(0, len(self.storage[0]), size=batch_size)

        x, gs, y, gt, rl, rh = [], [], [], [], [], []

        for i in ind: 
            X, Gs, Y, Gt, Rl, Rh = (array[i] for array in self.storage)
            x.append(np.array(X, copy=False))
            gs.append(np.array(Gs, copy=False))
            y.append(np.array(Y, copy=False))
            gt.append(np.array(Gt, copy=False))
            rl.append(np.array(Rl, copy=False))
            rh.append(np.array(Rh, copy=False))

        return np.array(x), np.array(gs), np.array(y), np.array(gt), \
            np.array(rl).reshape(-1, 1), np.array(rh).reshape(-1, 1)

    def target_sample(self, start_partition, target_partition, batch_size):
        indices = []
        for i in range(len(self.storage[0])):
            if (self.storage[1][i] == start_partition).all() and (self.storage[3][i] == target_partition).all():
                indices.append(i)

        if len(indices) == 0:
            if len(self.storage[0]) <= batch_size:
                ind = np.arange(len(self.storage[0]))
            else:
                ind = np.random.randint(0, len(self.storage[0]), size=batch_size)
        elif len(indices) <= batch_size:
            ind = indices
        else:            
            ind = np.random.choice(indices, size=batch_size)

        x, gs, y, gt, rl, rh = [], [], [], [], [], []

        for i in ind: 
            X, Gs, Y, Gt, Rl, Rh = (array[i] for array in self.storage)
            x.append(np.array(X, copy=False))
            gs.append(np.array(Gs, copy=False))
            y.append(np.array(Y, copy=False))
            gt.append(np.array(Gt, copy=False))
            rl.append(np.array(Rl, copy=False))
            rh.append(np.array(Rh, copy=False))

        return np.array(x), np.array(gs), np.array(y), np.array(gt), \
            np.array(rl).reshape(-1, 1), np.array(rh).reshape(-1, 1)

    def save(self, file):
        np.savez_compressed(file, idx=np.array([self.next_idx]), x=self.storage[0],
                            gs=self.storage[1], y=self.storage[2], gt=self.storage[3],
                            rl=self.storage[4], rh=self.storage[5])

    def load(self, file):
        with np.load(file) as data:
            self.next_idx = int(data['idx'][0])
            self.storage = [data['x'], data['gs'], data['y'], data['gt'], data['rl'],
                            data['rh']]
            self.storage = [list(l) for l in self.storage]

    def __len__(self):
        return len(self.storage[0])


class TrajectoryBuffer(object):

    def __init__(self, capacity):
        self._capacity = capacity
        self.reset()

    def reset(self):
        self._num_traj = 0  # number of trajectories
        self._size = 0    # number of game frames
        self.trajectory = []

    def __len__(self):
        return self._num_traj

    def size(self):
        return self._size

    def get_traj_num(self):
        return self._num_traj

    def full(self):
        return self._size >= self._capacity

    def create_new_trajectory(self):
        self.trajectory.append([])
        self._num_traj += 1

    def append(self, s):
        self.trajectory[self._num_traj-1].append(s)
        self._size += 1

    def get_trajectory(self):
        return self.trajectory

    def set_capacity(self, new_capacity):
        assert self._size <= new_capacity
        self._capacity = new_capacity


class NormalNoise(object):
    def __init__(self, sigma):
        self.sigma = sigma

    def perturb_action(self, action, min_action=-np.inf, max_action=np.inf):
        action = (action + np.random.normal(0, self.sigma,
            size=action.shape)).clip(min_action, max_action)
        return action


class OUNoise(object):
    def __init__(self, action_dim, mu=0, theta=0.15, sigma=0.3):
        self.mu = mu
        self.theta = theta
        self.sigma = sigma
        self.action_dim = action_dim
        self.X = np.ones(self.action_dim) * self.mu

    def reset(self):
        self.X = np.ones(self.action_dim) * self.mu

    def perturb_action(self, action, min_action=-np.inf, max_action=np.inf):
        dx = self.theta * (self.mu - self.X)
        dx = dx + self.sigma * np.random.randn(len(self.X))
        self.X = self.X + dx
        return (self.X + action).clip(min_action, max_action)


def train_forward_model(forward_model, partition_buffer, Gs=None, Gt=None, n_epochs=100, batch_size=64, device='cpu', verbose=False):
    if Gs is not None and Gt is not None:
        x, gs, y, gt, rl, rh = partition_buffer.target_sample(Gs, Gt, batch_size)
    else:        
        x, gs, y, gt, rl, rh = partition_buffer.sample(batch_size)
        
    forward_model.fit(x, gt, y, n_epochs=n_epochs, verbose=verbose)

def train_adj_net(a_net, states, adj_mat, optimizer, margin_pos, margin_neg,
                  n_epochs=100, batch_size=64, device='cpu', verbose=False):
    if verbose:
        print('Generating training data...')
    dataset = MetricDataset(states, adj_mat)
    if verbose:
        print('Totally {} training pairs.'.format(len(dataset)))
    dataloader = Data.DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0, drop_last=False)
    n_batches = len(dataloader)

    loss_func = ContrastiveLoss(margin_pos, margin_neg)

    for i in range(n_epochs):
        epoch_loss = []
        for j, data in enumerate(dataloader):
            x, y, label = data
            x = x.float().to(device)
            y = y.float().to(device)
            label = label.long().to(device)
            x = a_net(x)
            y = a_net(y)
            loss = loss_func(x, y, label)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            if verbose and (j % 50 == 0 or j == n_batches - 1):
                print('Training metric network: epoch {}/{}, batch {}/{}'.format(i+1, n_epochs, j+1, n_batches))

            epoch_loss.append(loss.item())

        if verbose:
            print('Mean loss: {:.4f}'.format(np.mean(epoch_loss)))


class ContrastiveLoss(nn.Module):

    def __init__(self, margin_pos, margin_neg):
        super().__init__()
        assert margin_pos <= margin_neg
        self.margin_pos = margin_pos
        self.margin_neg = margin_neg

    def forward(self, x, y, label):
        # mutually reachable states correspond to label = 1
        dist = torch.sqrt(torch.pow(x - y, 2).sum(dim=1) + 1e-12)
        loss = (label * (dist - self.margin_pos).clamp(min=0)).mean() + ((1 - label) * (self.margin_neg - dist).clamp(min=0)).mean()
        return loss


class MetricDataset(Data.Dataset):

    def __init__(self, states, adj_mat):
        super().__init__()
        n_samples = adj_mat.shape[0]
        self.x = []
        self.y = []
        self.label = []
        for i in range(n_samples - 1):
            for j in range(i + 1, n_samples):
                self.x.append(states[i])
                self.y.append(states[j])
                self.label.append(adj_mat[i, j])
        self.x = np.array(self.x)
        self.y = np.array(self.y)
        self.label = np.array(self.label)

    def __len__(self):
        return self.x.shape[0]

    def __getitem__(self, idx):
        return self.x[idx], self.y[idx], self.label[idx]


class PartitionDataset(Data.Dataset):

    def __init__(self, partition_buffer, batch_size):
        super().__init__()
        n_samples = len(partition_buffer.storage[0])
        self.state = []
        self.target_partition = []
        self.reached_state = []
        x, gs, y, gt, rl, rh = partition_buffer.sample(batch_size)

        self.state = x
        self.target_partition = gt
        self.reached_state = y

    def __len__(self):
        return self.state.shape[0]

    def __getitem__(self, idx):
        return self.state[idx], self.target_partition[idx], self.reached_state[idx]
    

def manager_mapping(grid, g_low, g_high, file, resolution=100):
    """ plots a heatmap of the manager's subgoals and save it to a file """
    ax = sns.heatmap(grid,cmap="viridis", cbar=False)
    ax.invert_yaxis()
    plt.savefig(file)
    plt.close()
    
def generate_user_prompt(state, r1, goal, r2, coordination=None, adjacency_list=None, maze=None, instruction=None):
    prompt = (
        "Data:\n"
        f"State: {state}, Region {r1}\n"
        f"Goal: {goal}, Region {r2}\n"
    )
    
    # if coordination is not None:
    #     prompt += (f"- Coordination Info (each region is described by two diagonal vertices of a rectangle)")
    #     # Append regions
    #     for i, region in enumerate(regions, 1):
    #         prompt += (f"Region {i}: {region}\n")
    
    # if adjacency_list is not None:
    #     prompt += ("- Adjacency list:\n")
    #     for k, v in adjacency_list.items():
    #         # if len(row) == 0:
    #         #     continue
    #         prompt += (f"Region {k+1}: {v}\n")
    if adjacency_list is not None:
        prompt += ("Adjacency list:\n")
        for i, row in adjacency_list.items():
            # if len(row) == 0:
            #     continue
            prompt += (f"Region {i}: {row}\n")
    
    if maze is not None:
        prompt += ("The top-down view of the maze is shown below, W represents walls, A represents the agent's current position, G represents the goal. The number represents the region number:\n")
        prompt += (maze)
    
    prompt += (
        # "\nThinking Process:\n"
        # "1. Identify the agent's current region, identify the goal region\n"
        # "2. Identify where is the wall.\n"
        # "3. Examine the adjacency list to see which regions connect to the current region.\n"
        # "4. Observe the maze to see which other regions are also connected to the current region.\n"
        # "5. From these connected regions, choose the one that moves closest to the goal without hitting walls.\n"
        "\nBased on the analysis, identify the most strategic next region to explore and format your answer as follows: Answer: Region <i>"
    )
    # prompt += ("\nProvide the answer in the following exact format without any additional explanation or text: Region <i>\n")
    return prompt

def generate_antfall_maze_representation(regions, position, has_bridge):
    # Define the fixed size of the maze
    # x: -8 to 16, y: 0 to 32
    goal = (0, 54, 9)
    size = (49, 65, 11)
    offset = (16, 0, 0)  # offset to make all coordinates positive
    
    # Initialize the maze representation with zeros
    maze = np.zeros(size, dtype=int)
    
    # Mark regions with their respective indices
    for i, r in enumerate(regions):
        x1, y1, z1, x2, y2, z2 = int(r[0]*2)+offset[0], int(r[1]*2)+offset[1], int(r[2]*2)+offset[2], \
                                 int(r[3]*2)+offset[0], int(r[4]*2)+offset[1], int(r[5]*2)+offset[2]
        maze[x1:x2+1, y1:y2+1, z1:z2+1] = i + 1

    maze[goal[0]+offset[0], goal[1]+offset[1], :] = 99
    maze[int(position[0]*2)+offset[0], int(position[1]*2)+offset[1], :] = 98
    
    # Pit boundaries
    # Pit = ((-8, 16), (12, 24), (0, 10))
    if not has_bridge:
        maze[-16+offset[0]:32+offset[0]+1, \
            24+offset[1]:48+offset[1]+1, \
            0+offset[2]:10+offset[2]+1] = -1
    
        # Bridge
        # Bridge = (8, 8, (0, 10))
        maze[16+offset[0]:, 16+offset[1], 0+offset[2]:10+offset[2]+1] = 97
    else:
        maze[-16+offset[0]:16+offset[0]+1, \
            24+offset[1]:48+offset[1]+1, \
            0+offset[2]:10+offset[2]+1] = -1
    
    # Compress the maze
    # Column
    col_mask = np.append([True], (np.diff(maze, axis=2) != 0).any(axis=(0, 1)))
    maze = maze[:, :, col_mask]
    
    # Depth
    depth_mask = np.append([True], (np.diff(maze, axis=0) != 0).any(axis=(1, 2)))
    maze = maze[depth_mask]

    # Row
    row_mask = np.append([True], (np.diff(maze, axis=1) != 0).any(axis=(0, 2)))
    maze = maze[:, row_mask]

    
    # Rotate the maze representation by 90 degrees
    maze = np.rot90(maze)
    
    # Generate the maze string using numpy vectorization
    char_maze = np.full(maze.shape, ' ', dtype='<U2')
    char_maze[maze == -1] = 'P'
    char_maze[maze == 98] = 'A'
    char_maze[maze == 99] = 'G'
    char_maze[maze == 97] = 'B'
    char_maze[(maze >= 0) & (maze < 97)] = maze[(maze >= 0) & (maze < 97)].astype(str)
    
    char_maze_list = []
    for i in range(char_maze.shape[2]):
        char_maze_list.append('\n'.join(' '.join(row) for row in char_maze[:, :, i]))
    # Join all characters and form the final string
    return char_maze_list

def generate_maze_representation(regions, goal, position):
    # Define the fixed size of the maze
    size = 49  # from -4 to 20, scaled by 2
    offset = 8  # offset to make all coordinates positive
    
    # Initialize the maze representation with zeros
    maze = np.zeros((size, size), dtype=int)

    # Mark regions with their respective indices
    for i, r in enumerate(regions):
        x1, y1, x2, y2 = int(r[0]*2)+offset, int(r[1]*2)+offset, int(r[2]*2)+offset, int(r[3]*2)+offset
        maze[x1:x2+1, y1:y2+1] = i + 1

    # Define wall boundaries (scaled by 2)
    # wall = ((-8, 16), (32, 32))  # Middle wall
    maze[-8+offset:32+offset+1, 16+offset:32+offset+1] = -1
    
    maze[int(goal[0]*2)+offset, int(goal[1]*2)+offset] = 99
    maze[int(position[0]*2)+offset, int(position[1]*2)+offset] = 98 

    # Compress the maze if required
    row_mask = np.append([True], (np.diff(maze, axis=0) != 0).any(axis=1))
    maze = maze[row_mask]
    col_mask = np.append([True], (np.diff(maze, axis=1) != 0).any(axis=0))
    maze = maze[:, col_mask]
    
    # Rotate the maze representation by 90 degrees
    maze = np.rot90(maze)
    
    # Generate the maze string using numpy vectorization
    char_maze = np.full(maze.shape, ' ', dtype='<U2')
    char_maze[maze == -1] = 'W'
    char_maze[maze == 98] = 'A'
    char_maze[maze == 99] = 'G'
    char_maze[(maze >= 0) & (maze < 98)] = maze[(maze >= 0) & (maze < 98)].astype(str)
    
    # Join all characters and form the final string
    return '\n'.join(' '.join(row) for row in char_maze)

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyEncoder, self).default(obj)

def are_adjacent(region1, region2):
    wx_low, wx_high, wy_low, wy_high = -4, 16, 8, 16

    # 分别提取两个矩形的坐标
    x1_low, x1_high, y1_low, y1_high = region1[0], region1[2], region1[1], region1[3]
    x2_low, x2_high, y2_low, y2_high = region2[0], region2[2], region2[1], region2[3]
 
    # 检查x方向上的相邻情况
    if (x1_high == x2_low or x1_low == x2_high) and ((y1_low <= y2_high and y1_high >= y2_high) or (y1_low <= y2_low and y1_high >= y2_low)):
        x_edge = x1_high if x1_high == x2_low else x1_low
        y_edge_low, y_edge_high = max(y1_low, y2_low), min(y1_high, y2_high)
        # print('x_edge:', x_edge)
        # print('y_edge_low:', y_edge_low, 'y_edge_high:', y_edge_high)
        if y_edge_low == y_edge_high:
            return False
        if x_edge <= wx_high and x_edge >= wx_low:
            if y_edge_low >= wy_low and y_edge_high <= wy_high:
                return False
        return True

    # 检查y方向上的相邻情况
    if (y1_high == y2_low or y1_low == y2_high) and ((x1_low <= x2_high and x1_high >= x2_high) or (x1_low <= x2_low and x1_high >= x2_low)):
        y_edge = y1_high if y1_high == y2_low else y1_low
        x_edge_low, x_edge_high = max(x1_low, x2_low), min(x1_high, x2_high)
        # print('y_edge:', y_edge)
        # print('x_edge_low:', x_edge_low, 'x_edge_high:', x_edge_high)
        if x_edge_low == x_edge_high:
            return False
        if y_edge <= wy_high and y_edge >= wy_low:
            if x_edge_low >= wx_low and x_edge_high <= wx_high:
                return False
        return True

    return False

def are_adjacent_antfall(region1, region2, has_bridge):
    if not has_bridge:
        wx_low, wx_high, wy_low, wy_high = -8, 16, 12, 24
    else:
        wx_low, wx_high, wy_low, wy_high = -8, 8, 12, 24

    # 分别提取两个矩形的坐标
    x1_low, x1_high, y1_low, y1_high = region1[0], region1[2], region1[1], region1[3]
    x2_low, x2_high, y2_low, y2_high = region2[0], region2[2], region2[1], region2[3]
 
    # 检查x方向上的相邻情况
    if (x1_high == x2_low or x1_low == x2_high) and ((y1_low <= y2_high and y1_high >= y2_high) or (y1_low <= y2_low and y1_high >= y2_low)):
        x_edge = x1_high if x1_high == x2_low else x1_low
        y_edge_low, y_edge_high = max(y1_low, y2_low), min(y1_high, y2_high)
        # print('x_edge:', x_edge)
        # print('y_edge_low:', y_edge_low, 'y_edge_high:', y_edge_high)
        if y_edge_low == y_edge_high:
            return False
        if x_edge <= wx_high and x_edge >= wx_low:
            if y_edge_low >= wy_low and y_edge_high <= wy_high:
                return False
        return True

    # 检查y方向上的相邻情况
    if (y1_high == y2_low or y1_low == y2_high) and ((x1_low <= x2_high and x1_high >= x2_high) or (x1_low <= x2_low and x1_high >= x2_low)):
        y_edge = y1_high if y1_high == y2_low else y1_low
        x_edge_low, x_edge_high = max(x1_low, x2_low), min(x1_high, x2_high)
        # print('y_edge:', y_edge)
        # print('x_edge_low:', x_edge_low, 'x_edge_high:', x_edge_high)
        if x_edge_low == x_edge_high:
            return False
        if y_edge <= wy_high and y_edge >= wy_low:
            if x_edge_low >= wx_low and x_edge_high <= wx_high:
                return False
        return True

    return False

def generate_adjacency_list(regions):
    adjacency_list = {i: [] for i in range(1, len(regions) + 1)}
    
    for i in range(len(regions)):
        for j in range(i + 1, len(regions)):
            # print('i:', i+1, 'j:', j+1)
            if are_adjacent(regions[i], regions[j]):
                adjacency_list[i + 1].append(j + 1)
                adjacency_list[j + 1].append(i + 1)

    return adjacency_list

def generate_adjacency_list_antfall(regions, has_bridge):
    adjacency_list = {i: [] for i in range(1, len(regions) + 1)}
    
    for i in range(len(regions)):
        for j in range(i + 1, len(regions)):
            # print('i:', i+1, 'j:', j+1)
            if are_adjacent_antfall(regions[i][:2]+regions[i][3:5], regions[j][:2] + regions[j][3:5], has_bridge=has_bridge):
                adjacency_list[i + 1].append(j + 1)
                adjacency_list[j + 1].append(i + 1)
                
    return adjacency_list

def calculate_center(region):
    x_center = (region[0] + region[2]) / 2
    y_center = (region[1] + region[3]) / 2
    return (x_center, y_center)

# 计算两个点之间的欧氏距离
def calculate_distance(point1, point2):
    return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)

# 生成带权重的邻接图
def generate_adjacency_graph(regions):
    G = nx.Graph()
    
    for i in range(len(regions)):
        G.add_node(i + 1, center=calculate_center(regions[i]))
    
    for i in range(len(regions)):
        for j in range(i + 1, len(regions)):
            if are_adjacent(regions[i], regions[j]):
                center1 = calculate_center(regions[i])
                center2 = calculate_center(regions[j])
                distance = calculate_distance(center1, center2)
                G.add_edge(i + 1, j + 1, weight=distance)

    return G

if __name__ == '__main__':
    # AntFall
    # regions =[[2.5,8.0,0,4,16.0,5],
    #           [10.0,4.0,0,13.0,8.0,5],
    #           [-8,16,0,4,32,5],
    #           [4,16,0,16,32,5],
    #           [1.0,4.0,0,4,6.0,5],
    #           [1.0,6.0,0,4,8.0,5],
    #           [-8,0.0,0,-2.0,16.0,5],
    #           [1.0,0.0,0,4,4.0,5],
    #           [-2.0,8.0,0,2.5,12.0,5],
    #           [-2.0,12.0,0,2.5,16,5],
    #           [-2.0,0.0,0,1.0,8.0,5],
    #           [10.0,12.0,0,13.0,16,5],
    #           [4.0,0,0,16.0,4.0,5],
    #           [13.0,4.0,0,16,8.0,5],
    #           [13.0,12.0,0,16,16,5],
    #           [4.0,4.0,0,10.0,8.0,5],
    #           [4.0,8.0,0,16.0,12.0,5],
    #           [4.0,12.0,0,10.0,16,5]]
    # regions = [[1.0,0,0,4,2.0,5],
    #            [4,0.0,0,10.0,8.0,5],
    #            [-8,16,0,4,32,5],
    #            [4,16,0,16,32,5],
    #            [2.5,8.0,0,4,12.0,5],
    #            [1.0,2.0,0,4,4.0,5],
    #            [1.0,4.0,0,4,6.0,5],
    #            [1.0,6.0,0,4,8.0,5],
    #            [1.0,8.0,0,2.5,12.0,5],
    #            [-2.0,0.0,0,1.0,4.0,5],
    #            [-8,0.0,0,-2.0,16.0,5],
    #            [1.0,12.0,0,4.0,16,5],
    #            [-2.0,4.0,0,1.0,16.0,5],
    #            [10.0,0.0,0,13.0,8.0,5],
    #            [4.0,8.0,0,16.0,16,5],
    #            [13.0,0.0,0.0,16,6.0,5.0],
    #            [13.0,6.0,0,16,8.0,5]]
    regions = [
        [1.0,4.0,0,4,6.0,5],
        [4,0,0,10.0,4.0,5],
        [-8,16,0,4,32,5],
        [4,16,0,16,32,5],
        [1.0,0.0,0,4,4.0,5],
        [1.0,8.0,2.5,4,16.0,5],
        [-2.0,4.0,0,1.0,8.0,2.5],
        [-2.0,4.0,2.5,1.0,8.0,5],
        [1.0,6.0,0,4,8.0,5],
        [-2.0,0.0,0,1.0,4.0,5],
        [-8,0.0,0,-2.0,16.0,5],
        [1.0,8.0,0,4,16.0,2.5],
        [-2.0,8.0,0,1.0,16.0,5],
        [7.0,4.0,0,10.0,8.0,5],
        [10.0,0.0,0,16,12.0,5],
        [10.0,12.0,0,16.0,16,5],
        [7.0,8.0,0,10.0,16,5],
        [4.0,4.0,0,7.0,16.0,5],
    ]
    has_bridge = False
    # regions = [[-8,0,0,4,16,5],
    #            [4,0,0,16,16,5],
    #            [-8,16,0,4,32,5],
    #            [4,16,0,16,32,5]]
    char_maze_list = generate_antfall_maze_representation(regions, (0,0,4.5), has_bridge)
    
    adjacency_list = generate_adjacency_list_antfall(regions, has_bridge)
    with open('antfall_maze.txt', 'w') as f:
        f.write('\n\n'.join(char_maze_list))
        f.write('\n\n')
        for k, v in adjacency_list.items():
            f.write(f"Region {k}: {v}\n")
    f.close()
    # 示例矩形列表
    # regions = [
    #     [6.0,2.0,8,4.0],
    #     [8,4.0,14.0,6.0],
    #     [8,14.0,11.0,20],
    #     [0,8,8,20],
    #     [0,0.0,4.0,4.0],
    #     [4.0,2.0,6.0,3.0],
    #     [4.0,3.0,6.0,4.0],
    #     [2.0,4.0,4.0,6.0],
    #     [0,4.0,2.0,6.0],
    #     [0.0,6.0,8.0,8],
    #     [4.0,0.0,8.0,2.0],
    #     [4.0,4.0,8.0,6.0],
    #     [8,6.0,14.0,8],
    #     [8.0,3.0,14.0,4.0],
    #     [14.0,3.0,20,8.0],
    #     [17.0,2.0,20,3.0],
    #     [8.0,0,20.0,2.0],
    #     [8.0,2.0,17.0,3.0],
    #     [11.0,14.0,20.0,17.0],
    #     [8.0,8,20.0,14.0],
    #     [11.0,17.0,15.5,20],
    #     [15.5,17.0,18.5,20],
    #     [18.5,17.0,20,20]
    # ]

    # adjacency_list = generate_adjacency_list(regions)
    # print(adjacency_list)
    # adjacency_graph = generate_adjacency_graph(regions)
    # start_region = 5
    # goal_region = 4
    # path = nx.shortest_path(adjacency_graph, source=start_region, target=goal_region)
    
    # print('Shortest path:', path)
