#!/usr/bin/env python3
import feedparser
import future
import yattag
from bs4 import BeautifulSoup

urls = [
    'https://ecc-comp.blogspot.com/feeds/posts/default',
    'https://drewdevault.com/feed.xml',
    'http://www.devttys0.com/feed/',
    'https://feeds.feedburner.com/codinghorror',
    'https://eev.ee/feeds/atom.xml',
    'https://aturon.github.io/blog/atom.xml',
    'https://gkbrk.com/feed.xml',
    'https://www.cronweekly.com/feed/',
    'https://www.petekeen.net/index.xml',
    'http://jvns.ca/atom.xml',
    'https://www.neyaptik.com/blog/feed/',
    'https://pyfisch.org/blog/feed.xml',
    'http://www.windytan.com/feeds/posts/default',
    'https://mlvnt.com/blog/feed.xml',
    'https://sevagh.github.io/index.xml',
    'http://etodd.io/feed/',
    'https://medium.com/feed/@batuhanosmantaskaya',
    'https://drewkestell.us/rss.xml',
    'http://stevehanov.ca/blog/?atom',
    'http://techsnuffle.com/feed.xml',
    'http://eng.hakopako.net/feed',
    'https://xkcd.com/atom.xml',
    'https://queryfeed.net/tw?q=gkbrk.com',
    'https://www.sheffield.ac.uk/cmlink/1.434416',
    'https://tjaddison.com/feed.xml',
    'http://syndication.thedailywtf.com/TheDailyWtf',
]

def clean_html(content):
    soup = BeautifulSoup(content, 'html.parser')
    return soup.get_text()[:850]

def get_date(entry):
    date = entry.get('published_parsed') or entry.get('date_parsed') or entry.get('updated_parsed')
    return f"{date[0]}-{date[1]}-{date[2]} {date[3]}:{date[4]}"

def get_content(entry):
    if 'content' in entry and len(entry.get('content')) > 0:
        return entry.get('content')[0]['value']
    elif 'summary' in entry:
        return entry.get('summary')

if __name__ == '__main__':
    future_calls = [future.Future(feedparser.parse, feed) for feed in urls]
    feeds = [feed() for feed in future_calls]

    entries = []
    for feed in feeds:
        if not feed or 'items' not in feed:
            print('<!--{}-->'.format(feed))
            continue
        for item in feed['items']:
            item['feed'] = feed.feed
        entries.extend(feed['items'])

    sorted_entries = sorted(entries, key=lambda x: x.get('published_parsed', None) or x.get('date_parsed', 0))
    sorted_entries.reverse() # Most recent first

    doc, tag, text = yattag.Doc().tagtext()
    doc.asis('<!DOCTYPE html>')

    with tag('html'):
        with tag('head'):
            doc.stag('meta', charset='utf-8')
            doc.stag('link', type='text/css', rel='stylesheet', href='https://noelboss.github.io/featherlight/release/featherlight.min.css')
            doc.line('script', '', src='https://noelboss.github.io/featherlight/assets/javascripts/jquery-1.7.0.min.js')
            doc.line('script', '', src='https://noelboss.github.io/featherlight/release/featherlight.min.js')

            doc.line('style', 'a {color: black;}')
        with tag('body'):
            with tag('h1', style='text-align: center;'):
                text('Leo\'s Feed Reader')
            doc.stag('hr', style='text-align: center; width: 80%;')
            for entry in sorted_entries[:50]:
                with tag('div', klass='entry'):
                    with tag('div', klass='entry-header'):
                        author = next(filter(None, [entry.get('author'), entry['feed'].title]))
                        date = get_date(entry)
                        doc.asis(f"<b>{entry['title']}</b> - by {author} @ {date}")
                        with tag('div'):
                            if 'summary' in entry:
                                doc.line('p', clean_html(entry['summary']))
                            if 'link' in entry:
                                doc.line('a', 'Read full', href=entry['link'], target='_blank')
                            text(' - ')
                            doc.line('a', 'View modal', ('data-featherlight', get_content(entry) or '<p>Could not fetch content</p>'), href='#')
                        doc.stag('hr')

    print(doc.getvalue())
