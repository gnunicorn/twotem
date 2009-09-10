#
# (C) Benjamin Kampmann
#


from twisted.internet import gtk2reactor
gtk2reactor.install()

import totem
import gobject
import gtk
import re

from urllib import quote

from twisted.internet import reactor
from simplejson import decode as decode_json
from twisted.web.client import getPage

# FIXME: uuuuuiiii hardcoded sucks ...

TWITTER_SEARCH_URL = "http://search.twitter.com/search.json"
LONG_URL = "http://api.longurl.org/v2/expand?format=json&url=%s"

# not working
FIND_URL = re.compile(".*(http://\w*?)[$|\ ].*")


GET_YOUTUBE_ID = re.compile(".*/watch\?v=(.*?)[&| |$].*")
FIND_T_PARAM = re.compile("swfArgs.*\"t\": \"([^\"]+)\"")

class TwitterConnection(object):

    def get_search_tweets(self, term, since=None):
        print term
        this_url = "%s?rpp=100&q=%s" % (TWITTER_SEARCH_URL, quote(term))
        if since:
            this_url = "%s?since_id=%s" % (this_url, since)

        dfr = getPage(this_url)
        dfr.addCallback(decode_json)
        return dfr

class UrlExpander(object):
    def expand(self, url):
        url = LONG_URL % quote(url)
        dfr = getPage(url)
        dfr.addCallback(decode_json)
        dfr.addCallback(self._resulter)
        return dfr

    def _resulter(self, result):
        return result['long-url']

class Twotem(totem.Plugin):

    def __init__(self):
        totem.Plugin.__init__(self)
        self.con = TwitterConnection()
        self.expander = UrlExpander()
        self.results = []
        self.refresh_time = 60 # in seconds
        gobject.idle_add(reactor.run)

    def activate(self, totem):
        self.my_totem = totem
        self.since_tweet = 0
        self._perform_update()
        print "Active"

    def _perform_update(self):
        first_update = self.con.get_search_tweets("cool+youtube", since=self.since_tweet)
        first_update.addCallback(self._got_tweets)
        first_update.addErrback(self._log_error)
        first_update.addCallback(self._enqueue_updates_later)

    def _enqueue_updates_later(self, result):
        # call again later
        reactor.callLater(self.refresh_time, self._perform_update)
        return result

    def _log_error(self, error):
        print "got Error", error

    def _got_tweets(self, search_results):
        print "got smth"
        results = search_results['results']
        print "got %s results" % len(results)

        try:
            self.since_tweet = results[0]['id']
        except IndexError:
            # we don't even have one tweet :(
            return

        actually_links = []
        for tweet in results:
            if 'http://' in tweet['text']:
                print "found a tweet with url"
                actually_links.append(tweet)

        print "found %s links" % len(actually_links)
        for tweet in actually_links:
            # would be nicer to have a good re instead
            for word in tweet['text'].split():
                if word.startswith('http://'):
                    link = word
                    break
            else:
                print "no link found"
                continue

            print "found", link
            expandefer = self.expander.expand(link)
            expandefer.addCallback(self._load_link, tweet)

    def _load_link(self, link, tweet):
        #print "start loading", link
        res = GET_YOUTUBE_ID.match(link)
        if not res:
            #print "sorry, only youtube, support", link
            return

        u_id = res.group(1)
        print "got id", u_id, link

        user = tweet['from_user']
        text = tweet['text']
        get_page_dfr = getPage(link.encode('utf-8'))
        get_page_dfr.addCallback(self._find_param, u_id)
        get_page_dfr.addCallback(self._add_link, "%s: %s" % (user, text))
        get_page_dfr.addErrback(self._log_error)
        print "over and out"

    def _find_param(self, data, youtube_id):
        print "trying to find param", youtube_id
        t_param = FIND_T_PARAM.search(data).group(1)
        return "http://www.youtube.com/get_video?video_id=%s&t=%s" % (
                youtube_id, t_param)


    def _add_link(self, link, text):
        print "adding", link, text
        self.my_totem.action_remote(totem.REMOTE_COMMAND_ENQUEUE, link)


    def deactivate(self, totem):
        print "off"

