import os
from datetime import datetime
import mysql.connector

import db_tables


class MySQLClient:
    def __init__(
        self,
        host=None,
        port=None,
        user=None,
        passwd=None,
        db=None
    ):
        self.host = host or os.getenv("MYSQL_HOST")
        self.port = port or os.getenv("MYSQL_PORT")
        self.user = user or os.getenv("MYSQL_USER")
        self.passwd = passwd or os.getenv("MYSQL_PASSWORD")
        self.db = db or os.getenv("MYSQL_DATABASE")

        print(f"MySQL client initialization finished, host: {self.host}, port: {self.port}, user: {self.user}")

    def connect(self):
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.passwd,
        )

    def init_tables(self):
        self._create_table_patch()

    def _create_table_patch(self):
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

        sql = "INSERT INTO patch (name, order_id) VALUES (%s, %s)"
        val = (name, order_id)
        c.execute(sql, val)
        conn.commit()
        print(f"Patch table insertion: name {name}, order_id {order_id}")

    def create_table_index_pages(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute(f"use {self.db}")
        c.execute(db_tables.SQL_TABLE_CREATION_INDEX_PAGES)
        print("Table index_pages created")

    def index_pages_table_load(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute(f"use {self.db}")

        c.execute("select * from index_pages")
        rows = c.fetchall()
        ret = {}

        for row in rows:
            category = row[1]
            name = row[2]
            ret[category] = ret.get(category) or {}

            ret[category][name] = {
                "index_id": row[3],
                "created_at": row[4],
                "updated_at": row[5],
            }

        return ret

    def index_pages_table_insert(self, category, name, index_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute(f"use {self.db}")

        sql = "INSERT INTO index_pages (category, name, index_id) VALUES (%s, %s, %s)"
        val = (category, name, index_id)
        c.execute(sql, val)
        conn.commit()
        print(f"Index_pages table insertion: category: {category}, name: {name}, index_id {index_id}")
