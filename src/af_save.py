import argparse
import os
import copy
import time
from datetime import date, timedelta, datetime
from operator import itemgetter
from collections import Counter

from dotenv import load_dotenv
import utils
import data_model
from notion import NotionAgent
from llm_agent import LLMAgentCategoryAndRanking

from ops_article import OperatorArticle
from ops_youtube import OperatorYoutube


parser = argparse.ArgumentParser()
parser.add_argument("--prefix", help="runtime prefix path",
                    default="./run")
parser.add_argument("--start", help="start time",
                    default=datetime.now().isoformat())
parser.add_argument("--run-id", help="run-id",
                    default="")
parser.add_argument("--job-id", help="job-id",
                    default="")
parser.add_argument("--data-folder", help="data folder to save",
                    default="./data")
parser.add_argument("--sources", help="sources to pull, comma separated",
                    default="twitter,article,youtube")
parser.add_argument("--targets", help="targets to push, comma separated",
                    default="notion")
parser.add_argument("--topics-top-k", help="pick top-k topics to push",
                    default=3)
parser.add_argument("--categories-top-k", help="pick top-k categories to push",
                    default=3)


def retrieve_twitter(args):
    """
    get data from local data folder
    """
    workdir = os.getenv("WORKDIR")

    filename = "twitter.json"
    data_path = f"{workdir}/{args.data_folder}/{args.run_id}"
    full_path = utils.gen_filename(data_path, filename)

    data = utils.read_data_json(full_path)

    print(f"retrieve twitter data from {full_path}, data: {data}")
    return data


def tweets_dedup(args, tweets, target="inbox"):
    print("#####################################################")
    print("# Tweets Dedup                                      #")
    print("#####################################################")

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


def tweet_mark_visited(args, list_name, tweet, target="inbox"):
    redis_url = os.getenv("BOT_REDIS_URL")
    redis_conn = utils.redis_conn(redis_url)

    tweet_id = tweet["tweet_id"]

    key_tpl = ""
    if target == "inbox":
        key_tpl = data_model.NOTION_INBOX_ITEM_ID
    elif target == "toread":
        key_tpl = data_model.NOTION_TOREAD_ITEM_ID

    key = key_tpl.format("twitter", list_name, tweet_id)

    # mark as visited
    utils.redis_set(redis_conn, key, "true")
    print(f"Mark tweet as visited, key: {key}")


def push_to_inbox(args, data):
    """
    data: {list_name1: [tweet1, tweet2, ...], list_name2: [...], ...}
    """
    print("#####################################################")
    print("# Push Tweets to Inbox                              #")
    print("#####################################################")

    targets = args.targets.split(",")

    print(f"input data: {data}")

    for target in targets:
        print(f"Pushing data to target: {target} ...")

        if target == "notion":
            notion_api_key = os.getenv("NOTION_TOKEN")
            notion_agent = NotionAgent(notion_api_key)

            database_id = os.getenv("NOTION_DATABASE_ID_TWITTER_INBOX")

            for list_name, tweets in data.items():
                for tweet in tweets:
                    try:
                        notion_agent.createDatabaseItem_TwitterInbox(
                            database_id, [list_name], tweet)

                        print("Insert one tweet into inbox")

                        tweet_mark_visited(args, list_name, tweet, target="inbox")
                    except Exception as e:
                        print(f"[ERROR]: Failed to push tweet to notion, skip it: {e}")

        else:
            print(f"[ERROR]: Unknown target {target}, skip")


def tweets_category_and_rank(args, data):
    print("#####################################################")
    print("# Category and Rank                                 #")
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


def _get_topk_items(items: list, k):
    """
    items: [(name, score), ...]
    """
    tops = sorted(items, key=itemgetter(1), reverse=True)
    return tops[:k]


def _push_to_read_notion(
        args, notion_agent, database_id, list_name, ranked_tweet):
    # topics: [(name, score), ...]
    topics = _get_topk_items(ranked_tweet["__topics"], args.topics_top_k)
    print(f"Original topics: {ranked_tweet['__topics']}, top-k: {topics}")

    # Notes: notion doesn't accept comma in the selection type
    # fix it first
    topics_topk = [x[0].replace(",", " ") for x in topics]

    # categories: [(name, score), ...]
    categories = _get_topk_items(ranked_tweet["__categories"], args.categories_top_k)
    print(f"Original categories: {ranked_tweet['__categories']}, top-k: {categories}")
    categories_topk = [x[0].replace(",", " ") for x in categories]

    # The __rate is [0, 1], scale to [0, 100]
    rate = ranked_tweet["__rate"] * 100

    notion_agent.createDatabaseItem_ToRead(
        database_id, [list_name], ranked_tweet,
        topics_topk, categories_topk, rate)

    print("Insert one tweet into ToRead database")

    tweet_mark_visited(args, list_name, ranked_tweet, target="toread")


def push_to_read(args, data):
    """
    data: {list_name1: [ranked_tweet1, ranked_tweet2, ...],
           list_name2: [...], ...}
    """

    print("#####################################################")
    print("# Push to ToRead database                           #")
    print("#####################################################")

    targets = args.targets.split(",")

    print(f"input data: {data}")

    for target in targets:
        print(f"Pushing data to target: {target} ...")

        if target == "notion":
            notion_api_key = os.getenv("NOTION_TOKEN")
            notion_agent = NotionAgent(notion_api_key)

            database_id = os.getenv("NOTION_DATABASE_ID_TOREAD")

            for list_name, tweets in data.items():
                for ranked_tweet in tweets:
                    try:
                        _push_to_read_notion(
                            args,
                            notion_agent,
                            database_id,
                            list_name,
                            ranked_tweet)

                    except Exception as e:
                        print(f"[ERROR]: Push to notion failed, skip: {e}")
        else:
            print(f"[ERROR]: Unknown target {target}, skip")


def printStats(source, data, inbox_data_deduped, rank_data_deduped, data_ranked):
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


def process_article(args):
    print("#####################################################")
    print("# Process Article")
    print("#####################################################")
    op = OperatorArticle()

    data = op.readFromJson(args.data_folder, args.run_id)
    data_deduped = op.dedup(data, target="toread")
    data_summarized = op.summarize(data_deduped)
    data_ranked = op.rank(data_summarized)

    targets = args.targets.split(",")
    op.push(data_ranked, targets)


def process_youtube(args):
    print("#####################################################")
    print("# Process Youtube")
    print("#####################################################")
    op = OperatorYoutube()

    data = op.readFromJson(args.data_folder, args.run_id)
    data_deduped = op.dedup(data, target="toread")
    data_summarized = op.summarize(data_deduped)
    data_ranked = op.rank(data_summarized)

    targets = args.targets.split(",")
    op.push(data_ranked, targets)


def run(args):
    print(f"environment: {os.environ}")
    sources = args.sources.split(",")

    for source in sources:
        print(f"Pushing data for source: {source} ...")

        # Notes: For twitter we don't need summary step
        if source == "twitter":
            # Dedup and push to inbox
            data = retrieve_twitter(args)
            data_deduped = tweets_dedup(args, data, target="inbox")
            push_to_inbox(args, data_deduped)

            # Dedup and push to ToRead
            rank_data_deduped = tweets_dedup(args, data, target="toread")
            data_ranked = tweets_category_and_rank(args, rank_data_deduped)
            push_to_read(args, data_ranked)

            printStats(source, data, data_deduped, rank_data_deduped, data_ranked)

        elif source == "article":
            process_article(args)

        elif source == "youtube":
            process_youtube(args)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
