import argparse
import os
from datetime import datetime

from dotenv import load_dotenv

from ops_twitter import OperatorTwitter
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
                    default="Twitter,Article,Youtube")
parser.add_argument("--pulling-count", help="pulling count",
                    default=3)
parser.add_argument("--pulling-interval", help="pulling interval (s)",
                    default=0.1)


def pull_twitter(args, op):
    print("######################################################")
    print("# Pull from Twitter")
    print("######################################################")
    print(f"environment: {os.environ}")
    data = op.pull(args.pulling_count, args.pulling_interval)
    return data


def save_twitter(args, op, data):
    """
    Save the middle result (json) to data folder
    """
    print("######################################################")
    print("# Save Twitter data to json")
    print("######################################################")
    op.save2json(args.data_folder, args.run_id, "twitter.json", data)


def pull_article(args, op):
    """
    Pull from inbox - articles
    """
    print("######################################################")
    print("# Pull from Inbox - Articles")
    print("######################################################")
    print(f"environment: {os.environ}")

    data = op.pull()
    return data


def save_article(args, op, data):
    print("######################################################")
    print("# Save Articles to json file")
    print("######################################################")
    op.save2json(args.data_folder, args.run_id, "article.json", data)


def pull_youtube(args, op):
    """
    Pull from inbox - youtube
    """
    print("######################################################")
    print("# Pull from Inbox - Youtube")
    print("######################################################")
    print(f"environment: {os.environ}")

    data = op.pull()

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
            op = OperatorTwitter()
            data = pull_twitter(args, op)
            save_twitter(args, op, data)

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
