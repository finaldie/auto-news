import json
import os

from langchain import LLMChain
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains.mapreduce import MapReduceChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI

import llm_prompts


class LLMAgentBase:
    def __init__(self, api_key, model_name):
        self.api_key = api_key
        self.model_name = model_name
        self.prompt_tpl = None
        self.llm = None
        self.llmchain = None

    def _init_prompt(self, prompt=None):
        prompt_tpl = PromptTemplate(
            input_variables=["content"],
            template=prompt,
        )

        print(f"Initialized prompt: {prompt_tpl}")
        self.prompt_tpl = prompt_tpl

    def init_llm(self):
        llm = ChatOpenAI(
            # model_name="text-davinci-003"
            model_name="gpt-3.5-turbo",
            # temperature dictates how whacky the output should be
            temperature=0.3)

        self.llm = llm
        self.llmchain = LLMChain(llm=self.llm, prompt=self.prompt_tpl)

    def parse_response_json(self, resp):
        res = resp.replace("\\n", "\n")
        res = resp.replace("\t", "")
        return res


class LLMAgentCategoryAndRanking(LLMAgentBase):
    def __init__(self, api_key="", model_name="gpt-3.5-turbo"):
        super().__init__(api_key, model_name)

    def init_prompt(self, prompt=None):
        prompt = prompt or llm_prompts.LLM_PROMPT_CATEGORY_AND_RANKING_TPL
        self._init_prompt(prompt)

    def run(self, text: str):
        """
        @return something like below
        {'topics': [
            {'topic': 'Jeff Dean', 'category': 'Person', 'score': 0.8},
            {'topic': 'Verena Rieser', 'category': 'Person', 'score': 0.7},
            {'topic': 'Google', 'category': 'Company', 'score': 0.9},
            {'topic': 'DeepMind', 'category': 'Company', 'score': 0.9},
            {'topic': 'Research Scientist', 'category': 'Position', 'score': 0.8}],
         'overall_score': 0.82
        }
        """
        response = self.llmchain.run(text)

        # fix the response json format
        response_json = self.parse_response_json(response)

        # return the json object
        return json.loads(response_json)


class LLMAgentSummary(LLMAgentBase):
    def __init__(self, api_key, model_name):
        super().__init__(api_key, model_name)

    def run(self, text: str):
        return True
