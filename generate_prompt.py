import csv

def read_data(matrix_folder, region_folder, timestep):
    matrix_filename = matrix_folder + f"AntMaze_{timestep}_TransitionMatrix.pth"
    region_filename = region_folder + f"AntMaze_{timestep}_Regions.txt"
    
    regions = []
    matrix = []
    
    with open(matrix_filename, 'r') as file:
        csv_reader = csv.reader(file, delimiter=',')

        for row in csv_reader:
            if len(row) <= 2:
                continue
            v = [float(rec) for rec in row]
            matrix.append(v)
    file.close()
    
    with open(region_filename, 'r') as file:
        csv_reader = csv.reader(file, delimiter=',')
        for row in csv_reader:
            if len(row) <= 2:
                continue
            r = [float(rec) for rec in row]
            r = [r[:2], r[2:]]
            regions.append(r)
    file.close()
    return matrix, regions

def read_maze(maze_filename):
    with open(maze_filename, 'r') as file:
        maze = file.read()
    file.close()
    return maze

# def generate_prompt(state, r1, goal, r2, matrix, matrix_type, regions, maze = None, image=False):
#     '''
#     Old function to generate prompt
#     '''
#     prompt = (
#         "In this task, the ant must navigate a maze to reach the exit. Act as Navigator for the ant, "
#         "and select the most appropriate region from the divided areas as the ant's next target region.\n"
#     )
#     if matrix_type == "visit":
#         prompt += (
#             "The matrix below shows whether the ant has moved from one region to another during the exploration.\n\n"
#         )
#     elif matrix_type == "graph":
#         prompt += (
#             "The adjacency list below shows the regions that are connected to each region.\n\n"
#         )
#     elif matrix_type == "matrix":
#         prompt += (
#             "The matrix below shows the regions that are connected to each region. A value of 1 indicates a connection.\n\n"
#         )
#     else:
#         pass
    
#     if maze is not None:
#         prompt += (
#             "The top-down view of the maze is shown below. "
#             "In the maze layout, 'W' represents walls, 'A' represents the ant's current position, 'G' represents the goal. "
#             "The number represents the region number.\n\n"
#         )
#     elif image:
#         prompt += (
#             "The top-down view of the maze is shown below. "
#             "In the image, red represents ant's current position, grey represents obstacles, and yellow represents the goal, the regions are divided by black lines and filled with blue color. "
#             "The number represents the region number.\n\n"
#         )
#     prompt += (
#         "Data:\n"
#         f"- State: {state}, Region {r1}\n"
#         f"- Goal: {goal}, Region {r2}\n"
#         "- Areas Info (each area is described by two diagonal vertices of a square):\n"
#     )

#     # Append regions
#     for i, region in enumerate(regions, 1):
#         prompt += f"Region {i}: {region}\n"

#     # Append matrix
#     if matrix_type == "graph":
#         prompt += "- Graph representation:\n"
#         for i, row in enumerate(matrix):
#             if len(row) == 0:
#                 continue
#             prompt += f"Region {i+1}: {adjacency_graph[i]}\n"
#     elif matrix_type == "visit" or matrix_type == "matrix":
#         prompt += "- visit matrix:\n"
#         for row in matrix:
#             # prompt += " " += (row) + "\n"
#             prompt += " " += ([str(int(x)) for x in row]) + "\n"
#     else:
#         pass
    
#     if maze is not None:
#         prompt += "-Maze layout:\n"
#         for row in maze:
#             prompt += " " += (row) + "\n"
            
#     prompt += (
#         "\nInstructions:\n"
#         "1. Determine the most appropriate region for the ant to move next, avoiding obstacles.\n"
#         "2. Ensure your selected region avoids obstacles and brings the ant closer to the goal.\n"
#         "3. Provide the answer in the following exact format without any additional explanation or text: Region <i>: [x1, y1], [x2, y2]\n"
#         "4. Ensure the format is strictly followed without adding any extra text.\n"
#         "5. Re-evaluate your answer before submission to ensure it is the best choice.\n"
#     )
    
#     return prompt

def generate_user_prompt(state, r1, goal, r2, coordination=None, adjacency_list=None, maze=None, instruction=None):
    prompt = (
        "Data:\n"
        f"- State: {state}, Region {r1}\n"
        f"- Goal: {goal}, Region {r2}\n"
    )
    
    if coordination is not None:
        prompt += (f"- Coordination Info (each region is described by two diagonal vertices of a rectangle)")
        # Append regions
        for i, region in enumerate(regions, 1):
            prompt += (f"Region {i}: {region}\n")
    
    if adjacency_list is not None:
        prompt += ("- Adjacency list:\n")
        for i, row in enumerate(adjacency_list):
            if len(row) == 0:
                continue
            prompt += (f"Region {i+1}: {adjacency_list[i]}\n")
    
    if maze is not None:
        prompt += ("-The top-down view of the maze is shown below, 'W' represents walls, 'A' represents the ant's current position, 'G' represents the goal. The number represents the region number:\n")
        prompt += (maze)
    
    if instruction is not None:
        prompt += (f"\n{instruction}")
    # prompt += ("\nProvide the answer in the following exact format without any additional explanation or text: Region <i>\n")
    return prompt
                    
def convert_matrix(visit_matrix):
    # Convert visit matrix to a simple adjacency matrix
    adjacency_matrix = []
    for row in visit_matrix:
        adjacency_matrix.append([1 if x > 0 else 0 for x in row])
    return adjacency_matrix

def convert_graph(matrix):
    adjacency_graph = []
    for row in enumerate(matrix):
        adjacency_graph.append([i+1 for i, x in enumerate(row[1]) if x > 0])
    return adjacency_graph

if __name__ == "__main__":
    # Use the functions
    matrix_folder = "./results/transition_AntMaze/"
    region_folder = "./maze/regions/"
    maze_folder = "./maze/text/"
    output_folder = "./prompts/name/"
    
    timesteps = [305000, 605000, 930000, 4980000]
    state = [[0, 0], [5, 3], [10, 3], [18, 15]]
    r1 = [1, 7, 14, 19]
    goal = [0, 15]
    r2 = 4
    
    
    combination = [{'C':True, 'A':True, 'M':True},
                   {'C':False, 'A':False, 'M':True},
                   {'C':True, 'A':False, 'M':True},
                   {'C':False, 'A':True, 'M':True}]
    for ti, timestep in enumerate(timesteps):
        matrix, regions = read_data(matrix_folder, region_folder, timestep)
        instruction = "Provide the answer in the following exact format without any additional explanation or text: \nNext Region: <i>\n"
        for i in range(len(regions)):
            instruction += (f"Region <{i+1}>: <name>\n")
        for c in combination:
            matrix, regions = read_data(matrix_folder, region_folder, timestep)
            adjacency_list = None
            maze = read_maze(f"{maze_folder}AntMaze_{timestep}_Maze.txt")
            output = f"{output_folder}AntMaze_{timestep}_Prompt_"
            
                
            if c['C']:
                output += "C"
            else:
                regions = None
                
            if c['A']:
                output += "A"
                adjacency_matrix = convert_matrix(matrix)
                adjacency_list = convert_graph(matrix)
            if c['M']:
                output += "M"
            output += ".txt"
                
            with open(output, 'w') as file:
                # print(adjacency_list)
                # prompt = generate_prompt(p, r1[ti][pi], goal, r2, matrix, "visit", regions, maze=None, image=True)
                prompt = generate_user_prompt(state[ti], r1[ti], goal, r2, 
                                            coordination=regions, 
                                            adjacency_list=adjacency_list, 
                                            maze=maze, 
                                            instruction=instruction)
                # print(prompt)
                file.write(prompt)
        file.close()
