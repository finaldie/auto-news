import os

import httpx
from langchain import LLMChain
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter
)
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain_community.chat_models import ChatOllama
from langchain_community.document_loaders import YoutubeLoader
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders import ArxivLoader
from langchain.utilities.arxiv import ArxivAPIWrapper
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai

import llm_prompts


#######################################################################
# Loaders
#######################################################################
class LLMWebLoader:
    def load(self, url: str) -> list:
        if not url:
            return []

        loader = WebBaseLoader([url])
        docs = loader.load()
        return docs


class LLMYoutubeLoader:
    def load(
        self,
        url: str,
        language: str = "en",
        continue_on_failure: bool = False,
    ) -> list:
        if not url:
            return []

        docs = []

        try:
            loader = YoutubeLoader.from_youtube_url(
                url,
                add_video_info=True,
                language=language,
                continue_on_failure=continue_on_failure
            )

            docs = loader.load()

        except Exception as e:
            print(f"[WARN] LLMYoutubeLoader load transcript failed: {e}")
            # traceback.print_exc()

        return docs


class LLMArxivLoader:
    def isvalid(self, url):
        return url.startswith("https://arxiv.org")

    def load_from_url(self, url, load_all_available_meta=True, max_chars=4000):
        if not self.isvalid(url):
            return False, {}

        arxiv_id = url.split("/")[-1]

        # Fix potential wrong id
        arxiv_id = arxiv_id.replace(".pdf", "")
        print(f"[_load_arxiv]: arxiv_id: {arxiv_id}")

        # According to the arxiv identifier https://info.arxiv.org/help/arxiv_identifier.html
        # the format could be 1501.0001[vx] or 1501.00001[vx]
        # Here the library cannot fetch the id with version > v1
        # example: 1706.03762v6, will return empty docs
        if "v" in arxiv_id:
            idx = 0
            for idx in range(len(arxiv_id)):
                if arxiv_id[idx] == "v":
                    break

            arxiv_id = arxiv_id[:idx]

        print(f"[_load_arxiv]: final arxiv_id: {arxiv_id}")

        docs = self.load_doc_from_id(
            arxiv_id,
            load_all_available_meta=load_all_available_meta,
            max_chars=max_chars)

        if len(docs) == 0:
            print("[_load_arxiv]: Empty docs loaded")
            return False, {}

        meta = docs[0].metadata
        pdf_url = ""
        for link in meta['links']:
            if "pdf" in link:
                pdf_url = link
                break

        print(f"[_load_arxiv]: Found PDF link: {pdf_url}")

        text = f"""
        Published: {meta['Published']},
        Published First Time: {meta['published_first_time']},
        Title: {meta['Title']},
        Authors: {meta['Authors']},
        Url: {meta['entry_id']},
        Primary Category: {meta['primary_category']},
        Categories: {meta['categories']},
        PDF Link: {pdf_url},
        """

        res = {
            "doc": docs[0],
            "metadata": meta,
            "metadata_text": text,
        }

        return True, res

    def load_from_id(self, arxiv_id, load_all_available_meta=True):
        """
        Load doc and metadata, doc has 4000 chars limitation
        """
        docs = []

        try:
            docs = ArxivLoader(
                query=arxiv_id,
                load_all_available_meta=load_all_available_meta
            ).load()

        except Exception as e:
            print(f"[ERROR] LLMArxivLoader.load failed: {e}")

        return docs

    def load_doc_from_id(self, arxiv_id, load_all_available_meta=True, max_chars=100000):
        docs = []

        try:
            arxiv_client = ArxivAPIWrapper(
                load_max_docs=100,
                load_all_available_meta=load_all_available_meta,
                doc_content_chars_max=max_chars,
            )

            docs = arxiv_client.load(query=arxiv_id)

        except Exception as e:
            print(f"[ERROR] LLMArxivLoader.load_doc failed: {e}")

        return docs


#######################################################################
# Agents
#######################################################################
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

    def init_llm(
        self,
        provider=None,
        model_name=None,
        temperature=0,
        create_default_chain=True
    ):
        provider = provider or os.getenv("LLM_PROVIDER", "openai")
        llm = None

        # TODO: support non-openAI llm
        if provider == "openai":
            model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            if os.getenv('OPENAI_PROXY') is not None:
                client = httpx.Client(proxies={"http://": os.getenv("OPENAI_PROXY"),
                                               "https://": os.getenv("OPENAI_PROXY")})
                llm = ChatOpenAI(
                    # model_name="text-davinci-003"
                    model_name=model_name,
                    http_client=client,
                    # temperature dictates how whacky the output should be
                    # for fixed response format task, set temperature = 0
                    temperature=temperature)
            else:
                llm = ChatOpenAI(
                    # model_name="text-davinci-003"
                    model_name=model_name,
                    # temperature dictates how whacky the output should be
                    # for fixed response format task, set temperature = 0
                    temperature=temperature)

        elif provider == "google":
            model_name = model_name or os.getenv("GOOGLE_MODEL", "gemini-pro")

            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature)

        elif provider == "ollama":
            model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3")
            ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

            llm = ChatOllama(
                base_url=ollama_url,
                model=model_name,
                temperature=temperature,
            )

        else:
            print(f"[ERROR] Non-supported LLM provider: {provider}")
            raise

        self.llm = llm

        # Create a default chain
        if create_default_chain:
            self.llmchain = LLMChain(llm=self.llm, prompt=self.prompt_tpl)

        print(f"LLM chain initalized, provider: {provider}, model_name: {model_name}, temperature: {temperature}")

    def get_num_tokens(self, text):
        return self.llm.get_num_tokens(text)


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
        tokens = self.get_num_tokens(text)
        print(f"[LLM] Category and Ranking, number of tokens: {tokens}")

        response = self.llmchain.run(text)
        return response


class LLMAgentSummary(LLMAgentBase):
    def __init__(self, api_key="", model_name="gpt-3.5-turbo"):
        super().__init__(api_key, model_name)

    def init_prompt(
        self,
        map_prompt=None,
        combine_prompt=None,
        translation_enabled=True
    ):
        self.map_prompt = map_prompt
        self.combine_prompt = combine_prompt

        if not self.combine_prompt:
            translation_lang = os.getenv("TRANSLATION_LANG")
            print(f"[LLMAgentSummary] translation language: {translation_lang}, translation_enabled: {translation_enabled}")

            prompt_no_translation = llm_prompts.LLM_PROMPT_SUMMARY_COMBINE_PROMPT3
            prompt_with_translation = llm_prompts.LLM_PROMPT_SUMMARY_COMBINE_PROMPT3 + llm_prompts.LLM_PROMPT_SUMMARY_COMBINE_PROMPT_SUFFIX.format(translation_lang, translation_lang)

            # When user specific translation language in the config AND
            # translation_enabled=True, we use combined translation
            # prompt
            prompt_tpl = prompt_with_translation if translation_lang and translation_enabled else prompt_no_translation
            self.combine_prompt = prompt_tpl

        self.combine_prompt_tpl = PromptTemplate(
            template=self.combine_prompt,
            input_variables=["text"])

        print(f"[LLMAgentSummary] Initialized prompt: {self.combine_prompt_tpl}")

    def init_llm(
        self,
        provider=None,
        model_name=None,
        temperature=0,
        chain_type="map_reduce",
        verbose=False
    ):
        super().init_llm(
            provider,
            model_name,
            temperature,
            create_default_chain=False)

        self.llmchain = load_summarize_chain(
            self.llm,
            combine_prompt=self.combine_prompt_tpl,
            chain_type=chain_type,
            verbose=verbose)

        print(f"[LLMAgentSummary] LLM chain initalized, provider: {provider}, model_name: {model_name}, temperature: {temperature}, chain_type: {chain_type}")

    def run(
        self,
        text: str,
        chunk_size=None,
        chunk_overlap=None,
    ):
        chunk_size = chunk_size or int(os.getenv("TEXT_CHUNK_SIZE", 2048))
        chunk_overlap = chunk_overlap or int(os.getenv("TEXT_CHUNK_OVERLAP", 256))

        print(f"[LLM] input text ({len(text)} chars), chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap}, text: {text[:200]}")

        if not text:
            print("[LLM] Empty input text, return empty summary")
            return ""

        tokens = self.get_num_tokens(text)
        print(f"[LLM] Summary, number of tokens needed: {tokens}")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        docs = text_splitter.create_documents([text])
        print(f"[LLM] number of splitted docs: {len(docs)}")

        summary_resp = self.llmchain.run(docs)
        return summary_resp


class LLMAgentJournal(LLMAgentBase):
    def __init__(self, api_key="", model_name="gpt-3.5-turbo"):
        super().__init__(api_key, model_name)

    def init_prompt(self, prompt=None):
        if not prompt:
            prompt = llm_prompts.LLM_PROMPT_JOURNAL_PREFIX.strip()
            prompt += llm_prompts.LLM_PROMPT_JOURNAL_SUFFIX.strip()

        self._init_prompt(prompt)

    def run(self, text: str):
        tokens = self.get_num_tokens(text)
        print(f"[LLMAgentJournal] number of tokens: {tokens}")

        response = self.llmchain.run(text)
        return response


class LLMAgentTranslation(LLMAgentBase):
    def __init__(self, api_key="", model_name="gpt-3.5-turbo"):
        super().__init__(api_key, model_name)

    def init_prompt(self, prompt=None, trans_lang=None):
        if not prompt:
            translation_lang = trans_lang or os.getenv("TRANSLATION_LANG")
            print(f"[LLMAgentTranslation] translation language: {translation_lang}")

            prompt = llm_prompts.LLM_PROMPT_TRANSLATION.format(translation_lang) + "{content}"
            prompt = prompt.strip()

        self._init_prompt(prompt)

    def run(self, text: str):
        tokens = self.get_num_tokens(text)
        print(f"[LLMAgentTranslation] number of tokens: {tokens}")

        response = self.llmchain.run(text)
        return response


class LLMAgentGeneric(LLMAgentBase):
    def __init__(self, api_key="", model_name="gpt-3.5-turbo"):
        super().__init__(api_key, model_name)

    def init_prompt(self, prompt):
        self._init_prompt(prompt.strip())
        return self

    def run(self, text: str):
        tokens = self.get_num_tokens(text)
        print(f"[LLMAgentGeneric] number of tokens: {tokens}")

        response = self.llmchain.run(text)
        return response


class LLMAgentGemini:
    """
    A Gemini standalone LLM
    """
    def __init__(self, api_key="", model_name="gemini-pro", temperature=0):
        self.api_key = api_key if api_key else os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name or os.getenv("GOOGLE_MODEL", "gemini-pro")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        self.temperature = temperature

    def init_prompt(self, prompt=""):
        self.default_prompt = """
        Write a concise and precise numbered list summary of the following text without losing any numbers and key points (English numbers need to be converted to digital numbers): {}
        """

        self.prompt = prompt or self.default_prompt

    def init_llm(self):
        pass

    def run(self, text: str):
        prompt = self.prompt.format(text)
        print(f"[LLMAgentGemini] prompt: {prompt}")

        response = self.model.generate_content(
            prompt,

            # pass a config
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature),

            # safety settings
            safety_settings={
                'HARASSMENT'        : 'block_none',
                'HATE_SPEECH'       : 'block_none',
                'DANGEROUS_CONTENT' : 'block_none',
                'SEXUALLY_EXPLICIT' : 'block_none',
            }
        )

        return response
