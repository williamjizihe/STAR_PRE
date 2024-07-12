import matplotlib.pyplot as plt
import json

filename = 'json (4).json'
# Load the data from the file
with open(filename, 'r') as f:
    data = json.load(f)
f.close()

# Extract steps and timestamps from the data
steps = [item[1] for item in data]
timestamps = [item[0] for item in data]

# Calculate the time taken for each step
time_taken = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
steps_diff = [steps[i] - steps[i - 1] for i in range(1, len(steps))]

# Normalize time by step increment to get time per step
time_per_step = [time_taken[i] / steps_diff[i] for i in range(len(time_taken))]

# Smoothing the data
smoothed_time_per_step = []
window_size = 20
for i in range(len(time_per_step)):
    if i < window_size:
        smoothed_time_per_step.append(sum(time_per_step[:i + 1]) / (i + 1))
    else:
        smoothed_time_per_step.append(sum(time_per_step[i - window_size + 1:i + 1]) / window_size)
        
# Plotting the data
plt.figure(figsize=(10, 6))
plt.plot(steps[1:], smoothed_time_per_step)
plt.title('Time per Step Change vs. Step')
plt.xlabel('Step')
plt.ylabel('Time per Step (seconds)')
plt.grid(True)
plt.savefig(f'{filename}_timecost_smoothed.png')
       
# Plotting the data
plt.figure(figsize=(10, 6))
plt.plot(steps[1:], time_per_step, marker='o')
plt.title('Time per Step Change vs. Step')
plt.xlabel('Step')
plt.ylabel('Time per Step (seconds)')
plt.grid(True)
plt.savefig(f'{filename}_timecost.png')

# Time cost
time_cost = [timestamps[i] - timestamps[0] for i in range(1, len(timestamps))]
plt.figure(figsize=(10, 6))
plt.plot(steps[1:], time_cost, marker='o')
plt.title('Time Cost vs. Step')
plt.xlabel('Step')
plt.ylabel('Time Cost (seconds)')
plt.grid(True)
plt.savefig(f'{filename}_timecost2.png')