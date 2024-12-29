import os
import base64
import dashscope

from copy import deepcopy
from http import HTTPStatus
from typing import List, Tuple

from src.agent import Agent
from src.utils import replace_image_url, image_to_base64


class Qwen(Agent):
    def __init__(self, api_args=None, **config):
        if not api_args:
            api_args = {}
        api_args = deepcopy(api_args)
        api_key = api_args.pop("key", None) or os.getenv('QWEN_API_KEY')
        if not api_key:
            raise ValueError("Qwen API key is required, please assign api_args.key or set QWEN_API_KEY environment variable.")
        os.environ['QWEN_API_KEY'] = api_key
        dashscope.api_key = api_key

        api_args["model"] = api_args.pop("model", None)
        if not api_args["model"]:
            raise ValueError("Qwen model is required, please assign api_args.model.")
        self.api_args = api_args
        super().__init__(**config)
        # self.top_k = args.get('top_k')
        # self.seed = args.get('seed')
        # self.model = "qwen-vl-max"
        # self.sleep = args.get('sleep')


    def inference(self, history: List[dict]) -> str:
        history = replace_image_url(history, keep_path=True, throw_details=True)

        new_messages = []
        for message in history:
            if message["role"] == "user":
                if isinstance(message["content"], str):
                    new_message = {"role": "user", "content": [{"text": message["content"]}]}
                else:
                    new_message = {"role": "user", "content": []}
                    for content in message["content"]:
                        if content["type"] == "text":
                            new_message["content"].append({
                                "text": content["text"],
                            })
                        else:
                            new_message["content"].append({
                                "image": content["image_url"]["url"]
                            })
            else:
                new_message = {"role": "assistant"}
                new_message["content"] = [{"text": message["content"]}]
            new_messages.append(new_message)

        response = dashscope.MultiModalConversation.call(model=self.api_args["model"], messages=new_messages, seed=self.api_args.get("seed"), top_k=self.api_args.get("top_k"), temperature=0)
        
        return response.output.choices[0].message.content[0]['text']

    # def get_model_response(self, messages) -> Tuple[bool, str]:
        
    #     response = dashscope.MultiModalConversation.call(model = self.model, messages = messages, seed = self.seed, top_k = self.top_k)
        
    #     # time.sleep(self.sleep)
        
    #     if response.status_code == HTTPStatus.OK:
    #         print(f"Prompt Tokens: {response.usage.input_tokens}\nCompletion Tokens: {response.usage.output_tokens}\n")
    #         return True, response.output.choices[0].message.content[0]['text']
    #     else:
    #         return False, response.message