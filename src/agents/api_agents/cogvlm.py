import requests
import uuid
import os
import cv2
import numpy as np

from src.agent import Agent
from src.utils import replace_image_url, image_to_base64

from typing import Tuple, List
from PIL import Image
from transformers import LlamaTokenizer, PreTrainedTokenizerFast, AutoTokenizer


# load llama3 tokenizer
# tokenizer = LlamaTokenizer.from_pretrained("meta-llama/Meta-Llama-3-8B-Instruct")  # still waiting for access
# tokenizer = LlamaTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")
# tokenizer = AutoTokenizer.from_pretrained("lmsys/vicuna-7b-v1.5")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen-VL", trust_remote_code=True)



class CogVLM(Agent):
    def __init__(self, api_args=None):
        super().__init__()
        self.url =  api_args.get("url", None)

        self.task_input = ""
        self.image_input = ""

    
    def process_user_message(self, message, handle_image=False):
        text = ""
        if isinstance(message, str):
            text += message + "\n"
            return text
        for content in message:
            if isinstance(content, str):
                text += content + "\n"
            elif content["type"] == "text":
                text += f"{content['text']}" + "\n"
            else:
                text += f"** Image **"
                if handle_image:
                    image_url = content["image_url"]["url"].split(";base64,")[1]
                    img = cv2.imread(self.image_input)
                    img2 = cv2.imread(image_url)
                    assert img.shape[1] == img2.shape[1]
                    concat_img = np.concatenate((img, img2), axis=0)
                    cv2.imwrite(f"{os.path.join(os.path.dirname(self.image_input), 'concat.png')}", concat_img)
        
        return text


    def process_history(self, history: List[dict]) -> List[dict]:
        if len(history) == 3: # first time call
            self.task_input = ""  # reset the task input

            image_paths = []
            # process the input message, which will never be discarded
            self.task_input += f"<|system|>\n{history[0]['content']}\n\n" # first cast the first message to system message
            assert history[2]["role"] == "user"
            for content in history[2]["content"]:    
                if isinstance(content, str):
                    self.task_input += content + "\n"
                elif content["type"] == "text":
                    self.task_input += f"{content['text']}" + "\n"
                else:
                    # todo: process image: concat index.png and index_corrupted.png
                    self.task_input += f"** Image **"
                    image_url = content["image_url"]["url"].split(";base64,")[1]
                    image_paths.append(image_url)
            img = cv2.imread(image_paths[0])
            img2 = cv2.imread(image_paths[1])
            assert img.shape[1] == img2.shape[1]
            concat_img = np.concatenate((img, img2), axis=0)
            cv2.imwrite(f"{os.path.join(os.path.dirname(image_paths[0]), 'concat.png')}", concat_img)
            # the file name will be the same across the same conversation
            self.image_input = os.path.join(os.path.dirname(image_paths[0]), 'concat.png')

            dialog = [self.task_input]
            dialog = "\n\n".join(dialog)
        else:
            # assert the last turn is a user turn
            assert history[-1]["role"] == "user"
            # assert initial image exists
            assert os.path.exists(self.image_input)

            dialog = []
            # first process the latest user turn, including update the image
            last_user_text = self.process_user_message(history[-1]["content"], handle_image=True)
            # process the input message, which is dynamic with truncation
            for i in range(len(history) - 2, 2, -1):
                if history[i]["role"] == "user":
                    text = self.process_user_message(history[i]["content"])
                else:
                    text = history[i]["content"]

                length = len(tokenizer.tokenize(
                "\n\n".join([self.task_input, "** Earlier trajectory has been truncated **", text] + dialog) +
                f"\n\n{last_user_text}\n\n"))

                # if length > 12288 - 2304 - 50:
                if length > 12288 - 2304 - 500:
                    dialog = [f"** Earlier trajectory has been truncated **\n\n"] + dialog
                    break
                else:
                    dialog = [text] + dialog

            dialog = [self.task_input] + dialog
            dialog.append(last_user_text)
            dialog.append("<|assistant|>\n")

            dialog = "\n\n".join(dialog)

        return [
            {"image": open(self.image_input, "rb")},
            {"prompt": dialog}
        ]


    def inference(self, history: List[dict]) -> str:
        # history = replace_image_url(history, throw_details=True, keep_path=True)
        new_messages = self.process_history(history)
        
        flag = False
        count = 0
        while not flag and count < 5:
            count += 1
            flag, resp = self.get_model_response(new_messages)
        
        if not flag:
            raise Exception(resp)
            return

        # remove <|end_of_text|>
        resp = resp.replace("<|end_of_text|>", "")

        return resp

    def get_model_response(self, messages) -> Tuple[bool, str]:
        
        try:
            print(messages[0])
            # print(messages[1])
            response = requests.post(self.url, files=messages[0], data=messages[1], timeout=480)
            print("response:", response)
            response = response.json()
        except Exception as e:
            print(e)
            return False, str(e)
            
        if "error" in response:
            return False, response["error"]["message"]

        return True, response["response"]