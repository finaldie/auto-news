import argparse
import os
from datetime import date, datetime

from dotenv import load_dotenv

from ops_todo import OperatorTODO
from ops_deepdive import OperatorDeepDive
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
    data = op.readFromJson(args.data_folder, args.run_id, "action_todo.json")
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


def process_dd(args, op):
    print("#####################################################")
    print("# Process deep dive")
    print("#####################################################")
    data = op.readFromJson(args.data_folder, args.run_id, "action_deepdive.json")
    dedup_pages = op.dedup(data)

    workdir = os.getenv("WORKDIR")
    workspace = f"{workdir}/{args.data_folder}/{args.run_id}"

    collection_pages = op.collect(dedup_pages, work_dir=workspace)
    deepdive_pages = op.deepdive(collection_pages, work_dir=workspace)

    return deepdive_pages


def publish_dd(args, op, pages, targets):
    """
    Push to targets
    """
    print("#####################################################")
    print(f"# DeepDive: Data publish, target: {targets}, start_date: {args.start}")
    print("#####################################################")

    op.push(pages, targets, start_date=args.start)


def run(args):
    targets = args.targets.split(",")
    exec_date = date.fromisoformat(args.start)
    workdir = os.getenv("WORKDIR")
    dedup = utils.str2bool(args.dedup)
    action_deepdive_enabled = os.getenv("ACTION_DEEPDIVE_ENABLED", "False")
    action_deepdive_enabled = utils.str2bool(action_deepdive_enabled)

    print(f"targets: {targets}, exec_date: {exec_date}, workdir: {workdir}, dedup: {dedup}, action_deepdive_enabled: {action_deepdive_enabled}")

    # Action 'TODO'
    def action_todo():
        op = OperatorTODO()
        todo_pages = process(args, op)
        publish(args, op, todo_pages, targets)

    utils.prun(action_todo)

    # Action 'DeepDive'
    if action_deepdive_enabled:
        def action_deepdive():
            op = OperatorDeepDive()
            dd_pages = process_dd(args, op)
            publish_dd(args, op, dd_pages, targets)

        utils.prun(action_deepdive)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
