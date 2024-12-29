from src.agent import Agent
from src.utils import replace_image_url, image_to_base64
import os
import json
import backoff
import requests
from typing import List, Callable
import dataclasses
from copy import deepcopy

import requests
from PIL import Image
from typing import List, Tuple
import time
from http import HTTPStatus
import json
import os
import google.auth
from google.oauth2 import service_account
from google.auth.transport.requests import Request


def reduce_image_size(image_url: str, ratio=0.5) -> str:
    img = Image.open(image_url)
    # print image size
    img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)))
    # img.save(f"{image_url.split('.')[0]}_reduced.{image_url.split('.')[1]}")
    img.save(image_url)


class Gemini(Agent):
    def __init__(self, api_args=None, **config):
        if not api_args:
            api_args = {}
        api_args = deepcopy(api_args)
        self.key_file = api_args.pop("key_file", None) or os.getenv('GCLOUD_KEY_FILE_PATHY')
        api_args["model"] = api_args.pop("model", None)
        if not self.key_file:
            raise ValueError("Claude API KEY is required, please assign api_args.key or set OPENAI_API_KEY environment variable.")
        if not api_args["model"]:
            raise ValueError("Gemini model is required, please assign api_args.model.")
        
        with open(self.key_file, "r") as f:
            project_id = json.load(f)["project_id"]
        region_code = "asia-east1"
        self.api_url = f"https://{region_code}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{region_code}/publishers/google/models/{api_args['model']}"

        self.api_args = {}
        self.api_args["temperature"] = api_args.get("temperature", 0.0)
        self.api_args["maxOutputTokens"] = api_args.get("max_tokens", 256)
        self.api_args["stopSequences"] = api_args.get("stop_sequences", ["\n\n###\n\n"])

        self.low_resolution = api_args.get("low_resolution", False)

        self.api_key = self.get_gcloud_token()
        fail_time = 0
        while not self.api_key and fail_time < 5:
            time.sleep(5)
            self.api_key = self.get_gcloud_token()
            fail_time += 1
        if not self.api_key:
            raise ValueError("Failed to get gcloud token.")

        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ]

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        super().__init__(**config)

    def get_gcloud_token(self):
        try:
            # Load the credentials from the key file
            creds = service_account.Credentials.from_service_account_file(
                self.key_file,
                # You can list multiple scopes if needed
                scopes=['https://www.googleapis.com/auth/cloud-platform']  
            )

            # Refresh the token (this is needed even for the first time)
            creds.refresh(Request())

            # Print the access token
            return creds.token

        except Exception as e:
            print(f"An error occurred while trying to fetch the gcloud token: {str(e)}")
            return None

    def process_history(self, history: List[dict]) -> List[dict]:
        history = replace_image_url(history, keep_path=False, throw_details=False)
        parts = []
        dialog = ""
        for message in history:
            if message["role"] == "system":
                dialog += "SYSTEM:\n"
                dialog += message["content"] + "\n\n###\n\n"
            if message["role"] == "user":
                dialog += "USER:\n"
                for content in message["content"]:
                    if isinstance(content, str):
                        dialog += content + "\n"
                    elif content["type"] == "text":
                        dialog += content["text"] + "\n"
                    elif content["type"] == "image_url":
                        parts.append({
                            "text": dialog
                        })
                        dialog = ""
                        image_type = content["image_url"]["url"].split("data:")[1].split(";base64,")[0]
                        image_base64 = content["image_url"]["url"].split(";base64,")[1]
                        parts.append({
                            "inline_data": {
                                "mime_type": image_type,
                                "data": image_base64
                            }
                        })
                dialog += "\n\n###\n\n"
            if message["role"] == "agent":
                dialog += "ASSISTANT:\n"
                dialog += message["content"] + "\n\n###\n\n"
        
        parts.append({
            "text": dialog + "ASSISTANT:\n"
        })
        
        new_messages = [
            {
                "parts": parts,
                "role": "user"
            }
        ]

        return new_messages


    # @backoff.on_exception(backoff.expo, (anthropic.InternalServerError, anthropic.RateLimitError), max_tries=10)
    def inference(self, history: List[dict]) -> str:
        # if self.low_resolution:
        #     # fetch the image url in the last message in the history and reduce the size
        #     message = history[-1]
        #     if isinstance(message["content"], list):
        #         for content in message["content"]:
        #             if content["type"] == "image_url":
        #                 image_url = content["image_url"]["url"].split(";base64,")[1]
        #                 reduce_image_size(image_url, ratio=0.3)
        #                 print("hongpangsile")

        # time.sleep(15)

        new_messages = self.process_history(history)
        

        payload = {
            "contents": new_messages,
            "generationConfig": self.api_args,
            "safetySettings": self.safety_settings
        }   

        retry = 0
        while True:
            retry += 1
            if retry > 3:
                return "max retry reached"
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=120
            )

            # update the api key
            api_key = self.get_gcloud_token()
            fail_time = 0
            while not api_key and fail_time < 10:
                time.sleep(5)
                api_key = self.get_gcloud_token()
                fail_time += 1
            self.headers["Authorization"] = f"Bearer {api_key}"

            # print("response", response)
            response = response.json()
            print("response", response)
            if 'error' in response:
                if "but model only supports up to 8128" in response['error']['message']:
                    # aggressive truncation for gemini-1.0
                    payload = {
                        "contents": self.process_history(history[:3]),
                        "generationConfig": self.api_args,
                        "safetySettings": self.safety_settings
                    }   

            if  "candidates" not in response:
                print(response)
                continue
            if 'content' in response["candidates"][0]:
                break

        return response['candidates'][0]['content']['parts'][0]['text']
