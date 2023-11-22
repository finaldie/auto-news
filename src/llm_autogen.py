import os
import time
import json
import datetime

from itertools import islice
from duckduckgo_search import DDGS
import autogen

import llm_prompts
from llm_agent import (
    LLMAgentBase,
    LLMAgentSummary,
)

import utils
import arxiv


#######################################################################
# Utils
#######################################################################
def search(query: str, max_results=3, max_attempts=3, timelimit="m"):
    print(f"[utils.search] query: {query}, max_results: {max_results}, timelimit: {timelimit}")

    if not query:
        return "[]"

    attempts = 0

    with DDGS() as ddgs:
        while attempts < max_attempts:
            # Tips: max_results=max_results only available when
            #       duckduckgo-search >= 3.9.x
            response = ddgs.text(
                query,
                max_results=max_results,
                timelimit=timelimit)

            results = list(islice(response, max_results))

            if results:
                return json.dumps(results, ensure_ascii=False, indent=4)

            attempts += 1
            time.sleep(1)

    return "[]"


def scrape(url: str):
    print(f"[scrape] url: {url}")

    content = ""

    try:
        content = utils.load_web(url)

    except Exception as e:
        print(f"[ERROR] Exception occurred: url: {url}, error: {e}")
        return False

    llm_agent = LLMAgentSummary()
    llm_agent.init_prompt(llm_prompts.LLM_PROMPT_SUMMARY_SIMPLE)
    llm_agent.init_llm()

    SUMMARY_MAX_LENGTH = int(os.getenv("SUMMARY_MAX_LENGTH", 20000))
    print(f"Summary max length: {SUMMARY_MAX_LENGTH}")

    content = content[:SUMMARY_MAX_LENGTH]
    summary = llm_agent.run(content)
    return summary


def arxiv_search(query: str, days_ago=30, max_results=10):
    start_time = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).strftime('%Y%m%d%H%M%S')
    print(f"[arxiv_search] query: {query}, days_ago: {days_ago}, start_time: {start_time}, max_results: {max_results}")

    # Search for papers
    results = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending
    )

    json_res = {}

    for result in arxiv.Client().results(results):
        print(f"processed arxiv result: {result}, published time: {result.published.strftime('%Y%m%d%H%M%S')}, start_time: {start_time}")
        # Check if the paper was published >= start_time
        if result.published.strftime('%Y%m%d%H%M%S') >= start_time:
            print(f"| {result.title} | {', '.join(author.name for author in result.authors)} | {result.summary} | {result.entry_id} |")

            json_res[result.title] = {
                "authors": ', '.join(author.name for author in result.authors),
                "summary": result.summary,
                "URL": result.entry_id,
            }

    return json.dumps(json_res, ensure_ascii=False, indent=4)


def write_to_file(text: str, filename: str, work_dir: str = ""):
    work_dir = work_dir or os.getenv("AN_CURRENT_WORKDIR", "./")
    filename = os.getenv("AN_FILENAME", filename)
    filepath = f"{work_dir}/{filename}"

    print(f"[write_to_file] filename: {filename}, work_dir: {work_dir}, filepath: {filepath}, text: {text}")

    f = open(filepath, "w+")
    f.write(text)
    f.close()

    return f"{text}\n\n{filename} TERMINATE"


#######################################################################
# Agents
#######################################################################
class LLMAgentAutoGen(LLMAgentBase):
    def __init__(self):
        super().__init__("", "")

        _gpt4_model_name = os.getenv("AUTOGEN_GPT4_MODEL", "gpt-4-1106-preview")
        _gpt4_api_version = os.getenv("AUTOGEN_GPT4_API_VERSION", "2023-08-01-preview")
        _gpt4_api_key = os.getenv("AUTOGEN_GPT4_API_KEY", "")

        # create autogen user proxy and assisants
        self.gpt4_config_list = [{
            "model": _gpt4_model_name,
            "api_version": _gpt4_api_version,
            "api_key": _gpt4_api_key,
        }]

        print(f"[LLMAgentAutoGen] Initialize GPT4 model_name: {_gpt4_model_name}, api_version: {_gpt4_api_version}")

        _gpt3_model_name = os.getenv("AUTOGEN_GPT3_MODEL", "gpt-3.5-turbo-1106")
        _gpt3_api_version = os.getenv("AUTOGEN_GPT3_API_VERSION", "2023-08-01-preview")
        _gpt3_api_key = os.getenv("AUTOGEN_GPT3_API_KEY", "")

        self.gpt3_config_list = [{
            "model": _gpt3_model_name,
            "api_version": _gpt3_api_version,
            "api_key": _gpt3_api_key,
        }]

        # functions
        self.functions_collection = [
            {
                "name": "search",
                "description": "google search for relevant information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Google search query",
                        }
                    },
                    "required": ["query"],
                },
            },

            {
                "name": "scrape",
                "description": "Scraping and summarize website content based on url",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Website url to scrape",
                        }
                    },
                    "required": ["url"],
                },
            },

            {
                "name": "arxiv",
                "description": "arxiv search for relevant papers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Arxiv search query",
                        }
                    },
                    "required": ["query"],
                },
            },
        ]

        self.functions_pub = [
            {
                "name": "write_to_file",
                "description": "write text to file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to write to file",
                        },
                        "filename": {
                            "type": "string",
                            "description": "The filename to save the text",
                        },
                    },
                    "required": ["text", "filename"],
                },
            },
        ]

        print(f"[LLMAgentAutoGen] Initialize GPT3 model_name: {_gpt3_model_name}, api_version: {_gpt3_api_version}")

        self.llm_config_gpt4 = {
            "timeout": 120,
            "max_retries": 2,
            "cache_seed": 42,
            "temperature": 0,
            "config_list": self.gpt4_config_list,
        }

        self.llm_config_gpt3 = {
            "timeout": 120,
            "max_retries": 2,
            "cache_seed": 42,
            "temperature": 0,
            "config_list": self.gpt3_config_list,
        }

        self.llm_config_gpt3_pub = {
            "timeout": 120,
            "max_retries": 2,
            "cache_seed": 42,
            "temperature": 0,
            "config_list": self.gpt3_config_list,
            "functions": self.functions_pub,
        }

        self.llm_config_gpt3_collection = {
            "timeout": 120,
            "max_retries": 2,
            "cache_seed": 42,
            "temperature": 0,
            "config_list": self.gpt3_config_list,
            "functions": self.functions_collection,
        }

        # agents
        self.agent_planner = autogen.AssistantAgent(
            name="Planner",
            system_message="Planner. Suggest a plan. Revise the plan based on feedback from admin and critic, until admin approval. The plan may involve and engineer who can excute the task by provided tools/functions, or write the code only when provided functions cannot finish the task. Explain the plan first. Be clearwhich step is performed by an engineer, which step is performed by a scientist, which step is performed by a collector, and which step is performed by an editor.",
            llm_config=self.llm_config_gpt3,
        )

        self.agent_collector = autogen.AssistantAgent(
            name="Collector",
            system_message="Information Collector. For the given query, collect as much information as possible. You can get the data from the web search or Arxiv, then scrape the content; Add TERMINATE to the end of the research report.",
            llm_config=self.llm_config_gpt3_collection,
        )

        self.agent_editor = autogen.AssistantAgent(
            name="Editor",
            system_message="You are a senior editor. You will define the structure based on user's query and material provided, and give it to the Writer to write the article.",
            llm_config=self.llm_config_gpt3,
        )

        self.agent_writer = autogen.AssistantAgent(
            name="Writer",
            system_message="You are a professional article writer, you will write an article with in-depth insights based on the structure provided by the editor and the feedback from the Reviewer.",
            llm_config=self.llm_config_gpt3,
        )

        self.agent_reviewer = autogen.AssistantAgent(
            name="Reviewer",
            system_message="You are a world-class tech article critic, you will review and critique the written article and provide feedback to Writer. After 2 rounds of reviewihng iteration with the Writer, pass the article to the Publisher.",
            llm_config=self.llm_config_gpt3,
        )

        self.agent_publisher = autogen.AssistantAgent(
            name="Publisher",
            system_message="Publisher. You will get the article after reviewer's review, then save the article to a file.",
            llm_config=self.llm_config_gpt3_pub,
        )

        print("[LLMAgentAutoGen] Initialize finished")

    def init_prompt(self, prompt):
        return self

    def collect(self, query: str, work_dir: str):
        print(f"[LLMAgentAutoGen.collect] query: {query}, work_dir: {work_dir}")

        user_proxy = autogen.UserProxyAgent(
            name="UserProxy",
            is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in "\n".join(x.get("content", "").rstrip().split("\n")[-2:]),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            code_execution_config={
                "last_n_messages": 2,
                "work_dir": work_dir,
            },
            llm_config=self.llm_config_gpt3,
            system_message="A human admin. Interact with the editor to discuss the plan.",
        )

        user_proxy.register_function(
            function_map={
                "search": search,
                "scrape": scrape,
                "arxiv": arxiv_search,
            }
        )

        user_proxy.initiate_chat(
            self.agent_collector,
            message=query,
        )

        data = user_proxy.last_message()["content"]
        print(f"collected: {data}")

        return data

    def gen_article(
        self,
        query: str,
        work_dir: str,
        filename: str = "llm_article.txt"
    ):
        print(f"[LLMAgentAutoGen.gen_report] query: {query}, work_dir: {work_dir}, filename: {filename}")

        user_proxy = autogen.UserProxyAgent(
            name="UserProxy",
            is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
            code_execution_config=False,
            llm_config=self.llm_config_gpt3,
            system_message="A human admin. Interact with the editor to discuss the plan.",
        )

        agent_executor = autogen.UserProxyAgent(
            name="Executor",

            # The whole group chat will be ended after receiving the TERMINATE message
            is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),

            system_message="Executor. Execute the task by provided functions and report the result.",
            human_input_mode="NEVER",
            code_execution_config={
                "last_n_messages": 2,
                "work_dir": work_dir,
            },
        )

        agent_executor.register_function(
            function_map={
                "write_to_file": write_to_file,
            }
        )

        # create group
        agents = [
            user_proxy,
            agent_executor,
            self.agent_editor,
            self.agent_writer,
            self.agent_reviewer,
            self.agent_publisher,
        ]

        groupchat = autogen.GroupChat(
            agents=agents,
            messages=[],
            max_round=50)

        manager = autogen.GroupChatManager(
            groupchat=groupchat,
            llm_config=self.llm_config_gpt3,
        )

        # Set current workdir first
        os.environ["AN_CURRENT_WORKDIR"] = work_dir
        os.environ["AN_FILENAME"] = filename

        user_proxy.initiate_chat(
            manager,
            message=query,
        )

        # after group chat finished, the result will be saved to a file
        article = user_proxy.last_message()["content"]
        print(f"generated article:\n{article}")

        return article
