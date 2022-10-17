import os.path
import sys
import re
import sqlite3
from datetime import datetime, timedelta

import feedparser
from mastodon import Mastodon
import requests, json, time, logging
from bs4 import BeautifulSoup


def main():
    # sqlite db to store processed tweets (and corresponding post ids)
    sql = sqlite3.connect('/config/tootbot.db')
    db = sql.cursor()
    db.execute('''CREATE TABLE IF NOT EXISTS tweets (tweet text, toot text,
            twitter text, mastodon text, instance text)''')

    if os.environ.get('RSS_BRIDGE_URL'):
        d = requests.get(url=f'{os.environ.get("RSS_BRIDGE_URL")}').json()
    elif os.environ.get('RSS_BRIDGE_BASE_URL'):
        if os.environ.get('TWITTER_USER'):
            twitter = os.environ.get('TWITTER_USER')
            d = requests.get(
                url=
                f'{os.environ.get("RSS_BRIDGE_BASE_URL")}/?action=display&bridge=TwitterBridge&context=By+username&u={twitter}&norep=on&nopinned=on&format=Json'
            ).json()
        elif os.environ.get('TWITTER_SEARCH'):
            twitter = os.environ.get('TWITTER_SEARCH')
            d = requests.get(
                url=
                f'{os.environ.get("RSS_BRIDGE_BASE_URL")}/?action=display&bridge=TwitterBridge&context=By+keyword+or+hashtag&q=%23{twitter}&format=Json'
            ).json()
        else:
            print(f'TWITTER_USER or TWITTER_SEARCH must be set')
            raise
    else:
        print(f'RSS_BRIDGE_URL or RSS_BRIDGE_BASE_URL must be set')
        raise

    if not os.environ.get('MASTODON_INSTANCE'):
        print(f'MASTODON_INSTANCE must be set')
    else:
        instance = os.environ.get('MASTODON_INSTANCE')

    if not os.environ.get('MASTODON_TOKEN'):
        print(f'MASTODODN_TOKEN must be set')
    else:
        access_token = os.environ.get('MASTODON_TOKEN')

    mastodon_api = None
    days = os.environ.get('DAYS') if os.environ.get('DAYS') else 1
    tags = os.environ.get('TAGS')
    delay = os.environ.get('DELAY') if os.environ.get('DELAY') else 0
    mastodon = 'bot_account'

    if d.get('items'):
        items_sorted = sorted(d['items'],
                              key=lambda item: item['date_modified'],
                              reverse=False)
        for t in items_sorted:
            # check if this tweet has been processed
            if t.get('id'):
                id = t['id'].translate({ord("\\"): None})
            else:
                id = t['title'].translate({ord("\\"): None})
            db.execute(
                'SELECT * FROM tweets WHERE tweet = ? AND twitter = ?  and mastodon = ? and instance = ?',
                (id, twitter, mastodon, instance))  # noqa
            last = db.fetchone()

            dt = datetime.strptime(t['date_modified'],
                                   '%Y-%m-%dT%H:%M:%S+00:00')
            age = datetime.now() - dt
            # process only unprocessed tweets less than 1 day old, after delay
            if last is None and age < timedelta(days=days) and age > timedelta(
                    days=delay):
                mastodon_api = Mastodon(access_token=access_token,
                                        api_base_url=f'https://{instance}')

                soup = BeautifulSoup(t['content_html'])
                c = soup.blockquote.text
                post_media = []
                media_embed = {}
                author_string = t['_rssbridge']['username']
                # get the pictures...
                if t.get('attachments'):
                    # Return a set of positive indexes for video links and/or -1 for all non-video links (usually thumbnails for videos)
                    check_urls_for_video = set([
                        x['url'].find('video.twimg') for x in t['attachments']
                    ])
                    # Discard the non-video link
                    check_urls_for_video.discard(-1)

                    if len(check_urls_for_video) >= 1:
                        for a in t['attachments']:
                            url = a['url'].translate({ord("\\"): None})
                            print(url)
                            for p in re.finditer(
                                    r"https://video.twimg.com/[^ \xa0\"]*",
                                    url):
                                print(f'P: {p}')
                                media = requests.get(p.group(0))
                                try:
                                    media_posted = mastodon_api.media_post(
                                        media.content,
                                        mime_type=media.headers.get(
                                            'content-type'))
                                    post_media.append(media_posted['id'])
                                except:
                                    media_embed[
                                        'error'] = 'Media too large to embed.  Please visit original URL'
                                    pass
                    elif len(check_urls_for_video) == 0:
                        for a in t['attachments']:
                            url = a['url'].translate({ord("\\"): None})
                            for p in re.finditer(
                                    r"https://pbs.twimg.com/[^ \xa0\"]*", url):
                                media = requests.get(p.group(0))
                                try:
                                    media_posted = mastodon_api.media_post(
                                        media.content,
                                        mime_type=media.headers.get(
                                            'content-type'))
                                    post_media.append(media_posted['id'])
                                except:
                                    media_embed[
                                        'error'] = 'Media too large to embed.  Please visit original URL'
                                    pass

                # replace short links by original URL
                m = re.search(r"http[^ \xa0]*", c)
                if m is not None:
                    l = m.group(0)
                    r = requests.get(l, allow_redirects=False)
                    if r.status_code in {301, 302}:
                        c = c.replace(l, r.headers.get('Location'))

                # remove pic.twitter.com links
                m = re.search(r"pic.twitter.com[^ \xa0]*", c)
                if m is not None:
                    l = m.group(0)
                    c = c.replace(l, ' ')

                # remove ellipsis
                c = c.replace('\xa0…', ' ')

                c = t['url'].translate({ord('\\'): None}) + '\n\n' + c

                if os.environ.get('TWITTER_USER'):
                    if twitter and twitter.lower() not in author_string.lower(
                    ):
                        c = (u"\U0001F501  " + f'Re-Tweeted from ') + c
                    else:
                        c = (f'Original Post: ') + c
                elif os.environ.get('TWITTER_SEARCH'):
                    c = (f'Original Post: ') + c

                if tags:
                    c = c + '\n' + tags

                if media_embed.get('error'):
                    c = c + f"\n\n({media_embed['error']})"

                if post_media != []:
                    print('Posting Tweet: %s' % t['title'])
                    try:
                        post = mastodon_api.status_post(c,
                                                        in_reply_to_id=None,
                                                        media_ids=post_media,
                                                        sensitive=False,
                                                        visibility='public',
                                                        spoiler_text=None)
                        if "id" in post:
                            db.execute(
                                "INSERT INTO tweets VALUES ( ? , ? , ? , ? , ? )",
                                (id, post["id"], twitter, mastodon, instance))
                            sql.commit()
                    except Exception as e:
                        print(e)
                else:
                    print('Posting Tweet: %s' % t['title'])
                    try:
                        post = mastodon_api.status_post(c,
                                                        in_reply_to_id=None,
                                                        media_ids=None,
                                                        sensitive=False,
                                                        visibility='public',
                                                        spoiler_text=None)
                        if "id" in post:
                            db.execute(
                                "INSERT INTO tweets VALUES ( ? , ? , ? , ? , ? )",
                                (id, post["id"], twitter, mastodon, instance))
                            sql.commit()
                    except Exception as e:
                        print(e)

    else:
        Exception('RSS Feed is not compatible')


if __name__ == "__main__":
    while True:
        main()
        time.sleep(300)
