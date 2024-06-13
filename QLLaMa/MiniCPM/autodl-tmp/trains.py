from transformers import AutoModelForCausalLM, AutoTokenizer  # 从transformers库导入所需的类
import torch  # 导入torch库，用于深度学习相关操作

torch.manual_seed(0)  # 设置随机种子以确保结果的可复现性

# 定义模型路径
path = '/home/zji/data/MiniCPM/autodl-tmp/OpenBMB/MiniCPM-2B-sft-fp32'

# 从模型路径加载分词器，
tokenizer = AutoTokenizer.from_pretrained(path)

# 从模型路径加载模型，设置为使用bfloat16精度以优化性能，并将模型部署到支持CUDA的GPU上,trust_remote_code=True允许加载远程代码
model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.bfloat16, device_map='cuda', trust_remote_code=True)

# 使用模型进行聊天，提出问题并设置生成参数，如temperature、top_p值和repetition_penalty（重复惩罚因子）
prompts = []
prompt = ""
with open('prompt.txt', 'r') as f:
    lines = f.readlines()
    for line in lines:
        line = line.strip()
        if line == "Next":
            prompts.append(prompt)
            prompt = ""
        else:
            prompt += line + "\n"

# responds, history = model.chat(tokenizer, "山东省最高的山是哪座山, 它比黄山高还是矮？差距多少？", temperature=0.5, top_p=0.8, repetition_penalty=1.02)
for prompt in prompts:
    print(prompt)
    print("====================================")
    responds, history = model.chat(tokenizer, prompt, temperature=0.3, top_p=0.8, repetition_penalty=1.02)

    # 显示生成的回答
    print(responds)
    print("====================================")