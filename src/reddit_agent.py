import os
import time
import uuid
import requests
from datetime import datetime

import utils


class RedditAgent:
    AUTH_URL = 'https://www.reddit.com/api/v1/access_token'
    SUBREDDIT_NEW_URL = "https://oauth.reddit.com/r/{}/new"

    def __init__(self, client_id=None, client_secret=None):
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.app_id = os.getenv("REDDIT_APP_ID") or f"app_{str(uuid.uuid4())}"
        self.app_version = os.getenv("REDDIT_APP_VERSION") or "1.0.0"
        self.user_agent = f"auto_news:{self.app_id}:{self.app_version}"
        self.access_token = self.auth()
        self._save_ratelimit_info()

        print(f"[INFO] Initialized RedditAgent, user_agent: {self.user_agent}")

    def auth(self):
        data = {
            'grant_type': 'client_credentials'
        }

        auth = requests.auth.HTTPBasicAuth(
            self.client_id, self.client_secret)

        response = requests.post(self.AUTH_URL,
                                 data=data,
                                 headers={'User-Agent': self.user_agent},
                                 auth=auth)

        response.raise_for_status()
        return response.json()['access_token']

    def get_subreddit_posts(self, subreddit, limit=25, wait_on_ratelimit=True):
        if self.ratelimit_remaining == 0 and wait_on_ratelimit:
            print(f"Reaching ratelimit cap, wait {self.ratelimit_reset} seconds until cap reset...")

            wait_secs = self.ratelimit_reset + 10
            time.sleep(wait_secs)

        headers = {
            'User-Agent': self.user_agent,
            'Authorization': f'Bearer {self.access_token}'
        }

        params = {
            "limit": limit,
        }

        URL = self.SUBREDDIT_NEW_URL.format(subreddit)
        print(f"[INFO] get_subreddit_posts for url: {URL}")

        response = requests.get(URL,
                                headers=headers,
                                params=params)

        response.raise_for_status()
        self._save_ratelimit_info(response=response)
        return self._extractSubredditPosts(response)

    def _extractSubredditPosts(self, response):
        posts = response.json()["data"]["children"]
        ret = []

        for post in posts:
            ts = post["data"]["created_utc"]
            dt_utc = datetime.fromtimestamp(ts).isoformat()
            dt_pdt = utils.convertUTC2PDT_str(dt_utc)
            author = post["data"]["author"]
            subreddit = post["data"]["subreddit"]
            title = post["data"]["title"]
            post_long_id = f"{subreddit}_{title}_{author}_{ts}"
            post_hash_id = utils.hashcode_md5(post_long_id.encode("utf-8"))

            extracted_post = {
                "long_id": post_long_id,
                "hash_id": post_hash_id,
                "timestamp": ts,
                "created_time": dt_utc,
                "datetime_utc": dt_utc,
                "datetime_pdt": dt_pdt,
                "source": "Reddit",

                "title": title,
                "text": post["data"]["selftext"],
                "url": post["data"]["url"],
                "subreddit": subreddit,
                "author": author,
                "ups": post["data"]["ups"],
                "downs": post["data"]["downs"],
                "num_comments": post["data"]["num_comments"],
                "visited": post["data"]["visited"],

                "raw": post,
            }

            ret.append(extracted_post)

        return ret

    def _save_ratelimit_info(self, response=None):
        if not response:
            # Set default values (600 / 10mins) according to Reddit wiki
            self.ratelimit_remaining = 600
            self.ratelimit_used = 0
            self.ratelimit_reset = 60 * 10  # unit second
            return

        if response.status_code != 200:
            print(f"[ERROR] Failure in response: headers: {response.headers}, body: {response.text}")
            return

        prev_ratelimit_remaining = self.ratelimit_remaining
        prev_ratelimit_used = self.ratelimit_used
        prev_ratelimit_reset = self.ratelimit_reset

        # Extract rate limit info from response
        headers = response.headers
        self.ratelimit_remaining = headers["x-ratelimit-remaining"]
        self.ratelimit_used = headers["x-ratelimit-used"]
        self.ratelimit_reset = headers["x-ratelimit-reset"]

        print(f"prev ratelimit_remaining: {prev_ratelimit_remaining}, new ratelimit_remaining: {self.ratelimit_remaining}")
        print(f"prev ratelimit_used: {prev_ratelimit_used}, new ratelimit_used: {self.ratelimit_used}")
        print(f"prev ratelimit_reset: {prev_ratelimit_reset}, new ratelimit_reset: {self.ratelimit_reset}")
