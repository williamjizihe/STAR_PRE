from typing import List, Optional
from myllama import Llama
import copy
from transformers import GPT2Tokenizer
import tiktoken
import re

class ChatGenerator:
    def __init__(self, 
                 ckpt_dir: str = "Meta-Llama-3.1-8B-Instruct/", 
                 tokenizer_path: str = "Meta-Llama-3.1-8B-Instruct/tokenizer.model", 
                 max_seq_len: int = 4196, 
                 max_batch_size: int = 2, 
                 temperature: float = 0.6, 
                 top_p: float = 0.9, 
                 seed: int = 42,
                 max_gen_len: Optional[int] = 2048, 
                 system_prompt: Optional[str] = None,
                ):
        """
        Initializes the chat generator by loading configurations and setting up the model.
        """
        self.ckpt_dir = ckpt_dir
        self.tokenizer_path = tokenizer_path
        self.max_seq_len = max_seq_len
        self.max_batch_size = max_batch_size
        self.temperature = temperature
        self.top_p = top_p
        self.max_gen_len = max_gen_len
        self.system_prompt = system_prompt
        self.seed = seed
        self.shot_tokens = None
        self.head_tokens = None
        self.count = 0
        self.tokens_num = 0
        self.GPTtokenizer = tiktoken.get_encoding("cl100k_base")
        self.chat_strip_match = re.compile(r'<\|.*?\|>')
        
        # Initialize the generator model
        self.generator = Llama.build(
            ckpt_dir=self.ckpt_dir,
            tokenizer_path=self.tokenizer_path,
            max_seq_len=self.max_seq_len,
            max_batch_size=self.max_batch_size,
            seed=self.seed,
        )

        self.head_tokens = self.generator.formatter.encode_header({"role": "assistant", "content": ""})

        # Load user prompts once
        # with open("user_prompt.json", 'r') as f:
        #     self.user_prompt = json.load(f)[1]
    def __call__(self, prompt) -> str:
        """
        Generate a response to the user input using the model.

        Args:
        user_input (str): Input from the user to generate a response to.

        Returns:
        str: The generated response.
        """
        tokens = copy.deepcopy(self.shot_tokens)
        tokens.extend(self.generator.formatter.encode_message({"role": "user", "content": prompt}))
        tokens.extend(self.head_tokens)
        # print("Length of tokens: ", len(tokens))
        # print("Length of GPT tokens: ", self.GPT_tokens_num + len(self.GPTtokenizer.encode(prompt)))
              
        generation_tokens = self.generator.generate(
            prompt_tokens=[tokens],
            max_gen_len=self.max_gen_len,
            temperature=self.temperature,
            top_p=self.top_p
        )
        self.count += 1
        return self.generator.tokenizer.decode(generation_tokens[0])

    def save_shot(self, shot):
        GPT_shot_tokens_num = 0
        tokens = []
        tokens.append(self.generator.formatter.tokenizer.special_tokens["<|begin_of_text|>"])
        tokens.extend(self.generator.formatter.encode_message({"role": "system", "content": self.system_prompt}))
        GPT_shot_tokens_num += self.count_GPT_tokens(self.system_prompt)
        
        for message in shot:
            tokens.extend(self.generator.formatter.encode_message(message))
            GPT_shot_tokens_num += self.count_GPT_tokens(message["content"])
        self.shot_tokens = tokens
        return GPT_shot_tokens_num

    def count_GPT_tokens(self, text):
        text = self.chat_strip_match.sub('', text)
        encoded_text = self.GPTtokenizer.encode(text)
        return len(encoded_text)