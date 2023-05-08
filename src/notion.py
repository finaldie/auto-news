import time
import traceback

from notion_client import Client

import utils


class NotionAgent:
    """
    A notion agent to operate page/database
    """
    def __init__(self, api_key):
        self.api_key = api_key

        self.api = self._init_client(self.api_key)
        self.databases = {}  # <source, {database_id}>

    def _init_client(self, api_key):
        return Client(auth=api_key)

    def addDatabase(self, source_name, database_id):
        self.databases[source_name] = {
            "database_id": database_id,
        }

    def _extractRichText(self, data, prefix="", suffix=""):
        """
        The rich_text is a data type and can be used for many blocks,
        e.g. paragraph, bulleted_list_item, headings, etc

        @param data - the rich_text array from one block
        @return the extracted content
        """
        content = ""

        for rich_text in data:
            plain_text = rich_text["plain_text"]

            text = f"{prefix}{plain_text}{suffix}"
            # print(f"Block's rich_text: {text}")

            content += text

        return content

    def _extractBlockParagraph(self, block):
        """
        block: notion block object (paragraph type)
        """
        return self._extractRichText(block["paragraph"]["rich_text"])

    def _extractQuote(self, block):
        """
        block: notion block object (quote type)
        """
        return self._extractRichText(block["quote"]["rich_text"])

    def _extractBulletedListItems(self, block):
        """
        block: notion block object (bulleted_list_item type)
        """
        return self._extractRichText(
            block["bulleted_list_item"]["rich_text"],
            prefix="- ",
            suffix="\n")

    def _extractNumberedListItems(self, block):
        """
        block: notion block object (numbered_list_item type)
        """
        return self._extractRichText(
            block["numbered_list_item"]["rich_text"],
            prefix="1. ",
            suffix="\n")

    def _extractHeading_1(self, block):
        """
        block: notion block object (heading_1 type)
        """
        return self._extractRichText(block["heading_1"]["rich_text"])

    def _extractHeading_2(self, block):
        """
        block: notion block object (heading_2 type)
        """
        return self._extractRichText(block["heading_2"]["rich_text"])

    def _extractHeading_3(self, block):
        """
        block: notion block object (heading_3 type)
        """
        return self._extractRichText(block["heading_3"]["rich_text"])

    def _extractCode(self, block):
        """
        block: notion block object (code type)
        """
        return self._extractRichText(
            block["code"]["rich_text"],
            prefix="```",
            suffix="```")

    def _extractTableRow(self, block):
        """
        block: notion block object (table_row type)
        """
        table_row = block["table_row"]
        cells = table_row["cells"]
        content = ""

        for cell in cells:
            # Like rich_text, one cell may contact with
            # multiple cell pieces
            for cell_data in cell:
                content += cell_data["plain_text"]
                # print(f"cell data: {cell_data['plain_text']}")

            content += ","

        return content

    def _extractBlock(self, block):
        """
        block: notion block object

        @return a simplified block_data only contain id, type and text
        """
        block_id = block["id"]
        block_data = {
            "id": block_id,
            "type": block["type"],
            "text": "",
        }

        # print(f"Read block type: {block['type']}, block: {block}")

        text = ""

        if block["type"] == "paragraph":
            text = self._extractBlockParagraph(block)

        elif block["type"] == "bulleted_list_item":
            text = self._extractBulletedListItems(block)

        elif block["type"] == "numbered_list_item":
            text = self._extractNumberedListItems(block)

        elif block["type"] == "heading_1":
            text = self._extractHeading_1(block)

        elif block["type"] == "heading_2":
            text = self._extractHeading_2(block)

        elif block["type"] == "heading_3":
            text = self._extractHeading_3(block)

        elif block["type"] == "table":
            # depth forward in the child blocks
            pros, blocks = self.extractPage(block_id)
            text = self._concatBlocksText(blocks)

        elif block["type"] == "table_row":
            text = self._extractTableRow(block)

            # Easier for human reading
            text += "\n"

        elif block["type"] == "quote":
            text = self._extractQuote(block)

        elif block["type"] == "code":
            text = self._extractCode(block)

        else:
            print(f"[Unsupported block type]!!!: {block['type']}, block: {block}")

        block_data["text"] = text
        return block_data

    def _extractPageProps(self, page):
        """
        cherry pick props from notion page object
        """
        return {
            "id": page["id"],

            # below two time are utc time
            "created_time": page["created_time"],
            "last_edited_time": page["last_edited_time"],

            "url": page["url"],
            "properties": page["properties"],
        }

    def _concatBlocksText(self, blocks):
        """
        blocks: Converted internal blocks dict (not notion block
                object). format: <block_id, block_data>

        """
        content = ""

        for block_id, block_data in blocks.items():
            text = block_data["text"]

            content += text

        return content

    def extractPage(
            self,
            page_id,
            extract_blocks=True,
            retrieval_retry=3,
    ):
        properties = {}

        # block_id -> block data
        blocks = {}

        page = None
        trying_cnt = 0
        retry_sleep_time = 5  # 5 seconds

        while trying_cnt < retrieval_retry:
            trying_cnt += 1

            try:
                print(f"Retrieving {trying_cnt}/{retrieval_retry}, page id: {page_id}")
                page = self.api.pages.retrieve(page_id=page_id)
                properties = self._extractPageProps(page)
                break

            except Exception as e:
                print(f"Retry {trying_cnt}/{retrieval_retry}, sleep for {retry_sleep_time}s, error: {e}")
                time.sleep(retry_sleep_time)

        if not page:
            print(f"[ERROR] After {trying_cnt} retries (max {retrieval_retry}), still cannot fetch the page {page_id}, exit...")
            return properties, blocks

        if extract_blocks:
            childs = self.api.blocks.children.list(block_id=page_id).get("results")
            # print(f"n: {len(childs)}, childs: {childs}")

            for block in childs:
                block_data = self._extractBlock(block)

                block_id = block["id"]
                blocks[block_id] = block_data

        return properties, blocks

    def queryDatabaseInbox_Twitter(self, database_id, created_time=None):
        query_data = {
            "database_id": database_id,
            "sorts": [
                {
                    "property": "Created time",
                    "direction": "ascending",
                },
            ],
        }

        # filter by created_time
        if created_time:
            query_data["filter"]["and"] = []
            query_data["filter"]["and"].append({
                "property": "Created time",
                "date": {
                    "on_or_after": created_time,
                }
            })

        pages = self.api.databases.query(**query_data).get("results")

        extracted_pages = {}
        for page in pages:
            print(f"result: page id: {page['id']}")

            page_id = page["id"]
            props, blocks = self.extractPage(page_id)
            page_content = self._concatBlocksText(blocks)

            extracted_pages[page_id] = {
                "name": page["properties"]["Name"]["title"]["text"]["content"],
                "to": page["properties"]["To"]["rich_text"][0]["text"]["content"],
                # pdt timezone
                "created_at": page["properties"]["Created at"]["date"]["start"],
                "created_time": page["created_time"],
                "preview": page["properties"]["Preview"]["rich_text"][0]["text"]["content"],
                "notion_url": page["url"],
                "source": "Twitter",

                "content": page_content,
            }

        return extracted_pages

    def queryDatabaseInbox_Article(
        self,
        database_id,
        filter_last_edited_time=None,
        filter_created_time=None
    ):
        query_data = {
            "database_id": database_id,

            "sorts": [
                {
                    "property": "Created time",
                    "direction": "ascending",
                },
            ],

            "filter": {
                "and": [],
            },
        }

        if filter_last_edited_time:
            query_data["filter"]["and"].append({
                "property": "Last edited time",
                "date": {
                    "on_or_after": filter_last_edited_time,
                }
            })

        if filter_created_time:
            query_data["filter"]["and"].append({
                "property": "Created time",
                "date": {
                    "on_or_after": filter_created_time,
                }
            })

        print(f"Query article inbox, query: {query_data}")

        pages = self.api.databases.query(**query_data).get("results")
        print(f"Queried pages: {pages}")

        extracted_pages = {}
        for page in pages:
            print(f"result: page id: {page['id']}")

            page_id = page["id"]
            props, blocks = self.extractPage(page_id)
            page_content = self._concatBlocksText(blocks)

            print(f"Extracting one page: {page}, props: {props}")

            extracted_pages[page_id] = {
                "id": page_id,

                # article title
                "title": props["properties"]["Name"]["title"][0]["plain_text"],
                # utc timezone (notion auto-created)
                "created_time": props["created_time"],

                # utc timezone (notion auto-created)
                "last_edited_time": props["last_edited_time"],
                "notion_url": props["url"],
                "source_url": props["properties"]["URL"]["url"],
                "source": "Article",

                "props": props,
                "blocks": blocks,

                "content": page_content,
            }

        return extracted_pages

    def queryDatabaseInbox_Youtube(
        self,
        database_id,
        filter_last_edited_time=None,
        filter_created_time=None
    ):
        extracted_pages = self.queryDatabaseInbox_Article(
            database_id,
            filter_last_edited_time=filter_last_edited_time,
            filter_created_time=filter_created_time)

        # Fix fields such as 'source'
        for page_id, page in extracted_pages.items():
            page["source"] = "Youtube"

        return extracted_pages

    def _createDatabaseItem_TwitterBase(self, list_names, tweet):
        """
        Create page properties and blocks
        """

        # assemble list name(s), sub-category of source, e.g.
        # The content from twitter and AI list
        source_list_names = [{"name": ln} for ln in list_names]
        tweet_url = f"https://twitter.com/{tweet['screen_name']}/status/{tweet['tweet_id']}"

        preview_content = tweet['text']
        if tweet["retweeted"]:
            preview_content = f"Retweeted: {preview_content}"

        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": f"{tweet['name']}"
                        }
                    }
                ]
            },

            "To": {
                "rich_text": [
                    {
                        "text": {
                            "content": tweet['reply_to_name'] if tweet['reply_to_name'] else ""
                        }
                    }
                ]
            },

            "Created at": {
                "date": {
                    "start": tweet['created_at_pdt'],
                    # "time_zone": "America/Los_Angeles",
                }
            },

            "Preview": {
                "rich_text": [
                    {
                        "text": {
                            "content": preview_content,
                            "link": {
                                "url": tweet_url,
                            }
                        },
                        "href": tweet_url,
                    },
                ]
            },

            "List Name": {
                "multi_select": source_list_names,
            },
        }

        block_content = f"{tweet['name']}"
        if tweet["retweeted"]:
            block_content += " (Retweeted)"

        block_content += f": {tweet['text']}"

        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": block_content
                            }
                        }
                    ]
                }
            }
        ]

        # append embeded content (if have)
        if tweet['embed']:
            blocks.append({
                "type": "embed",
                "embed": {
                    "url": tweet['embed']
                }
            })

        if tweet['reply_text']:
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"Reply-to: {tweet['reply_to_name']}: {tweet['reply_text']}",
                                # "link": tweet["reply_url"],
                            },
                            # "href": tweet["reply_url"],
                        }
                    ]
                }
            })

            # assemble embeding content if it's in the replied content
            if tweet['reply_embed']:
                blocks.append({
                    "type": "embed",
                    "embed": {
                        "url": tweet['reply_embed']
                    }
                })

            # print(f"reply_tweet.url: {tweet['reply_embed']}")
        elif tweet['reply_deleted']:
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"Reply-to: @{tweet['reply_to_screen_name']}: Tweet has been deleted",
                                "link": tweet["reply_url"],
                            },
                            "href": tweet["reply_url"],
                        }
                    ]
                }
            })

        return properties, blocks

    def _createDatabaseItem_ArticleBase(self, ranked_page):
        """
        Create page properties and blocks, will put the summary
        instead of orignal content

        Special fields:
        - content    The original content (Could be very huge), notes that each block has 2000 chars limitation
        - __summary  The summary content
        """
        summary = ranked_page["__summary"]
        preview_content = summary[:100] + "..."

        created_time_pdt = utils.convertUTC2PDT_str(ranked_page["created_time"])

        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": f"{ranked_page['title']}"
                        }
                    }
                ]
            },

            "Created at": {
                "date": {
                    "start": created_time_pdt.isoformat(),
                    # "time_zone": "America/Los_Angeles",
                }
            },

            "Preview": {
                "rich_text": [
                    {
                        "text": {
                            "content": preview_content,
                            "link": {
                                "url": ranked_page["source_url"],
                            }
                        },
                        "href": ranked_page["source_url"],
                    },
                ]
            },
        }

        # put summary content
        block_content = f"Summary: {summary}"

        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": block_content
                            }
                        }
                    ]
                }
            }
        ]

        # append orginal notion url
        blocks.append({
            "type": "link_to_page",
            "link_to_page": {
                "type": "page_id",
                "page_id": ranked_page['id']
            }
        })

        return properties, blocks

    def _createDatabaseItem_YoutubeBase(self, ranked_page):
        """
        Create page properties and blocks, will put the summary first
        Follow by the video

        Special fields:
        - content    The original content (Could be very huge), notes that each block has 2000 chars limitation
        - __summary  The summary content
        """
        summary = ranked_page["__summary"]
        preview_content = summary[:100] + "..."

        created_time_pdt = utils.convertUTC2PDT_str(ranked_page["created_time"])

        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": f"{ranked_page['title']}"
                        }
                    }
                ]
            },

            "Created at": {
                "date": {
                    "start": created_time_pdt.isoformat(),
                    # "time_zone": "America/Los_Angeles",
                }
            },

            "Preview": {
                "rich_text": [
                    {
                        "text": {
                            "content": preview_content,
                            "link": {
                                "url": ranked_page["source_url"],
                            }
                        },
                        "href": ranked_page["source_url"],
                    },
                ]
            },
        }

        blocks = [
            # put summary content
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"Summary: {summary}",
                            }
                        }
                    ]
                }
            },

            # append external video
            {
                "object": "block",
                "type": "video",
                "video": {
                    "type": "external",
                    "external": {
                        "url": ranked_page["source_url"],
                    },
                }
            },
        ]

        return properties, blocks

    def createDatabaseItem_TwitterInbox(
        self,
        database_id,
        list_names,
        tweet
    ):
        """
        Create a page under a database
        database_id: the target notion database id
        tweet: the extracted tweet from TwitterAgent
        """
        properties, blocks = self._createDatabaseItem_TwitterBase(
            list_names, tweet)

        print(f"notion twitter inbox: database_id: {database_id}, properties: {properties}, blocks: {blocks}")

        # Add the new page to the database
        new_page = self.api.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=blocks)

        return new_page

    def createDatabaseItem_ToRead(
        self,
        database_id,
        list_names: list,
        tweet,
        topics: list,
        categories: list,
        rate_number
    ):
        """
        Create toread database item, source twitter
        """
        properties, blocks = self._createDatabaseItem_TwitterBase(
            list_names, tweet)

        # assemble topics
        topics_list = [{"name": t} for t in topics]

        # assemble category (multi-select)
        categories_list = [{"name": c} for c in categories]

        properties["Source"] = {
            "rich_text": [
                {
                    "text": {
                        "content": "Twitter"
                    }
                }
            ]
        }

        properties.update({"Topic": {
            "multi_select": topics_list,
        }})

        properties.update({"Category": {
            "multi_select": categories_list,
        }})

        properties.update({"Rating": {
            "number": rate_number
        }})

        print(f"notion ToRead: database_id: {database_id}, properties: {properties}, blocks: {blocks}")

        # Add the new page to the database
        new_page = self.api.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=blocks)

        # Try to add comments for user and reply_user
        try:
            page_id = new_page["id"]

            print(f"Add user description as comment: {tweet['name']}, desc: {tweet['user_desc']}")
            self.createPageComment(
                page_id,
                f"{tweet['name']}: {tweet['user_desc']}")

            if tweet["reply_to_name"] and tweet["name"] != tweet["reply_to_name"]:
                self.createPageComment(
                    page_id,
                    f"{tweet['reply_to_name']}: {tweet['reply_user_desc']}")

        except Exception as e:
            print(f"[ERROR] Failed to add comment: {e}")
            traceback.print_exc()

        return new_page

    def _postprocess_ToRead(
        self,
        properties,
        blocks,
        database_id,
        ranked_page,
        topics: list,
        categories: list,
        rate_number
    ):
        # assemble topics
        topics_list = [{"name": t} for t in topics]

        # assemble category (multi-select)
        categories_list = [{"name": c} for c in categories]

        properties.update({"Source": {
            "rich_text": [
                {
                    "text": {
                        "content": ranked_page["source"],
                    }
                }
            ]
        }})

        properties.update({"Topic": {
            "multi_select": topics_list,
        }})

        properties.update({"Category": {
            "multi_select": categories_list,
        }})

        properties.update({"Rating": {
            "number": rate_number
        }})

        print(f"notion ToRead: database_id: {database_id}, properties: {properties}, blocks: {blocks}")

        # Add the new page to the database
        new_page = self.api.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=blocks)

        return new_page

    def createDatabaseItem_ToRead_Article(
        self,
        database_id,
        ranked_page,
        topics: list,
        categories: list,
        rate_number
    ):
        properties, blocks = self._createDatabaseItem_ArticleBase(ranked_page)

        # Common fields for article, youtube, etc
        return self._postprocess_ToRead(
            properties,
            blocks,
            database_id,
            ranked_page,
            topics,
            categories,
            rate_number
        )

    def createDatabaseItem_ToRead_Youtube(
        self,
        database_id,
        ranked_page,
        topics: list,
        categories: list,
        rate_number
    ):
        properties, blocks = self._createDatabaseItem_YoutubeBase(ranked_page)

        # Common fields for article, youtube, etc
        new_page = self._postprocess_ToRead(
            properties,
            blocks,
            database_id,
            ranked_page,
            topics,
            categories,
            rate_number
        )

        # Add video metadata as a comment
        video_metadata = f"""
        author: {ranked_page['__author']}
        description: {ranked_page['__description']}
        publishing_date: {ranked_page['__publish_date']}
        duration (minutes): {ranked_page['__length'] / 60}
        view_count: {ranked_page['__view_count']}
        """

        try:
            page_id = new_page["id"]

            print("Add video metadata as comment")
            self.createPageComment(page_id, video_metadata)

        except Exception as e:
            print(f"[ERROR] Failed to add comment: {e}")
            traceback.print_exc()

        return new_page

    def createPageComment(
        self,
        page_id,
        comment_text: str
    ):
        new_comment = self.api.comments.create(
            parent={"page_id": page_id},
            rich_text=[{
                "type": "text",
                "text": {
                    "content": f"{comment_text}"
                }
            }]
        )

        print(f"Created a new comment: {comment_text}, new_comment object: {new_comment}")
        return new_comment
