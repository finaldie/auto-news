from langchain import LLMChain
from langchain.text_splitter import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter
)
from langchain.chains.mapreduce import MapReduceChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.document_loaders import YoutubeLoader
from langchain.document_loaders import WebBaseLoader

import llm_prompts


class LLMWebLoader:
    def load(self, url: str) -> list:
        if not url:
            return []

        loader = WebBaseLoader(url)
        docs = loader.load()
        return docs


class LLMYoutubeLoader:
    def load(self, url: str) -> list:
        if not url:
            return []

        loader = YoutubeLoader.from_youtube_url(url, add_video_info=True)
        docs = loader.load()
        return docs


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

    def init_llm(self, model_name="gpt-3.5-turbo", temperature=0):
        llm = ChatOpenAI(
            # model_name="text-davinci-003"
            model_name=model_name,
            # temperature dictates how whacky the output should be
            # for fixed response format task, set temperature = 0
            temperature=temperature)

        self.llm = llm
        self.llmchain = LLMChain(llm=self.llm, prompt=self.prompt_tpl)
        print(f"LLM chain initalized, model_name: {model_name}, temperature: {temperature}")


class LLMAgentCategoryAndRanking(LLMAgentBase):
    def __init__(self, api_key="", model_name="gpt-3.5-turbo"):
        super().__init__(api_key, model_name)

    def init_prompt(self, prompt=None):
        prompt = prompt or llm_prompts.LLM_PROMPT_CATEGORY_AND_RANKING_TPL2
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

        return response


class LLMAgentSummary(LLMAgentBase):
    def __init__(self, api_key="", model_name="gpt-3.5-turbo"):
        super().__init__(api_key, model_name)

    def init_prompt(self, prompt=None):
        self.user_prompt = prompt

    def init_llm(
        self,
        model_name="gpt-3.5-turbo",
        temperature=0,
        chain_type="map_reduce",
        verbose=False
    ):
        llm = ChatOpenAI(
            # model_name="text-davinci-003"
            model_name=model_name,
            # temperature dictates how whacky the output should be
            # for fixed response format task, set temperature = 0
            temperature=temperature)

        self.llm = llm
        self.llmchain = load_summarize_chain(
            self.llm,
            chain_type=chain_type,
            verbose=verbose)

        print(f"LLM chain initalized, model_name: {model_name}, temperature: {temperature}, chain_type: {chain_type}")

    def run(
        self,
        text: str,
        chunk_size=1024,
        chunk_overlap=0,
    ):
        print(f"[LLM] input text ({len(text)} chars): {text}")

        if not text:
            print("[LLM] Empty input text, return empty summary")
            return ""

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        docs = text_splitter.create_documents([text])
        print(f"[LLM] number of splitted docs: {len(docs)}")

        summary_resp = self.llmchain.run(docs)
        return summary_resp
