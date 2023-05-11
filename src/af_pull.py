import argparse
import os
from datetime import date, timedelta, datetime

from dotenv import load_dotenv

from tweets import TwitterAgent
from ops_article import OperatorArticle
from ops_youtube import OperatorYoutube
import utils


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
                    default="Twitter,Article,Youtube")
parser.add_argument("--pulling-count", help="pulling count",
                    default=3)
parser.add_argument("--pulling-interval", help="pulling interval (s)",
                    default=0.1)


def pull_twitter(args):
    print("######################################################")
    print("# Pull from Twitter")
    print("######################################################")
    print(f"environment: {os.environ}")

    screen_names_famous = os.getenv("TWITTER_LIST_FAMOUS", "")
    screen_names_ai = os.getenv("TWITTER_LIST_AI", "")

    print(f"screen name famous: {screen_names_famous}")
    print(f"screen name ai: {screen_names_ai}")

    api_key = os.getenv("TWITTER_API_KEY")
    api_key_secret = os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    agent = TwitterAgent(api_key, api_key_secret, access_token, access_token_secret)

    agent.subscribe("Famous", screen_names_famous.split(","), args.pulling_count)
    agent.subscribe("AI", screen_names_ai.split(","), args.pulling_count)

    data = agent.pull(pulling_interval_sec=args.pulling_interval)
    print(f"Pulled from twitter: {data}")

    return data


def save_twitter(args, data):
    """
    Save the middle result (json) to data folder
    """
    print("######################################################")
    print("# Save Twitter data to json")
    print("######################################################")
    workdir = os.getenv("WORKDIR")

    filename = "twitter.json"
    data_path = f"{workdir}/{args.data_folder}/{args.run_id}"
    full_path = utils.gen_filename(data_path, filename)

    print(f"Save data to {full_path}, data: {data}")
    utils.save_data_json(full_path, data)


def pull_article(args, op):
    """
    Pull from inbox - articles
    """
    print("######################################################")
    print("# Pull from Inbox - Articles")
    print("######################################################")
    print(f"environment: {os.environ}")

    database_id = os.getenv("NOTION_DATABASE_ID_ARTICLE_INBOX")
    data = op.pull(database_id)

    return data


def save_article(args, op, data):
    print("######################################################")
    print("# Save Articles to json file")
    print("######################################################")
    op.save2json(args.data_folder, args.run_id, data)


def pull_youtube(args, op):
    """
    Pull from inbox - youtube
    """
    print("######################################################")
    print("# Pull from Inbox - Youtube")
    print("######################################################")
    print(f"environment: {os.environ}")

    database_id = os.getenv("NOTION_DATABASE_ID_YOUTUBE_INBOX")
    data = op.pull(database_id)

    print(f"Pulled {len(data.keys())} youtube videos")
    return data


def save_youtube(args, op, data):
    print("######################################################")
    print("# Save Youtube transcripts to json file")
    print("######################################################")
    op.save2json(args.data_folder, args.run_id, "youtube.json", data)


def run(args):
    sources = args.sources.split(",")

    for source in sources:
        print(f"Pulling from source: {source} ...")

        if source == "Twitter":
            data = pull_twitter(args)
            save_twitter(args, data)

        elif source == "Article":
            op = OperatorArticle()
            data = pull_article(args, op)
            save_article(args, op, data)

        elif source == "Youtube":
            op = OperatorYoutube()
            data = pull_youtube(args, op)
            save_youtube(args, op, data)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
