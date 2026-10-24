# ブログの公開日に、公式LINEへお知らせを送る（月2回：12/2の記事から1本おき）
# 使い方：python3 tools/line_blog.py src/pages [YYYY-MM-DD] [--dry]
#  ・LINE_TOKEN（GitHub の Secrets に代表が登録）がないときは送らない
#  ・LINE_BLOG_ON が 1 のときだけ送る（止めたいときは GitHub の Variables で 0 にする）
import os, re, sys, json, datetime, urllib.request
SRC = sys.argv[1]
args = [a for a in sys.argv[2:] if not a.startswith('--')]
DRY = '--dry' in sys.argv
JST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = args[0] if args else datetime.datetime.now(JST).strftime('%Y-%m-%d')
BASE = os.environ.get('SITE_BASE', 'https://hayashi-group.jp/').rstrip('/') + '/'
START = '2026-12-02'   # この日の記事から、1本おきに送る（月2回くらい）

posts = []
for f in sorted(os.listdir(SRC)):
    if not re.match(r'BlogPost\d*\.html$', f): continue
    s = open(os.path.join(SRC, f), encoding='utf-8').read()
    d = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})"', s)
    t = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S)
    c = re.search(r'font-weight: 700">([^<]+)</span><time', s)
    if d and t: posts.append(dict(f=f, d=d.group(1), cat=c.group(1) if c else '', title=re.sub(r'<[^>]+>', '', t.group(1)).strip()))
today = [p for p in posts if p['d'] == TODAY]
seq = sorted(p['d'] for p in posts if p['d'] >= START)
send_day = TODAY in seq and seq.index(TODAY) % 2 == 0
# 「院からのお知らせ」（年末年始の休みなど）は、1本おきのルールに関係なく送る（10/24 代表：案A）
if any(p['cat'] == '院からのお知らせ' for p in today) and TODAY >= START: send_day = True
if not today or not send_day:
    print('今日はお知らせなし', TODAY, '記事あり' if today else '記事なし', '送る日' if send_day else '送らない週'); sys.exit(0)
p = today[0]
blog = open(os.path.join(SRC, 'Blog.html'), encoding='utf-8').read()
m = re.search(r'<a href="%s"[^>]*>\s*<img src="\./img/([^"]+)"' % re.escape(p['f']), blog)
img = BASE + 'img/' + (m.group(1) if m else 'logo.png')
url = BASE + p['f'] + '?utm_source=line&utm_medium=message&utm_campaign=blog'
msg = {'type': 'flex', 'altText': ('【院からのお知らせ】' if p['cat'] == '院からのお知らせ' else '【カラダのブログ】') + p['title'], 'contents': {
    'type': 'bubble',
    'hero': {'type': 'image', 'url': img, 'size': 'full', 'aspectRatio': '16:10', 'aspectMode': 'cover', 'action': {'type': 'uri', 'uri': url}},
    'body': {'type': 'box', 'layout': 'vertical', 'spacing': 'sm', 'contents': [
        {'type': 'text', 'text': '院からのお知らせ' if p['cat'] == '院からのお知らせ' else '今週のカラダのブログ', 'size': 'sm', 'color': '#17594F', 'weight': 'bold'},
        {'type': 'text', 'text': p['title'], 'size': 'lg', 'weight': 'bold', 'wrap': True, 'color': '#1B2A27'},
        {'type': 'text', 'text': 'はやしハリきゅう整骨院 江別本院', 'size': 'xs', 'color': '#4A5C58'}]},
    'footer': {'type': 'box', 'layout': 'vertical', 'contents': [
        {'type': 'button', 'style': 'primary', 'color': '#17594F', 'action': {'type': 'uri', 'label': '記事を読む', 'uri': url}}]}}}
print(json.dumps(msg, ensure_ascii=False, indent=1))
token = os.environ.get('LINE_TOKEN', '')
if DRY or not token or os.environ.get('LINE_BLOG_ON') != '1':
    print('送っていません（お試し・または設定がオフ）'); sys.exit(0)
req = urllib.request.Request('https://api.line.me/v2/bot/message/broadcast', data=json.dumps({'messages': [msg]}).encode(),
                             headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token, 'X-Line-Retry-Key': __import__('uuid').uuid4().__str__()})
with urllib.request.urlopen(req, timeout=30) as r:
    print('送りました', r.status)
