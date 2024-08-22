import argparse
import os
from datetime import date, datetime, timedelta

from dotenv import load_dotenv

from ops_journal import OperatorJournal
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
                    default="Journal")
parser.add_argument("--targets",
                    help="targets to push, comma separated",
                    default="notion")


def process_journal(args, op):
    print("#####################################################")
    print("# Process Journal")
    print("#####################################################")
    pages = op.readFromJson(args.data_folder, args.run_id, "journal.json")

    refined_pages = op.refine(pages, today=args.start)
    return refined_pages


def publish(args, op, refined_pages, targets):
    """
    Push to targets
    """
    print("#####################################################")
    print(f"# Data publish, target: {targets}, start_date: {args.start}")
    print("#####################################################")

    op.push(refined_pages, targets)


def run(args):
    sources = args.sources.split(",")
    targets = args.targets.split(",")
    exec_date = date.fromisoformat(args.start)
    workdir = os.getenv("WORKDIR")

    print(f"sources: {sources}, targets: {targets}, exec_date: {exec_date}, workdir: {workdir}")

    pages = []
    for source in sources:
        op = OperatorJournal()
        refined_pages = process_journal(args, op)
        pages.extend(refined_pages)

    publish(args, op, pages, targets)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
