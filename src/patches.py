from dotenv import load_dotenv
from mysql_cli import MySQLClient

import patch_0
import patch_1
import patch_2


# patches: table creation, alter column/index, insert data, etc
PATCHES_TABLE = [
    {
        "name": "init_notion",
        "order_id": 0,
        "function": patch_0.apply,
    },

    {
        "name": "init_notion_reddit",
        "order_id": 1,
        "function": patch_1.apply,
    },

    {
        "name": "init_notion_journal",
        "order_id": 2,
        "function": patch_2.apply,
    },
]


def apply_patches():
    # 1. Init patch table (1st time)
    print("1 Database initializing...")
    db_cli = MySQLClient()
    db_cli.init_tables()
    print("1 Database initialization done")

    # 2. Apply patches (according to order_id)
    applied_orders = db_cli.patch_table_load()
    print(f"2 Applied_orders: {applied_orders}")

    for patch in PATCHES_TABLE:
        name = patch["name"]
        order_id = patch["order_id"]
        func = patch["function"]
        print(f"2 Checking order {order_id}")

        if order_id in applied_orders:
            print(f"2 order_id {order_id} has been applied, skip")
            continue

        ok, msg = func()

        if ok:
            db_cli.patch_table_insert(name, order_id)

        else:
            print(f"2 order_id {order_id} applied failed, error: {msg}")


if __name__ == "__main__":
    load_dotenv()
    apply_patches()
