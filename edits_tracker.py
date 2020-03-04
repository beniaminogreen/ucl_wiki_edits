#!/usr/bin/python
from sseclient import SSEClient as EventSource
import json
import os
import queue
import re
import threading
import tweepy

class TweetThread(threading.Thread):
    def __init__(self, queue):
        #Setup from:
        #https://github.com/eeevanbbb/UniversityEdits/blob/master/tweet.py
        try:
            consumer_key = os.getenv("TWITTER_CONSUMER_KEY")
            consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET")
            access_token = os.getenv("TWITTER_ACCESS_TOKEN")
            access_secret = os.getenv("TWITTER_ACCESS_SECRET")
        except KeyError:
            print("Enviroment variables missing")
        else:
            auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
            auth.set_access_token(access_token, access_secret)
            self.api = tweepy.API(auth)

            threading.Thread.__init__(self)
            self.queue = queue

    def run(self):
        while True:
            tweet = self.queue.get()
            try:
                revision = tweet['revision']
                base_url = tweet['server_url']
                old = revision['old']
                new = revision['new']
                title = tweet['title']
            except KeyError:
                print("key error:")
                print(tweet.keys())
            else:
                edit_url = f"{base_url}/w/index.php?&diff={new}&oldid={old}"
                tweet = f"someone from UCL anonymously edited '{title}': {edit_url}"
                try:
                    self.api.update_status(tweet)
                    print(f"tweeted: '{tweet}'")
                except:
                    print(f"failed to tweet: '{tweet}'")
            self.queue.task_done()

class ListenerThread(threading.Thread):
    def __init__(self, out_queue):
        #UCL wifi IP Adresses
        #https://www.ucl.ac.uk/isd/services/get-connected/wired-networks/about-wired-networks/ucl-internet-protocol-ip-addresses
        #https://www.ucl.ac.uk/isd/services/get-connected/wi-fi-wireless-networks#
        re_list = [
                r"28\.40\.0\.\d{1,2}",
                r"128\.41\.0\.\d{1,2}",
                r"144\.82\.0\.\d{1,2}",
                r"193\.60\.(221|224)\.\d{1,2}",
                r"212\.219\.75\.\d{1,2}",
                r"144\.82\.[89]\.\d{1,3}"
        ]
        self.re_list = [re.compile(string) for string in re_list]

        self.url = 'https://stream.wikimedia.org/v2/stream/recentchange'

        threading.Thread.__init__(self)
        self.out_queue = out_queue

    def run(self):
        #SSE example code from:
        #https://github.com/ebraminio/aiosseclient
        for event in EventSource(self.url):
            if event.event == 'message':
                try:
                    change = json.loads(event.data)
                except ValueError:
                    print("SSE client error: Can't make json")
                else:
                    if not change['bot'] and change['type'] == "edit":
                        if any(regex.match(change['user']) for regex in self.re_list):
                            self.out_queue.put(change)
                            print('tweeted')

tweets_queue = queue.Queue()

listener_th = ListenerThread(tweets_queue)
listener_th.setDaemon(True)
listener_th.start()

tweet_th = TweetThread(tweets_queue)
tweet_th.setDaemon(True)
tweet_th.start()

listener_th.join()
