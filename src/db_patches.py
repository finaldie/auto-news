from mysql_cli import MySQLClient


def patch_0(db_cli):
    return True, "OK"


# DB patches: table creation, alter column/index, insert data, etc
DATABASE_PATCHES = [
    {
        "name": "init",
        "order_id": 0,
        "function": patch_0,
    },
]


def apply_database_patches():
    # 1. Init patch table (1st time)
    print("1 Database initializing...")
    db_cli = MySQLClient()
    db_cli.init_tables()
    print("1 Database initialization done")

    # 2. Apply patches (according to order_id)
    applied_orders = db_cli.patch_table_load()
    print(f"2 Applied_orders: {applied_orders}")

    for patch in DATABASE_PATCHES:
        name = patch["name"]
        order_id = patch["order_id"]
        func = patch["fucntion"]
        print(f"2 Checking order {order_id}")

        if order_id in applied_orders:
            print(f"2 order_id {order_id} has been applied, skip")

        ok, msg = func(db_cli)

        if ok:
            db_cli.patch_table_insert(name, order_id)

        else:
            print(f"2 order_id {order_id} applied failed, error: {msg}")


if __name__ == "__main__":
    apply_database_patches()
