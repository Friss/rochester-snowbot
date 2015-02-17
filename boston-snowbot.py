#!/usr/bin/python
#  -*- coding: utf-8 -*-
# Copyright (c) 2015 Molly White
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from datetime import datetime
import json
import os
import re
from secrets import *
import tweepy
from urllib2 import urlopen, URLError

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

url = "https://api.forecast.io/forecast/{}/42.3587,-71.0567?exclude=currently,minutely,hourly" \
      "flags".format(FORECAST_KEY)
auth = tweepy.OAuthHandler(C_KEY, C_SECRET)
auth.set_access_token(A_TOKEN, A_TOKEN_SECRET)
api = tweepy.API(auth)

under_match = re.compile(r'snow \(under (?P<max>\d+) in\.\)')
range_match = re.compile(r'snow \((?P<min>\d+)\W(?P<max>\d+) in.\)')
changed_text = "{0}: {1}–{2} in. snow (changed from {3}–{4})."
new_text = "{0}: {1}–{2} in. snow."


def get_weather():
    print url
    try:
        resp = urlopen(url)
    except URLError:
        return None
    else:
        html = resp.read().decode('utf-8')
        return json.loads(html)


def parse_weather(blob):
    weather = {}
    b = blob["daily"]["data"]
    for t in b:
        timestamp = str(t["time"])
        weather[timestamp] = {}
        weather[timestamp]["date_str"] = datetime.fromtimestamp(t["time"]).strftime("%a, %b %d")
        summary = t["summary"].lower()
        if "snow" in summary:
            print summary
            if "under" in summary:
                m = re.search(under_match, summary)
                if m:
                    weather[timestamp]["min"] = 0
                    weather[timestamp]["max"] = int(m.group("max"))
            else:
                m = re.search(range_match, summary)
                weather[timestamp]["min"] = int(m.group("min"))
                weather[timestamp]["max"] = int(m.group("max"))
        else:
            weather[timestamp]["min"] = 0
            weather[timestamp]["max"] = 0
    return weather


def diff_weather(new, stored):
    diff = {}
    for t in new:
        if t in stored:
            if new[t]["max"] != stored[t]["max"] or new[t]["min"] != stored[t]["min"]:
                diff[t] = {}
                diff[t]["date_str"] = new[t]["date_str"]
                diff[t]["old"] = {}
                diff[t]["old"]["min"] = stored[t]["min"]
                diff[t]["old"]["max"] = stored[t]["max"]
                diff[t]["new"] = {}
                diff[t]["new"]["min"] = new[t]["min"]
                diff[t]["new"]["max"] = new[t]["max"]
        else:
            diff[t] = {}
            diff[t]["date_str"] = new[t]["date_str"]
            diff[t]["new"] = {}
            diff[t]["new"]["min"] = new[t]["min"]
            diff[t]["new"]["max"] = new[t]["max"]
    return diff

def store_weather(parsed):
    with open(os.path.join(__location__, "weather.json"), 'w') as f:
        json.dump(parsed, f)


def get_stored_weather():
    with open(os.path.join(__location__, "weather.json"), 'r') as f:
        stored = json.load(f)
    return stored


def make_sentences(diff):
    info = []
    for t in diff:
        if "old" in diff[t]:
            info.append(changed_text.format(diff[t]["date_str"], diff[t]["new"]["min"],
                                            diff[t]["new"]["max"], diff[t]["old"]["min"],
                                            diff[t]["old"]["max"]))
        else:
            info.append(new_text.format(diff[t]["date_str"], diff[t]["new"]["min"],
                                        diff[t]["new"]["max"]))
    return info

def form_tweets(info):
    tweet = ""
    tweets = []
    while info:
        if len(tweet) + len(info[0]) > 138:
            tweets.append(tweet)
            tweet = ""
        else:
            tweet += " " + info.pop(0)
    tweets.append(tweet)
    return tweets

def do_tweet(tweets):
    for tweet in tweets:
        api.update_status(tweet)


def do_the_thing():
    blob = get_weather()
    new = parse_weather(blob)
    stored = get_stored_weather()
    diff = diff_weather(new, stored)
    if diff:
        sentences = make_sentences(diff)
        tweets = form_tweets(sentences)
        do_tweet(tweets)

if __name__ == "__main__":
    do_the_thing()