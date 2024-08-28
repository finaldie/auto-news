import os
import time
import requests
from datetime import datetime


from llm_agent import (
    LLMArxivLoader
)

import utils


class RedditAgent:
    AUTH_URL = 'https://www.reddit.com/api/v1/access_token'
    SUBREDDIT_NEW_URL = "https://oauth.reddit.com/r/{}/new"

    def __init__(self, client_id=None, client_secret=None):
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.app_id = os.getenv("REDDIT_APP_ID", "app_reddit_api")
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

    def get_subreddit_posts(
        self,
        subreddit,
        limit=25,
        wait_on_ratelimit=True,
        retries=3,
        data_folder="/tmp",
        run_id="",
    ):
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

        def query():
            response = requests.get(
                URL,
                headers=headers,
                params=params)

            response.raise_for_status()
            self._save_ratelimit_info(response=response)

            return self._extractSubredditPosts(
                response, data_folder, run_id)

        return utils.retry(query, retries=retries)

    def _extractSubredditPosts(self, response, data_folder, run_id):
        posts = response.json()["data"]["children"]
        ret = []
        tot = 0
        err = 0

        for post in posts:
            tot += 1
            ts = post["data"]["created_utc"]
            dt_utc = datetime.fromtimestamp(ts).isoformat()
            dt_pdt = utils.convertUTC2PDT_str(dt_utc).isoformat()
            author = post["data"].get("author") or post["data"].get("author_fullname") or "unknown_author"
            subreddit = post["data"]["subreddit"]
            title = post["data"]["title"]
            post_long_id = f"{subreddit}_{title}_{author}_{ts}"
            post_hash_id = utils.hashcode_md5(post_long_id.encode("utf-8"))

            page_url = post["data"]["url"]
            if page_url.startswith("/r/"):
                print(f"[RedditAgent]: Fixing page_url: original: {page_url}")
                page_url = f"https://www.reddit.com{page_url}"
                print(f"[RedditAgent]: Fixing page_url: Fixed: {page_url}")

            page_permalink = f'https://www.reddit.com{post["data"]["permalink"]}'
            is_video = self._is_video(post, page_url)
            is_image = self._is_image(post, page_url)
            is_gallery = self._is_gallery(post, page_url)
            is_external_link = self._is_external_link(post, page_url)
            video_blob = self._extract_video_url(post)
            text = post["data"]["selftext"]

            print(f"[RedditAgent] Loading reddit post: {page_permalink}, page_url: {page_url}")

            if not text and not is_video and not is_image and is_external_link:
                arxiv_loader = LLMArxivLoader()
                loaded, arxiv_res = arxiv_loader.load_from_url(page_url)

                if loaded:  # if it's arxiv paper
                    text = arxiv_res["metadata_text"]
                    print(f"[RedditAgent] Loaded from arxiv, text summary: {text[:200]}..., arxiv_res: {arxiv_res}")

                else:
                    def load_web():
                        print(f"[RedditAgent] Loading web page from {page_url} ...")
                        return utils.load_web(page_url)

                    try:
                        text = utils.retry(load_web, retries=3)

                    except Exception as e:
                        print(f"[ERROR] Load web content failed from {page_url}, use empty string instead: {e}")
                        err += 1

                print(f"Post from external link (non-video/image), load from source {page_url}, text: {text[:200]}...")

            elif is_video:
                print(f"[RedditAgent] is_video: {is_video}, loading video: {video_blob} ...")
                video_url = video_blob["video_url"]
                audio_url = video_blob["audio_url"]

                try:
                    transcript, metadata = utils.load_video_transcript(
                        video_url,
                        audio_url,
                        post_hash_id,
                        data_folder,
                        run_id)

                    print(f"[RedditAgent] Loaded video {video_url}, audio {audio_url}, transcript: {transcript[:200]}...")
                    text = transcript

                except Exception as e:
                    print(f"[ERROR] Load video {video_url}, audio {audio_url} failed: {e}")
                    err += 1

            extracted_post = {
                "id": post_hash_id,
                "long_id": post_long_id,
                "hash_id": post_hash_id,
                "timestamp": ts,
                "created_time": dt_utc,
                "datetime_utc": dt_utc,
                "datetime_pdt": dt_pdt,
                "source": "Reddit",

                "title": title,
                "text": text,

                # resource link
                "url": page_url,
                # original post link
                "permalink": page_permalink,

                "subreddit": subreddit,
                "author": author,
                "ups": post["data"]["ups"],
                "downs": post["data"]["downs"],
                "num_comments": post["data"]["num_comments"],
                "visited": post["data"]["visited"],

                "is_video": is_video,
                "is_image": is_image,
                "is_gallery": is_gallery,
                "is_external_link": is_external_link,
                "video": video_blob,
                "gallery_medias": self._extract_gallery(post),

                "raw": post,
            }

            ret.append(extracted_post)

        print(f"Reddit post loaded total {tot}, error {err}")
        return ret

    def _is_video(self, post, page_url):
        has_media = post["data"]["media"]
        is_video = post["data"]["is_video"] or "https://v.redd.it" in page_url

        if has_media or is_video:
            return True
        else:
            return False

    def _extract_video_url(self, post):
        media = post["data"].get("media")
        print(f"[RedditAgent] Extract media section: {media}, type: {type(media)}")

        if not media or len(media) == 0 or not isinstance(media, dict):
            return {
                "video_provider": "unknown",
                "video_url": "",
                "audio_url": "",
            }

        if media.get("reddit_video"):
            # This one can be embedded in notion but no audio
            video_url = media["reddit_video"].get("fallback_url") or ""

            # This one can be downloaded via yt-dlp but cannot be embedded in notion
            dash_url = media["reddit_video"].get("dash_url") or ""

            return {
                "video_provider": "reddit",
                "video_url": video_url,
                "audio_url": dash_url,
            }

        elif media.get("type"):
            # For example, a youtube video:
            # {'type': 'youtube.com', 'oembed': {'provider_url': 'https://www.youtube.com/', 'version' ...
            #
            # Notes: youtube and v.redd.it can be displayed correctly
            #        others maybe not...
            provider_name = media["oembed"]["provider_name"]

            return {
                "video_provider": provider_name,
                "video_url": post["data"]["url"],
                "audio_url": post["data"]["url"],
            }

    def _is_image(self, post, page_url):

        suffixs = ("jpg", "png", "gif")
        others = ["https://i.redd.it"]

        for suffix in suffixs:
            if page_url.endswith(suffix):
                return True

        for part in others:
            if part in page_url:
                return True

        return False

    def _is_gallery(self, post, page_url):
        """
        Multiple images combined, and user can scroll it
        """
        if post["data"].get("is_gallery"):
            return post["data"]["is_gallery"]

        others = ["www.reddit.com/gallery"]

        for part in others:
            if part in page_url:
                return True

        return False

    def _is_external_link(self, post, page_url):
        """
        post is the original reddit returned post dict object
        """
        cands = ("https://www.reddit.com", ".redd.it")

        for cand in cands:
            if cand in page_url:
                return False

        return True

    def _extract_gallery(self, post):
        media_metadata = post["data"].get("media_metadata")
        if not media_metadata:
            return []

        print(f"[_extract_gallery] media_metadata: {media_metadata}")
        res = []

        for media_id, metadata in media_metadata.items():
            if metadata["status"] != "valid":
                print(f"[WARN] media {media_id} is invalid, skip")
                continue

            media_type = metadata["e"]
            print(f"[INFO] media_id: {media_id}, type: {media_type}")

            if not metadata.get("s"):
                print(f"[WARN] Skip media_id: {media_id}, type: {media_type}, it has no valid section to extract: {metadata}")
                continue

            media_url = metadata["s"].get("u") or metadata["s"].get("gif")

            res.append({
                "id": media_id,
                "type": media_type,
                "url": media_url,
            })

        return res

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
