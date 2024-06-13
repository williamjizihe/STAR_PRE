import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.patches as patches
import numpy as np
import os
import csv
import numpy as np
title_fontsize = 15
legend_fontsize = 12

dir = './results/partitions_AntMaze/'

def transform(regions):
    trans = []
    for r in regions:
        t = (r[0],r[3],r[1],r[4],r[2],r[5])
        trans.append(t)
    return trans

def plot_sphere(ax, position, radius):
    """Plot a sphere at the specified position with the given radius."""
    u = np.linspace(0, 2 * np.pi, 100)
    v = np.linspace(0, np.pi, 100)
    x = position[0] + radius * np.outer(np.cos(u), np.sin(v))
    y = position[1] + radius * np.outer(np.sin(u), np.sin(v))
    z = position[2] + radius * np.outer(np.ones(np.size(u)), np.cos(v))

    ax.plot_surface(x, y, z, color='yellow', alpha=1)

def calculate_cube_colors(data_values, cmap):
    # Normalize data values to the range [0, 1]
    # normalized_values = (data_values - np.min(data_values)) / (np.max(data_values) - np.min(data_values))
    normalized_values = data_values / np.max(data_values)
    # normalized_values = (data_values - np.min([0])) / (np.max([5000]) - np.min([0]))
    # Apply the colormap to get colors
    face_colors = cmap(normalized_values)
    return face_colors, normalized_values

def plot_colored_cube(ax, bounds, alpha, cube_color, edgecolors = 'k'):
    """Plot a cube colored with a single color based on data values."""
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    vertices = [
        (xmin, ymin, zmin),
        (xmax, ymin, zmin),
        (xmax, ymax, zmin),
        (xmin, ymax, zmin),
        (xmin, ymin, zmax),
        (xmax, ymin, zmax),
        (xmax, ymax, zmax),
        (xmin, ymax, zmax)
    ]

    faces = [
        [vertices[0], vertices[1], vertices[2], vertices[3]],
        [vertices[4], vertices[5], vertices[6], vertices[7]],
        [vertices[0], vertices[1], vertices[5], vertices[4]],
        [vertices[2], vertices[3], vertices[7], vertices[6]],
        [vertices[0], vertices[3], vertices[7], vertices[4]],
        [vertices[1], vertices[2], vertices[6], vertices[5]]
    ]

    ax.add_collection3d(Poly3DCollection(faces, alpha=alpha, linewidths=1, edgecolors=edgecolors, facecolors=cube_color))

    # Set equal aspect ratio for all axes
    ax.set_box_aspect([1, 1, 1])

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

def plot_Ant_Fall(regions, data_values, ax, title):
    # Arrow initialization
    x_start = -10  # x-coordinate of the starting point
    y_start = -10  # y-coordinate of the starting point
    z_start = 4
    x_end = -10  # x-coordinate of the ending point
    y_end = -10
    z_end = 4

    fixed_blocks = [
        (-8, 16, 0, 12, 0, 4),
        (-8, 16, 16, 32, 0, 4),
    ]
    # Example usage
    # fig = plt.figure()
    # ax = fig.add_subplot(111, projection='3d')

    for i in range(len(fixed_blocks)):
        # cube_bounds = (0, 4, 0, 5, 1, 3)  # (xmin, xmax, ymin, ymax, zmin, zmax)
        cube_bounds = fixed_blocks[i]
        plot_colored_cube(ax, cube_bounds, 0.2, 'grey', 'grey')
        # Set the experiment name as the title for each graph
        ax.set_title(title, fontsize=title_fontsize, y=-0.25)

    regions = transform(regions)

    cmap = plt.get_cmap('viridis')

    # Calculate the single color based on data values and colormap
    cube_colors, visits = calculate_cube_colors(data_values, cmap)

    for i in range(len(regions)):
        r = regions[i]
        if visits[i] > 0:
            plot_colored_cube(ax, r, 0.7, cube_colors[i], 'k')

        if x_start > -10 and y_start > -10:
            x_end = (r[2] - r[0])/2 + r[0]  # x-coordinate of the ending point
            y_end = (r[3] - r[1])/2 + r[1]  # y-coordinate of the ending point
            # Create an arrow patch
            ax.annotate('', xy=(x_end, y_end), xytext=(x_start, y_start),
                        arrowprops=dict(arrowstyle='->', color='r', linewidth=2))

        # Define arrow parameters (start and end points)
        x_start = (r[2] - r[0])/2 + r[0]  # x-coordinate of the starting point
        y_start = (r[3] - r[1])/2 + r[1]  # y-coordinate of the starting point


    movable_block = (8, 12, 8, 12, 4, 8)
    plot_colored_cube(ax, movable_block, 0.5, 'r', 'r')
    # Set axis limits
    ax.set_xlim(-12, 20)
    ax.set_ylim(0, 32)
    ax.set_zlim(0, 10)

    # Set equal aspect ratio for all axes
    ax.set_box_aspect([1, 1, 1])

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    # Define sphere parameters (position and radius)
    sphere_position = (0, 27, 6)  # Specify the position (x, y, z)
    sphere_radius = 1  # Specify the radius

    # plot_sphere(ax, sphere_position, sphere_radius)

    # plt.show()

def plot_Ant_Fall_seq(regions, visits, idx=0):
    fig = plt.figure(figsize=(12, 4))  # Adjust the figure size as needed
    titles = ['1M Timesteps', '2M Timesteps', '3M Timesteps']
    for i in range(len(regions)):
        # Calculate the left position for each subplot
        ax = fig.add_subplot(1, len(regions), i + 1, projection='3d')
        ax.view_init(elev=50, azim=-60)  # Set the elevation (vertical angle) and azimuth (horizontal angle)
        plot_Ant_Fall(regions[i], visits[i], ax, titles[i])

    cmap = plt.get_cmap('viridis')
    # Create a colorbar to show the mapping of data values to colors
    cax = fig.add_axes([0.96, 0.1, 0.01, 0.8])  # Position and size of the colorbar
    cbar = plt.colorbar(plt.cm.ScalarMappable(cmap=cmap), cax=cax)
    cbar.set_label('Frequency of visits (Normalized)')
    # Set a fixed angle for all subplots
    plt.subplots_adjust(left=0.03, right=0.95, wspace=0.1)  # Adjust subplot spacing
    plt.show()
    fname = f"./antfall_repr_{idx}.png"
    plt.savefig(fname, dpi=300, bbox_inches='tight')

def plot_Ant_Maze(regions, data_values, ax, title, show=False, fill=True):
    cmap = plt.get_cmap('viridis')

    # Define rectangle parameters (position and size)
    rectangle = patches.Rectangle((-8, -8), 32, 4, linewidth=2, edgecolor='grey', facecolor='grey')
    ax.add_patch(rectangle)
    rectangle = patches.Rectangle((-8, 20), 32, 4, linewidth=2, edgecolor='grey', facecolor='grey')
    ax.add_patch(rectangle)
    rectangle = patches.Rectangle((-8, -4), 4, 24, linewidth=2, edgecolor='grey', facecolor='grey')
    ax.add_patch(rectangle)
    rectangle = patches.Rectangle((20, -4), 4, 24, linewidth=2, edgecolor='grey', facecolor='grey')
    ax.add_patch(rectangle)
    rectangle = patches.Rectangle((-4, 8), 20, 8, linewidth=2, edgecolor='grey', facecolor='grey')
    ax.add_patch(rectangle)

    color, visits = calculate_cube_colors(data_values, cmap)
    for i in range(len(regions)):
        r = regions[i]
        if fill:
            rectangle = patches.Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], alpha=0.7, facecolor=color[i], edgecolor='k')
        else: # No face color
            rectangle = patches.Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], alpha=0.7, edgecolor='k')
        ax.add_patch(rectangle)
        ax.set_title(title, fontsize=title_fontsize, y=-0.25)
        
        # Adding the index number in the center of each region
        center_x = (r[0] + r[2]) / 2
        center_y = (r[1] + r[3]) / 2
        ax.text(center_x, center_y, str(i+1), color='white', ha='center', va='center', fontsize=12, fontweight='bold')

    # Define circle parameters (position and radius)
    x = 0  # x-coordinate of the center
    y = 16  # y-coordinate of the center
    radius = 0.5  # Radius of the circle

    # Create a Circle patch
    circle = patches.Circle((x, y), radius, linewidth=2, edgecolor='y', facecolor='y')

    # Add the circle to the axis
    ax.add_patch(circle)

    # Set axis limits (optional)
    ax.set_xlim(-8, 24)
    ax.set_ylim(-8, 24)

    # Show the plot
    if show:
        plt.show()

def plot_Ant_Maze_seq(regions, visits):
    fig = plt.figure(figsize=(12, 4))  # Adjust the figure size as needed
    # Calculate the width and height for each subplot
    width = 1 / 3
    height = 1
    titles = ['1M Timesteps', '2M Timesteps', '3M Timesteps']

    for i in range(len(regions)):
        # Calculate the left position for each subplot
        left = i * width

        # ax = fig.add_axes([left, 0, width, height], projection='3d')
        ax = fig.add_subplot(1, len(regions), i + 1)
        plot_Ant_Maze(regions[i], visits[i], ax, titles[i])

    cmap = plt.get_cmap('viridis')
    # Create a colorbar to show the mapping of data values to colors
    cax = fig.add_axes([0.96, 0.1, 0.01, 0.8])  # Position and size of the colorbar
    cbar = plt.colorbar(plt.cm.ScalarMappable(cmap=cmap), cax=cax)
    cbar.set_label('Frequency of visits (Normalized)')
    # Set a fixed angle for all subplots
    plt.subplots_adjust(left=0.05, right=0.95, wspace=0.1)  # Adjust subplot spacing
    plt.show()
    fname = "./antmaze_repr.png"
    plt.savefig(fname, dpi=300, bbox_inches='tight')

def read_partitions(idx, AntMaze=False, AntFall=False):
    visits = {}
    regions = {}
    experiments = []
    if AntMaze:
        visits['AntMaze'] = []
        regions['AntMaze'] = []
        experiments.append('AntMaze')
    if AntFall:
        visits['AntFall'] = []
        regions['AntFall'] = []
        experiments.append('AntFall')
    # for i in range(3):
    for e in experiments:
        file = f"{dir}{e}_{idx}_BossPartitions.pth"
        v = []
        r = []
        with open(file) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if line_count <= 1:
                    line_count += 1
                if line_count == 2:
                    v = [float(rec) for rec in row]
                    line_count += 1
                    print(row)
                else:
                    if len(row) != 4:
                        continue
                    r.append([float(rec) for rec in row])
                    # print(row)

    visits[e].append(v)
    regions[e].append(r)

    return visits, regions


def generate_maze_representation(regions, visits, goal, position, filename):
    # Define the fixed size of the maze
    size = 40  # from -8 to 24, scaled by 2

    # Initialize the maze representation with zeros
    maze = np.zeros((size, size), dtype=int)

    # Mark regions with their respective indices
    for i, r in enumerate(regions):
        if visits[i] < 0:
            continue
        x1, y1, x2, y2 = int(r[0]*2), int(r[1]*2), int(r[2]*2), int(r[3]*2)
        maze[x1:x2, y1:y2] = i + 1

    # Define wall boundaries (scaled by 2)
    walls = [
        ((0, 16), (32, 32))     # Middle wall
    ]

    for wall in walls:
        x1, y1 = wall[0]
        x2, y2 = wall[1]
        maze[x1:x2, y1:y2] = -1
    
    # maze[0, 32] = 99 # Goal
    # maze[0, 0] = 98 # Position
    maze[goal[0]*2, goal[1]*2] = 99 # Goal
    maze[position[0]*2, position[1]*2] = 98 # Position
    
    # Rotate the maze representation by 90 degrees
    maze = np.rot90(maze)
    
    # Save the maze representation to a file
    with open(filename, 'w') as f:
        for row in maze:
            for i in row:
                if i == -1:
                    f.write("W")
                elif i == 98:
                    f.write("A")
                elif i == 99:
                    f.write("G")
                else:
                    f.write(str(i))
                f.write(" ")
            f.write("\n")
    return 

# plot_Ant_Maze_seq(r['AntMaze'], v['AntMaze'])
# for i in range(5):
#     v, r = read_partitions(i, AntFall=True)
#     plot_Ant_Fall_seq(r['AntFall'], v['AntFall'], i)

# Get all files named by {env}_{timestep}_BossPartitions.pth
all_timesteps = []
for file in os.listdir(dir):
    if file.endswith(".pth"):
        all_timesteps.append(int(file.split('_')[1]))

# maze_timesteps = [305000, 605000, 4980000]
# positions = [[0, 0], [18, 5], [18, 15]]
# goal = [0, 16]
# for timestep in maze_timesteps:
#     visits, regions = read_partitions(timestep, AntMaze=True)

#     regions = regions['AntMaze'][0]
#     visits = visits['AntMaze'][0]
#     for p in positions:
#         # generate_maze_representation(regions, visits, goal, p, f"./results/Maze/AntMaze_{timestep}_Maze_{p[0]}_{p[1]}.txt")
        
#         fig = plt.figure(figsize=(4, 4))  # Adjust the figure size as needed
#         ax = fig.add_subplot(111)
#         step = f"{timestep // 1000}K Timesteps" if timestep != 0 else "0 Timestep"
#         # plot_Ant_Maze(regions, visits, plt.gca(), f"AntMaze {step}\n{len(regions)} regions", show = False)
#         plot_Ant_Maze(regions, visits, plt.gca(), f" ", show = False, fill=False)
#         # Define circle parameters (position and radius)
#         x = p[0]  # x-coordinate of the center
#         y = p[1]  # y-coordinate of the center
#         radius = 0.5  # Radius of the circle

#         # Create a Circle patch
#         circle = patches.Circle((x, y), radius, linewidth=2, edgecolor='r', facecolor='r')

#         # Add the circle to the axis
#         ax.add_patch(circle)
#         # plt.show()
#         fname = "./exp/AntMaze_" + str(timestep) + "_" + str(p[0]) + "_" + str(p[1]) + ".png"
#         plt.savefig(fname, dpi=300, bbox_inches='tight')
#         plt.close()


for timestep in all_timesteps[:1]:
    visits, regions = read_partitions(timestep, AntMaze=True)

    regions = regions['AntMaze'][0]
    visits = visits['AntMaze'][0]
    
    print(regions)
    print(visits)
    # save regions
    fname = f"./maze/regions/AntMaze_{timestep}_Regions.txt"
    with open(fname, 'w', newline='') as f:
    # write with csv writer, delimiter is ','
        writer = csv.writer(f, delimiter=',')
        for r in regions:
            writer.writerow(r)  
    f.close()
    
    positions = [0, 0]
    goal = [0, 16]
    generate_maze_representation(regions, visits, goal, positions, f"./maze/text/AntMaze_{timestep}_Maze.txt")
    fig = plt.figure(figsize=(4, 4))  # Adjust the figure size as needed
    ax = fig.add_subplot(111)
    step = f"{timestep // 1000}K Timesteps" if timestep != 0 else "0 Timestep"
    # plot_Ant_Maze(regions, visits, plt.gca(), f"AntMaze {step}\n{len(regions)} regions", show = False)
    plot_Ant_Maze(regions, visits, plt.gca(), f" ", show = False, fill=False)
    # plt.show()
    fname = "./maze/image/" + str(timestep) + ".png"
    plt.savefig(fname, dpi=300, bbox_inches='tight')
    plt.close()
