from chat import ChatGenerator
import json
import time

system_prompt = "In this task, You are a navigation assistant, helping agent to reach the goal. Based on the data, determine the most appropriate next region for the agent to explore, avoiding obstacles, then name each region with a unique name understandable by the user to help him follow your instructions."
# system_prompt = "In this task, You are a navigation assistant, helping agent to reach the goal. Based on the data, determine the most appropriate next region for the agent to explore, avoiding obstacles."
# system_prompt = "In this task, You are an assistant"

chat = ChatGenerator(system_prompt=system_prompt, max_batch_size=1, max_seq_len = 2048, max_gen_len = 512)
with open("input.txt") as f:
    user_prompt3 = f.read()
f.close()
r = chat(user_prompt3)
# with open("input2.txt") as f:
#     user_prompt2 = f.read()
# f.close()
# with open("input3.txt") as f:
#     user_prompt = f.read()
# f.close()    
# with open("user_prompt.json") as f:
#     user_prompt = json.load(f)
# f.close()

prompts_folder = "../prompts/name/"
response_folder = "../responses/"
import os
from tabulate import tabulate

data = []

# for filename in os.listdir(prompts_folder):
#     fn_l = filename.split(".")[0].split("_")
#     env, timestep, CAM = fn_l[0], int(fn_l[1]), fn_l[3]
#     C = 'C' in CAM
#     A = 'A' in CAM
#     M = 'M' in CAM
    
#     with open(prompts_folder + filename) as f:
#         user_prompt = f.read()
#     f.close()
    
#     time1 = time.time()
#     response = chat(user_prompt)
#     time2 = time.time()
    
#     time_taken = time2 - time1
#     data.append([timestep, '√' if C else '', '√' if A else '', '√' if M else '', response, f"{time_taken:.2f}s"])
    
#     print("Time taken for prompt: ", time2-time1)
# # sort
# data.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
# headers = ["timestep", "C", "A", "M", "answer", "Time taken"]
# table = tabulate(data, headers, tablefmt="pipe")

# # Saving the markdown table to a file
# with open(response_folder + 'llama3_name.md', "w") as ff:
#     ff.write(table)
# ff.close()

def parse_response(response):
    lines = response.split("\n")
    # delete empty lines
    lines = [line for line in lines if line.strip()]
    next_region = lines[0].split(":")[1].strip()
    regions = {}
    for line in lines[1:]:
        parts = line.split(":")
        if len(parts) == 2:
            region_num = parts[0].strip()
            region_desc = parts[1].strip()
            regions[region_num] = region_desc
    return next_region, regions

region_counts = {305000: 4, 605000: 12, 930000: 18, 4980000: 23}

data = {}
time_taken_data = []

for filename in os.listdir(prompts_folder):
    fn_l = filename.split(".")[0].split("_")
    env, timestep, CAM = fn_l[0], int(fn_l[1]), fn_l[3]
    C = 'C' in CAM
    A = 'A' in CAM
    M = 'M' in CAM
    
    with open(prompts_folder + filename) as f:
        user_prompt = f.read()
    
    time1 = time.time()
    response = chat(user_prompt)  # Assuming chat() is defined elsewhere to handle prompts
    time2 = time.time()
    
    time_taken = time2 - time1
    
    if timestep not in data:
        data[timestep] = {
            "M": {"next_region": "", "regions": []},
            "CM": {"next_region": "", "regions": []},
            "AM": {"next_region": "", "regions": []},
            "CAM": {"next_region": "", "regions": []},
            "time taken": {"M": "", "CM": "", "AM": "", "CAM": ""}
        }
    
    cam_key = ""
    if C:
        cam_key += "C"
    if A:
        cam_key += "A"
    if M:
        cam_key += "M"
    
    next_region, regions = parse_response(response)
    regions_dict = {f"Region {i+1}": "" for i in range(region_counts[timestep])}
    for i in range(region_counts[timestep]):
        region_key = f"Region {i+1}"
        regions_dict[region_key] = regions.get(region_key, "")
    
    data[timestep][cam_key]["next_region"] = next_region
    data[timestep][cam_key]["regions"] = [regions_dict[f"Region {i+1}"] for i in range(region_counts[timestep])]
    data[timestep]["time taken"][cam_key] = f"{time_taken:.2f}s"
    
    print("Time taken for prompt: ", time2 - time1)

# Generating markdown tables for each timestep
for timestep, results in sorted(data.items()):
    headers = ["Region", "M", "CM", "AM", "CAM"]
    table_data = []
    for i in range(region_counts[timestep]):
        row = [
            f"Region {i+1}",
            results["M"]["regions"][i],
            results["CM"]["regions"][i],
            results["AM"]["regions"][i],
            results["CAM"]["regions"][i]
        ]
        table_data.append(row)
    table = tabulate(table_data, headers, tablefmt="pipe")
    with open(response_folder + f'llama3_regions_{timestep}.md', "w") as ff:
        ff.write(f"## Timestep {timestep}\n\n")
        ff.write(f"Next Region M: {results['M']['next_region']}\n")
        ff.write(f"Next Region CM: {results['CM']['next_region']}\n")
        ff.write(f"Next Region AM: {results['AM']['next_region']}\n")
        ff.write(f"Next Region CAM: {results['CAM']['next_region']}\n\n")
        ff.write(table)
        ff.write("\n\n")

# Generating markdown table for time taken
time_headers = ["timestep", "M", "AM", "CM", "CAM"]
time_table_data = []
for timestep, results in sorted(data.items()):
    row = [
        timestep,
        results["time taken"]["M"],
        results["time taken"]["AM"],
        results["time taken"]["CM"],
        results["time taken"]["CAM"]
    ]
    time_table_data.append(row)
time_table = tabulate(time_table_data, time_headers, tablefmt="pipe")
with open(response_folder + 'llama3_time_taken.md', "w") as ff:
    ff.write(time_table)

    
    
# while True:
#     print("----------------")
    
#     user_prompt = input("User: ")
#     time1 = time.time()
#     response = chat(user_prompt)
#     time2 = time.time()
#     print("------------------")
#     print(f"> {response}")
#     print("Time taken for first prompt: ", time2-time1)

# print("-------2--------")
# print(user_prompt2)
# print("------------------")
# print(f"> {response2}")
# print("Time taken for second prompt: ", time3-time2)
# print("-------3--------")
# print(user_prompt3)
# print("------------------")
# print(f"> {response3}")
# print("Time taken for third prompt: ", time4-time3)
