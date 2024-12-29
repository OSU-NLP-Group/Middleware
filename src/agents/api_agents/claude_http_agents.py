import anthropic
from src.agent import Agent
from src.utils import replace_image_url, image_to_base64
import os
import json
import backoff
import requests
from http import HTTPStatus
import http.client
from typing import List, Callable
import dataclasses
from copy import deepcopy

import time


class ClaudeHttp(Agent):
    def __init__(self, api_args=None, **config):
        if not api_args:
            api_args = {}
        api_args = deepcopy(api_args)
        self.key = api_args.pop("key", None)
        api_args["model"] = api_args.pop("model", None)
        if not self.key:
            raise ValueError("Claude API KEY is required, please assign api_args.key or set OPENAI_API_KEY environment variable.")
        if not api_args["model"]:
            raise ValueError("Claude model is required, please assign api_args.model.")
        self.api_args = api_args
        # if not self.api_args.get("stop_sequences"):
        #     self.api_args["stop_sequences"] = [anthropic.HUMAN_PROMPT]
        super().__init__(**config)


    @backoff.on_exception(backoff.expo, (anthropic.InternalServerError, anthropic.RateLimitError), max_tries=10)
    def inference(self, history: List[dict]) -> str:

        # time.sleep(5)

        conn = http.client.HTTPSConnection("cn2us02.opapi.win", timeout=900)

        # first convert into openai formats
        history = replace_image_url(history, keep_path=False, throw_details=False)
        history = json.loads(json.dumps(history))
        for h in history:
            if h['role'] == 'agent':
                h['role'] = 'assistant'
            # convert the openai format to claude format
            if isinstance(h['content'], list):
                for i, c in enumerate(h['content']):
                    if isinstance(c, dict) and c.get('type') == 'image_url':
                        new_c = {}
                        new_c['type'] = 'image'
                        new_c['source'] = {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": c['image_url']['url'].split(",")[1],
                        }
                        h['content'][i] = new_c
        
        payload = {
            "messages": history,
            **self.api_args
        }
        payload = json.dumps(payload)
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.key}',
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json'
        }

        try:
            conn.request("POST", "/v1/messages", payload, headers)
            res = conn.getresponse()
            data = res.read()
            response = json.loads(data.decode("utf-8"))
        except Exception as e:
            return str(e)
        
        if "statusCode" in response and response["statusCode"] != 200:
            return response["message"]


        return response["content"][0]["text"]
