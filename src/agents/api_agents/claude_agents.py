import anthropic
from src.agent import Agent
from src.utils import replace_image_url, image_to_base64
import os
import json
import backoff
import requests
from typing import List, Callable
import dataclasses
from copy import deepcopy

import time


class Claude(Agent):
    def __init__(self, api_args=None, **config):
        if not api_args:
            api_args = {}
        api_args = deepcopy(api_args)
        self.key = api_args.pop("key", None) or os.getenv('Claude_API_KEY')
        api_args["model"] = api_args.pop("model", None)
        if not self.key:
            raise ValueError("Claude API KEY is required, please assign api_args.key or set OPENAI_API_KEY environment variable.")
        if not api_args["model"]:
            raise ValueError("Claude model is required, please assign api_args.model.")
        self.api_args = api_args
        if not self.api_args.get("stop_sequences"):
            self.api_args["stop_sequences"] = [anthropic.HUMAN_PROMPT]
        super().__init__(**config)


    @backoff.on_exception(backoff.expo, (anthropic.InternalServerError, anthropic.RateLimitError), max_tries=10)
    def inference(self, history: List[dict]) -> str:
        # this is the code for Claude 1, which is deprecated
        # prompt = ""
        # for message in history:
        #     if message["role"] == "user":
        #         prompt += anthropic.HUMAN_PROMPT + message["content"]
        #     else:
        #         prompt += anthropic.AI_PROMPT + message["content"]
        # prompt += anthropic.AI_PROMPT
        # c = anthropic.Client(self.key)
        # resp = c.completion(
        #     prompt=prompt,
        #     **self.api_args
        # )
        # return resp

        time.sleep(5)

        # for claude 3
        client = anthropic.Anthropic(
            api_key=self.key,
        )
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

        resp = client.messages.create(
            messages=history,
            **self.api_args
        )

        return resp.content[0].text
