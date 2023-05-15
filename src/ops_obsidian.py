import os
import traceback

from db_cli import DBClient
from notion import NotionAgent
import tpl_obsidian


class OperatorObsidian:
    def dedup(self, pages):
        """
        data: {
            "page_id1": page1,
            "page_id2": page2,
            ...
        }
        """
        print("#####################################################")
        print("# Dedup Obsidian pages")
        print("#####################################################")
        client = DBClient()
        deduped_pages = []

        for page_id, page in pages.items():
            name = page["name"]
            print(f"Dedupping page, title: {name}")

            if client.get_obsidian_inbox_item_id(
                    "obsidian", "default", page_id):
                print(f"Duplicated obsidian found, skip. page_id: {page_id}")
            else:
                deduped_pages.append(page)

        print(f"Pages after dedup: {len(deduped_pages)}")
        return deduped_pages

    def filters(self, pages: list, **kwargs):
        """
        pages after dedup, format: [page1, page2, ...]
        """
        print("#####################################################")
        print("# Filtering Obsidian pages")
        print("#####################################################")
        min_rating = kwargs.setdefault("min_rating", 4)
        print(f"min_rating: {min_rating}, type: {type(min_rating)}")

        filtered_pages = []
        tot = 0
        skipped = 0

        for page in pages:
            name = page["name"]
            user_rating = page["user_rating"]
            tot += 1

            if user_rating < min_rating:
                print(f"[INFO] Skip low quality content, name: {name}, user_rating: {user_rating}")
                skipped += 1
                continue

            filtered_pages.append(page)

        print(f"[INFO] Finished, total {tot}, skipped: {skipped}")
        return filtered_pages

    def push(self, pages, **kwargs):
        """
        Create and push Obsidian pages to specific folder
        """
        print("#####################################################")
        print("# Push Obsidian pages")
        print("#####################################################")

        data_folder = kwargs.setdefault("data_folder", "") or os.getenv("OBSIDIAN_FOLDER")
        if not data_folder:
            print("[ERROR] Data folder path is invalid, skip pushing")
            return

        print(f"Data folder: {data_folder}, total pages: {len(pages)}")

        client = DBClient()
        notion_agent = NotionAgent()
        tot = 0
        err = 0
        skipped = 0

        for page in pages:
            page_id = page["id"]
            tot += 1

            try:
                filename, content = self._gen_ob_page(
                    page, notion_agent=notion_agent)

                if self._save_ob_page(data_folder, filename, content):
                    print(f"[INFO] Gen obsidian page, filename: {filename}")
                    print(f"[INFO] Gen obsidian body, content: {content}")
                    self.markVisisted(page_id, db_client=client)
                else:
                    skipped += 1

            except Exception as e:
                print(f"[ERROR] Failed to push obsidian md: {e}")
                traceback.print_exc()
                err += 1

        print(f"[INFO] Finished, total {tot}, skipped: {skipped}, errors: {err}")

    def markVisisted(self, page_id, db_client=None):
        client = db_client or DBClient()
        client.set_obsidian_inbox_item_id(
            "obsidian", "default", page_id)

    def _gen_ob_page(self, page, notion_agent: NotionAgent = None):
        # print(f"[_gen_ob_page] page: {page}")
        tpl_title = tpl_obsidian.TEMPLATE_OBSIDIAN_INBOX_FILE
        tpl_body = tpl_obsidian.TEMPLATE_OBSIDIAN_INBOX_BODY

        page_id = page["id"]
        name = page["name"]
        props = page["properties"]["properties"]
        source = page.get("source") or props["Source"]["select"]["name"]

        created_at = page["created_at"]
        rating = props["Rating"]["number"]
        user_rating = props["User Rating"]["select"]["name"]
        alias = name
        to = notion_agent.extractRichText(props["To"]["rich_text"])
        list_name = notion_agent.extractMultiSelect(props["List Name"])
        notion_url = page["notion_url"]
        take_aways = notion_agent.extractRichText(props["Take Aways"]["rich_text"])
        topic = notion_agent.extractMultiSelect(props["Topic"])
        category = notion_agent.extractMultiSelect(props["Category"])
        body = notion_agent.concatBlocksText(page["blocks"], separator="\n")

        # The filename is using page_id (uuid) directly
        # To query the actual title using 'alias' field
        filename = tpl_title.format(source, "default", page_id)

        content = tpl_body.format(
            created_at,
            rating,
            user_rating,
            alias,
            to,
            source,
            list_name,
            notion_url,
            topic,
            category,
            take_aways,
            body
        )

        return filename, content

    def _save_ob_page(self, data_path, filename, content):
        workdir = os.getenv("WORKDIR")
        topdir = f"{workdir}/{data_path}"
        full_path = f"{topdir}/{filename}"
        print(f"[INFO] Obsidian data path: {topdir}, filename: {filename}, full_path: {full_path}")

        if not os.path.exists(topdir):
            print(f"[ERROR] Not found Obsidian folder, skip to save: {topdir}")
            return False

        if os.path.exists(full_path):
            print("[INFO] the file exsit, skip")
            return False

        with open(full_path, "w") as file:
            file.write(content)

        print(f"File saved: {full_path}")
        return True
