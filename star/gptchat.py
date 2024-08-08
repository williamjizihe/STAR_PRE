from typing import List, Optional
from openai import OpenAI
import re
import json
import yaml
import tiktoken

class ChatGenerator:
    def __init__(self,
                 model: str = "gpt-4o",
                 max_gen_len: int = 2048,
                 temperature: float = 0.6,
                 top_p: float = 0.9,
                 system_prompt: Optional[str] = None):
        """
        Initializes the chat generator with API key and default settings.
        """
        with open("./star/config.json", "r") as f:
            config = json.load(f)
            api_key = config["api_key"]
        f.close()
        self.api_key = api_key
        self.model = model
        self.max_gen_len = max_gen_len
        self.temperature = temperature
        self.top_p = top_p
        self.system_prompt = [{"role": "system", "content": system_prompt}]
        self.chat_strip_match = re.compile(r'<\|.*?\|>')
        self.client = OpenAI(api_key=self.api_key)
        self.shots = []
        self.input_tokens = 0
        self.output_tokens = 0
        self.GPTtokenizer = tiktoken.get_encoding("cl100k_base")
        self.count = 0

    def save_shot(self, shot):
        GPT_shot_tokens_num = self.count_GPT_tokens(self.system_prompt)
        self.shots = shot
        return GPT_shot_tokens_num
        
    def __call__(self, prompt: str) -> str:
        """
        Generate a response to the user input using the GPT-4 model.
        
        Args:
        prompt (str): Input from the user to generate a response to.
        
        Returns:
        str: The generated response.
        """
        # Strip special chat formatting tokens before sending to GPT-4
        self.count += 1
        messages = self.system_prompt+self.shots+ [{"role": "user", "content": prompt}]
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_gen_len,
            temperature=self.temperature,
            top_p=self.top_p)
        
        return completion.choices[0].message.content

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens that a given text would be converted to by GPT tokenizer.

        Args:
        text (str): Text to count the tokens of.

        Returns:
        int: Number of tokens.
        """
        # OpenAI API does not directly expose a token count function, so this is illustrative.
        # You might need to approximate or use another method to get accurate token counts.
        return len(text.split())  # Simple placeholder for demonstration.

    def count_GPT_tokens(self, text):
        if isinstance(text, list):
            text = "\n\n".join(f"{item['role']}: {item['content']}" for item in text)
        text = self.chat_strip_match.sub('', text)
        encoded_text = self.GPTtokenizer.encode(text)
        return len(encoded_text)
    
if __name__ == "__main__":
    system_prompt = ("As a navigation assistant, help the agent find the best route through the maze to their goal by analyzing the given data. Consider each region's position and connections.\n"
            "Thinking Process:\n"
            "1. Identify the agent's current region, identify the goal region\n"
            "2. Identify where is the wall.\n"
            "3. Examine the adjacency list to see which regions connect to the current region.\n"
            "4. Observe the maze to see which other regions are also connected to the current region.\n"
            "5. From these connected regions, choose the one that moves closest to the goal without hitting walls.\n"
            )
    client = ChatGenerator(model="gpt-4o-mini", system_prompt=system_prompt)
    with open('shot.yaml', 'r') as f:
        shot = yaml.safe_load(f)
    f.close()
    print(shot)
    client.save_shots(shot)
    question = """
    Data:
    State: (0.0, 0.0), Region 7
    Goal: (0.0, 16.0), Region 4
    Adjacency list:
    Region 1: [2, 5, 8, 9, 11]
    Region 2: [1, 9, 13]
    Region 3: [4, 10, 11]
    Region 4: [3]
    Region 5: [1, 6, 7, 8]
    Region 6: [5, 7, 8]
    Region 7: [5, 6]
    Region 8: [1, 5, 6]
    Region 9: [1, 2, 11, 13, 14]
    Region 10: [3, 11, 15]
    Region 11: [1, 3, 9, 10, 12, 14, 15]
    Region 12: [11, 13, 14, 15]
    Region 13: [2, 9, 12, 14]
    Region 14: [9, 11, 12, 13]
    Region 15: [10, 11, 12]
    The top-down view of the maze is shown below, W represents walls, A represents the agent's current position, G represents the goal. The number represents the region number:
    0 4 4 4 4 4 4 3 3 3 3 3 3 3
    W G W W W W W W W W W 3 3 3
    W W W W W W W W W W W 3 3 3
    W W W W W W W W W W W 11 11 10
    0 7 7 6 8 1 11 11 11 11 11 11 11 10
    0 7 7 6 8 1 11 11 11 11 11 11 15 15
    0 7 7 5 5 1 11 11 11 11 11 11 15 15
    0 7 7 5 5 1 11 11 11 14 12 12 15 15
    0 7 7 5 5 1 9 9 9 14 12 12 15 15
    0 7 7 5 5 1 9 9 13 14 12 12 15 15
    0 7 7 5 5 1 2 2 13 13 12 12 15 15
    0 A 7 5 5 1 2 2 13 13 12 12 15 15
    0 0 0 0 0 0 0 0 0 0 0 0 0 0
    Based on the analysis, identify the most strategic next region to explore and format your answer as follows: Answer: Region <i>"""
    answer = client(question)
    print(answer)