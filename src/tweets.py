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
        api = tweepy.API(auth, wait_on_rate_limit=True)
        return api

    def _extractTweet(self, tweet, pull_reply=True):
        tweet_embed = ""
        if tweet._json["entities"].get("media") and tweet._json["entities"]["media"][0].get("expanded_url"): 
            tweet_embed = tweet._json["entities"]["media"][0]["expanded_url"]

        output = {
            "screen_name": screen_name,
            "tweet_id": tweet.id,
            "created_at_utc": tweet.created_at.isoformat(),
            "created_at_pdt": tweet.created_at.astimezone(pytz.timezone('America/Los_Angeles')).isoformat(),

            "text": tweet.text,
            "embed": tweet_embed,

            "reply_to_screen_name": tweet.in_reply_to_screen_name,
            "reply_to_user_id": tweet.in_reply_to_user_id,
            "reply_to_status_id": tweet.in_reply_to_status_id,
            "reply_to_name": "",
            "reply_embed": "",
            "reply_text": "",

            # "json": tweet._json,
        }

        if pull_reply:
            reply_tweet = api.get_status(tweet.in_reply_to_status_id, tweet_mode='extended')

            reply_name = reply_tweet.user.name

            reply_embed = None

            if reply_tweet._json["entities"].get("media") and reply_tweet._json["entities"]["media"][0].get("expanded_url"):
                reply_embed = reply_tweet._json["entities"]["media"][0]["expanded_url"]

            output["reply_to_name"] = reply_name
            output["reply_embed"] = reply_embed
            output["reply_text"] = reply_tweet.full_text

        return output

    def subscribe(self, list_name, screen_names, recent_count=10, pull_interval=900):
        """
        list_name: AI, Famous people, ...
        screen_names: elonmusk, JeffDean, ...
        """
        self.lists[list_name] = {
            "screen_names": screen_names,
            "recent_count": recent_count,
            "pull_interval": pull_interval,
        }

    def pull(self):
        output = {}

        for source in self.lists:
            screen_names = source["screen_names"]
            recent_count = source["recent_count"]
            pull_interval = source["pull_interval"]

            output[source] = []

            for screen_name in screen_names:
                tweets = api.user_timeline(screen_name=screen_name, count=recent_count)

                if len(tweets) == 0:
                    continue

                for tweet in tweets:
                    data = self._extractTweet(tweet)
                    output[source].append(data)

        return output
