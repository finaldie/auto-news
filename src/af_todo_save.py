import argparse
import os
from datetime import date, datetime

from dotenv import load_dotenv

from ops_todo import OperatorTODO
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
parser.add_argument("--targets",
                    help="targets to push, comma separated",
                    default="notion")
parser.add_argument("--dedup", help="whether dedup item",
                    default=True)


def process(args, op):
    print("#####################################################")
    print("# TODO: generate todo items")
    print("#####################################################")
    data = op.readFromJson(args.data_folder, args.run_id, "todo.json")
    dedup_pages = op.dedup(data)
    todo_pages: list = op.generate(dedup_pages)

    return todo_pages


def publish(args, op, data, targets):
    """
    Push to targets
    """
    print("#####################################################")
    print(f"# TODO: Data publish, target: {targets}, start_date: {args.start}")
    print("#####################################################")

    op.push(data, targets, start_date=args.start)


def run(args):
    print(f"environment: {os.environ}")
    targets = args.targets.split(",")
    exec_date = date.fromisoformat(args.start)
    workdir = os.getenv("WORKDIR")
    dedup = utils.str2bool(args.dedup)

    print(f"targets: {targets}, exec_date: {exec_date}, workdir: {workdir}, dedup: {dedup}")

    op = OperatorTODO()
    todo_pages = process(args, op)
    publish(args, op, todo_pages, targets)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
