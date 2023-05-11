import os
import time
import copy
from operator import itemgetter
from collections import Counter

from tweets import TwitterAgent
from notion import NotionAgent
from llm_agent import (
    LLMAgentCategoryAndRanking
)
import utils
import data_model
from ops_base import OperatorBase


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
        screen_names_famous = os.getenv("TWITTER_LIST_FAMOUS", "")
        screen_names_ai = os.getenv("TWITTER_LIST_AI", "")

        print(f"screen name famous: {screen_names_famous}")
        print(f"screen name ai: {screen_names_ai}")

        api_key = os.getenv("TWITTER_API_KEY")
        api_key_secret = os.getenv("TWITTER_API_KEY_SECRET")
        access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

        agent = TwitterAgent(api_key, api_key_secret, access_token, access_token_secret)

        agent.subscribe("Famous", screen_names_famous.split(","), pulling_count)
        agent.subscribe("AI", screen_names_ai.split(","), pulling_count)

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

        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)

        print(f"Redis keys: {redis_conn.keys()}")

        tweets_deduped = {}

        for list_name, data in tweets.items():
            tweets_list = tweets_deduped.setdefault(list_name, [])

            for tweet in data:
                tweet_id = tweet["tweet_id"]

                key_tpl = ""
                if target == "inbox":
                    key_tpl = data_model.NOTION_INBOX_ITEM_ID
                elif target == "toread":
                    key_tpl = data_model.NOTION_TOREAD_ITEM_ID

                key = key_tpl.format("twitter", list_name, tweet_id)

                if utils.redis_get(redis_conn, key):
                    print(f"Duplicated tweet found, key: {key}, skip")
                else:
                    tweets_list.append(tweet)

        print(f"tweets_deduped ({len(tweets_deduped)}): {tweets_deduped}")
        return tweets_deduped

    def rank(self, data):
        """
        Rank tweets (not the entire content)

        data: deduped tweets from dedup()
        """
        print("#####################################################")
        print("# Rank Tweets")
        print("#####################################################")

        llm_agent = LLMAgentCategoryAndRanking()
        llm_agent.init_prompt()
        llm_agent.init_llm()

        redis_url = os.getenv("BOT_REDIS_URL")
        redis_key_expire_time = os.getenv("BOT_REDIS_KEY_EXPIRE_TIME", 604800)
        redis_conn = utils.redis_conn(redis_url)

        ranked = {}

        for list_name, tweets in data.items():
            ranked_list = ranked.setdefault(list_name, [])

            for tweet in tweets:
                # Assemble tweet content
                text = ""
                if tweet["reply_text"]:
                    text += f"{tweet['reply_to_name']}: {tweet['reply_text']}"
                text += f"{tweet['name']}: {tweet['text']}"

                # Let LLM to category and rank
                st = time.time()

                ranking_key = data_model.NOTION_RANKING_ITEM_ID.format(
                    "twitter", list_name, tweet["tweet_id"])

                llm_ranking_resp = utils.redis_get(redis_conn, ranking_key)

                category_and_rank_str = None

                if not llm_ranking_resp:
                    print("Not found category_and_rank_str in cache, fallback to llm_agent to rank")
                    category_and_rank_str = llm_agent.run(text)

                    print(f"Cache llm response for {redis_key_expire_time}s, key: {ranking_key}")
                    utils.redis_set(
                        redis_conn,
                        ranking_key,
                        category_and_rank_str,
                        expire_time=int(redis_key_expire_time))

                else:
                    print("Found category_and_rank_str from cache")
                    category_and_rank_str = llm_ranking_resp

                print(f"Used {time.time() - st:.3f}s, Category and Rank: text: {text}, rank_resp: {category_and_rank_str}")

                category_and_rank = utils.fix_and_parse_json(category_and_rank_str)
                print(f"LLM ranked result (json parsed): {category_and_rank}")

                # Parse LLM response and assemble category and rank
                ranked_tweet = copy.deepcopy(tweet)

                if not category_and_rank:
                    print("[ERROR] Cannot parse json string, assign default rating -0.01")
                    ranked_tweet["__topics"] = []
                    ranked_tweet["__categories"] = []
                    ranked_tweet["__rate"] = -0.01
                else:
                    ranked_tweet["__topics"] = [(x["topic"], x.get("score") or 1) for x in category_and_rank["topics"]]
                    ranked_tweet["__categories"] = [(x["category"], x.get("score") or 1) for x in category_and_rank["topics"]]
                    ranked_tweet["__rate"] = category_and_rank["overall_score"]
                    ranked_tweet["__feedback"] = category_and_rank.get("feedback") or ""

                ranked_list.append(ranked_tweet)

        print(f"Ranked tweets: {ranked}")
        return ranked

    def push(self, data, targets, topics_topk=3, categories_topk=3):
        """
        data is the ranked tweets

        data: {list_name1: [ranked_tweet1, ranked_tweet2, ...],
               list_name2: [...], ...}
        """
        print("#####################################################")
        print("# Push Articles")
        print("#####################################################")
        print(f"Targets: {targets}")
        print(f"input data: {data}")

        for target in targets:
            print(f"Pushing data to target: {target} ...")

            if target == "notion":
                notion_api_key = os.getenv("NOTION_TOKEN")
                notion_agent = NotionAgent(notion_api_key)

                # Get the latest toread database id from index db
                db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_TOREAD")
                database_id = utils.get_notion_database_id_toread(
                    notion_agent, db_index_id)
                print(f"Latest ToRead database id: {database_id}")

                if not database_id:
                    print("[ERROR] no index db pages found... skip")
                    break

                for list_name, tweets in data.items():
                    for ranked_tweet in tweets:
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
            else:
                print(f"[ERROR]: Unknown target {target}, skip")

    def _get_top_items(self, items: list, k):
        """
        items: [(name, score), ...]
        """
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
        topics = self._get_topk_items(ranked_tweet["__topics"], topics_top_k)
        print(f"Original topics: {ranked_tweet['__topics']}, top-k: {topics}")

        # Notes: notion doesn't accept comma in the selection type
        # fix it first
        topics_topk = [x[0].replace(",", " ") for x in topics]

        # categories: [(name, score), ...]
        categories = self._get_topk_items(ranked_tweet["__categories"], categories_top_k)
        print(f"Original categories: {ranked_tweet['__categories']}, top-k: {categories}")
        categories_topk = [x[0].replace(",", " ") for x in categories]

        # The __rate is [0, 1], scale to [0, 100]
        rate = ranked_tweet["__rate"] * 100

        notion_agent.createDatabaseItem_ToRead(
            database_id, [list_name], ranked_tweet,
            topics_topk, categories_topk, rate)

        print("Inserted one tweet into ToRead database")
        self.markVisited(list_name, ranked_tweet["tweet_id"])

    def markVisited(self, list_name, tweet_id: str):
        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)

        key_tpl = data_model.NOTION_TOREAD_ITEM_ID
        key = key_tpl.format("twitter", list_name, tweet_id)

        # mark as visited
        utils.redis_set(redis_conn, key, "true")
        print(f"Mark tweet as visited, key: {key}")

    def printStats(self, source, data, inbox_data_deduped, rank_data_deduped, data_ranked):
        print("#####################################################")
        print(f"# Stats of {source}")
        print("#####################################################")

        for list_name, items in data.items():
            print(f"{list_name}: Raw pulling data count: {len(items)}")

        for list_name, items in inbox_data_deduped.items():
            print(f"{list_name}: Deduped inbox data count: {len(items)}")

        for list_name, items in rank_data_deduped.items():
            print(f"{list_name}: Deduped rank data count: {len(items)}")

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
