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
                    default="Twitter,Article,Youtube,RSS")
parser.add_argument("--targets",
                    help="targets to push, comma separated",
                    default="notion")
parser.add_argument("--min-rating",
                    help="Minimum user rating to publish",
                    default=4)
parser.add_argument("--dedup", help="whether dedup item",
                    default=True)
parser.add_argument("--collection-type", help="weekly, monthly, yearly",
                    default="weekly")
parser.add_argument("--max-distance",
                    help="Max distance for similarity search, range [0.0, 1.0]",
                    default=0.5)


def process_collection(args, op):
    print("#####################################################")
    print("# Process collection")
    print("#####################################################")
    data = op.readFromJson(args.data_folder, args.run_id, "collection.json")

    data_filtered = op.post_filter(data, min_score=args.min_rating)

    data_scored = op.score(
        data_filtered,
        start_date=args.start,
        max_distance=args.max_distance)

    return data_scored


def publish(args, op, data, targets):
    """
    Push to targets
    """
    print("#####################################################")
    print(f"# Data publish, target: {targets}, start_date: {args.start}")
    print("#####################################################")

    op.push(data, targets, collection_type=args.collection_type)


def run(args):
    print(f"environment: {os.environ}")
    sources = args.sources.split(",")
    targets = args.targets.split(",")
    exec_date = date.fromisoformat(args.start)
    workdir = os.getenv("WORKDIR")
    dedup = utils.str2bool(args.dedup)

    print(f"sources: {sources}, targets: {targets}, exec_date: {exec_date}, workdir: {workdir}, dedup: {dedup}")

    op = OperatorCollection()
    data_scored = process_collection(args, op)
    publish(args, op, data_scored, targets)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
