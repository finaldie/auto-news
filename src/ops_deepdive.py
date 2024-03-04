import os
import copy
import json
import traceback
from datetime import date

import utils
from notion import NotionAgent
from ops_base import OperatorBase
from db_cli import DBClient
from ops_notion import OperatorNotion

import llm_prompts
from llm_agent import (
    LLMAgentTranslation,
)

from llm_autogen import LLMAgentAutoGen


class OperatorDeepDive(OperatorBase):
    """
    An Operator to handle:
    - pulling data from source
    - save to local json
    - restore from local json
    - dedup
    - generate deep dive
    - publish
    """
    def pull(self, **kwargs):
        """
        @return pages <id, page>
        """
        takeaways_pages = self.pull_takeaways(**kwargs)

        return {
            "takeaways": takeaways_pages,
        }

    def dedup(self, pages):
        print("#####################################################")
        print("# DeepDive: dedup")
        print("#####################################################")
        takeaways_pages = pages["takeaways"]

        dedup_takeaways_pages = self._dedup(takeaways_pages)

        print(f"Total takeaways {len(takeaways_pages)}, post dedup {len(dedup_takeaways_pages)}")

        return {
            "takeaways": dedup_takeaways_pages,
        }

    def _dedup(self, pages):
        """
        One page only generate a deepdive once, the page updating won't
        trigger the deep dive action again
        """
        dedup_pages = {}
        client = DBClient()

        for page_id, page in pages.items():
            last_edited_time = page["last_edited_time"]

            page_action_meta = client.get_action_item_id(page_id)
            print(f"_dedup: page_id: {page_id}, returned meta: {page_action_meta}")

            page_action_meta = utils.fix_and_parse_json(page_action_meta)

            if not page_action_meta:
                dedup_pages[page_id] = page
                print(f"Valid page to trigger action: page_id {page_id}, page name: {page.get('name')}, metadata: {page_action_meta}")

            else:
                print(f"[WARN] same last_edited_time {last_edited_time}, skip this page: {page}")

        return dedup_pages

    def collect(self, pages, work_dir):
        print("#####################################################")
        print("# DeepDive: Collect information for takeaways pages")
        print("#####################################################")
        print(f"work_dir: {work_dir}")

        takeaways_pages = pages["takeaways"]
        extracted_pages = self._get_takeaways_from_pages(takeaways_pages)

        collected_pages = []
        tot = 0
        err = 0

        for page in extracted_pages:
            tot += 1
            tags = page["tags"]
            takeaways = page["__content"]

            print(f"[Processing ] page takeaways: {takeaways}, tags: {tags}")

            if "action:deepdive" in tags:
                new_page = copy.deepcopy(page)

                try:
                    agent_autogen = LLMAgentAutoGen()

                    # query = f"For the topic \'{takeaways}\', search from Internet to get top 3 articles and search papers from Arxiv, scrape the content, then return the aggregated results with reference link attached."
                    query = llm_prompts.AUTOGEN_DEEPDIVE_COLLECTION.format(takeaways)

                    print(f"Deep dive data collection query: {query}")

                    collection_filename = f"action_deepdive_collection_{new_page['id']}.txt"
                    print(f"Deep dive data collection filename: {collection_filename}")

                    ref_filename = f"action_deepdive_refs_{new_page['id']}.txt"
                    print(f"Deep dive ref filename: {ref_filename}")

                    collected_data = agent_autogen.collect(
                        query=query,
                        work_dir=work_dir,
                        filename=collection_filename,
                        ref_filename=ref_filename,
                    )

                    new_page["__deepdive_collection"] = collected_data or ""
                    new_page["__deepdive_collection_filename"] = collection_filename
                    new_page["__deepdive_ref_filename"] = ref_filename

                    collected_pages.append(new_page)

                except Exception as e:
                    err += 1
                    print(f"[ERROR] Exception occurred during deep dive collection, skip it: {e}")

        print(f"Collected pages {tot}, errors {err}")
        return collected_pages

    def _deepdive(
        self,
        iter_cnt,
        agent_autogen,
        work_dir,
        collection_filename,
        ref_filename,
        raw_query,
        full_query,
        dd_page,
    ):
        """
        dd_page: Output page for holding deepdive
        """
        print(f"Deep dive article query: {full_query}")

        output_filename = f"action_deepdive_article_{dd_page['id']}_v{iter_cnt}.txt"
        print(f"Deep dive article filename: {output_filename}")

        article = agent_autogen.gen_article(
            raw_query=raw_query,
            query=full_query,
            work_dir=work_dir,
            filename=output_filename,
            collection_filename=collection_filename,
            ref_filename=ref_filename,
        )

        collection_path = f"{work_dir}/{collection_filename}"
        collection_updated = utils.prun(utils.read_file, full_path=collection_path)

        ref_path = f"{work_dir}/{ref_filename}"
        ref_data = utils.prun(utils.read_file, full_path=ref_path)

        deepdive_content = f"{raw_query} (version {iter_cnt})\n\n{article}"
        print(f"[AutoGen]: generated deepdive article: {deepdive_content}")

        # keep each iteration version
        dd_page[f"__deepdive_v{iter_cnt}"] = deepdive_content

        # __deepdive is the latest one for publishing
        dd_page["__deepdive"] = deepdive_content

        dd_page["__deepdive_collection_updated"] = collection_updated
        dd_page["__deepdive_ref_data"] = ref_data

        # Return the raw article
        return article

    def deepdive(self, pages, work_dir):
        print("#####################################################")
        print("# DeepDive: Generating result for pages")
        print("#####################################################")
        print(f"work_dir: {work_dir}")

        print(f"Total takeaways pages: {len(pages)}")

        extracted_pages = []
        extracted_pages.extend(pages)

        agent_autogen = LLMAgentAutoGen()

        llm_agent_trans = LLMAgentTranslation()
        llm_agent_trans.init_prompt()
        llm_agent_trans.init_llm()

        dd_pages = []
        tot = 0
        err = 0

        for page in extracted_pages:
            tot += 1
            print(f"======= [Generating DeepDive] page id: {page['id']}, title: {page['title']}")

            # This is the takeaways or journal content
            content = page["__content"]
            print(f"Raw query: {content}")

            collected_data = page["__deepdive_collection"]
            collection_filename = page["__deepdive_collection_filename"]
            ref_filename = page["__deepdive_ref_filename"]

            if collected_data:
                print(f"Collected_data (first 30chars): {collected_data[:30]}")

            # Start deepdive iterations
            try:
                iter_max_cnt = int(os.getenv("ACTION_DEEPDIVE_ITERATIONS", 3))
                print(f"Iteration max count: {iter_max_cnt}")

                dd_page = copy.deepcopy(page)

                latest_deepdive_content = ""
                latest_collection_content = ""

                for iter_cnt in range(iter_max_cnt):
                    print(f"------ [Generating DeepDive] Iteration {iter_cnt + 1}")

                    # TODO: For very long deep dive article, use RAG
                    # instead of passing entire reference data
                    query = ""

                    if iter_cnt == 0:
                        query = llm_prompts.AUTOGEN_DEEPDIVE_ARTICLE.format(
                            content, collected_data)

                    else:
                        query = llm_prompts.AUTOGEN_DEEPDIVE_FOLLOWUP.format(
                            content,
                            latest_deepdive_content,
                            latest_collection_content)

                    article = self._deepdive(
                        iter_cnt + 1,
                        agent_autogen,
                        work_dir,
                        collection_filename,
                        ref_filename,
                        content,
                        query,
                        dd_page
                    )

                    latest_deepdive_content = article
                    latest_collection_content = dd_page["__deepdive_collection_updated"]

                # After all iterations, do translation if needed
                if os.getenv("TRANSLATION_LANG"):
                    llm_translation_response = llm_agent_trans.run(dd_page["__deepdive"])
                    print(f"LLM: Translation response: {llm_translation_response}")
                    dd_page["__translation_deepdive"] = llm_translation_response

                dd_pages.append(dd_page)

            except Exception as e:
                err += 1
                print(f"[ERROR] Exception occurred during LLM_Agent.generate: {e}")

        print(f"Returns pages: {len(dd_pages)}, total {tot}, errors {err}")
        return dd_pages

    def _get_takeaways_from_pages(self, pages, **kwargs):
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)
        takeaway_pages = []

        for page_id, raw_page in pages.items():
            takeaways = notion_agent.extractRichText(
                raw_page["properties"]["properties"]["Take Aways"]["rich_text"])

            if not takeaways:
                continue

            page = copy.deepcopy(raw_page)
            page["__content"] = takeaways
            takeaway_pages.append(page)

        return takeaway_pages

    def push(self, pages, targets, **kwargs):
        print("#####################################################")
        print("# Push DeepDive Pages")
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
                        takeaways = page["__content"]

                        print(f"====== Pushing page for: {takeaways} ======")

                        tot += 1
                        last_edited_time = page["last_edited_time"]
                        source = page["source"]

                        notion_agent.createDatabaseItem_ToRead_DeepDive(
                            database_id,
                            page)

                        # mark this action:deepdive as visited
                        client.set_action_item_id(
                            page["id"],
                            json.dumps({
                                "last_edited_time": last_edited_time,
                                "title": takeaways,
                            }),
                            overwrite=True
                        )

                        self.updateLastEditedTime(
                            last_edited_time,
                            source,
                            "deepdive",
                            client)

                    except Exception as e:
                        err += 1
                        print(f"[ERROR]: Pushing notion pages failed, skip: {e}")
                        traceback.print_exc()

                print(f"Pushing to {target} finished, total: {tot}, errors: {err}")

            else:
                print(f"[ERROR]: Unknown target {target}, skip")
