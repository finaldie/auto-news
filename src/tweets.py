import json
import pytz

import tweepy


class TwitterAgent:
    def __init__(self, api_key, api_key_secret, access_token, access_token_secret):
        """
        Use twitter 1.1 API
        """
        self.api_key = api_key
        self.api_key_secret = api_key_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.api = self._init_client()
        print(f"Initialized twitter API: {self.api}")

        self.lists = {}

    def _init_client(self):
        self.auth = tweepy.OAuthHandler(self.api_key, self.api_key_secret)
        self.auth.set_access_token(self.access_token, self.access_token_secret)
        api = tweepy.API(self.auth, wait_on_rate_limit=True)
        return api

    def _extractEmbed(self, tweet):
        tweet_embed = ""

        # get the last one
        if (tweet._json["entities"].get("media")
            and tweet._json["entities"]["media"][-1].get("expanded_url")):
            tweet_embed = tweet._json["entities"]["media"][-1]["expanded_url"]

        # if not found, fallback to 'urls' field
        if (not tweet_embed
            and tweet._json["entities"].get("urls")
            and tweet._json["entities"]["urls"][-1]["expanded_url"]):
            tweet_embed = tweet._json["entities"]["urls"][-1]["expanded_url"]

        return tweet_embed

    def _extractTweet(self, tweet, pull_reply=True):
        print(f"extractTweet: {tweet}")

        output = {
            "name": tweet.user.name,
            "screen_name": tweet.user.screen_name,
            "tweet_id": tweet.id,
            "created_at_utc": tweet.created_at.isoformat(),
            "created_at_pdt": tweet.created_at.astimezone(pytz.timezone('America/Los_Angeles')).isoformat(),

            "text": tweet.text,
            "embed": self._extractEmbed(tweet),
            "url": f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",

            "reply_to_screen_name": tweet.in_reply_to_screen_name,
            "reply_to_user_id": tweet.in_reply_to_user_id,
            "reply_to_status_id": tweet.in_reply_to_status_id,
            "reply_to_name": "",
            "reply_embed": "",
            "reply_text": "",
            "reply_deleted": False,

            # "json": tweet._json,
        }

        if pull_reply and tweet.in_reply_to_status_id:
            print(f"pulling reply tweet id: {tweet.in_reply_to_status_id}")
            reply_tweet = None

            try:
                reply_tweet = self.api.get_status(tweet.in_reply_to_status_id, tweet_mode='extended')
            except Exception as e:
                print(f"[ERROR]: Reply tweet fetching error, could be deleted, skip it: {e}")
                output["reply_deleted"] = True
                return output

            reply_name = reply_tweet.user.name
            reply_screen_name = reply_tweet.user.screen_name

            output["reply_tweet_id"] = reply_tweet.id
            output["reply_to_name"] = reply_name
            output["reply_to_screen_name"] = reply_screen_name
            output["reply_embed"] = self._extractEmbed(reply_tweet)
            output["reply_text"] = reply_tweet.full_text
            output["reply_url"] = f"https://twitter.com/{reply_screen_name}/status/{reply_tweet.id}"

        return output

    def subscribe(self, list_name, screen_names, recent_count=10):
        """
        list_name: AI, Famous people, ...
        screen_names: elonmusk, JeffDean, ...
        """

        if len(screen_names) == 0:
            print("[WARN]: Input screen_names is empty, skip")
            return

        self.lists[list_name] = {
            "screen_names": screen_names,
            "recent_count": recent_count,
        }

    def pull(self):
        output = {}

        for source_name, source in self.lists.items():
            screen_names = source["screen_names"]
            recent_count = source["recent_count"]

            output[source_name] = []

            for screen_name in screen_names:
                if not screen_name:
                    continue

                print(f"Pulling tweets from source {source_name}, user screen_name: {screen_name}")

                tweets = self.api.user_timeline(screen_name=screen_name, count=recent_count)

                if len(tweets) == 0:
                    continue

                for tweet in tweets:
                    data = self._extractTweet(tweet)
                    output[source_name].append(data)

        return output
