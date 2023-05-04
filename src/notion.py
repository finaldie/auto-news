import json
import os
from datetime import datetime

from notion_client import Client
import pytz


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

    def extractPageBlocks(self, page_id, ignore_embed=True):
        content = ""

        childs = self.api.blocks.children.list(block_id=page_id).get("results")
        # print(f"n: {len(childs)}, childs: {childs}")

        # only extrace paragraph (ignore embeded content)
        for page in childs:
            print(f"Read page type: {page['type']}, page: {page}")

            if page["type"] == "paragraph":
                text = page["paragraph"]["rich_text"][0]["plain_text"]
                content += text

                print(f"Text: {text}")
            elif page["type"] == "embed":
                if ignore_embed:
                    continue

        return content

    def queryDatabase_TwitterInbox(self, database_id, created_time=None):
        query_data = {
            "database_id": database_id,
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
            page_content = extractPageBlocks(page_id)

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

    def _createDatabaseItem_TwitterBase(self, list_names, tweet):
        """
        Create page properties and blocks
        """

        # assemble list name(s), sub-category of source, e.g.
        # The content from twitter and AI list
        source_list_names = [{"name": ln} for ln in list_names]
        tweet_url = f"https://twitter.com/{tweet['screen_name']}/status/{tweet['tweet_id']}"

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
                            "content": tweet['text'],
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

        block_content = f"{tweet['name']}: {tweet['text']}"
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
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"Reply-to: {tweet['reply_to_name']}: {tweet['reply_text']}"
                            }
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

        return properties, blocks

    def createDatabaseItem_TwitterInbox(self, database_id, list_names, tweet):
        """
        Create a page under a database
        database_id: the target notion database id
        tweet: the extracted tweet from TwitterAgent
        """
        properties, blocks = self._createDatabaseItem_TwitterBase(list_names, tweet)
        print(f"notion twitter inbox: database_id: {database_id}, properties: {properties}, blocks: {blocks}")

        # Add the new page to the database
        new_page = self.api.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=blocks)

        return new_page


    def createDatabaseItem_ToRead(self, database_id, list_names: list, tweet, topics: list, categories: list, rate_number):
        properties, blocks = self._createDatabaseItem_TwitterBase(list_names, tweet)

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

        properties.update({"Rate": {
            "number": rate_number
        }})

        print(f"notion ToRead: database_id: {database_id}, properties: {properties}, blocks: {blocks}")

        # Add the new page to the database
        new_page = self.api.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=blocks)

        return new_page
