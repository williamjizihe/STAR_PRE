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
    maze = []
    with open(maze_filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
            maze.append(list(line.strip().split(' ')))
    file.close()
    return maze

def generate_prompt(state, r1, goal, r2, matrix, matrix_type, regions, maze = None, image=False):
    prompt = (
        "In this task, the ant must navigate a maze to reach the exit. Act as Navigator for the ant, "
        "and select the most appropriate region from the divided areas as the ant's next target region.\n"
    )
    if matrix_type == "visit":
        prompt += (
            "The matrix below shows whether the ant has moved from one region to another during the exploration.\n\n"
        )
    elif matrix_type == "graph":
        prompt += (
            "The adjacency list below shows the regions that are connected to each region.\n\n"
        )
    elif matrix_type == "matrix":
        prompt += (
            "The matrix below shows the regions that are connected to each region. A value of 1 indicates a connection.\n\n"
        )
    else:
        pass
    
    if maze is not None:
        prompt += (
            "The top-down view of the maze is shown below. "
            "In the maze layout, 'W' represents walls, 'A' represents the ant's current position, 'G' represents the goal. "
            "The number represents the region number.\n\n"
        )
    elif image:
        prompt += (
            "The top-down view of the maze is shown below. "
            "In the image, red represents ant's current position, grey represents obstacles, and yellow represents the goal, the regions are divided by black lines and filled with blue color. "
            "The number represents the region number.\n\n"
        )
    prompt += (
        "Data:\n"
        f"- State: {state}, Region {r1}\n"
        f"- Goal: {goal}, Region {r2}\n"
        "- Areas Info (each area is described by two diagonal vertices of a square):\n"
    )

    # Append regions
    for i, region in enumerate(regions, 1):
        prompt += f"Region {i}: {region}\n"

    # Append matrix
    if matrix_type == "graph":
        prompt += "- Graph representation:\n"
        for i, row in enumerate(matrix):
            if len(row) == 0:
                continue
            prompt += f"Region {i+1}: {adjacency_graph[i]}\n"
    elif matrix_type == "visit" or matrix_type == "matrix":
        prompt += "- visit matrix:\n"
        for row in matrix:
            # prompt += " ".join(row) + "\n"
            prompt += " ".join([str(int(x)) for x in row]) + "\n"
    else:
        pass
    
    if maze is not None:
        prompt += "-Maze layout:\n"
        for row in maze:
            prompt += " ".join(row) + "\n"
            
    prompt += (
        "\nInstructions:\n"
        "1. Determine the most appropriate region for the ant to move next, avoiding obstacles.\n"
        "2. Ensure your selected region avoids obstacles and brings the ant closer to the goal.\n"
        "3. Provide the answer in the following exact format without any additional explanation or text: Region <i>: [x1, y1], [x2, y2]\n"
        "4. Ensure the format is strictly followed without adding any extra text.\n"
        "5. Re-evaluate your answer before submission to ensure it is the best choice.\n"
    )
    
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
    timesteps = [305000, 605000, 4980000]
    matrix_folder = "./results/transition/"
    region_folder = "./results/Regions/"
    maze_folder = "./results/Maze/"
    
    state = [[0, 0], [18, 5], [18, 15]]
    r1 = [[1,2,3],[5,2,3],[5,15,19]]
    goal = [0, 15]
    r2 = 4
        
    for ti, timestep in enumerate(timesteps):
        matrix, regions = read_data(matrix_folder, region_folder, timestep)
        adjacency_matrix = convert_matrix(matrix)
        adjacency_graph = convert_graph(matrix)
        
        output = f"prompt_{timestep}_visit_image.txt"
        with open(output, 'w') as file:
            for pi, p in enumerate(state):
                maze = read_maze(f"./results/Maze/AntMaze_{timestep}_Maze_{p[0]}_{p[1]}.txt")

                prompt = generate_prompt(p, r1[ti][pi], goal, r2, matrix, "visit", regions, maze=None, image=True)
                file.write(prompt)
                file.write("Next\n")
        file.close()
