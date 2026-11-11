import json
import os
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

URL = 'https://m.dcinside.com/board/pokemongoplus?headid=80'
STATE = Path('seen.json')
WEBHOOK = os.environ.get('DISCORD_WEBHOOK_URL', '')

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.href = dict(attrs).get('href', '')
            self.text = []
    def handle_data(self, data):
        if self.href is not None:
            self.text.append(data)
    def handle_endtag(self, tag):
        if tag == 'a' and self.href is not None:
            self.links.append((self.href, ' '.join(''.join(self.text).split())))
            self.href = None
            self.text = []

def request(url, data=None):
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1', 'Accept-Language': 'ko-KR,ko;q=0.9'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode('utf-8', errors='replace')

def main():
    if not WEBHOOK:
        sys.exit('DISCORD_WEBHOOK_URL secret missing')
    parser = LinkParser()
    parser.feed(request(URL))
    found = {}
    for href, title in parser.links:
        full = urllib.parse.urljoin(URL, href)
        parsed = urllib.parse.urlparse(full)
        match = re.fullmatch(r'/board/pokemongoplus/(\d+)', parsed.path)
        if match and title and len(title) >= 2:
            found[match.group(1)] = {'title': title[:180], 'url': f'https://m.dcinside.com/board/pokemongoplus/{match.group(1)}'}
    if not found:
        sys.exit('No post links found. Site may have changed or blocked access; keeping state unchanged.')
    current = sorted(found, key=int, reverse=True)[:80]
    if not STATE.exists():
        STATE.write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n')
        print(f'Initialized {len(current)} posts, no alerts on first run')
        return
    old = set(json.loads(STATE.read_text()))
    new = sorted((x for x in current if x not in old), key=int)
    for post_id in new[:20]:
        post = found[post_id]
        content = f'🔔 **포고플갤 이벤 탭 새 글**\n**{post["title"]}**\n{post["url"]}'
        request(WEBHOOK, json.dumps({'content': content, 'allowed_mentions': {'parse': []}}, ensure_ascii=False).encode('utf-8'))
        print('Sent:', post_id)
    STATE.write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n')
    print(f'Checked {len(current)} posts, new {len(new)}')

if __name__ == '__main__':
    main()
