import json
import matplotlib.pyplot as plt

# 加载数据
with open('./JSON/json_rate.json', 'r') as f:
    json_rate = json.load(f)
with open('./JSON/json_regions.json', 'r') as f:
    json_regions = json.load(f)
with open('./JSON/json_rate_3.1.json', 'r') as f:
    json_rate_3_1 = json.load(f)
with open('./JSON/json_regions_3.1.json', 'r') as f:
    json_regions_3_1 = json.load(f)
with open('./JSON/json_rate_gpt4o.json', 'r') as f:
    json_rate_gpt4o = json.load(f)
with open('./JSON/json_regions_gpt4o.json', 'r') as f:
    json_regions_gpt4o = json.load(f)
f.close()

# 解析数据
timesteps_rate, rates = zip(*[(x[1], x[2]) for x in json_rate])
timesteps_regions, regions = zip(*[(x[1], x[2]) for x in json_regions])
timesteps_rate_3_1, rates_3_1 = zip(*[(x[1], x[2]) for x in json_rate_3_1])
timesteps_regions_3_1, regions_3_1 = zip(*[(x[1], x[2]) for x in json_regions_3_1])
timesteps_rate_gpt4o, rates_gpt4o = zip(*[(x[1], x[2]) for x in json_rate_gpt4o])
timesteps_regions_gpt4o, regions_gpt4o = zip(*[(x[1], x[2]) for x in json_regions_gpt4o])

# 定义平滑函数
def smooth(data, window_size=20):
    smoothed_data = []
    for i in range(len(data)):
        if i < window_size:
            smoothed_data.append(sum(data[:i + 1]) / (i + 1))
        else:
            smoothed_data.append(sum(data[i - window_size + 1:i + 1]) / window_size)
    return smoothed_data

def main(window_size=5):
    # 应用平滑函数
    smoothed_rates = smooth(rates, window_size=window_size)
    smoothed_rates_3_1 = smooth(rates_3_1, window_size=window_size)
    smoothed_rates_gpt4o = smooth(rates_gpt4o, window_size=window_size)
    
    # 绘图
    fig, ax1 = plt.subplots()

    # 配置第一个y轴 (平滑后的rates)
    color = 'tab:blue'
    ax1.set_xlabel('Timestep')
    ax1.set_ylabel('Smoothed Rates', color=color)
    ax1.plot(timesteps_rate, smoothed_rates, color='tab:blue')
    ax1.plot(timesteps_rate_3_1, smoothed_rates_3_1, color='tab:green')
    ax1.plot(timesteps_rate_gpt4o, smoothed_rates_gpt4o, color='tab:purple')
    ax1.tick_params(axis='y', labelcolor=color)

    # 配置第二个y轴 (regions)
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Number of Regions', color=color)
    ax2.plot(timesteps_regions, regions, color='tab:blue',linestyle='--', alpha=0.7)
    ax2.plot(timesteps_regions_3_1, regions_3_1, color='tab:green',linestyle='--', alpha=0.7)
    ax2.plot(timesteps_regions_gpt4o, regions_gpt4o, color='tab:purple',linestyle='--', alpha=0.7)
    ax2.tick_params(axis='y', labelcolor=color)

    ax1.legend(['3.0', '3.1', 'gpt4o'], loc='upper left')
    ax2.legend(['3.0', '3.1', 'gpt4o'], bbox_to_anchor=(0.17, 0.88))
    

    # x轴0-3M
    # plt.xlim(0, 3100000)
    # 调整布局并显示图像
    fig.tight_layout()
    plt.savefig('draw_success_rate.png')

# 从命令行读取参数
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--window_size", type=int, default=5)
args = parser.parse_args()
main(window_size=args.window_size)
