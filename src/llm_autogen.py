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
def _write_search_refs(
    query,
    results,
    ref_fullpath
):
    with open(ref_fullpath, "a+") as f:
        f.write(f"Search query: {query}\n")

        for result in results:
            title = result["title"]
            url = result["href"].strip().replace(" ", "")
            f.write(f"- [{title}]({url})\n")

        f.write("\n")

    print("[_write_search_refs] finished")


def _write_arxiv_refs(
    query,
    results,
    ref_fullpath
):
    with open(ref_fullpath, "a+") as f:
        f.write(f"Arxiv query: {query}\n")

        for result in results:
            title = result.title
            url = result.entry_id.strip().replace(" ", "")
            f.write(f"- [{title}]({url})\n")

        f.write("\n")

    print("[_write_arxiv_refs] finished")


def search(
    query: str,
    max_results=3,
    max_attempts=3,
    timelimit="y",
    output_format="json_string"  # json_string | json_object
):
    auto_scrape = os.getenv("AN_AUTO_SCRAPE_ENABLED", "False")
    auto_scrape = utils.str2bool(auto_scrape)

    work_dir = os.getenv("AN_CURRENT_WORKDIR", "./")
    ref_filename = os.getenv("AN_REF_FILENAME", "")
    ref_fullpath = f"{work_dir}/{ref_filename}"

    print(f"[search] query: {query}, max_results: {max_results}, timelimit: {timelimit}, auto_scrape: {auto_scrape}, ref_fullpath: {ref_fullpath}")

    if not query:
        return "[]" if output_format == "json_string" else []

    attempts = 0
    results = []

    with DDGS() as ddgs:
        while attempts < max_attempts:
            try:
                # Tips: max_results=max_results only available when
                #       duckduckgo-search >= 3.9.x
                response = ddgs.text(
                    query,
                    max_results=max_results,
                    # timelimit=timelimit
                )

                results = list(islice(response, max_results))

                if results:
                    break

            except Exception as e:
                print(f"[search] Exception occurred during searching: {e}")

            attempts += 1
            time.sleep(1)

    print(f"[search] results: {results}")

    if auto_scrape:
        for result in results:
            title = result["title"]
            url = result["href"].strip().replace(" ", "")
            details = utils.prun(scrape, url=url)

            print(f"[search auto_scape] title: {title}, url: {url}, details: {details}")

            if details:
                result["details"] = details

    # Save refs
    _write_search_refs(query, results, ref_fullpath)

    if output_format == "json_string":
        return json.dumps(results, ensure_ascii=False, indent=4)
    else:
        return results


def scrape(
    url: str = "",
    output_format="json_string"  # json_string | json_object
):
    url = url.strip().replace(" ", "")
    print(f"[scrape] url: {url}")

    work_dir = os.getenv("AN_CURRENT_WORKDIR", "./")
    filename = os.getenv("AN_COLLECTION_FILENAME", "")
    filepath = f"{work_dir}/{filename}"
    print(f"[scrape] collection file path: {filepath}")

    content = ""

    try:
        content = utils.load_web(url)

    except Exception as e:
        print(f"[ERROR] Exception occurred: url: {url}, error: {e}")
        return "[]" if output_format == "json_string" else []

    print(f"[scrape] content length: {len(content)}, first 20 chars: {content[:20]} ...")

    output = content

    # Summarize when > 2k chars
    if len(content) > 2000:
        print(f"[scrape] content length: {len(content)}, summarize it...")
        llm_agent = LLMAgentSummary()
        llm_agent.init_prompt(translation_enabled=False)
        llm_agent.init_llm()

        SUMMARY_MAX_LENGTH = int(os.getenv("SUMMARY_MAX_LENGTH", 20000))
        print(f"Summary max length: {SUMMARY_MAX_LENGTH}")

        content = content[:SUMMARY_MAX_LENGTH]
        output = llm_agent.run(content)

    res = [
        {
            "href": url,
            "body": output,
        }
    ]

    with open(filepath, "a+") as f:
        f.write(f"URL: {url}\n")
        f.write(f"Body: {output}\n")
        f.write("=========")
        f.write("\n")

    if output_format == "json_string":
        return json.dumps(res, ensure_ascii=False, indent=4)
    else:
        return res


def arxiv_search(
    query: str,
    days_ago=365 * 10,
    max_results=5,
    output_format="json_string"  # json_string | json_object
):
    start_time = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).strftime('%Y%m%d%H%M%S')
    print(f"[arxiv_search] query: {query}, days_ago: {days_ago}, start_time: {start_time}, max_results: {max_results}")

    work_dir = os.getenv("AN_CURRENT_WORKDIR", "./")
    filename = os.getenv("AN_COLLECTION_FILENAME", "")
    filepath = f"{work_dir}/{filename}"

    ref_filename = os.getenv("AN_REF_FILENAME", "")
    ref_fullpath = f"{work_dir}/{ref_filename}"
    print(f"[arxiv_search] collection file path: {filepath}, ref path: {ref_fullpath}")

    # Search for papers
    results = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending
    )

    json_res = {}
    valid_papers = []

    for result in arxiv.Client().results(results):
        print(f"processed arxiv result: {result}, {result.title}, published time: {result.published.strftime('%Y%m%d%H%M%S')}, start_time: {start_time}")
        # Check if the paper was published >= start_time
        if result.published.strftime('%Y%m%d%H%M%S') >= start_time:
            authors = ', '.join(author.name for author in result.authors)
            print(f"| {result.title} | {authors} | {result.summary} | {result.entry_id} |")

            valid_papers.append(result)

            json_res[result.title] = {
                "authors": authors,
                "summary": result.summary,
                "URL": result.entry_id.strip().replace(" ", ""),
            }

            # Save collection full content
            if filepath:
                print(f"[arxiv_search] save collections into {filepath}")
                with open(filepath, "a+") as f:
                    f.write(f"Title: {result.title}\n")
                    f.write(f"URL: {result.entry_id}\n")
                    f.write(f"Summary: {result.summary}\n")
                    f.write("=========")
                    f.write("\n")

    # Save refs
    _write_arxiv_refs(query, valid_papers, ref_fullpath)

    if output_format == "json_string":
        return json.dumps(json_res, ensure_ascii=False, indent=4)
    else:
        return json_res


def write_to_file(text: str, filename: str, work_dir: str = ""):
    work_dir = work_dir or os.getenv("AN_CURRENT_WORKDIR", "./")
    filename = os.getenv("AN_OUTPUT_FILENAME", filename)
    filepath = f"{work_dir}/{filename}"

    print(f"[write_to_file] filename: {filename}, work_dir: {work_dir}, filepath: {filepath}, text: {text}")

    f = open(filepath, "w+")
    f.write(text)
    f.close()

    # return f"{text}\n\n{filename} TERMINATE"
    return "TERMINATE"


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

        self.functions_review = [
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

        self.llm_cfg_timeout = 180  # seconds
        self.llm_cfg_max_retries = 5

        print(f"[LLMAgentAutoGen] Initialize config: timeout: {self.llm_cfg_timeout}, max_retries: {self.llm_cfg_max_retries}")

        self.llm_config_gpt4 = {
            "timeout": self.llm_cfg_timeout,
            "max_retries": self.llm_cfg_max_retries,
            "cache_seed": 42,
            "temperature": 0,
            "config_list": self.gpt4_config_list,
        }

        self.llm_config_gpt3 = {
            "timeout": self.llm_cfg_timeout,
            "max_retries": self.llm_cfg_max_retries,
            "cache_seed": 42,
            "temperature": 0,
            "config_list": self.gpt3_config_list,
        }

        self.llm_config_gpt3_pub = {
            "timeout": self.llm_cfg_timeout,
            "max_retries": self.llm_cfg_max_retries,
            "cache_seed": 42,
            "temperature": 0,
            "config_list": self.gpt3_config_list,
            "functions": self.functions_pub,
        }

        self.llm_config_gpt3_collection = {
            "timeout": self.llm_cfg_timeout,
            "max_retries": self.llm_cfg_max_retries,
            "cache_seed": 42,
            "temperature": 0,
            "config_list": self.gpt3_config_list,
            "functions": self.functions_collection,
        }

        self.llm_config_gpt3_review = {
            "timeout": self.llm_cfg_timeout,
            "max_retries": self.llm_cfg_max_retries,
            "cache_seed": 42,
            "temperature": 0,
            "config_list": self.gpt3_config_list,
            "functions": self.functions_review,
        }

        # Tips: for gpt 3.5 agent keep thanking each other, append this one to the prompt to avoid it. ref: https://microsoft.github.io/autogen/docs/FAQ#agents-keep-thanking-each-other-when-using-gpt-35-turbo
        self.termination_notice = (
            '\n\nDo not show appreciation in your responses, say only what is necessary. '
        )

        # agents
        self.agent_planner = autogen.AssistantAgent(
            name="Planner",
            system_message="Planner. Suggest a plan. Revise the plan based on feedback from admin and critic, until admin approval. The plan may involve and engineer who can excute the task by provided tools/functions, or write the code only when provided functions cannot finish the task. Explain the plan first. Be clearwhich step is performed by an engineer, which step is performed by a scientist, which step is performed by a collector, and which step is performed by an editor." + self.termination_notice,
            llm_config=self.llm_config_gpt3,
        )

        self.agent_collector = autogen.AssistantAgent(
            name="Collector",
            # system_message=llm_prompts.AUTOGEN_COLLECTOR + self.termination_notice,
            system_message=llm_prompts.AUTOGEN_COLLECTOR2 + self.termination_notice,
            llm_config=self.llm_config_gpt3_collection,
        )

        self.agent_editor = autogen.AssistantAgent(
            name="Editor",
            # system_message=llm_prompts.AUTOGEN_EDITOR + self.termination_notice,
            system_message=llm_prompts.AUTOGEN_EDITOR2 + self.termination_notice,
            llm_config=self.llm_config_gpt3,
        )

        self.agent_writer = autogen.AssistantAgent(
            name="Writer",
            # system_message=llm_prompts.AUTOGEN_WRITER + self.termination_notice,
            system_message=llm_prompts.AUTOGEN_WRITER2 + self.termination_notice,
            llm_config=self.llm_config_gpt3,
        )

        self.agent_reviewer = autogen.AssistantAgent(
            name="Reviewer",
            # system_message=llm_prompts.AUTOGEN_REVIEWER + self.termination_notice,
            system_message=llm_prompts.AUTOGEN_REVIEWER2 + self.termination_notice,
            llm_config=self.llm_config_gpt3_review,
        )

        self.agent_publisher = autogen.AssistantAgent(
            name="Publisher",
            system_message=llm_prompts.AUTOGEN_PUBLISHER2 + self.termination_notice,
            llm_config=self.llm_config_gpt3_pub,
        )

        print("[LLMAgentAutoGen] Initialize finished")

    def init_prompt(self, prompt):
        return self

    def collect(
        self,
        query: str,
        work_dir: str,
        filename: str = "llm_collection.txt",
        ref_filename: str = "llm_ref.txt",
    ):
        print(f"[LLMAgentAutoGen.collect] query: {query}, work_dir: {work_dir}, filename: {filename}")

        user_proxy = autogen.UserProxyAgent(
            name="UserProxy",
            is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in "\n".join(x.get("content", "").rstrip().split("\n")[-2:]),
            human_input_mode="NEVER",
            # max_consecutive_auto_reply=10,
            code_execution_config={
                "last_n_messages": 2,
                "work_dir": work_dir,
            },
            system_message="A human admin. Interact with the editor to discuss the plan." + self.termination_notice,
        )

        user_proxy.register_function(
            function_map={
                "search": search,
                # "scrape": scrape,
                "arxiv": arxiv_search,
            }
        )

        # pass values to functions via env
        os.environ["AN_CURRENT_WORKDIR"] = work_dir
        os.environ["AN_COLLECTION_FILENAME"] = filename
        os.environ["AN_REF_FILENAME"] = ref_filename
        os.environ["AN_AUTO_SCRAPE_ENABLED"] = "True"

        user_proxy.initiate_chat(
            self.agent_collector,
            message=query,
        )

        data = user_proxy.last_message()["content"]
        print(f"collected (returned): {data}")

        # Tips: agent returned value may not reliable to use,
        # use file-based output instead
        full_path = f"{work_dir}/{filename}"
        data_from_file = utils.prun(utils.read_file, full_path=full_path)
        print(f"collected (from file): {data_from_file}")

        return data_from_file

    def gen_article(
        self,
        raw_query: str,
        query: str,
        work_dir: str,
        filename: str = "llm_article.txt",
        collection_filename: str = "llm_collection.txt",
        ref_filename: str = "llm_ref.txt",
    ):
        print(f"[LLMAgentAutoGen.gen_report] raw_query: {raw_query}, query: {query}, work_dir: {work_dir}, output filename: {filename}, collection filename: {collection_filename}")

        user_proxy = autogen.UserProxyAgent(
            name="UserProxy",
            is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
            human_input_mode="NEVER",
            # max_consecutive_auto_reply=1,
            code_execution_config=False,
            system_message="A human admin. Interact with the Editor to discuss the structure." + self.termination_notice,
        )

        agent_executor = autogen.UserProxyAgent(
            name="Executor",

            # The whole group chat will be ended after receiving the TERMINATE message
            is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),

            system_message="Executor. Execute the task by provided functions and report the result." + self.termination_notice,
            human_input_mode="NEVER",
            code_execution_config={
                "last_n_messages": 2,
                "work_dir": work_dir,
            },
        )

        checker = autogen.AssistantAgent(
            name="Checker",
            # system_message=llm_prompts.AUTOGEN_WRITER + self.termination_notice,
            system_message="Content Checker. According to the Reviewer's feedback, for content missing, gaps or low-quality part, find it from the provided materials first, if cannot find, leverage functions to search the content from Internet or search papers from Arxiv." + self.termination_notice,
            llm_config=self.llm_config_gpt3_review,
        )

        agent_executor.register_function(
            function_map={
                "search": search,
                "scrape": scrape,
                "arxiv": arxiv_search,
                "write_to_file": write_to_file,
            }
        )

        editor = autogen.AssistantAgent(
            name="Editor",
            # system_message=llm_prompts.AUTOGEN_EDITOR + self.termination_notice,
            # system_message=llm_prompts.AUTOGEN_EDITOR2 + self.termination_notice,
            system_message=llm_prompts.AUTOGEN_EDITOR3.format(raw_query) + self.termination_notice,
            llm_config=self.llm_config_gpt3,
        )

        writer = autogen.AssistantAgent(
            name="Writer",
            # system_message=llm_prompts.AUTOGEN_WRITER + self.termination_notice,
            system_message=llm_prompts.AUTOGEN_WRITER4 + self.termination_notice,
            # system_message=llm_prompts.AUTOGEN_WRITER3.format(raw_query) + self.termination_notice,
            llm_config=self.llm_config_gpt3,
        )

        # create group
        agents = [
            user_proxy,
            agent_executor,
            editor,
            writer,
            # checker,
            self.agent_reviewer,
            self.agent_publisher,
        ]

        groupchat = autogen.GroupChat(
            agents=agents,
            messages=[],
            max_round=30)

        manager = autogen.GroupChatManager(
            groupchat=groupchat,
            llm_config=self.llm_config_gpt3,
        )

        # Set current workdir first
        os.environ["AN_CURRENT_WORKDIR"] = work_dir
        os.environ["AN_OUTPUT_FILENAME"] = filename
        os.environ["AN_COLLECTION_FILENAME"] = collection_filename
        os.environ["AN_REF_FILENAME"] = ref_filename
        os.environ["AN_AUTO_SCRAPE_ENABLED"] = "True"

        user_proxy.initiate_chat(
            manager,
            message=query,
        )

        # after group chat finished, the result will be saved to a file
        article_from_ret = user_proxy.last_message()["content"]
        print(f"generated article (from group return value):\n{article_from_ret}")

        # Tips: the group chat may not ended correctly, in the case
        # the return value may not be reliable to use, here we read
        # it from the saved file instead until we figured a reliable
        # way to terminate the group chat
        full_path = f"{work_dir}/{filename}"
        print(f"generated article full path: {full_path}")

        article_from_file = utils.prun(utils.read_file, full_path=full_path)

        print()
        print(f"generated article (from file):\n{article_from_file}")

        return article_from_file
