import os
import time
import copy
import traceback
from operator import itemgetter
from collections import Counter

from reddit_agent import RedditAgent
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
from ops_stats import OpsStats


class OperatorReddit(OperatorBase):
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
    def __init__(self):
        notion_api_key = os.getenv("NOTION_TOKEN")
        self.notion_agent = NotionAgent(notion_api_key)
        self.reddit_agent = RedditAgent()
        self.op_notion = OperatorNotion()

    def pull(self, pulling_count, pulling_interval, **kwargs):
        print("#####################################################")
        print("# Pulling Reddit")
        print("#####################################################")
        data_folder = kwargs.setdefault("data_folder", "")
        run_id = kwargs.setdefault("run_id", "")

        print(f"pulling_count: {pulling_count}")
        print(f"pulling_interval: {pulling_interval}")
        print(f"data_folder: {data_folder}, run_id: {run_id}")

        # Get reddit lists
        db_index_id = self.op_notion.get_index_inbox_dbid()

        db_pages = utils.get_notion_database_pages_inbox(
            self.notion_agent, db_index_id, "Reddit")
        print(f"The database pages founded: {db_pages}")

        subreddit_names = {}  # <list_name, []>

        for db_page in db_pages:
            database_id = db_page["database_id"]

            # <list_name, [...]>
            name_dict = self.notion_agent.queryDatabase_RedditList(
                database_id)

            subreddit_names.update(name_dict)

        # pull subreddit posts
        data = {}

        for list_name, subreddit_names in subreddit_names.items():
            print(f"list_name: {list_name}, subreddit_names: {subreddit_names}")
            name_list = [x['subreddit'] for x in subreddit_names]
            print(f"name_list: {name_list}")

            # pull all the subreddits in this list

            list_posts = data.setdefault(list_name, [])

            for subreddit in name_list:
                print(f"Pulling subreddit {subreddit}...")

                posts = self.reddit_agent.get_subreddit_posts(
                    subreddit, limit=pulling_count,
                    data_folder=data_folder, run_id=run_id)

                list_posts.extend(posts)

                if pulling_interval > 0:
                    print(f"sleep {pulling_interval}s ...")
                    time.sleep(pulling_interval)

        print(f"Pulled from Reddit: {data}")
        return data

    def dedup(self, posts, target="toread"):
        """
        posts: {
            "list_name1": [...],
            "list_name2": [...],
        }
        """
        print("#####################################################")
        print("# Dedup Reddit Posts")
        print("#####################################################")
        print(f"Target: {target}")

        client = DBClient()
        reddit_deduped = {}
        tot = 0
        dup = 0
        cnt = 0

        for list_name, data in posts.items():
            reddit_list = reddit_deduped.setdefault(list_name, [])

            for post in data:
                post_hash_id = post["hash_id"]
                post_long_id = post["long_id"]
                tot += 1

                if client.get_notion_toread_item_id(
                        "reddit", list_name, post_hash_id):
                    dup += 1
                    print(f"Duplicated post found, post_hash_id: {post_hash_id}, long_id: {post_long_id}, skip it")

                else:
                    cnt += 1
                    reddit_list.append(post)

        print(f"reddit_deduped (total: {tot}, duplicated: {dup}, new: {cnt}): {reddit_deduped}")
        return reddit_deduped

    def rank(self, data, **kwargs):
        """
        Rank Reddit Post (not the entire content)

        data: deduped post from dedup()
        """
        print("#####################################################")
        print("# Rank Reddit Post")
        print("#####################################################")
        ENABLED = utils.str2bool(os.getenv("REDDIT_ENABLE_CLASSIFICATION", "False"))
        min_score = kwargs.setdefault("min_score", 4)
        print(f"Minimum score to rank: {min_score}, enabled: {ENABLED}")

        llm_agent = LLMAgentCategoryAndRanking()
        llm_agent.init_prompt()
        llm_agent.init_llm()

        client = DBClient()
        redis_key_expire_time = os.getenv("BOT_REDIS_KEY_EXPIRE_TIME", 604800)
        tot = 0
        skipped = 0
        err = 0
        rank = 0
        ranked = {}

        for list_name, posts in data.items():
            ranked_list = ranked.setdefault(list_name, [])

            for post in posts:
                tot += 1
                relevant_score = post.get("__relevant_score")
                title = post["title"]
                text = post["text"]
                post_hash_id = post["hash_id"]

                # Assemble ranking content
                content = f"{title}: {text}"

                print(f"Ranking post: length: {len(content)}, content: {content[:200]}...")
                print(f"Relevant score: {relevant_score}")

                ranked_post = copy.deepcopy(post)

                # Skip the ranking steps for now, to save the tokens
                if (not ENABLED or (relevant_score and relevant_score >= 0 and relevant_score < min_score) or len(content) > 2000):
                    print(f"Skip the low score {relevant_score} or long content ({len(content)}) to rank")
                    skipped += 1

                    ranked_post["__topics"] = []
                    ranked_post["__categories"] = []
                    ranked_post["__rate"] = -0.02

                    ranked_list.append(ranked_post)
                    continue

                # Let LLM to category and rank, for:
                # cold-start: no relevant score or < 0
                # warm/hot-start: relevant score >= min_score
                st = time.time()

                llm_ranking_resp = client.get_notion_ranking_item_id(
                    "reddit", list_name, post_hash_id)

                category_and_rank_str = None

                if not llm_ranking_resp:
                    print("Not found category_and_rank_str in cache, fallback to llm_agent to rank")
                    category_and_rank_str = llm_agent.run(text)

                    print(f"Cache llm response for {redis_key_expire_time}s, hash_id: {post_hash_id}")
                    client.set_notion_ranking_item_id(
                        "reddit", list_name, post_hash_id,
                        category_and_rank_str,
                        expired_time=int(redis_key_expire_time))

                else:
                    print("Found category_and_rank_str from cache")
                    category_and_rank_str = llm_ranking_resp

                print(f"Used {time.time() - st:.3f}s, Category and Rank: text: {content}, rank_resp: {category_and_rank_str}")

                category_and_rank = utils.fix_and_parse_json(category_and_rank_str)
                print(f"LLM ranked result (json parsed): {category_and_rank}")

                # Parse LLM response and assemble category and rank
                if not category_and_rank:
                    print("[ERROR] Cannot parse json string, assign default rating -0.01")
                    ranked_post["__topics"] = []
                    ranked_post["__categories"] = []
                    ranked_post["__rate"] = -0.01
                    err += 1

                else:
                    ranked_post["__topics"] = [(x["topic"], x.get("score") or 1) for x in category_and_rank["topics"]]
                    ranked_post["__categories"] = [(x["category"], x.get("score") or 1) for x in category_and_rank["topics"]]
                    ranked_post["__rate"] = category_and_rank["overall_score"] or -0.01
                    ranked_post["__feedback"] = category_and_rank.get("feedback") or ""
                    rank += 1

                ranked_list.append(ranked_post)

        print(f"Ranked reddit posts: {ranked}")
        print(f"Total {tot}, ranked: {rank}, skipped: {skipped}, errors: {err}")
        return ranked

    def push(self, data, targets, topics_topk=3, categories_topk=3):
        """
        data is the ranked reddit posts

        data: {list_name1: [ranked_post1, ranked_post2, ...],
               list_name2: [...], ...}
        """
        print("#####################################################")
        print("# Push Reddit Posts")
        print("#####################################################")
        print(f"Targets: {targets}")
        print(f"input data: {data}")

        stats = {}

        for target in targets:
            print(f"Pushing data to target: {target} ...")

            if target == "notion":
                tot = 0
                err = 0

                # Get the latest toread database id from index db
                db_index_id = self.op_notion.get_index_toread_dbid()
                database_id = utils.get_notion_database_id_toread(
                    self.notion_agent, db_index_id)
                print(f"Latest ToRead database id: {database_id}")

                if not database_id:
                    print("[ERROR] no index db pages found... skip")
                    break

                for list_name, posts in data.items():
                    stat = stats.setdefault(list_name, {"total": 0, "error": 0})

                    for ranked_post in posts:
                        tot += 1
                        stat["total"] += 1

                        try:
                            self._push_to_read_notion(
                                self.notion_agent,
                                database_id,
                                list_name,
                                ranked_post,
                                topics_topk,
                                categories_topk)

                        except Exception as e:
                            print(f"[ERROR]: Push to notion failed, skip: {e}")
                            err += 1
                            stat["error"] += 1
                            traceback.print_exc()

            else:
                print(f"[ERROR]: Unknown target {target}, skip")

            print(f"Push Reddit posts to notion finished, total: {tot}, err: {err}")
            return stats

    def score(self, data, **kwargs):
        print("#####################################################")
        print("# Score Reddit Posts")
        print("#####################################################")
        start_date = kwargs.setdefault("start_date", "")
        max_distance = kwargs.setdefault("max_distance", 0.45)
        print(f"start_date: {start_date}, max_distance: {max_distance}")

        op_milvus = OperatorMilvus()
        client = DBClient()

        scored_pages = {}

        for list_name, posts in data.items():
            scored_list = scored_pages.setdefault(list_name, [])
            print(f"Scoring list {list_name}, total {len(posts)} reddit posts")

            for post in posts:
                try:
                    title = post["title"]
                    text = post["text"]
                    content = f"{list_name} {title}: {text}"

                    # Notes: k = 10 looks too noisy, tune k = 2
                    relevant_metas = op_milvus.get_relevant(
                        start_date, content, topk=2,
                        max_distance=max_distance, db_client=client)

                    page_score = op_milvus.score(relevant_metas)

                    scored_page = copy.deepcopy(post)
                    scored_page["__relevant_score"] = page_score

                    scored_list.append(scored_page)
                    print(f"Reddit post scored {page_score}")

                except Exception as e:
                    print(f"[ERROR]: Score page failed, skip: {e}")
                    traceback.print_exc()

        print(f"Scored_pages ({len(scored_pages)}): {scored_pages}")
        return scored_pages

    def filter(self, pages, **kwargs):
        print("#####################################################")
        print("# Filter Reddit Posts (After Scoring)")
        print("#####################################################")
        default_min_score = kwargs.setdefault("min_score", 4)
        print(f"Default min_score: {default_min_score}")

        # 1. filter all score >= min_score
        filtered = {}
        tot = 0
        cnt = 0

        min_score_param: str = os.getenv("REDDIT_FILTER_MIN_SCORES", "")
        min_scores: list = min_score_param.split(",")
        print(f"min_scores: {min_scores}")

        min_scores_dict: dict = {}
        for data in min_scores:
            if not data:
                continue

            print(f"parsing min_score: [{data}]")

            if not data or len(data.split(":")) < 2:
                print(f"Invalid min_score: {data}, skip it")

            else:
                list_name = data.split(":")[0]
                min_score = float(data.split(":")[1])
                min_scores_dict[list_name] = min_score

                print(f"Parsed min_score: list_name: {list_name}, min_score: {min_score}")

        for list_name, posts in pages.items():
            filtered_pages = filtered.setdefault(list_name, [])
            min_score = min_scores_dict.get(list_name) or default_min_score
            print(f"Filter list_name: {list_name}, min_score: {min_score}")

            for post in posts:
                relevant_score = post["__relevant_score"]
                tot += 1

                if relevant_score < 0 or relevant_score >= min_score:
                    filtered_pages.append(post)
                    cnt += 1
                    print(f"Valid Reddit post with relevant score: {relevant_score}")

        print(f"Filter output size: {cnt} / {tot}")
        return filtered

    def summarize(self, pages):
        print("#####################################################")
        print("# Summarize Reddit Post")
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

        summarized_pages = {}

        for list_name, posts in pages.items():
            list_pages = summarized_pages.setdefault(list_name, [])

            for page in posts:
                title = page["title"]
                page_id = page["hash_id"]
                content = page["text"]
                source_url = page["url"]

                if len(content) <= 200:
                    print(f"Post title: {title}, content length <= 200, skip summarization")
                    list_pages.append(page)
                    continue

                print(f"Summarying page, title: {title}, source_url: {source_url}")
                print(f"Page content ({len(content)} chars): {content[:200]}...")

                st = time.time()
                summary = ""

                llm_summary_resp = client.get_notion_summary_item_id(
                    "reddit", list_name, page_id)

                if not llm_summary_resp:
                    if not content:
                        print(f"[ERROR] Empty Reddit posts, title: {title}, source_url: {source_url}, skip it")
                        continue

                    content = content[:SUMMARY_MAX_LENGTH]

                    try:
                        summary = llm_agent.run(content)

                        print(f"Cache llm response for {redis_key_expire_time}s, page_id: {page_id}, summary: {summary}")

                        client.set_notion_summary_item_id(
                            "reddit", list_name, page_id, summary,
                            expired_time=int(redis_key_expire_time))

                    except Exception as e:
                        print(f"[ERROR] Exception from llm_agent.run(): {e}")

                    if not summary and os.getenv("LLM_PROVIDER", "") != "openai":
                        try:
                            print("Fallback to OpenAI")
                            fallback_agent = LLMAgentSummary()
                            fallback_agent.init_prompt()
                            fallback_agent.init_llm(provider="openai")

                            summary = fallback_agent.run(content)
                        except Exception as e:
                            print(f"[ERROR] Exception from fallback_agent.run(): {e}")

                else:
                    print("Found llm summary from cache, decoding (utf-8) ...")
                    summary = utils.bytes2str(llm_summary_resp)

                # assemble summary into page
                summarized_page = copy.deepcopy(page)
                summarized_page["__summary"] = summary

                print(f"Used {time.time() - st:.3f}s, Summarized page_id: {page_id}, summary: {summary}")
                list_pages.append(summarized_page)

        return summarized_pages

    def _get_top_items(self, items: list, k):
        """
        items: [(name, score), ...]
        """
        if not items or len(items) == 0:
            return []

        tops = sorted(items, key=itemgetter(1), reverse=True)
        return tops[:k]

    def _push_to_read_notion(
        self,
        notion_agent,
        database_id,
        list_name,
        ranked_post,
        topics_top_k,
        categories_top_k
    ):
        # topics: [(name, score), ...]
        topics = self._get_top_items(ranked_post["__topics"], topics_top_k)
        print(f"Original topics: {ranked_post['__topics']}, top-k: {topics}")

        # Notes: notion doesn't accept comma in the selection type
        # fix it first
        topics_topk = [x[0].replace(",", " ")[:20] for x in topics]

        # categories: [(name, score), ...]
        categories = self._get_top_items(ranked_post["__categories"], categories_top_k)
        print(f"Original categories: {ranked_post['__categories']}, top-k: {categories}")
        categories_topk = [x[0].replace(",", " ")[:20] for x in categories]

        # The __rate is [0, 1], scale to [0, 100]
        rate = ranked_post["__rate"] * 100

        notion_agent.createDatabaseItem_ToRead_Reddit(
            database_id, [list_name], ranked_post,
            topics_topk, categories_topk, rate)

        print("Inserted one Reddit post into ToRead database")
        self.markVisited(
            ranked_post["hash_id"],
            source="reddit",
            list_name=list_name)

    def printStats(self, source, data, inbox_data_deduped, data_ranked):
        print("#####################################################")
        print(f"# Stats of {source}")
        print("#####################################################")

        for list_name, items in data.items():
            print(f"{list_name}: Raw pulling data count: {len(items)}")

        for list_name, items in inbox_data_deduped.items():
            print(f"{list_name}: Deduped inbox data count: {len(items)}")

        rank_stats = {}
        for list_name, items in data_ranked.items():
            print(f"{list_name}: Ranked data count: {len(items)}")
            rank_stats[list_name] = Counter()

            for ranked_post in items:
                rating = ranked_post["__rate"]

                if rating <= 0.5:
                    rank_stats[list_name]["below_0.5"] += 1
                elif rating <= 0.6:
                    rank_stats[list_name]["below_0.6"] += 1
                elif rating <= 0.7:
                    rank_stats[list_name]["below_0.7"] += 1
                elif rating <= 0.8:
                    rank_stats[list_name]["below_0.8"] += 1
                elif rating <= 0.9:
                    rank_stats[list_name]["below_0.9"] += 1
                elif rating <= 1:
                    rank_stats[list_name]["below_1"] += 1

            for key, count in rank_stats[list_name].items():
                print(f"{list_name} - {key}: {count}")

    def createStats(
        self,
        data_input,
        data_deduped=None,
        data_scored=None,
        data_filtered=None,
        data_summary=None,
        data_ranked=None,
        pushed_stats=None
    ):
        stats = {}

        data_dict = {
            "total_input": data_input,
            "post_deduping": data_deduped,
            "post_scoring": data_scored,
            "post_filtering": data_filtered,
            "post_summary": data_summary,
            "post_ranking": data_ranked,
            "total_pushed": data_ranked,
        }

        for list_name, items in data_input.items():
            stats[list_name] = OpsStats("Reddit", list_name)

        for counter_name, data in data_dict.items():
            for list_name, items in data.items():
                stats[list_name].getCounter(counter_name).set(len(items))

        for list_name, stat in pushed_stats.items():
            stats[list_name].getCounter("total_pushed").set(stat["total"])

        return [stats[x] for x in stats]
