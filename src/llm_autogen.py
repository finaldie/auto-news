import os
import time

from itertools import islice
from duckduckgo_search import DDGS
import autogen

from llm_agent import (
    LLMAgentSummary,
)

import utils


#######################################################################
# Utils
#######################################################################
def search(query: str, max_results=3, max_attempts=3, timelimit="m"):
    print(f"[utils.search] query: {query}, max_results: {max_results}")

    if not query:
        return {
            "status": "ERROR",  # OK | ERROR | TIMEOUT
            "body": []
        }

    attempts = 0

    with DDGS() as ddgs:
        while attempts < max_attempts:
            response = ddgs.text(query, max_results=max_results, timelimit=timelimit)
            results = list(islice(response, max_results))

            if results:
                return {
                    "status": "OK",
                    "body": results,
                }

            attempts += 1
            time.sleep(1)

    return {
        "status": "ERROR",
        "body": [],
    }


def scrape(url: str):
    content = ""

    try:
        content = utils.load_web(url)

    except Exception as e:
        print(f"[ERROR] Exception occurred: url: {url}, error: {e}")
        return False

    llm_agent = LLMAgentSummary()
    llm_agent.init_prompt()
    llm_agent.init_llm()

    SUMMARY_MAX_LENGTH = int(os.getenv("SUMMARY_MAX_LENGTH", 20000))
    print(f"Summary max length: {SUMMARY_MAX_LENGTH}")

    content = content[:SUMMARY_MAX_LENGTH]
    summary = llm_agent.run(content)
    return summary


#######################################################################
# Agents
#######################################################################
class LLMAgentAutoGen:
    def __init__(self):
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

        _gpt3_model_name = os.getenv("AUTOGEN_GPT3_MODEL", "gpt-4-1106-preview")
        _gpt3_api_version = os.getenv("AUTOGEN_GPT3_API_VERSION", "2023-08-01-preview")
        _gpt3_api_key = os.getenv("AUTOGEN_GPT3_API_KEY", "")

        self.gpt3_config_list = [{
            "model": _gpt3_model_name,
            "api_version": _gpt3_api_version,
            "api_key": _gpt3_api_key,
        }]

        print(f"[LLMAgentAutoGen] Initialize GPT3 model_name: {_gpt3_model_name}, api_version: {_gpt3_api_version}")

        self.llm_config_gpt4 = {
            "timeout": 600,
            "cache_seed": 42,
            "temperature": 0,
            "config_list": self.gpt4_config_list,
        }

        self.llm_config_gpt3 = {
            "timeout": 600,
            "cache_seed": 42,
            "temperature": 0,
            "config_list": self.gpt3_config_list,
        }

        # functions
        self.functions = [
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
                "description": "Scraping website content based on url",
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
        ]

        # agents
        self.agent_planner = autogen.AssistantAgent(
            name="Planner",
            system_message="Planner. Suggest a plan. Revise the plan based on feedback from admin and critic, until admin approval. The plan may involve and engineer who can excute the task by provided tools/functions, or write the code only when provided functions cannot finish the task. Explain the plan first. Be clearwhich step is performed by an engineer, which step is performed by a scientist, which step is performed by a collector, and which step is performed by an editor.",
            llm_config=self.llm_config_gpt3,
        )

        self.agent_collector = autogen.AssistantAgent(
            name="Collector",
            system_message="Research for the given query, collect as many information as possible, and generate detailed research results with loads of technique details with all reference links attached; Add TERMINATE to the end of the research report;",
            llm_config=self.llm_config_gpt3,
        )

        self.agent_scientist = autogen.AssistantAgent(
            name="Scientist",
            system_message="",
            llm_config=self.llm_config_gpt3,
        )

        self.agent_editor = autogen.AssistantAgent(
            name="Editor",
            system_message="You are a senior editor of an AI blogger, you will define the structure of a short blog post based on material provided by the researcher, and give it to the writer to write the blog post",
            llm_config=self.llm_config_gpt3,
        )

        self.agent_writer = autogen.AssistantAgent(
            name="Writer",
            system_message="You are a professional blogger, you will write a short blog post based on the structured provided by the editor, and feedback from reviewer; After 2 rounds of content iteration, add TERMINATE to the end of the message",
            llm_config=self.llm_config_gpt3,
        )

        self.agent_reviewer = autogen.AssistantAgent(
            name="Reviewer",
            system_message="You are a world class hash tech blog content critic, you will review & critic the written blog and provide feedback to writer. After 2 rounds of content iteration, add TERMINATE to the end of the message",
            llm_config=self.llm_config_gpt3,
        )

        self.agent_user_proxy = autogen.UserProxyAgent(
            name="UserProxy",
            is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
            human_input_model="NEVER",
            max_consecutive_auto_reply=10,
            code_execution_config=False,
            llm_config=self.llm_config_gpt3,
            system_message="A human admin. Interact with the planner to discuss the plan. Plan execution needs to be approved by this admin",
        )

        self.agent_executor = autogen.UserProxyAgent(
            name="Executor",
            system_message="Executor. Execute the task by provided funtions and report the result.",
            human_input_model="NEVER",
            code_execution_config={
                "last_n_messages": 2,
                "work_dir": "data/autogen"
            },
        )

        self.agent_executor.register_function(
            function_map={
                "search": search,
                "scrape": scrape,
            }
        )

        # create group
        self.agents = [
            self.agent_editor,
            self.agent_writer,
            self.agent_planner,
            self.agent_scientist,
            self.agent_collector,
            self.agent_reviewer,
            self.agent_user_proxy,
            self.agent_executor,
        ]

        self.groupchat = autogen.GroupChat(
            agents=self.agents,
            messages=[],
            max_round=50)

        self.manager = autogen.GroupChatManager(
            groupchat=self.groupchat,
            llm_config=self.llm_config_gpt3,
        )

        print("[LLMAgentAutoGen] Initialize finished")

    def init_prompt(self, prompt):
        return self

    def run(self, text: str):
        tokens = self.get_num_tokens(text)
        print(f"[LLMAgentAutoGen] number of tokens: {tokens}, text: {text}")

        self.agent_user_proxy.initiate_chat(
            self.manager,
            message=text,
        )

        return self.agent_user_proxy.last_message()["content"]
