import json
import matplotlib.pyplot as plt

# 加载数据
with open('json_rate.json', 'r') as f:
    json_rate = json.load(f)
with open('json_regions.json', 'r') as f:
    json_regions = json.load(f)

# 解析数据
timesteps_rate, rates = zip(*[(x[1], x[2]) for x in json_rate])
timesteps_regions, regions = zip(*[(x[1], x[2]) for x in json_regions])

# 定义平滑函数
def smooth(data, window_size=20):
    smoothed_data = []
    for i in range(len(data)):
        if i < window_size:
            smoothed_data.append(sum(data[:i + 1]) / (i + 1))
        else:
            smoothed_data.append(sum(data[i - window_size + 1:i + 1]) / window_size)
    return smoothed_data

# 应用平滑函数
smoothed_rates = smooth(rates, window_size=3)

# 绘图
fig, ax1 = plt.subplots()

# 配置第一个y轴 (平滑后的rates)
color = 'tab:blue'
ax1.set_xlabel('Timestep')
ax1.set_ylabel('Smoothed Rates', color=color)
ax1.plot(timesteps_rate, smoothed_rates, color=color)
ax1.tick_params(axis='y', labelcolor=color)

# 配置第二个y轴 (regions)
ax2 = ax1.twinx()
color = 'tab:red'
ax2.set_ylabel('Number of Regions', color=color)
ax2.plot(timesteps_regions, regions, color=color)
ax2.tick_params(axis='y', labelcolor=color)

# 调整布局并显示图像
fig.tight_layout()
plt.savefig('draw_success_rate.png')
