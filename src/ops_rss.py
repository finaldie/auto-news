import os
import time
import copy
import traceback
from operator import itemgetter
from datetime import date, datetime
from time import mktime

from notion import NotionAgent
from llm_agent import (
    LLMAgentCategoryAndRanking,
    LLMAgentSummary,
)
import utils
from ops_base import OperatorBase
from db_cli import DBClient
from ops_milvus import OperatorMilvus
from ops_notion import OperatorNotion

import feedparser


class OperatorRSS(OperatorBase):
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

    def _fetch_articles(self, list_name, feed_url, count=3):
        """
        Fetch artciles from feed url (pull last n)
        """
        print(f"[fetch_articles] list_name: {list_name}, feed_url: {feed_url}, count: {count}")

        # Parse the RSS feed
        feed = feedparser.parse(feed_url)
        pulled_cnt = 0

        articles = []
        for entry in feed.entries:
            pulled_cnt += 1

            if pulled_cnt > count:
                print(f"[fetch_articles] Stop pulling, reached count: {count}")
                break

            # Extract relevant information from each entry
            title = entry.title
            link = entry.link

            # Example: Thu, 03 Mar 2022 08:00:00 GMT
            published = entry.published
            published_parsed = entry.published_parsed
            published_key = published

            # Convert above struct_time object to datetime
            created_time = date.today().isoformat()
            if published_parsed:
                dt = datetime.fromtimestamp(mktime(published_parsed))
                created_time = dt.isoformat()

                # Notes: The feedparser returns unreliable dates, e.g.
                # sometimes 2023-05-25T16:09:00.004-07:00
                # sometimes 2023-05-25T16:09:00.003-07:00
                # It leads the inconsistent md5 hash result which
                # causes duplicate result, so use YYYY-MM-DD instead
                published_key = dt.strftime("%Y-%m-%d")

            hash_key = f"{list_name}_{title}_{published_key}".encode('utf-8')
            article_id = utils.hashcode_md5(hash_key)

            print(f"[fetch_articles] pulled_cnt: {pulled_cnt}, list_name: {list_name}, title: {title}, published: {created_time}, article_id: {article_id}, hash_key: [{hash_key}]")

            # Create a dictionary representing an article
            article = {
                "id": article_id,
                'source': "RSS",
                'list_name': list_name,
                'title': title,
                'url': link,
                'created_time': created_time,
                "summary": entry.get("summary") or "",
                "content": "",
                "tags": entry.get("tags") or [],
                "published": published,
                "published_key": published_key,
            }

            # Add the article to the list
            articles.append(article)

        return articles

    def pull(self):
        """
        Pull RSS

        @return pages <id, page>
        """
        print("#####################################################")
        print("# Pulling RSS")
        print("#####################################################")
        # 1. prepare notion agent and db connection
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)
        op_notion = OperatorNotion()

        # 2. get inbox database indexes
        # db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_INBOX")
        db_index_id = op_notion.get_index_inbox_dbid()

        db_pages = utils.get_notion_database_pages_inbox(
            notion_agent, db_index_id, "RSS")
        print(f"The database pages founded: {db_pages}")

        # 2. get latest two databases and collect rss list
        db_pages = db_pages[:2]
        print(f"The latest 2 databases: {db_pages}")

        rss_list = []

        for db_page in db_pages:
            database_id = db_page["database_id"]
            print(f"Pulling from database_id: {database_id}...")

            # The api will return the pages and sort by "created time" asc
            # format dict(<page_id, page>)
            rss = notion_agent.queryDatabase_RSSList(database_id)

            rss_list.extend(rss)

        # 3. Fetch articles from rss list
        pages = {}

        for rss in rss_list:
            name = rss["name"]
            url = rss["url"]
            print(f"Fetching RSS: {name}, url: {url}")

            articles = self._fetch_articles(name, url, count=3)
            print(f"articles: {articles}")

            for article in articles:
                page_id = article["id"]

                pages[page_id] = article

        return pages

    def dedup(self, extractedPages, target="inbox"):
        print("#####################################################")
        print("# Dedup RSS")
        print("#####################################################")
        print(f"Number of pages: {len(extractedPages)}")

        client = DBClient()
        deduped_pages = []

        for page_id, page in extractedPages.items():
            title = page["title"]
            list_name = page["list_name"]
            created_time = page["created_time"]

            print(f"Dedupping page, title: {title}, list_name: {list_name}, created_time: {created_time}, page_id: {page_id}")

            if not client.get_notion_toread_item_id(
                    "rss", list_name, page_id):
                deduped_pages.append(page)
                print(f" - No duplicate RSS article found, move to next. title: {title}, page_id: {page_id}")

        return deduped_pages

    def filter(self, pages, **kwargs):
        print("#####################################################")
        print("# Filter RSS (After Scoring)")
        print("#####################################################")
        k = kwargs.setdefault("k", 3)
        min_score = kwargs.setdefault("min_score", 4)
        print(f"k: {k}, input size: {len(pages)}, min_score: {min_score}")

        # 1. filter all score >= min_score
        filtered1 = []
        for page in pages:
            relevant_score = page["__relevant_score"]

            if relevant_score < 0 or relevant_score >= min_score:
                filtered1.append(page)

        # 2. get top k
        tops = sorted(filtered1, key=lambda page: page["__relevant_score"], reverse=True)
        print(f"After sorting: {tops}")

        filtered2 = []
        for i in range(min(k, len(tops))):
            filtered2.append(tops[i])

        print(f"Filter output size: {len(filtered2)}")
        return filtered2

    def score(self, data, **kwargs):
        print("#####################################################")
        print("# Scoring RSS")
        print("#####################################################")
        start_date = kwargs.setdefault("start_date", "")
        max_distance = kwargs.setdefault("max_distance", 0.45)
        print(f"start_date: {start_date}, max_distance: {max_distance}")

        op_milvus = OperatorMilvus()
        client = DBClient()

        scored_list = []

        for page in data:
            try:
                title = page["title"]

                # Get a summary text (at most 1024 chars)
                score_text = f"{page['title']} - {page['list_name']} - {page['summary']}"
                score_text = score_text[:1024]
                print(f"Scoring page: {title}, score_text: {score_text}")

                relevant_metas = op_milvus.get_relevant(
                    start_date, score_text, topk=2,
                    max_distance=max_distance, db_client=client)

                page_score = op_milvus.score(relevant_metas)

                scored_page = copy.deepcopy(page)
                scored_page["__relevant_score"] = page_score

                scored_list.append(scored_page)
                print(f"RSS article scored {page_score}")

            except Exception as e:
                print(f"[ERROR]: Score page failed, skip: {e}")
                traceback.print_exc()

        print(f"Scored_pages ({len(scored_list)}): {scored_list}")
        return scored_list

    def summarize(self, pages):
        print("#####################################################")
        print("# Summarize RSS Articles")
        print("#####################################################")
        SUMMARY_MAX_LENGTH = int(os.getenv("SUMMARY_MAX_LENGTH", 20000))
        print(f"Number of pages: {len(pages)}")
        print(f"Summary max length: {SUMMARY_MAX_LENGTH}")

        llm_agent = LLMAgentSummary()
        llm_agent.init_prompt()
        llm_agent.init_llm()

        client = DBClient()
        redis_key_expire_time = os.getenv(
            "BOT_REDIS_KEY_EXPIRE_TIME", 604800)

        summarized_pages = []

        for page in pages:
            page_id = page["id"]
            title = page["title"]
            content = page["content"]
            list_name = page["list_name"]
            source_url = page["url"]
            print(f"Summarying page, title: {title}, list_name: {list_name}")
            # print(f"Page content ({len(content)} chars): {content}")

            st = time.time()

            llm_summary_resp = client.get_notion_summary_item_id(
                "rss", list_name, page_id)

            if not llm_summary_resp:
                # Double check the content, if empty, load it from
                # the source url. For RSS, we will load content
                # from this entrypoint
                if not content:
                    print("page content is empty, fallback to load web page via WebBaseLoader")

                    try:
                        content = utils.load_web(source_url)
                        print(f"Page content ({len(content)} chars)")

                    except Exception as e:
                        print(f"[ERROR] Exception occurred during utils.load_web(), source_url: {source_url}, {e}")

                    if not content:
                        print("[ERROR] Empty Web page loaded via WebBaseLoader, skip it")
                        continue

                content = content[:SUMMARY_MAX_LENGTH]
                summary = llm_agent.run(content)

                print(f"Cache llm response for {redis_key_expire_time}s, page_id: {page_id}, summary: {summary}")
                client.set_notion_summary_item_id(
                    "rss", list_name, page_id, summary,
                    expired_time=int(redis_key_expire_time))

            else:
                print("Found llm summary from cache, decoding (utf-8) ...")
                summary = utils.bytes2str(llm_summary_resp)

            # assemble summary into page
            summarized_page = copy.deepcopy(page)
            summarized_page["__summary"] = summary

            print(f"Used {time.time() - st:.3f}s, Summarized page_id: {page_id}, summary: {summary}")
            summarized_pages.append(summarized_page)

        return summarized_pages

    def rank(self, pages):
        """
        Rank page summary (not the entire content)
        """
        print("#####################################################")
        print("# Rank RSS Articles")
        print("#####################################################")
        ENABLED = utils.str2bool(os.getenv("RSS_ENABLE_CLASSIFICATION", "False"))
        print(f"Number of pages: {len(pages)}, enabled: {ENABLED}")

        llm_agent = LLMAgentCategoryAndRanking()
        llm_agent.init_prompt()
        llm_agent.init_llm()

        client = DBClient()
        redis_key_expire_time = os.getenv(
            "BOT_REDIS_KEY_EXPIRE_TIME", 604800)

        # array of ranged pages
        ranked = []

        for page in pages:
            title = page["title"]
            page_id = page["id"]
            list_name = page["list_name"]
            text = page["__summary"]
            print(f"Ranking page, title: {title}")

            # Let LLM to category and rank
            st = time.time()

            # Parse LLM response and assemble category and rank
            ranked_page = copy.deepcopy(page)

            if not ENABLED:
                ranked_page["__topics"] = []
                ranked_page["__categories"] = []
                ranked_page["__rate"] = -0.02

                ranked.append(ranked_page)
                continue

            llm_ranking_resp = client.get_notion_ranking_item_id(
                "rss", list_name, page_id)

            category_and_rank_str = None

            if not llm_ranking_resp:
                print("Not found category_and_rank_str in cache, fallback to llm_agent to rank")
                category_and_rank_str = llm_agent.run(text)

                print(f"Cache llm response for {redis_key_expire_time}s, page_id: {page_id}")
                client.set_notion_ranking_item_id(
                    "rss", list_name, page_id,
                    category_and_rank_str,
                    expired_time=int(redis_key_expire_time))

            else:
                print("Found category_and_rank_str from cache")
                category_and_rank_str = utils.bytes2str(llm_ranking_resp)

            print(f"Used {time.time() - st:.3f}s, Category and Rank: text: {text}, rank_resp: {category_and_rank_str}")

            category_and_rank = utils.fix_and_parse_json(category_and_rank_str)
            print(f"LLM ranked result (json parsed): {category_and_rank}")

            if not category_and_rank:
                print("[ERROR] Cannot parse json string, assign default rating -0.01")
                ranked_page["__topics"] = []
                ranked_page["__categories"] = []
                ranked_page["__rate"] = -0.01
            else:
                ranked_page["__topics"] = [(x["topic"], x.get("score") or 1) for x in category_and_rank["topics"]]
                ranked_page["__categories"] = [(x["category"], x.get("score") or 1) for x in category_and_rank["topics"]]
                ranked_page["__rate"] = category_and_rank["overall_score"]
                ranked_page["__feedback"] = category_and_rank.get("feedback") or ""

            ranked.append(ranked_page)

        print(f"Ranked pages: {ranked}")
        return ranked

    def _get_top_items(self, items: list, k):
        """
        items: [(name, score), ...]
        """
        tops = sorted(items, key=itemgetter(1), reverse=True)
        return tops[:k]

    def push(self, pages, targets, topk=3):
        print("#####################################################")
        print("# Push RSS")
        print("#####################################################")
        print(f"Number of pages: {len(pages)}")
        print(f"Targets: {targets}")
        print(f"Top-K: {topk}")
        print(f"input data: {pages}")
        stat = {
            "total": 0,
            "error": 0,
        }

        for target in targets:
            print(f"Pushing data to target: {target} ...")

            if target == "notion":
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
                    stat["total"] += 1

                    try:
                        page_id = page["id"]
                        list_name = page["list_name"]
                        title = page["title"]
                        tags = page["tags"]

                        print(f"Pushing page, title: {title}")

                        topics_topk = [x["term"].replace(",", " ")[:20] for x in tags]
                        topics_topk = topics_topk[:topk]

                        categories_topk = []
                        rating = page.get("__rate") or -1

                        notion_agent.createDatabaseItem_ToRead_RSS(
                            database_id,
                            page,
                            topics_topk,
                            categories_topk,
                            rating)

                        self.markVisited(page_id, source="rss", list_name=list_name)

                    except Exception as e:
                        print(f"[ERROR]: Push to notion failed, skip: {e}")
                        stat["error"] += 1
                        traceback.print_exc()

            else:
                print(f"[ERROR]: Unknown target {target}, skip")

        return stat
