#!/usr/bin/env python3

import sys
import os
import urllib
import csv
import requests
import subprocess

from pyquery import PyQuery as PQ
from fire import Fire

fake_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.97 Safari/537.11"
}

def fetch_artists():
    cache_fn = './artists.cache'
    if os.path.exists(cache_fn):
        ## maybe we could add some time based interval ?
        return list(csv.reader(open(cache_fn, 'r')))
    else:
        link = 'http://www.pingshu8.com/Music/bzmtv_1.Htm'
        with requests.Session() as sess:
            sess.headers.update(fake_headers)
            resp = sess.get(link)
            html = PQ(resp.content.decode('gbk'))
            ##print([(a.text, a.attrib['href']) for a in html('a')])
            records = [(a.text, 'http://www.pingshu8.com{}'.format(a.attrib['href'])) for a in html('#container > div.t2 > ul > li > a')]
            with open(cache_fn, 'w') as dstfd:
                dst = csv.writer(dstfd)
                dst.writerows(records)
            return records

def fetch_works(art_name):
    cache_fn = './works.{}.cache'.format(art_name)
    if os.path.exists(cache_fn):
        return list(csv.reader(open(cache_fn, 'r')))
    else:
        artists = dict(fetch_artists())
        link = artists.get(art_name, None)
        if link is None: raise Exception('sorry, the artist {} not exists'.format(art_name))

        with requests.Session() as sess:
            sess.headers.update(fake_headers)
            resp = sess.get(link)
            html = PQ(resp.content.decode('gbk'))
            records = [(a.text, 'http://www.pingshu8.com{}'.format(a.attrib['href'])) for a in html('div.tab33 > a')]
            with open(cache_fn, 'w') as dstfd:
                dst = csv.writer(dstfd)
                dst.writerows(records)
            return records

def analyze_and_download(sess, dest, name, link):
    if not os.path.exists(dest):
        os.makedirs(dest)

    tid = link.split('_')[1].split('.')[0]

    page = 'http://www.pingshu8.com/down_{}.html'.format(tid)
    down = 'http://www.pingshu8.com/bzmtv_Inc/download.asp?fid={}'.format(tid)

    cookie_str = ''.join(["{}={}".format(*pair) for pair in sess.cookies.items() if 'ASPSESSIONID' in pair[0]])
    cmd = """wget --header="User-Agent: Mozilla/5.0 (Windows NT 6.0) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.97 Safari/537.11" --header="Referer: {}" --header="Cookie: {}" {} -O '{}.mp3'""".format(page, cookie_str, down, '{}/{}'.format(dest, name))
    print(cmd)
    subprocess.call(cmd, shell=True)

class Commands(object):
    def artists(self):
        records = fetch_artists()
        for pair in records:
            print(pair[0])

    def works(self, art):
        records = fetch_works(art)
        for pair in records:
            print(pair[0])

    def download(self, art, work):
        artists = dict(fetch_artists())
        if art not in artists:
            raise Exception('sorry, the artist {} not exists'.format(art))
        works = dict(fetch_works(art))
        entry_link = works.get(work, None)
        print(art, work, entry_link)
        if entry_link is None:
            ## maybe we should give a choice menu?
            raise Exception('sorry, the work {} not exists'.format(work))

        ## now start to crawl
        with requests.Session() as sess:
            sess.headers.update(fake_headers)
            resp = sess.get(entry_link)
            html = PQ(resp.content.decode('gbk'))

            pages = [(el.text, el.attrib['value']) for el in html('select[name="turnPage"] > option')]
            print(pages)
            pages = sorted(pages, key=lambda pair: pair[0])

            targets = []
            for name, sub_uri in pages:
                link = 'http://www.pingshu8.com{}'.format(sub_uri)
                print('analyzing {} => {}'.format(name, link))
                resp = sess.get(link)
                html = PQ(resp.content.decode('gbk'))
                names = [el.text for el in html('ul  form[name="form"]  li.a1 a')]
                links = [el.attrib['href'] for el in html('ul form[name="form"] li.a2 a')]
                targets.extend(zip(names, links))

        dest = "./{}/{}".format(art, work)
        ## now begin to download
        for name, link in targets:
            print('downloading {} => {}'.format(name, link))
            analyze_and_download(sess, dest, name, link)

if '__main__' == __name__:
    Fire(Commands)
