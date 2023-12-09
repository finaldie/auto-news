import os
import time
from datetime import date, datetime, timedelta

import utils
from notion import NotionAgent
from ops_base import OperatorBase
from db_cli import DBClient
from ops_notion import OperatorNotion
import llm_prompts
from llm_agent import (
    LLMAgentJournal,
    LLMAgentTranslation,
    LLMAgentGeneric,
)


class OperatorJournal(OperatorBase):
    """
    An Operator to handle:
    - pulling data from source
    - save to local json
    - restore from local json
    - dedup
    - summarization
    - ranking
    - publish
    """

    def pull(self, **kwargs):
        """
        Pull Journal

        @return pages <id, page>
        """
        print("#####################################################")
        print("# Pulling Journal Items")
        print("#####################################################")
        sources = kwargs.setdefault("sources", ["Journal"])
        print(f"sources: {sources}")

        # 0. Get last_created_time
        client = DBClient()
        last_created_time = client.get_notion_inbox_created_time(
            "journal", "default")

        last_created_time = utils.bytes2str(last_created_time)
        print(f"Get last_created_time from redis: {last_created_time}")

        if not last_created_time:
            last_created_time = (datetime.now() - timedelta(days=365)).isoformat()

        print(f"last_created_time: {last_created_time}")

        # 1. prepare notion agent and db connection
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)
        op_notion = OperatorNotion()

        # 2. get inbox database indexes
        db_index_id = op_notion.get_index_inbox_dbid()

        db_pages = utils.get_notion_database_pages_inbox(
            notion_agent, db_index_id, "Journal")
        print(f"The database pages founded: {db_pages}")

        # 2. get latest two databases and collect recent items
        db_pages = db_pages[:2]
        print(f"The latest 2 databases: {db_pages}")

        page_list = {}

        for db_page in db_pages:
            database_id = db_page["database_id"]
            print(f"Pulling from database_id: {database_id}...")

            for source in sources:
                print(f"Querying source: {source} ...")
                # The api will return the pages and sort by "created time" asc
                # format dict(<page_id, page>)
                pages = notion_agent.queryDatabaseInbox_Journal(
                    database_id,
                    filter_created_time=last_created_time)

                page_list.update(pages)

                # Wait a moment to mitigate rate limiting
                wait_for_secs = 5
                print(f"Wait for a moment: {wait_for_secs}s")
                time.sleep(wait_for_secs)

        print(f"Pulled total {len(page_list)} items")
        return page_list

    def refine(self, pages, **kwargs):
        """
        Aggregate journal pages (ideally last day) and do content refinement
        """
        print("#####################################################")
        print("# Refine Journal Pages")
        print("#####################################################")
        today = kwargs.setdefault("today", date.today().isoformat())

        llm_agent = LLMAgentJournal()
        llm_agent.init_prompt()
        llm_agent.init_llm()

        content = ""
        last_created_time = ""
        for page_id, page in pages.items():
            content += f"{page['title']} {page['content']}" + "\n"
            last_created_time = page["created_time"]

        print(f"Journal input content: [{content}]")

        if not content:
            return [{
                "name": f"{today}",
                "source": "Journal",
                "last_created_time": last_created_time,
                "text": "",
                "translation": "",
                "title": f"{today} n/a",
                "todo": "n/a",
                "translation_todo": "n/a",
            }]

        llm_response = llm_agent.run(content)
        print(f"Refine content llm response: {llm_response}")

        # Generate title
        llm_agent_title = LLMAgentGeneric()
        llm_agent_title.init_prompt(llm_prompts.LLM_PROMPT_TITLE)
        llm_agent_title.init_llm()

        title = llm_agent_title.run(llm_response)
        print(f"Journal Title: {title}")

        # Generate insights
        llm_agent_insights = LLMAgentGeneric()
        llm_agent_insights.init_prompt(llm_prompts.LLM_PROMPT_KEY_INSIGHTS)
        llm_agent_insights.init_llm()

        insights = llm_agent_insights.run(llm_response)
        print(f"Journal insights: {insights}")

        # Generate takeaways
        llm_agent_takeaways = LLMAgentGeneric()
        llm_agent_takeaways.init_prompt(llm_prompts.LLM_PROMPT_TAKEAWAYS)
        llm_agent_takeaways.init_llm()

        takeaways = llm_agent_takeaways.run(llm_response)
        print(f"Journal takeaways: {takeaways}")

        # Generate action items
        llm_agent_todo = LLMAgentGeneric()
        llm_agent_todo.init_prompt(llm_prompts.LLM_PROMPT_ACTION_ITEM)
        llm_agent_todo.init_llm()

        todo_list = llm_agent_todo.run(llm_response)
        print(f"Journal TODO list: {todo_list}")

        # Generate action items
        llm_agent_summary = LLMAgentGeneric()
        llm_agent_summary.init_prompt(llm_prompts.LLM_PROMPT_SUMMARY_SIMPLE2)
        llm_agent_summary.init_llm()

        summary = llm_agent_summary.run(llm_response)
        print(f"Journal summary: {summary}")

        # Combine all sections together
        header_insights = "Critical Insights\n" if "Critical Insights" not in insights else ""
        header_takeaways = "Takeaways\n" if "Takeaways" not in takeaways else ""
        header_todo = "Action Items\n" if "Action Items" not in todo_list else ""

        full_content = f"{today} {title}\n\n{llm_response}\n\n{header_insights}{insights}\n\n{header_takeaways}{takeaways}\n\n{header_todo}{todo_list}\n\nOverall:\n{summary}"
        print(f"full_content: {full_content}")

        # Generate translation
        llm_agent_trans = LLMAgentTranslation()
        llm_agent_trans.init_prompt()
        llm_agent_trans.init_llm()

        llm_translation_response = llm_agent_trans.run(full_content)
        print(f"Translation llm response: {llm_translation_response}")

        llm_translation_response_todo = llm_agent_trans.run(todo_list)
        print(f"Translation llm response (todo): {llm_translation_response_todo}")

        journal_pages = []
        journal_page = {
            "name": f"{today}",
            "source": "Journal",
            "last_created_time": last_created_time,
            "text": full_content,
            "translation": llm_translation_response,
            "title": f"{today} {title}",
            "todo": todo_list or "n/a",
            "translation_todo": llm_translation_response_todo or "n/a",
        }

        journal_pages.append(journal_page)

        print(f"journal pages: {journal_pages}")
        return journal_pages

    def push(self, pages, targets, **kwargs):
        print("#####################################################")
        print("# Push Journal Pages")
        print("#####################################################")
        print(f"Number of pages: {len(pages)}")
        print(f"Input data: {pages}")
        print(f"Targets: {targets}")

        start_date = kwargs.setdefault("start_date", date.today().isoformat())
        print(f"Start date: {start_date}")

        for target in targets:
            print(f"Pushing data to target: {target} ...")

            if target == "notion":
                tot = 0
                err = 0

                notion_api_key = os.getenv("NOTION_TOKEN")
                notion_agent = NotionAgent(notion_api_key)
                op_notion = OperatorNotion()

                # Get the latest toread database id from index db
                db_index_id = op_notion.get_index_toread_dbid()
                database_id = utils.get_notion_database_id_toread(
                    notion_agent, db_index_id)
                print(f"Latest ToRead database id: {database_id}")

                if not database_id:
                    print("[ERROR] no index db pages found... skip")
                    break

                for page in pages:
                    tot += 1
                    title = page["name"]
                    full_title = page["title"]
                    print(f"Pushing title: {title}, full title: {full_title}")
                    print(f"Todo list: {page['todo']}")

                    try:
                        notion_agent.createDatabaseItem_ToRead_Journal(
                            database_id,
                            page)

                        self.updateCreatedTime(
                            page["last_created_time"],
                            source="journal",
                            list_name="default")

                    except Exception as e:
                        err += 1
                        print(f"[ERROR] Failed to push notion page for Journal: {e}")

                print(f"Pushing to {target} finished, total: {tot}, errors: {err}")

            else:
                print(f"[ERROR]: Unknown target {target}, skip")
