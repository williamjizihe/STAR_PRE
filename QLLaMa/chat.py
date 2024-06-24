from typing import List, Optional
from myllama import Llama
import json
import copy

class ChatGenerator:
    def __init__(self, 
                 ckpt_dir: str = "Meta-Llama-3-8B-Instruct/", 
                 tokenizer_path: str = "Meta-Llama-3-8B-Instruct/tokenizer.model", 
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
    def __call__(self, message) -> str:
        """
        Generate a response to the user input using the model.

        Args:
        user_input (str): Input from the user to generate a response to.

        Returns:
        str: The generated response.
        """
        tokens = copy.deepcopy(self.shot_tokens)
        tokens.extend(self.generator.formatter.encode_message(message))
        tokens.extend(self.head_tokens)
        
        generation_tokens, _ = self.generator.generate(
            prompt_tokens=[tokens],
            max_gen_len=self.max_gen_len,
            temperature=self.temperature,
            top_p=self.top_p,
            logprobs=False,
        )

        return self.generator.tokenizer.decode(generation_tokens[0])
    
    # def __call__(self, user_input: str) -> str:
    #     """
    #     Generate a response to the user input using the model.

    #     Args:
    #     user_input (str): Input from the user to generate a response to.

    #     Returns:
    #     str: The generated response.
    #     """
    #     prompts = []
    #     user_prompt = {"role": "user", "content": user_input}
    #     if self.system_prompt is not None:
    #         system_prompt = {"role": "system", "content": self.system_prompt}
    #         prompts.append(system_prompt)
    #     prompts.append(user_prompt)
        
    #     dialogs: List[Dialog] = [
    #         prompts
    #     ]

    #     results = self.generator.chat_completion(
    #         dialogs,
    #         max_gen_len=self.max_gen_len,
    #         temperature=self.temperature,
    #         top_p=self.top_p,
    #     )

    #     return results[0]['generation']['content']

    def save_shot(self, shot):
        tokens = []
        tokens.append(self.generator.formatter.tokenizer.special_tokens["<|begin_of_text|>"])
        for message in shot:
            tokens.extend(self.generator.formatter.encode_message(message))
        self.shot_tokens = tokens
        return

if __name__ == '__main__':
    system_prompt = "You are the navigation assistant for an ant. Your task is to name each region with a unique name."
    chat_gen = ChatGenerator(system_prompt=system_prompt)
    response = chat_gen("What should the next region be named?")
    print(response)
    response = chat_gen("What should the next region be named?")
    print(response)
