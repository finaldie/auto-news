import os
from notion import NotionAgent
from mysql_cli import MySQLClient


class OperatorNotion:
    """
    Operator of Notion, create and maintain metadata
    """
    def init(self):
        db_cli = MySQLClient()
        indexes = db_cli.index_pages_table_load()
        print(f"loaded indexes: {indexes}")

        notion_indexes = indexes.get("notion")
        print(f"loaded notion indexes: {notion_indexes}")

        # The initial set of table count is 8
        total_expected_keys = 8
        if notion_indexes and len(notion_indexes) >= total_expected_keys:
            print("[INFO] Notion index pages have been created, skip")
            return True

        # Initialize notion index pages
        notion_api_key = os.getenv("NOTION_TOKEN")
        agent = NotionAgent(notion_api_key)

        try:
            entry_page_id = os.getenv("NOTION_ENTRY_PAGE_ID")
            db_cli.index_pages_table_insert(
                "notion", "entry_page_id", entry_page_id)

            # create 3 sub pages: inbox, index, toread
            inbox_page = agent.createPageOfPage(entry_page_id, "Inbox")
            index_page = agent.createPageOfPage(entry_page_id, "Index")
            toread_page = agent.createPageOfPage(entry_page_id, "ToRead")

            db_cli.index_pages_table_insert(
                "notion", "inbox_page_id", inbox_page["id"])

            db_cli.index_pages_table_insert(
                "notion", "index_page_id", index_page["id"])

            db_cli.index_pages_table_insert(
                "notion", "toread_page_id", toread_page["id"])

            # create index-inbox
            index_inbox_db = agent.createDatabase_Index(
                "Index - Inbox", index_page["id"])

            # create index-toread
            index_toread_db = agent.createDatabase_Index(
                "Index - ToRead", index_page["id"])

            # create RSS_list
            index_rss_list_db = agent.createDatabase_RSS_List(
                "RSS_List", index_page["id"])

            # create Tweet_list
            index_tweets_list_db = agent.createDatabase_Tweets_List(
                "Tweets_List", index_page["id"])

            db_cli.index_pages_table_insert(
                "notion", "index_inbox_db_id", index_inbox_db["id"])

            db_cli.index_pages_table_insert(
                "notion", "index_toread_db_id", index_toread_db["id"])

            db_cli.index_pages_table_insert(
                "notion", "index_rss_list_db_id", index_rss_list_db["id"])

            db_cli.index_pages_table_insert(
                "notion", "index_tweets_list_db_id", index_tweets_list_db["id"])

            # create inbox-article database
            inbox_article_db = agent.createDatabase_Inbox(
                "Inbox - Article", inbox_page["id"])

            agent.createDatabaseItem_Index(
                index_inbox_db["id"],
                inbox_article_db["id"],
                source="Article",
                description="Article Inbox Database"
            )

            # create inbox-youtube database
            inbox_youtube_db = agent.createDatabase_Inbox(
                "Inbox - YouTube", inbox_page["id"])

            agent.createDatabaseItem_Index(
                index_inbox_db["id"],
                inbox_youtube_db["id"],
                source="Youtube",
                description="YouTube Inbox Database"
            )

            # create ToRead database (Output Inbox)
            inbox_toread_db = agent.createDatabase_ToRead(
                "ToRead", toread_page["id"])

            agent.createDatabaseItem_Index(
                index_toread_db["id"],
                inbox_toread_db["id"],
                source="ToRead",
                description="ToRead Inbox Database"
            )

            # create database item for rss and twitter list
            agent.createDatabaseItem_Index(
                index_inbox_db["id"],
                index_rss_list_db["id"],
                source="RSS",
                description="RSS List Database"
            )

            agent.createDatabaseItem_Index(
                index_inbox_db["id"],
                index_tweets_list_db["id"],
                source="Twitter",
                description="Twitter List Database"
            )

        except Exception as e:
            print(f"[ERROR] Errors in creating notion pages: {e}")
            raise

    def init_reddit_pages(self, notion_agent=None):
        print("Creating Reddit db and pages...")
        agent = notion_agent
        if not agent:
            notion_api_key = os.getenv("NOTION_TOKEN")
            agent = NotionAgent(notion_api_key)

        db_cli = MySQLClient()
        indexes = db_cli.index_pages_table_load()
        print(f"loaded indexes: {indexes}")

        notion_indexes = indexes.get("notion")
        print(f"loaded notion indexes: {notion_indexes}")

        index_page_id = notion_indexes["index_page_id"]["index_id"]
        index_inbox_db_id = notion_indexes["index_inbox_db_id"]["index_id"]
        reddit_list_db_id = notion_indexes.get("index_reddit_list_db_id")

        print(f"index_page_id: {index_page_id}")
        print(f"index_inbox_db_id: {index_inbox_db_id}")
        print(f"reddit_list_db_id: {reddit_list_db_id}")

        if reddit_list_db_id:
            print(f"[INFO] Reddit list database is already created {reddit_list_db_id}, skip")
            return

        print("[notion] Creating Reddit list inbox database ...")
        index_reddit_list_db = agent.createDatabase_Reddit_List(
            "Reddit_List", index_page_id)

        print("[notion] Update Inbox mapping ...")
        agent.createDatabaseItem_Index(
            index_inbox_db_id,
            index_reddit_list_db["id"],
            source="Reddit",
            description="Reddit List Database"
        )

        print("[MySQL] Update Reddit list inbox database ...")
        db_cli.index_pages_table_insert(
            "notion", "index_reddit_list_db_id", index_reddit_list_db["id"])

    def init_journal_pages(self, notion_agent=None):
        print("Creating Reddit db and pages...")
        agent = notion_agent

        if not agent:
            notion_api_key = os.getenv("NOTION_TOKEN")
            agent = NotionAgent(notion_api_key)

        db_cli = MySQLClient()
        indexes = db_cli.index_pages_table_load()
        print(f"loaded indexes: {indexes}")

        notion_indexes = indexes.get("notion")
        print(f"loaded notion indexes: {notion_indexes}")

        index_page_id = notion_indexes["index_page_id"]["index_id"]
        inbox_page_id = notion_indexes["inbox_page_id"]["index_id"]
        index_inbox_db_id = notion_indexes["index_inbox_db_id"]["index_id"]
        journal_db_id = notion_indexes.get("index_journal_db_id")

        print(f"index_page_id: {index_page_id}")
        print(f"index_inbox_db_id: {index_inbox_db_id}")
        print(f"journal_db_id: {journal_db_id}")

        if journal_db_id:
            print(f"[INFO] Journal database is already created {journal_db_id}, skip")
            return

        print("[notion] Creating Journal inbox database ...")
        index_journal_db = agent.createDatabase_Journal(
            "Inbox - Journal", inbox_page_id)

        print("[notion] Update Inbox mapping ...")
        agent.createDatabaseItem_Index(
            index_inbox_db_id,
            index_journal_db["id"],
            source="Journal",
            description="Journal Database"
        )

        print("[MySQL] Update Journal inbox database ...")
        db_cli.index_pages_table_insert(
            "notion", "index_journal_db_id", index_journal_db["id"])

    def get_index_inbox_dbid(self):
        """
        Get database id of index - inbox
        """
        db_cli = MySQLClient()
        indexes = db_cli.index_pages_table_load()
        print(f"loaded indexes: {indexes}")

        for category, metadata in indexes.items():
            if category != "notion":
                continue

            return metadata["index_inbox_db_id"]["index_id"]

        print("[WARN] Cannot find database id for index - inbox")
        return ""

    def get_index_toread_dbid(self):
        """
        Get database id of index - toread
        """
        db_cli = MySQLClient()
        indexes = db_cli.index_pages_table_load()
        print(f"loaded indexes: {indexes}")

        for category, metadata in indexes.items():
            if category != "notion":
                continue

            return metadata["index_toread_db_id"]["index_id"]

        print("[WARN] Cannot find database id for index - toread")
        return ""
