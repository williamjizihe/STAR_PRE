from chat import ChatGenerator
import json
import time

# system_prompt = "You are the navigation assistant. Your task is to name each region with a unique name understandable by the user to help him follow your instructions."
system_prompt = "In this task, You are the navigation assistant, helping agent to reach the exit. Determine the most appropriate next region for the ant to explore, avoiding obstacles."
chat = ChatGenerator(system_prompt=system_prompt, max_batch_size=1, max_seq_len = 6000, max_gen_len = 64)
with open("input.txt") as f:
    user_prompt = f.read()
f.close()
# with open("user_prompt.json") as f:
#     user_prompt = json.load(f)
# f.close()
user_prompt = user_prompt
print(user_prompt)
print("------------------")
time1 = time.time()
response = chat(user_prompt)
time2 = time.time()
print(response)
print(time2-time1)