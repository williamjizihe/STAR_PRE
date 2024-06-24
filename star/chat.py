from typing import List, Optional
from llama import Dialog, Llama
import json

class ChatGenerator:
    def __init__(self, config_path: str, **kwargs):
        """
        Initializes the chat generator by loading configurations from a JSON file.
        Allows overriding configurations through keyword arguments.

        Args:
        config_path (str): Path to the JSON configuration file.
        kwargs: Optional keyword arguments to override the configuration file settings.
        """
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Update configuration with any overrides provided as kwargs
        config.update(kwargs)
        
        self.ckpt_dir = config.get("ckpt_dir", "Meta-Llama-3-8B-Instruct/")
        self.tokenizer_path = config.get("tokenizer_path", "Meta-Llama-3-8B-Instruct/tokenizer.model")
        self.max_seq_len = config.get("max_seq_len", 4196)
        self.max_batch_size = config.get("max_batch_size", 2)
        self.temperature = config.get("temperature", 0.6)
        self.top_p = config.get("top_p", 0.9)
        self.seed = config.get("seed", 42)
        self.max_gen_len = config.get("max_gen_len", None)
        self.system_prompt = config.get("system_prompt", None)

        # Initialize the generator model
        self.generator = Llama.build(
            ckpt_dir=self.ckpt_dir,
            tokenizer_path=self.tokenizer_path,
            max_seq_len=self.max_seq_len,
            max_batch_size=self.max_batch_size,
            seed=self.seed,
        )

    def __call__(self, user_input: str) -> str:
        """
        Generate a response to the user input using the model.

        Args:
        user_input (str): Input from the user to generate a response to.

        Returns:
        str: The generated response.
        """
        prompts = []
        user_prompt = {"role": "user", "content": user_input}
        if self.system_prompt is not None:
            system_prompt = {"role": "system", "content": self.system_prompt}
            prompts.append(system_prompt)
        prompts.append(user_prompt)
        
        dialogs: List[Dialog] = [prompts]

        results = self.generator.chat_completion(
            dialogs,
            max_gen_len=self.max_gen_len,
            temperature=self.temperature,
            top_p=self.top_p,
        )

        return results[0]['generation']['content']

if __name__ == '__main__':
    # system_prompt = "You are the navigation assistant for an ant. Your task is to name each region with a unique name."
    chat_gen = ChatGenerator('llama_config.json')
    response = chat_gen("What should the next region be named?")
    print(response)
    response = chat_gen("What should the next region be named?")
    print(response)
