import os
import copy
import time
import json
import traceback
from datetime import date, datetime, timedelta

import utils
from notion import NotionAgent
from ops_base import OperatorBase
from db_cli import DBClient
from ops_notion import OperatorNotion

import llm_prompts
import llm_const
from llm_agent import (
    LLMAgentTranslation,
    LLMAgentGeneric,
)


class OperatorTODO(OperatorBase):
    """
    An Operator to handle:
    - pulling data from source
    - save to local json
    - restore from local json
    - dedup
    - generate todo list
    - publish
    """
    def pull(self, **kwargs):
        """
        @return pages <id, page>
        """
        takeaways_pages = self.pull_takeaways(**kwargs)
        journal_pages = self.pull_journal(**kwargs)

        return {
            "takeaways": takeaways_pages,
            "journal": journal_pages,
        }

    def dedup(self, pages):
        print("#####################################################")
        print("# TODO: dedup")
        print("#####################################################")
        takeaways_pages = pages["takeaways"]
        journal_pages = pages["journal"]

        dedup_takeaways_pages = self._dedup(takeaways_pages)
        dedup_journal_pages = self._dedup(journal_pages)

        print(f"Total takeaways {len(takeaways_pages)}, post dedup {len(dedup_takeaways_pages)}")
        print(f"Total journal {len(journal_pages)}, post dedup {len(dedup_journal_pages)}")

        return {
            "takeaways": dedup_takeaways_pages,
            "journal": dedup_journal_pages,
        }

    def _dedup(self, pages):
        dedup_pages = {}
        client = DBClient()

        for page_id, page in pages.items():
            last_edited_time = page["last_edited_time"]

            page_todo_meta = client.get_todo_item_id(page_id)
            print(f"_dedup: page_id: {page_id}, returned meta: {page_todo_meta}, current page last_edited_time: {last_edited_time}")

            page_todo_meta = utils.fix_and_parse_json(page_todo_meta)

            if not page_todo_meta or page_todo_meta.get("last_edited_time") != last_edited_time:
                dedup_pages[page_id] = page
                print(f"Valid page to generate TODO: page_id {page_id}, page name: {page.get('name')}, metadata: {page_todo_meta}")
            else:
                print(f"[WARN] same last_edited_time {last_edited_time}, skip this page id: {page_id}")

        return dedup_pages

    def generate(self, pages):
        print("#####################################################")
        print("# Generating TODOs for pages")
        print("#####################################################")

        takeaways_pages = pages["takeaways"]
        journal_pages = pages["journal"]

        print(f"Total takeaways pages: {len(takeaways_pages)}")
        print(f"Total journal pages: {len(journal_pages)}")

        extracted_takeaways_pages = self._get_takeaways_from_pages(takeaways_pages)
        print(f"Pages contains takeaways: {len(extracted_takeaways_pages)}")

        extracted_journal_pages = self._get_journals_from_pages(journal_pages)

        print(f"Pages contains journals: {len(extracted_journal_pages)}")

        extracted_pages = []
        extracted_pages.extend(extracted_takeaways_pages)
        extracted_pages.extend(extracted_journal_pages)

        llm_agent_todo = LLMAgentGeneric()
        llm_agent_todo.init_prompt(llm_prompts.LLM_PROMPT_ACTION_ITEM)
        llm_agent_todo.init_llm()

        llm_agent_trans = LLMAgentTranslation()
        llm_agent_trans.init_prompt()
        llm_agent_trans.init_llm()

        todo_pages = []

        excluded_sources = ["TODO", "Journal"]

        for page in extracted_pages:
            tags = page.get("tags") or []

            print(f"======= [Generating] page id: {page['id']}, title: {page['title']}, tags: {tags}")
            # This is the takeaways or journal content
            content = page["__content"]

            print(f"Content (Takeaways or Journal-notes): {content}")

            try:
                if page["source"] in excluded_sources:
                    print(f"Skip the page due to source excluded: {page['source']}")
                    continue

                if "action:deepdive" in tags:
                    print("Skip the page due to tag excluded: action:deepdive")
                    continue

                todo_list = llm_agent_todo.run(content)
                print(f"LLM: TODO list: {todo_list}")

                if todo_list in llm_const.LLM_INVALID_RESPONSES:
                    print(f"[WARN] generated TODO list is invalid ({todo_list}), skip it")
                    continue

                todo_page = copy.deepcopy(page)
                todo_page["todo"] = todo_list

                llm_translation_response_todo = llm_agent_trans.run(todo_list)
                print(f"LLM: Translation response: {llm_translation_response_todo}")
                todo_page["translation_todo"] = llm_translation_response_todo

                todo_pages.append(todo_page)

            except Exception as e:
                print(f"[ERROR] Exception occurred during LLM_Agent todo.run, {e}")

        print(f"Returns todo pages: {len(todo_pages)}")
        return todo_pages

    def _get_takeaways_from_pages(self, pages, **kwargs):
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)
        takeaway_pages = []

        for page_id, raw_page in pages.items():
            take_aways = notion_agent.extractRichText(
                raw_page["properties"]["properties"]["Take Aways"]["rich_text"])

            if not take_aways:
                continue

            page = copy.deepcopy(raw_page)
            page["__content"] = take_aways
            takeaway_pages.append(page)

        return takeaway_pages

    def _get_journals_from_pages(self, pages, **kwargs):
        journal_pages = []

        for page_id, raw_page in pages.items():
            content = f"{raw_page['title']} {raw_page['content']}"

            if not content:
                continue

            page = copy.deepcopy(raw_page)
            page["__content"] = content
            journal_pages.append(page)

        return journal_pages

    def push(self, pages, targets, **kwargs):
        print("#####################################################")
        print("# Push TODO Pages")
        print("#####################################################")
        print(f"Number of pages: {len(pages)}")
        print(f"Targets: {targets}")
        print(f"Input data: {pages}")

        start_date = kwargs.setdefault("start_date", date.today().isoformat())
        print(f"Start date: {start_date}")
        client = DBClient()

        for target in targets:
            print(f"Pushing data to target: {target} ...")

            if target == "notion":
                tot = 0
                err = 0

                notion_api_key = os.getenv("NOTION_TOKEN")
                notion_agent = NotionAgent(notion_api_key)
                op_notion = OperatorNotion()

                db_index_id = op_notion.get_index_toread_dbid()
                database_id = utils.get_notion_database_id_toread(
                    notion_agent, db_index_id)
                print(f"Latest ToRead database id: {database_id}")

                if not database_id:
                    print("[ERROR] no index db pages found... skip")
                    break

                for page in pages:
                    try:
                        print(f"====== Pushing page: {page} ======")

                        tot += 1
                        last_edited_time = page["last_edited_time"]
                        todo_list = page["todo"]
                        source = page["source"]

                        notion_agent.createDatabaseItem_ToRead_TODO(
                            database_id,
                            page)

                        # mark this todo as visited
                        client.set_todo_item_id(
                            page["id"],
                            json.dumps({
                                "last_edited_time": last_edited_time,
                                "todo": todo_list,
                            }),
                            overwrite=True
                        )

                        self.updateLastEditedTime(
                            last_edited_time,
                            source,
                            "todo",
                            client)

                    except Exception as e:
                        err += 1
                        print(f"[ERROR]: Pushing notion pages failed, skip: {e}")
                        traceback.print_exc()

                print(f"Pushing to {target} finished, total: {tot}, errors: {err}")

            else:
                print(f"[ERROR]: Unknown target {target}, skip")
