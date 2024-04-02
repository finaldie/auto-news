import os
import time
import copy
import traceback
from operator import itemgetter
from collections import Counter

from tweets import TwitterAgent
from notion import NotionAgent
from llm_agent import (
    LLMAgentCategoryAndRanking
)
import utils
from ops_base import OperatorBase
from db_cli import DBClient
from ops_milvus import OperatorMilvus
from ops_notion import OperatorNotion
from ops_stats import OpsStats


class OperatorTwitter(OperatorBase):
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
    def pull(self, pulling_count, pulling_interval):
        print("#####################################################")
        print("# Pulling Twitter")
        print("#####################################################")
        # Get twitter lists
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)

        op_notion = OperatorNotion()
        db_index_id = op_notion.get_index_inbox_dbid()

        db_pages = utils.get_notion_database_pages_inbox(
            notion_agent, db_index_id, "Twitter")
        print(f"The database pages founded: {db_pages}")

        screen_names = {}  # <list_name, []>

        for db_page in db_pages:
            database_id = db_page["database_id"]

            # <list_name, [...]>
            name_dict = notion_agent.queryDatabase_TwitterList(
                database_id)

            screen_names.update(name_dict)

        # Use twitter agent to pull tweets
        api_key = os.getenv("TWITTER_API_KEY")
        api_key_secret = os.getenv("TWITTER_API_KEY_SECRET")
        access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

        agent = TwitterAgent(api_key, api_key_secret, access_token, access_token_secret)

        for list_name, screen_names in screen_names.items():
            print(f"list_name: {list_name}, screen_names: {screen_names}")
            name_list = [x['twitter_id'] for x in screen_names]
            print(f"name_list: {name_list}")

            agent.subscribe(list_name, name_list, pulling_count)

        data = agent.pull(pulling_interval_sec=pulling_interval)
        print(f"Pulled from twitter: {data}")
        return data

    def dedup(self, tweets, target="toread"):
        """
        tweets: {
            "list_name1": [...],
            "list_name2": [...],
        }
        """
        print("#####################################################")
        print("# Dedup Twitter")
        print("#####################################################")
        print(f"Target: {target}")

        client = DBClient()
        tweets_deduped = {}
        tot = 0
        dup = 0
        cnt = 0

        for list_name, data in tweets.items():
            tweets_list = tweets_deduped.setdefault(list_name, [])

            for tweet in data:
                tweet_id = tweet["tweet_id"]
                tot += 1

                if client.get_notion_toread_item_id(
                        "twitter", list_name, tweet_id):
                    dup += 1
                    print(f"Duplicated tweet found, tweet_id: {tweet_id}, skip")

                else:
                    cnt += 1
                    tweets_list.append(tweet)

        print(f"tweets_deduped (total: {tot}, duplicated: {dup}, new: {cnt}): {tweets_deduped}")
        return tweets_deduped

    def rank(self, data, **kwargs):
        """
        Rank tweets (not the entire content)

        data: deduped tweets from dedup()
        """
        print("#####################################################")
        print("# Rank Tweets")
        print("#####################################################")
        min_score = kwargs.setdefault("min_score", 4)
        print(f"Minimum score to rank: {min_score}")

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

        for list_name, tweets in data.items():
            ranked_list = ranked.setdefault(list_name, [])

            for tweet in tweets:
                tot += 1
                relevant_score = tweet.get("__relevant_score")

                # Assemble tweet content
                text = ""
                if tweet["reply_text"]:
                    text += f"{tweet['reply_to_name']}: {tweet['reply_text']}"
                text += f"{tweet['name']}: {tweet['text']}"

                print(f"Ranking tweet: {text}")
                print(f"Relevant score: {relevant_score}")

                ranked_tweet = copy.deepcopy(tweet)

                if relevant_score and relevant_score >= 0 and relevant_score < min_score:
                    print("Skip the low score tweet to rank")
                    skipped += 1

                    ranked_tweet["__topics"] = []
                    ranked_tweet["__categories"] = []
                    ranked_tweet["__rate"] = -0.02

                    ranked_list.append(ranked_tweet)
                    continue

                # Let LLM to category and rank, for:
                # cold-start: no relevant score or < 0
                # warm/hot-start: relevant score >= min_score
                st = time.time()

                llm_ranking_resp = client.get_notion_ranking_item_id(
                    "twitter", list_name, tweet["tweet_id"])

                category_and_rank_str = None

                if not llm_ranking_resp:
                    print("Not found category_and_rank_str in cache, fallback to llm_agent to rank")
                    category_and_rank_str = llm_agent.run(text)

                    print(f"Cache llm response for {redis_key_expire_time}s, tweet_id: {tweet['tweet_id']}")
                    client.set_notion_ranking_item_id(
                        "twitter", list_name, tweet["tweet_id"],
                        category_and_rank_str,
                        expired_time=int(redis_key_expire_time))

                else:
                    print("Found category_and_rank_str from cache")
                    category_and_rank_str = llm_ranking_resp

                print(f"Used {time.time() - st:.3f}s, Category and Rank: text: {text}, rank_resp: {category_and_rank_str}")

                category_and_rank = utils.fix_and_parse_json(category_and_rank_str)
                print(f"LLM ranked result (json parsed): {category_and_rank}")

                # Parse LLM response and assemble category and rank
                if not category_and_rank:
                    print("[ERROR] Cannot parse json string, assign default rating -0.01")
                    ranked_tweet["__topics"] = []
                    ranked_tweet["__categories"] = []
                    ranked_tweet["__rate"] = -0.01
                    err += 1

                else:
                    ranked_tweet["__topics"] = [(x["topic"], x.get("score") or 1) for x in category_and_rank["topics"]]
                    ranked_tweet["__categories"] = [(x["category"], x.get("score") or 1) for x in category_and_rank["topics"]]
                    ranked_tweet["__rate"] = category_and_rank["overall_score"] or -0.01
                    ranked_tweet["__feedback"] = category_and_rank.get("feedback") or ""
                    rank += 1

                ranked_list.append(ranked_tweet)

        print(f"Ranked tweets: {ranked}")
        print(f"Total {tot}, ranked: {rank}, skipped: {skipped}, errors: {err}")
        return ranked

    def push(self, data, targets, topics_topk=3, categories_topk=3):
        """
        data is the ranked tweets

        data: {list_name1: [ranked_tweet1, ranked_tweet2, ...],
               list_name2: [...], ...}
        """
        print("#####################################################")
        print("# Push Tweets")
        print("#####################################################")
        print(f"Targets: {targets}")
        print(f"input data: {data}")

        stats = {}

        for target in targets:
            print(f"Pushing data to target: {target} ...")

            if target == "notion":
                tot = 0
                err = 0

                notion_api_key = os.getenv("NOTION_TOKEN")
                notion_agent = NotionAgent(notion_api_key)
                op_notion = OperatorNotion()

                # Get the latest toread database id from index db
                # db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_TOREAD")
                db_index_id = op_notion.get_index_toread_dbid()
                database_id = utils.get_notion_database_id_toread(
                    notion_agent, db_index_id)
                print(f"Latest ToRead database id: {database_id}")

                if not database_id:
                    print("[ERROR] no index db pages found... skip")
                    break

                for list_name, tweets in data.items():
                    stat = stats.setdefault(list_name, {"total": 0, "error": 0})

                    for ranked_tweet in tweets:
                        tot += 1
                        stat["total"] += 1

                        try:
                            self._push_to_read_notion(
                                notion_agent,
                                database_id,
                                list_name,
                                ranked_tweet,
                                topics_topk,
                                categories_topk)

                        except Exception as e:
                            print(f"[ERROR]: Push to notion failed, skip: {e}")
                            err += 1
                            stat["error"] += 1
                            traceback.print_exc()

            else:
                print(f"[ERROR]: Unknown target {target}, skip")

            print(f"Push Tweets to notion finished, total: {tot}, err: {err}")
            return stats

    def score(self, data, **kwargs):
        print("#####################################################")
        print("# Score Tweets")
        print("#####################################################")
        start_date = kwargs.setdefault("start_date", "")
        max_distance = kwargs.setdefault("max_distance", 0.45)
        print(f"start_date: {start_date}, max_distance: {max_distance}")

        op_milvus = OperatorMilvus()
        client = DBClient()

        scored_pages = {}

        for list_name, tweets in data.items():
            scored_list = scored_pages.setdefault(list_name, [])
            print(f"Scoring list {list_name}, total {len(tweets)} tweets")

            for tweet in tweets:
                try:
                    text = ""
                    if tweet["reply_text"]:
                        text += f"{tweet['reply_to_name']}: {tweet['reply_text']}"
                    text += f"{tweet['name']}: {tweet['text']}"

                    # Notes: k = 10 looks too noisy, tune k = 2
                    relevant_metas = op_milvus.get_relevant(
                        start_date, text, topk=2,
                        max_distance=max_distance, db_client=client)

                    page_score = op_milvus.score(relevant_metas)

                    scored_page = copy.deepcopy(tweet)
                    scored_page["__relevant_score"] = page_score

                    scored_list.append(scored_page)
                    print(f"Tweet scored {page_score}")

                except Exception as e:
                    print(f"[ERROR]: Score page failed, skip: {e}")
                    traceback.print_exc()

        print(f"Scored_pages ({len(scored_pages)}): {scored_pages}")
        return scored_pages

    def filter(self, pages, **kwargs):
        print("#####################################################")
        print("# Filter Tweets (After Scoring)")
        print("#####################################################")
        default_min_score = kwargs.setdefault("min_score", 3.5)
        print(f"Default min_score: {default_min_score}")

        # 1. filter all score >= min_score
        filtered = {}
        tot = 0
        cnt = 0

        min_score_param: str = os.getenv("TWITTER_FILTER_MIN_SCORES", "")
        min_scores: list = min_score_param.split(",")

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

        for list_name, tweets in pages.items():
            filtered_pages = filtered.setdefault(list_name, [])
            min_score = min_scores_dict.get(list_name) or default_min_score
            print(f"Filter list_name: {list_name}, min_score: {min_score}")

            for page in tweets:
                relevant_score = page["__relevant_score"]
                tot += 1

                if relevant_score < 0 or relevant_score >= min_score:
                    filtered_pages.append(page)
                    cnt += 1
                    print(f"Valid tweet with relevant score: {relevant_score}")

        print(f"Filter output size: {cnt} / {tot}")
        return filtered

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
        ranked_tweet,
        topics_top_k,
        categories_top_k
    ):
        # topics: [(name, score), ...]
        topics = self._get_top_items(ranked_tweet["__topics"], topics_top_k)
        print(f"Original topics: {ranked_tweet['__topics']}, top-k: {topics}")

        # Notes: notion doesn't accept comma in the selection type
        # fix it first
        topics_topk = [x[0].replace(",", " ")[:20] for x in topics]

        # categories: [(name, score), ...]
        categories = self._get_top_items(ranked_tweet["__categories"], categories_top_k)
        print(f"Original categories: {ranked_tweet['__categories']}, top-k: {categories}")
        categories_topk = [x[0].replace(",", " ")[:20] for x in categories]

        # The __rate is [0, 1], scale to [0, 100]
        rate = ranked_tweet["__rate"] * 100

        notion_agent.createDatabaseItem_ToRead(
            database_id, [list_name], ranked_tweet,
            topics_topk, categories_topk, rate)

        print("Inserted one tweet into ToRead database")
        self.markVisited(
            ranked_tweet["tweet_id"],
            source="twitter",
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

            for ranked_tweet in items:
                rating = ranked_tweet["__rate"]

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
        data_ranked=None,
        pushed_stats=None
    ):
        stats = {}

        data_dict = {
            "total_input": data_input,
            "post_deduping": data_deduped,
            "post_scoring": data_scored,
            "post_filtering": data_filtered,
            "total_pushed": data_ranked,
        }

        for list_name, items in data_input.items():
            stats[list_name] = OpsStats("Twitter", list_name)

        for counter_name, data in data_dict.items():
            for list_name, items in data.items():
                stats[list_name].getCounter(counter_name).set(len(items))

        for list_name, stat in pushed_stats.items():
            stats[list_name].getCounter("total_pushed").set(stat["total"])

        return [stats[x] for x in stats]
