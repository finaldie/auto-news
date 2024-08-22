import argparse
import os
from datetime import date, datetime, timedelta

from dotenv import load_dotenv

from ops_milvus import OperatorMilvus
from ops_collection import OperatorCollection
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
                    default="data")
parser.add_argument("--sources",
                    help="sources to pull, comma separated",
                    default=os.getenv("CONTENT_SOURCES", "Twitter,Reddit,Article,Youtube,RSS"))
parser.add_argument("--targets",
                    help="targets to push, comma separated",
                    default="notion")
parser.add_argument("--min-rating",
                    help="Minimum user rating to publish",
                    type=float,
                    default=4.5)
parser.add_argument("--dedup", help="whether dedup item",
                    default=True)
parser.add_argument("--collection-type", help="weekly, monthly, yearly",
                    default="weekly")
parser.add_argument("--max-distance",
                    help="Max distance for similarity search, range [0.0, 1.0]",
                    default=0.5)
parser.add_argument("--top-k",
                    help="top-k to publish",
                    default=10)


def process_collection(args, op):
    print("#####################################################")
    print("# Process collection")
    print("#####################################################")
    data = op.readFromJson(args.data_folder, args.run_id, "collection.json")

    data_scored = op.score(
        data,
        start_date=args.start,
        max_distance=args.max_distance)

    data_filtered = op.post_filter(data_scored, min_score=args.min_rating, k=args.top_k)

    takeaway_pages = op.get_takeaway_pages(data)

    return data_filtered, takeaway_pages


def publish(args, op, data, takeaway_pages, targets):
    """
    Push to targets
    """
    print("#####################################################")
    print(f"# Data publish, target: {targets}, start_date: {args.start}")
    print("#####################################################")

    op.push(data, takeaway_pages, targets, collection_type=args.collection_type, start_date=args.start)


def run(args):
    sources = args.sources.split(",")
    targets = args.targets.split(",")
    exec_date = date.fromisoformat(args.start)
    workdir = os.getenv("WORKDIR")
    dedup = utils.str2bool(args.dedup)

    print(f"sources: {sources}, targets: {targets}, exec_date: {exec_date}, workdir: {workdir}, dedup: {dedup}")

    op = OperatorCollection()
    data_scored, takeaway_pages = process_collection(args, op)
    publish(args, op, data_scored, takeaway_pages, targets)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
