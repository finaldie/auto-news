import os
from datetime import datetime
import mysql.connector

import db_tables


class MySQLClient:
    def __init__(self, host, port, user, passwd, db):
        self.host = host or os.getenv("MYSQL_HOST")
        self.port = port or os.getenv("MYSQL_PORT")
        self.user = user or os.getenv("MYSQL_USER")
        self.passwd = passwd or os.getnenv("MYSQL_PASSWORD")
        self.db = db or os.getenv("MYSQL_DATABASE")

        print("MySQL client initialization finished")

    def connect(self):
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.passwd,
        )

    def init_tables(self):
        self._init_table_patch()

    def _init_table_patch(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute(f"use {self.db}")
        c.execute(db_tables.SQL_TABLE_CREATION_PATCH)
        print("Table patch created")

    def patch_table_load(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute(f"use {self.db}")

        c.execute("select * from patch")
        rows = c.fetchall()
        ret = {}

        for row in rows:
            order_id = row[2]

            ret[order_id] = {
                "name": row[1],
                "order_id": row[2],
                "created_at": row[3],
            }

        return ret

    def patch_table_insert(self, name, order_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute(f"use {self.db}")

        sql = "INSERT INTO path (name, order_id) VALUES (%s, %s)"
        val = (name, order_id)
        c.execute(sql, val)
        conn.commit()
        print(f"Patch table insertion: name {name}, order_id {order_id}")
