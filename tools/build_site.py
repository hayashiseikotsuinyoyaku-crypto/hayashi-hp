# 公開用のHPを作る：src/pages（HP確認用と同じ中身・全部の記事）→ out/（その日に出してよいページだけ）
# 使い方：python3 tools/build_site.py src/pages out [YYYY-MM-DD]
#  ・トップ：PC（Main）とスマホ（Sp）を1つの index.html にまとめ、画面の幅で切り替える
#  ・ブログ：日付が来ていない記事は出さない（一覧・関連リンクからも外す）。毎日作り直すと、その日の記事が出る
#  ・ブログの分類（すべて・季節のカラダ…）を押すと、その分類だけ出す
#  ・canonical・OGP・ファビコン・sitemap.xml・robots.txt・404.html
import os, re, sys, shutil, datetime, html
SRC, OUT = sys.argv[1], sys.argv[2]
TODAY = sys.argv[3] if len(sys.argv) > 3 else (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime('%Y-%m-%d')
BASE = os.environ.get('SITE_BASE', 'https://hayashi-group.jp/').rstrip('/') + '/'
SITE = 'はやしハリきゅう整骨院 江別本院'
PREVIEW = os.environ.get('PREVIEW') == '1'  # 仮公開中は検索に出さない
# Googleアナリティクス（GA4）の測定ID（G-XXXXXXX）。空なら入れない。仮公開中は入れない（テストの閲覧で数字が汚れないように）
GA_ID = os.environ.get('GA_ID', '').strip()
def ga_tag():
    if not GA_ID or PREVIEW or not re.match(r'^G-[A-Z0-9]+$', GA_ID): return ''
    return ('<script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script>\n'
            '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag("js",new Date());gtag("config","%s")</script>\n') % (GA_ID, GA_ID)
import urllib.parse, urllib.request, json as _gj
# Googleの口コミ（★と件数）：予約システムの ?p=reviews から毎日読む（院のアカウントの「口コミ取り込み」が毎朝送っている）。読めないときは書いてある数字のまま
REVIEWS_URL = os.environ.get('REVIEWS_URL', '').strip()
def load_reviews():
    if not REVIEWS_URL: return None
    try:
        with urllib.request.urlopen(urllib.request.Request(REVIEWS_URL, headers={'User-Agent': 'hayashi-hp-build'}), timeout=30) as r:
            d = _gj.loads(r.read().decode('utf-8'))
        if not d.get('ok') or not (0 < float(d.get('rating') or 0) <= 5) or int(d.get('count') or 0) < 1: return None
        at = datetime.datetime.strptime(str(d.get('at', ''))[:19], '%Y-%m-%dT%H:%M:%S') + datetime.timedelta(hours=9)
        return {'rating': round(float(d['rating']), 1), 'count': int(d['count']), 'date': '%d年%d月%d日' % (at.year, at.month, at.day)}
    except Exception as e:
        print('口コミを読めませんでした（書いてある数字のまま）：', e); return None
GREV = load_reviews()
def grev_patch(s):
    if not GREV: return s
    r, n, d = GREV['rating'], GREV['count'], GREV['date']
    s = re.sub(r'aria-label="Googleの口コミ 星[0-9.]+・[0-9,]+件（[^）]*時点）"', 'aria-label="Googleの口コミ 星%.1f・%d件（%s時点）"' % (r, n, d), s)
    s = re.sub(r'(line-height: 1; color: #1B2A27">)[0-9.]+(</b><span style="display: flex; flex-direction: column; gap: 4px">)', lambda m: m.group(1) + '%.1f' % r + m.group(2), s)
    s = re.sub(r'(left: 0; top: 0; width: )[0-9.]+(%; overflow: hidden; white-space: nowrap; color: #E8A317)', lambda m: m.group(1) + str(int(round(r / 5 * 100))) + m.group(2), s)
    s = re.sub(r'(Googleの口コミ <b style="color: #1B2A27">)[0-9,]+件', lambda m: m.group(1) + '%d件' % n, s)
    s = re.sub(r'[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日時点。口コミの本文は', d + '時点。口コミの本文は', s)
    return s
BPATH = urllib.parse.urlparse(BASE).path or '/'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
shutil.copytree(os.path.join(SRC, 'img'), os.path.join(OUT, 'img'))
rd = lambda f: open(os.path.join(SRC, f), encoding='utf-8').read()

# ---- お知らせ（2026-11-21）：tools/news.json に書いた分から「お知らせ」のページを作り、トップページのいちばん上に新しい3件を出す ----
#  ・載せるのは日付が来た分だけ（先の日付は その日になってから出る）。新しい順
#  ・1件：{"date":"2026-12-01","cat":"お知らせ|休診|ブログ","title":"…","body":["段落",…],"img":"news_x.jpg"(なくてもよい),"link":["Faq.html","文字"](なくてもよい)}
_nj = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'news.json')
NEWS = [n for n in (_gj.load(open(_nj, encoding='utf-8')) if os.path.exists(_nj) else []) if n.get('date', '') <= TODAY or PREVIEW or os.environ.get('NEWS_ALL') == '1']
# 2026-11-22：ブログを出した日に「ブログを更新しました」を自動で足す（手で書かなくてよい）。日付が来ていない記事は足さない
for _f in sorted(os.listdir(SRC)):
    if re.match(r'BlogPost\d*\.html$', _f):
        _s = open(os.path.join(SRC, _f), encoding='utf-8').read()
        _m = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})"', _s); _t = re.search(r'<title>(.*?)</title>', _s, re.S)
        if _m and _t and _m.group(1) <= TODAY:
            NEWS.append({'date': _m.group(1), 'cat': 'ブログ', 'title': 'ブログ：' + html.unescape(_t.group(1)).split('｜')[0].strip(), 'body': [], 'link': [_f, 'この記事を読む'], 'blog': True})
NEWS.sort(key=lambda n: (n['date'], 0 if n.get('blog') else 1), reverse=True)
_E = html.escape
def _nd(d): return '%d年%d月%d日' % (int(d[:4]), int(d[5:7]), int(d[8:10]))
_NC = {'休診': '#B5451B', 'ブログ': '#1F5E8C'}
def _chip(c): return '<span style="display: inline-block; padding: 1px 10px; border-radius: 999px; background: %s; color: #FFFFFF; font-size: 12px; font-weight: 700; white-space: nowrap">%s</span>' % (_NC.get(c, '#17594F'), _E(c))
def news_page():
    base = open(os.path.join(SRC, 'Privacy.html'), encoding='utf-8').read()
    h, f = base.find('</header>') + 9, base.find('<footer')
    items = ''.join(
        '<article id="n%d" style="border: 1px solid #C9D8D4; border-radius: 14px; padding: 20px 22px; background: #FFFFFF; display: flex; flex-direction: column; gap: 10px">'
        '<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 10px; font-size: 14px; color: #4A5C58"><time datetime="%s">%s</time>%s</div>'
        '<h2 style="margin: 0; font-size: 22px; line-height: 1.5; font-weight: 900">%s</h2>%s%s%s</article>'
        % (i, n['date'], _nd(n['date']), _chip(n.get('cat', 'お知らせ')), _E(n['title']),
           ('<img src="./img/%s" alt="%s" loading="lazy" style="width: 100%%; max-width: 560px; border-radius: 12px; display: block">' % (_E(n['img']), _E(n['title']))) if n.get('img') else '',
           ''.join('<p style="margin: 0; font-size: 16px; color: #3A4B47">%s</p>' % _E(x) for x in n.get('body', [])),
           ('<a href="%s" style="font-weight: 700">%s</a>' % (_E(n['link'][0]), _E(n['link'][1]))) if n.get('link') else '')
        for i, n in enumerate(NEWS)) or '<p style="margin: 0; color: #3A4B47">いまお知らせはありません。</p>'
    mid = ('\n<nav aria-label="現在の場所" style="max-width: 1200px; margin: 0 auto; padding: 10px 24px; font-size: 13px; color: #4A5C58"><a href="Main.html">トップ</a> ＞ お知らせ</nav>\n'
           '<section aria-labelledby="hero-h" style="background: #F2F6F4"><div style="max-width: 900px; margin: 0 auto; padding: 48px 24px 52px; display: flex; flex-direction: column; gap: 16px">'
           '<h1 id="hero-h" style="margin: 0; font-size: 36px; line-height: 1.4; font-weight: 900">お知らせ</h1>'
           '<p style="margin: 0; font-size: 16px; color: #3A4B47">休診日・ブログの更新・院からのご案内をお伝えします。</p></div></section>\n'
           '<section aria-label="お知らせの一覧" style="background: #FFFFFF"><div style="max-width: 900px; margin: 0 auto; padding: 40px 24px 56px; display: flex; flex-direction: column; gap: 16px">%s</div></section>\n') % items
    out = base[:h] + mid + base[f:]
    out = re.sub(r'<title>.*?</title>', '<title>お知らせ｜はやしハリきゅう整骨院 江別本院</title>', out, count=1, flags=re.S)
    out = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="はやしハリきゅう整骨院 江別本院（江別市）からのお知らせ。休診日、ブログの更新、院からのご案内を新しい順にお伝えします。">', out, count=1)
    open(os.path.join(SRC, 'News.html'), 'w', encoding='utf-8').write(out)
news_page()
def news_strip(sp=False):
    if not NEWS: return ''
    top = [x for x in enumerate(NEWS) if not x[1].get('blog')][:2]; top = (top + [x for x in enumerate(NEWS) if x[1].get('blog')])[:3]
    rows = ''.join('<a href="News.html#n%d" style="display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; padding: 8px 0; border-top: %s; color: #1B2A27; text-decoration: none"><time datetime="%s" style="font-size: 13px; color: #4A5C58; white-space: nowrap">%s</time>%s<span style="font-weight: 700; font-size: 15px">%s</span></a>'
                   % (i, '0' if j == 0 else '1px solid #E3ECE9', n['date'], _nd(n['date']), _chip(n.get('cat', 'お知らせ')), _E(n['title'])) for j, (i, n) in enumerate(top))
    if sp:   # 2026-11-26：スマホは最初の画面で院の顔が見えるように 件名は新しい1件だけ
        rows = rows[:rows.find('</a>') + 4]
    if sp:   # スマホ：場所を取らないように「お知らせ ……… 一覧を見る」を1行にして、その下に件名
        return ('<section aria-label="お知らせ" style="background: #FFFFFF; border-bottom: 1px solid #DCE5E2"><div style="padding: 4px 16px 6px; display: flex; flex-wrap: wrap; align-items: center">'
                '<h2 style="margin: 0; flex: 1 1 auto; padding: 4px 0; font-size: 14px; font-weight: 900; color: #17594F">お知らせ</h2>'
                '<a href="News.html" style="padding: 4px 0; font-size: 13px; font-weight: 700">一覧を見る</a><div style="flex: 1 1 100%%; min-width: 0">%s</div></div></section>\n') % rows.replace('padding: 8px 0;', 'padding: 5px 0;')
    return ('<section aria-label="お知らせ" style="background: #FFFFFF; border-bottom: 1px solid #DCE5E2"><div style="max-width: 1200px; margin: 0 auto; padding: %s; display: flex; flex-wrap: wrap; align-items: flex-start; gap: 6px 20px">'
            '<h2 style="margin: 0; padding: 8px 0; font-size: 15px; font-weight: 900; color: #17594F; white-space: nowrap">お知らせ</h2><div style="flex: 1 1 280px; min-width: 0">%s</div>'
            '<a href="News.html" style="padding: 8px 0; font-size: 14px; font-weight: 700; white-space: nowrap">一覧を見る</a></div></section>\n') % ('6px 16px' if sp else '6px 24px', rows)
pages = sorted(f for f in os.listdir(SRC) if f.endswith('.html'))

# 1) ブログの日付
post_date = {}
for f in pages:
    if re.match(r'BlogPost\d*\.html$', f):
        m = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})"', rd(f))
        post_date[f] = m.group(1) if m else '0000-00-00'
hidden = {f for f, d in post_date.items() if d > TODAY}

# ブログの入口：トップの「新着ブログ」・症状のページの「関連するブログ」（その日に出ている記事だけ・新しい順）
CARDS = {}
for _m in re.finditer(r'<a href="(BlogPost\d*\.html)"[^>]*>(.*?)</a>', rd('Blog.html'), re.S):
    _f, _c = _m.group(1), _m.group(2)
    _img = re.search(r'<img src="([^"]+)" alt="([^"]*)"', _c)
    _cat = re.search(r'font-weight: 700">([^<]+)</span><time', _c)
    _t = re.search(r'<b[^>]*>(.*?)</b>', _c, re.S)
    _d = re.search(r'<time[^>]*>([^<]+)</time>', _c)
    if _img and _t:
        CARDS[_f] = dict(img=_img.group(1), alt=_img.group(2), cat=_cat.group(1) if _cat else '', title=_t.group(1), dtext=_d.group(1) if _d else '')
RELATED = {
    'Youtsu.html': ['BlogPost27.html', 'BlogPost28.html', 'BlogPost.html', 'BlogPost3.html', 'BlogPost8.html', 'BlogPost7.html', 'BlogPost22.html'],
    'Gikkuri.html': ['BlogPost27.html', 'BlogPost3.html', 'BlogPost.html', 'BlogPost8.html', 'BlogPost22.html'],
    'Yukikaki.html': ['BlogPost.html', 'BlogPost3.html', 'BlogPost8.html'],
    'Kubikata.html': ['BlogPost25.html', 'BlogPost26.html', 'BlogPost2.html', 'BlogPost5.html'],
    'StraightNeck.html': ['BlogPost25.html', 'BlogPost26.html', 'BlogPost2.html'],
    'Makigata.html': ['BlogPost25.html', 'BlogPost2.html', 'BlogPost20.html'],
    'Zutsu.html': ['BlogPost26.html', 'BlogPost5.html', 'BlogPost2.html'],
    'Nechigae.html': ['BlogPost5.html', 'BlogPost2.html'],
    'Gojukata.html': ['BlogPost20.html', 'BlogPost2.html'],
    'Hiza.html': ['BlogPost17.html', 'BlogPost13.html'],
    'Tentou.html': ['BlogPost4.html'],
    'Nenza.html': ['BlogPost23.html', 'BlogPost4.html'],
    'Sports.html': ['BlogPost23.html', 'BlogPost13.html'],
    'Zakotsu.html': ['BlogPost28.html', 'BlogPost7.html', 'BlogPost3.html'],
    'Sango.html': ['BlogPost28.html', 'BlogPost7.html', 'BlogPost9.html'],
    'Karada.html': ['BlogPost25.html', 'BlogPost7.html', 'BlogPost9.html'],
    'Kotsupika.html': ['BlogPost9.html', 'BlogPost7.html'],
    'Jiko.html': ['BlogPost6.html', 'BlogPost11.html', 'BlogPost12.html', 'BlogPost24.html', 'BlogPost14.html', 'BlogPost15.html',
                  'BlogPost16.html', 'BlogPost18.html', 'BlogPost19.html', 'BlogPost21.html'],
}


def visible_latest(files, n=3):
    fs = [f for f in files if f in CARDS and f not in hidden]
    return sorted(fs, key=lambda f: post_date.get(f, ''), reverse=True)[:n]


def blog_cards(files, sp=False):
    out = []
    for f in files:
        c = CARDS[f]
        if sp:  # スマホ：写真を左に小さく・文字を右に（縦に長くならないように）
            out.append('<a href="%s" style="text-decoration: none; color: #1B2A27; background: #FFFFFF; border: 1px solid #C9D8D4; border-radius: 14px; overflow: hidden; display: grid; grid-template-columns: 112px 1fr; align-items: center">'
                       '<img src="%s" alt="%s" loading="lazy" style="width: 112px; height: 100%%; min-height: 96px; max-height: 120px; object-fit: contain; display: block; background: #F2F6F4">'
                       '<span style="padding: 10px 12px; display: flex; flex-direction: column; gap: 4px"><span style="display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: center">'
                       '<span style="display: inline-flex; align-items: center; min-height: 22px; padding: 0 8px; border-radius: 999px; background: #E3F0EB; color: #17594F; font-size: 11px; font-weight: 700">%s</span>'
                       '<time datetime="%s" style="font-size: 11px; color: #4A5C58">%s</time></span><b style="font-size: 15px; line-height: 1.5">%s</b></span></a>'
                       % (f, c['img'], c['alt'], c['cat'], post_date.get(f, ''), c['dtext'], c['title']))
            continue
        out.append('<a href="%s" style="text-decoration: none; color: #1B2A27; background: #FFFFFF; border: 1px solid #C9D8D4; border-radius: 16px; overflow: hidden; display: flex; flex-direction: column">'
                   '<img src="%s" alt="%s" loading="lazy" style="width: 100%%; aspect-ratio: 16 / 10; object-fit: contain; display: block; background: #F2F6F4">'
                   '<span style="padding: 12px 14px 16px; display: flex; flex-direction: column; gap: 6px"><span style="display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: center">'
                   '<span style="display: inline-flex; align-items: center; min-height: 24px; padding: 0 10px; border-radius: 999px; background: #E3F0EB; color: #17594F; font-size: 12px; font-weight: 700">%s</span>'
                   '<time datetime="%s" style="font-size: 12px; color: #4A5C58">%s</time></span><b style="font-size: %s; line-height: 1.5">%s</b></span></a>'
                   % (f, c['img'], c['alt'], c['cat'], post_date.get(f, ''), c['dtext'], '16px' if sp else '17px', c['title']))
    out = [o.replace('align-items: center"><span style="display: inline-flex', 'align-items: center">' + NEWB + '<span style="display: inline-flex', 1) if re.search(r'href="(BlogPost\d*\.html)"', o).group(1) in NEW else o for o in out]
    return ''.join(out)


def blog_section(title, files, sp=False, bg='#FFFFFF'):
    if not files:
        return ''
    if sp:
        return ('<section aria-label="%s" style="background: %s; padding: 28px 16px; display: flex; flex-direction: column; gap: 12px">'
                '<h2 class="reveal" style="margin: 0; font-size: 22px; font-weight: 900">%s</h2>'
                '<div style="display: grid; grid-template-columns: 1fr; gap: 12px">%s</div>'
                '<a href="Blog.html" style="font-weight: 700">ブログの一覧を見る</a></section>\n') % (title, bg, title, blog_cards(files, True))
    return ('<section aria-label="%s" style="background: %s">'
            '<div style="max-width: 1200px; margin: 0 auto; padding: 56px 24px; display: flex; flex-direction: column; gap: 20px">'
            '<h2 class="reveal" style="margin: 0; font-size: 28px; line-height: 1.4; font-weight: 900">%s</h2>'
            '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 360px)); gap: 20px">%s</div>'
            '<a href="Blog.html" style="font-weight: 700">ブログの一覧を見る</a></div></section>\n') % (title, bg, title, blog_cards(files))


LATEST = visible_latest(list(CARDS))
_td = datetime.date.fromisoformat(TODAY)
NEW = {f for f, d in post_date.items() if f not in hidden and d != '0000-00-00' and (_td - datetime.date.fromisoformat(d)).days <= 7}
NEWB = '<span style="display: inline-flex; align-items: center; min-height: 20px; padding: 0 8px; border-radius: 999px; background: #D9480F; color: #FFFFFF; font-size: 11px; font-weight: 900; letter-spacing: 0.06em">NEW</span>'
NEWB_S = '<span aria-label="新しい記事があります" style="display: inline-block; margin-left: 4px; padding: 0 5px; border-radius: 6px; background: #D9480F; color: #FFFFFF; font-size: 10px; font-weight: 900; line-height: 1.6; vertical-align: middle">NEW</span>'

def out_name(f): return 'index.html' if f == 'Main.html' else f
def fix_links(s):
    s = re.sub(r'href="(?:Main|Sp)\.html(#[^"]*)?"', lambda m: 'href="./' + (m.group(1) or '') + '"', s)
    # まだ出していない記事へのリンク：ボタン型は消す・文中は文字だけ残す
    def a_repl(m):
        tag, href, inner = m.group(0), m.group(1), m.group(2)
        if href not in hidden: return tag
        return '' if re.search(r'style="[^"]*display', tag[:300]) else inner
    s = re.sub(r'<a\b[^>]*?href="(BlogPost\d*\.html)"[^>]*>(.*?)</a>', a_repl, s, flags=re.S)
    return s

def head_extra(f, s):
    t = re.search(r'<title>(.*?)</title>', s, re.S); t = t.group(1).strip() if t else SITE
    d = re.search(r'<meta name="description" content="([^"]*)"', s); d = d.group(1) if d else ''
    img = re.search(r'<img src="\./img/([^"]+\.(?:jpg|png))"[^>]*>', s[s.find('<main') if '<main' in s else s.find('</header>'):] if '</header>' in s else s)
    # URLを貼ったときの画像：ブログの記事はその記事の画像、ほかのページは院の専用画像（ogp.png・代表 11/1：トップが交通事故の絵になっていたため）
    ogimg = BASE + 'img/' + (img.group(1) if f.startswith('BlogPost') and img and 'logo' not in img.group(1) else 'ogp.png')
    url = BASE + ('' if f == 'Main.html' else f)
    return ('<link rel="canonical" href="%s">\n<link rel="icon" href="./img/logo.png">\n<link rel="apple-touch-icon" href="./img/logo.png">\n'
            '<meta property="og:type" content="%s">\n<meta property="og:site_name" content="%s">\n<meta property="og:title" content="%s">\n'
            '<meta property="og:description" content="%s">\n<meta property="og:url" content="%s">\n<meta property="og:image" content="%s">\n'
            '<meta name="twitter:card" content="summary_large_image">\n' + ('<meta name="robots" content="noindex">\n' if PREVIEW else '') + ga_tag()) % (url, 'website' if f == 'Main.html' else 'article', SITE, t, d, url, ogimg)

def body_of(s): return s[s.find('<body>') + 6: s.rfind('</body>')]
def head_of(s): return s[s.find('<head>') + 6: s.find('</head>')]

TOTOP = ('<style>html{scroll-behavior:smooth}#totop{position:fixed;right:16px;bottom:24px;z-index:60;width:56px;height:56px;border-radius:50%;border:2px solid #17594F;'
         'background:#FFFFFF;color:#17594F;font:700 12px/1.1 "Zen Kaku Gothic New","Hiragino Sans",sans-serif;cursor:pointer;box-shadow:0 4px 14px rgba(27,42,39,.2);'
         'display:none;flex-direction:column;align-items:center;justify-content:center;gap:2px}#totop.on{display:flex}'
         '@media (max-width:767px){body:has(.v-sp) #totop{bottom:96px}}</style>'
         '<button id="totop" type="button" aria-label="ページの一番上へ"><span aria-hidden="true" style="font-size:18px">▲</span>上へ</button>'
         '<script>(function(){var b=document.getElementById("totop");addEventListener("scroll",function(){b.classList.toggle("on",scrollY>600)},{passive:true});'
         'b.onclick=function(){scrollTo({top:0,behavior:"smooth"})}})()</script>\n')

# 整骨院の情報（Googleが読み取りやすい形：構造化データ）。トップページだけに入れる
import json as _json
def clinic_ld():
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'PublicHolidays']
    oh = [{'@type': 'OpeningHoursSpecification', 'dayOfWeek': days, 'opens': '09:00', 'closes': '12:00'},
          {'@type': 'OpeningHoursSpecification', 'dayOfWeek': [d for d in days if d != 'Wednesday'], 'opens': '15:00', 'closes': '19:00'}]
    d = {'@context': 'https://schema.org', '@type': 'MedicalClinic', '@id': BASE + '#clinic',
         'name': 'はやしハリきゅう整骨院 江別本院', 'url': BASE, 'telephone': '+81-11-384-5454',
         'image': BASE + 'img/gaikan.jpg', 'logo': BASE + 'img/logo.png',
         'description': '江別市元町の整骨院・鍼灸院。骨ぴか整体（骨格矯正）、鍼灸、交通事故（自賠責保険）のケガに対応。予約優先制。日曜・祝日も受付。第1水曜日は休診、ほかの水曜日は午後休診。',
         'address': {'@type': 'PostalAddress', 'postalCode': '067-0031', 'addressRegion': '北海道', 'addressLocality': '江別市', 'streetAddress': '元町32-1', 'addressCountry': 'JP'},
         'openingHoursSpecification': oh, 'medicalSpecialty': 'Musculoskeletal',
         'amenityFeature': [{'@type': 'LocationFeatureSpecification', 'name': '無料駐車場', 'value': True}],
         'parentOrganization': {'@type': 'Organization', 'name': '株式会社ぴっかぴか'},
         # 11/11：Google・AI に「いつから・どこで・だれが・何を」を事実で伝える（代表 11/11：AIの検索からも信頼される院に）
         'foundingDate': '1978-08-18', 'areaServed': [{'@type': 'City', 'name': '江別市'}, {'@type': 'City', 'name': '札幌市'}],
         'availableService': [{'@type': 'MedicalTherapy', 'name': n} for n in ['骨ぴか整体（骨格矯正）', '鍼（はり）・灸', '交通事故（自賠責保険）のケガの施術', 'ハイボルト療法', 'ショックマスター（衝撃波）', '筋肉矯正', 'ピークパフォーマンスストレッチ（PPS）']],
         'employee': [{'@type': 'Person', 'name': '林 恒博', 'jobTitle': '総括院長', 'url': BASE + 'Staff.html',
                       'description': '男子新体操の選手としてケガと復帰を経験し、全日本選手権大会で優勝三連覇。その経験と運動学・解剖学・スポーツ心理学をもとに、骨格施術と姿勢指導を行う。',
                       'award': '男子新体操 全日本選手権大会 優勝三連覇', 'knowsAbout': ['骨格矯正', '鍼灸', '交通事故（自賠責保険）のケガ', 'スポーツのケガと復帰', 'スポーツ心理学', '姿勢指導'],
                       'hasCredential': [{'@type': 'EducationalOccupationalCredential', 'credentialCategory': '国家資格', 'name': n} for n in ['柔道整復師', 'はり師', 'きゅう師']]}]}
    return '<script type="application/ld+json">' + _json.dumps(d, ensure_ascii=False) + '</script>\n'
def _txt(h): return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', h))).strip()
# 2026-11-23：写真を軽い形式（webp）で出す。見た目は同じ・スマホで開くのが速くなる。
#  ・src/pages/img に 同じ名前の .webp があるときだけ、<img> の src をそちらに変える（ない写真は そのまま）
#  ・検索やSNSに出す絵（og:image・名札の image・logo）と 動画の表紙（poster）は jpg/png のまま（<img> だけを変える）
_WEBP = set(os.path.splitext(n)[0] for n in os.listdir(os.path.join(SRC, 'img')) if n.endswith('.webp'))
def webp_imgs(s):
    def rep(m):
        return m.group(1) + m.group(2) + '.webp' + (m.group(4) or '') + '"' if m.group(2) in _WEBP else m.group(0)
    return re.sub(r'(<img\b[^>]*?\bsrc="\./img/)([^"./?]+)\.(jpg|png)(\?[^"]*)?"', rep, s)
_SPNAV = re.search(r'<nav aria-label="予約・お問い合わせ".*?</nav>', open(os.path.join(SRC, 'Sp.html'), encoding='utf-8').read(), re.S).group(0)
BKBAR = ('<style>#bkbar,#bkbar a{font-family:"Zen Kaku Gothic New","Hiragino Sans","Noto Sans JP",sans-serif}#bkbar{display:none!important}@media (max-width:767px){#bkbar{display:grid!important;position:fixed!important}body{padding-bottom:84px}#totop{bottom:100px!important}}</style>\n'
         + _SPNAV.replace('<nav ', '<nav id="bkbar" ', 1) + '\n')
_CTA_NOTE = '<p style="margin: 6px 0 0; color: #FFFFFF; font-size: 15px"><span style="display: inline-block">初回は約60分です</span> <span style="display: inline-block">ご予約がなくても受付しています</span> <a href="Ryokin.html" style="display: inline-block; color: #FFFFFF; font-weight: 700">料金の目安を見る</a></p>'
_CHK_CTA = ('<div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-top: 6px"><b style="flex: 1 1 100%; color: #17594F">ひとつでも当てはまったらお気軽にどうぞ</b>'
            '<a href="https://lin.ee/aRHpprR" target="_blank" rel="noopener" style="display: inline-flex; align-items: center; min-height: 48px; padding: 0 20px; border-radius: 12px; background: #04893F; color: #FFFFFF; text-decoration: none; font-weight: 700; font-size: 16px">LINEでまず相談する</a>'
            '</div>')
def polish(f, s):
    # 2026-11-26：写真の説明（alt）が空で すぐ下に説明の字があるものは その字を alt に入れる
    s = re.sub(r'(<img\b[^>]*?)alt=""([^>]*>\s*<figcaption[^>]*>)([^<]+)(</figcaption>)', lambda m: m.group(1) + 'alt="%s"' % html.escape(m.group(3).strip(), quote=True) + m.group(2) + m.group(3) + m.group(4), s)
    # 2026-11-26：しめくくりの見出しと住所の行は ことばの切れ目でだけ改行する（「が／まんせずに」「32-／1」にならないように）
    _ib = lambda t: '<span style="display: inline-block">%s</span>' % t
    s = s.replace('つらいときはがまんせずにご相談ください</h2>', _ib('ツライときは') + _ib('ガマンせずに') + _ib('ご相談ください') + '</h2>')
    s = re.sub(r'(<p style="margin: 0; color: #D6E2DF">)([^<]*〒[^<]*)(</p>)', lambda m: m.group(1) + ' '.join(_ib(x) for x in m.group(2).split('　')) + m.group(3), s)
    if f in ('Main.html', 'Sp.html') or 'https://lin.ee/aRHpprR' not in s: return s
    # 予約の帯（スマホだけ・下に出し続ける）
    s = s.replace('</body>', BKBAR + '</body>', 1)
    # しめくくりの予約の所に 時間と料金の案内
    k = s.find('id="cta-h"')
    if k > 0:
        e = s.find('</p>', k)
        if 0 < e < s.find('</section>', k): s = s[:e + 4] + '\n' + _CTA_NOTE + s[e + 4:]
    # チェック項目のすぐ下に 相談と予約のボタン
    k = s.find('<section id="chk"')
    if k > 0:
        e = s.find('</ul>', k)
        if 0 < e < s.find('</section>', k): s = s[:e + 5] + '\n' + _CHK_CTA + s[e + 5:]
    return s
def faq_ld(s):
    # 「Q. … A. …」の形（details/summary）を、よくある質問の名札（FAQPage）にする。画面に出ている文そのまま
    qa = []
    for m in re.finditer(r'<details\b[^>]*>\s*<summary[^>]*>(.*?)</summary>(.*?)</details>', s, re.S):
        q = _txt(m.group(1).split('Q.</span>', 1)[-1]); a = _txt(re.sub(r'<b[^>]*>A\.</b>', '', m.group(2)))
        if 'もっと見る' in q: continue   # 質問の形のものだけ（「もっと見る」などは入れない）
        if q and a and not any(x['name'] == q for x in qa): qa.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})
    if not qa: return ''
    return '<script type="application/ld+json">' + _json.dumps({'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': qa}, ensure_ascii=False) + '</script>\n'
def page_name(s):
    t = re.search(r'<title>(.*?)</title>', s, re.S); t = t.group(1).strip() if t else ''
    return re.split(r'[｜|]', t)[0].strip() or SITE
def crumb_ld(f, s):
    if f == 'Main.html': return ''
    it = [{'@type': 'ListItem', 'position': 1, 'name': 'ホーム', 'item': BASE}]
    if f.startswith('BlogPost'): it.append({'@type': 'ListItem', 'position': 2, 'name': 'ブログ', 'item': BASE + 'Blog.html'})
    it.append({'@type': 'ListItem', 'position': len(it) + 1, 'name': page_name(s), 'item': BASE + f})
    return '<script type="application/ld+json">' + _json.dumps({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': it}, ensure_ascii=False) + '</script>\n'
def post_ld(f, s):
    if not f.startswith('BlogPost'): return ''
    d = post_date.get(f, ''); img = re.search(r'<img src="\./img/([^"]+\.(?:jpg|png))"', s[s.find('</header>'):])
    desc = re.search(r'<meta name="description" content="([^"]*)"', s)
    o = {'@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': page_name(s)[:110], 'datePublished': d, 'dateModified': d, 'mainEntityOfPage': BASE + f,
         'author': {'@type': 'Organization', 'name': SITE, 'url': BASE}, 'publisher': {'@type': 'Organization', 'name': SITE, 'logo': {'@type': 'ImageObject', 'url': BASE + 'img/logo.png'}}}
    if img: o['image'] = BASE + 'img/' + img.group(1)
    if desc: o['description'] = desc.group(1)
    return '<script type="application/ld+json">' + _json.dumps(o, ensure_ascii=False) + '</script>\n'
def job_ld(f):
    # 採用ページ：Google の「しごと検索」に載るための名札（JobPosting）。中身は採用ページの募集要項と同じ（変えたら ここも直す）
    if f != 'Recruit.html': return ''
    o = {'@context': 'https://schema.org', '@type': 'JobPosting', 'title': '柔道整復師・鍼灸師（正社員）',
         'description': '<p>1978年創業の整骨院で 一緒に働く柔道整復師・鍼灸師を募集しています。入社3ヶ月以内に施術デビューできる新入社員研修があります。職場見学もできます。</p><p>仕事内容：整骨、鍼灸、トレーナー、骨格矯正、筋肉矯正、美容鍼、EMS、ハイボルト、ショックマスター</p><p>月給：柔道整復師 270,000円／鍼灸師 270,000円／両方の資格 300,000円（いずれも固定時間外手当40時間分を含む）。研修期間3ヶ月は240,000円。</p><p>休日：公休 月9日（2月は8日）、4連休を年2回、年末年始7日。</p><p>勤務時間：9:00〜13:00／15:00〜20:00。残業は月平均22時間。</p><p>保険：健康保険、厚生年金、雇用保険、労災保険、賠償責任保険。</p>',
         'datePosted': '2026-11-20', 'employmentType': 'FULL_TIME', 'directApply': False, 'url': BASE + 'Recruit.html',
         'hiringOrganization': {'@type': 'Organization', 'name': '株式会社ぴっかぴか（はやしハリきゅう整骨院 江別本院）', 'sameAs': BASE, 'logo': BASE + 'img/logo.png'},
         'jobLocation': {'@type': 'Place', 'address': {'@type': 'PostalAddress', 'postalCode': '067-0031', 'addressRegion': '北海道', 'addressLocality': '江別市', 'streetAddress': '元町32-1', 'addressCountry': 'JP'}},
         'baseSalary': {'@type': 'MonetaryAmount', 'currency': 'JPY', 'value': {'@type': 'QuantitativeValue', 'minValue': 270000, 'maxValue': 300000, 'unitText': 'MONTH'}},
         'qualifications': '柔道整復師 または はり師・きゅう師（新卒・既卒・ブランクのある方も可）'}
    return '<script type="application/ld+json">' + _json.dumps(o, ensure_ascii=False) + '</script>\n'
written = []; LLM = []
for f in pages:
    if f == 'Sp.html' or f in hidden: continue
    s = rd(f)
    if f in RELATED:
        s = s.replace('<footer', blog_section('関連するブログ', visible_latest(RELATED[f]), bg='#F7FAF9') + '<footer', 1)
    if f == 'Main.html':
        s = grev_patch(s)
        sp = grev_patch(rd('Sp.html')); spb = body_of(sp)
        s = s.replace('<section id="access"', blog_section('新着ブログ', LATEST) + '<section id="access"', 1)
        assert s.count('</header>') == 1; s = s.replace('</header>', '</header>\n' + news_strip(), 1)
        s = s.replace('<a href="Blog.html">ブログ</a>', '<a href="News.html">お知らせ</a><a href="Blog.html">ブログ</a>', 1)
        _k = spb.find('</nav>', spb.find('<nav id="sp-menu"')); assert _k > 0; spb = spb[:_k + 6] + '\n' + news_strip(True) + spb[_k + 6:]
        spb = spb.replace('<a href="Blog.html" style="display: flex; align-items: center; min-height: 48px;', '<a href="News.html" style="display: flex; align-items: center; min-height: 48px; padding: 0 16px; border-bottom: 1px solid #E3ECE9; color: #1B2A27; text-decoration: none; font-size: 15px; font-weight: 700">お知らせ</a><a href="Blog.html" style="display: flex; align-items: center; min-height: 48px;', 1)
        spb = spb.replace('<section style="background: #FFFFFF; padding: 28px 16px 120px', blog_section('新着ブログ', LATEST, sp=True, bg='#F7FAF9') + '<section style="background: #FFFFFF; padding: 28px 16px 120px', 1)
        # スマホ版のidは重ならないように sp- を付ける（ページ内リンクも）
        ids = set(re.findall(r'id="([^"]+)"', spb)) - {'sp-menu'}
        for i in ids:
            spb = spb.replace('id="%s"' % i, 'id="sp-%s"' % i).replace('aria-labelledby="%s"' % i, 'aria-labelledby="sp-%s"' % i).replace('href="#%s"' % i, 'href="#sp-%s"' % i)
        k = spb.find('<nav aria-label="グループのページ"')
        if k > 0:
            e = spb.find('</nav>', k)
            spb = spb[:e] + '<a href="Privacy.html" style="color: #FFFFFF">プライバシーポリシー</a>' + spb[e:]
        # 2026-11-21：前は パソコン用とスマホ用の中身を 両方ともページに入れて、見せるほうだけ切りかえていた（大見出しが2つ・同じ文が2回・写真160枚）。
        # → ページに入れるのはスマホ用だけ。パソコン用は <template>（ページの中身として数えられない・写真も読まない）に入れ、画面が広いときだけ取り出して差しかえる。
        #   検索（Googleはスマホの画面で読む）とAI（プログラムを動かさずに読む）には スマホ用の1つだけが見える
        sw = '<style>.v-pc{display:none}.is-pc .v-pc{display:block}.is-pc .v-sp{display:none}</style>'
        sph = re.sub(r'<(meta|title)[^>]*>(?:.*?</title>)?', '', head_of(sp), flags=re.S)
        s = s.replace('</head>', sph + sw + '\n</head>', 1)
        # スマホ用の写真：いちばん上の1枚のほかは 見える所まで来てから読む（パソコンでは読まれない）
        n_img = [0]
        def lazy(m):
            n_img[0] += 1
            return m.group(0) if (n_img[0] == 1 or 'loading=' in m.group(0)) else m.group(0).replace('<img ', '<img loading="lazy" decoding="async" ', 1)
        spb = re.sub(r'<img [^>]*>', lazy, spb)
        # スマホ用の動き（写真の切りかえ）は、パソコンの画面では動かさない（パソコン用のほうだけが動く）
        spb = re.sub(r'<script>\s*\(function', '<script>if(!document.documentElement.classList.contains("is-pc"))(function', spb)
        s = s.replace('<body>', '<body>\n<template id="v-pc-t">', 1)
        s = s[:s.rfind('</body>')] + '</template>\n<div class="v-pc" id="v-pc"></div>\n<script>(function(){var m=matchMedia("(min-width:768px)");if(m.matches){document.documentElement.classList.add("is-pc");document.getElementById("v-pc").appendChild(document.getElementById("v-pc-t").content.cloneNode(true));document.addEventListener("DOMContentLoaded",function(){var e=document.querySelector(".v-sp");if(e)e.remove()})}var w=m.matches;m.addEventListener("change",function(x){if(x.matches!==w)location.reload()})})()</script>\n<div class="v-sp">' + spb + '</div>\n<script>(function(){var h=location.hash.slice(1),e;if(h&&matchMedia("(max-width:767px)").matches&&(e=document.getElementById("sp-"+h)))setTimeout(function(){e.scrollIntoView()},50)})()</script>\n</body>' + s[s.rfind('</body>') + 7:]
    if f == 'Blog.html':
        # 分類のボタン（押すとその分類だけ）。カードに data-cat を付ける
        def card(m):
            c = re.search(r'font-weight: 700">([^<]+)</span><time', m.group(0))
            return m.group(0).replace('<a href=', '<a data-cat="%s" href=' % (c.group(1) if c else ''), 1)
        s = re.sub(r'<a href="BlogPost\d*\.html"[^>]*>.*?</a>', card, s, flags=re.S)
        nav = re.search(r'<nav aria-label="カテゴリー"[^>]*>(.*?)</nav>', s, re.S)
        if nav:
            btns = re.sub(r'<span style="([^"]*)">([^<]+)</span>', lambda m: '<button type="button" data-f="%s" style="%s;border:0;cursor:pointer;font-family:inherit" aria-pressed="%s">%s</button>' % ('' if m.group(2) == 'すべて' else m.group(2), m.group(1), 'true' if m.group(2) == 'すべて' else 'false', m.group(2)), nav.group(1))
            s = s.replace(nav.group(1), btns, 1)
            s = s.replace('</body>', '''<style>[data-f][aria-pressed="true"]{background:#17594F!important;color:#fff!important}</style>
<script>document.querySelectorAll('[data-f]').forEach(function(b){b.onclick=function(){var f=b.dataset.f;document.querySelectorAll('[data-f]').forEach(function(x){x.setAttribute('aria-pressed',String(x===b))});document.querySelectorAll('a[data-cat]').forEach(function(a){a.style.display=!f||a.dataset.cat===f?'':'none'})}})</script>
</body>''', 1)
    s = polish(f, s)
    s = fix_links(s)
    if f == 'Blog.html':
        for nf in NEW:
            s = re.sub(r'(<a data-cat="[^"]*" href="%s".*?<span style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center">)' % re.escape(nf), lambda m: m.group(1) + NEWB, s, count=1, flags=re.S)
    if NEW:
        s = re.sub(r'(<a href="Blog\.html"[^>]*>ブログ(?:（[^<]*）)?)(?=</a>)', lambda m: m.group(1) + NEWB_S, s)
    # 「上へ」ボタン（下にスクロールすると右下に出る。押すとページの一番上へ）
    s = s.replace('</body>', TOTOP + '</body>', 1)
    # すべてのページの一番下に「プライバシーポリシー」
    i = s.rfind('</footer>')
    if i > 0 and 'Privacy.html' not in s[s.rfind('<footer', 0, i):i]:
        j = s.rfind('</div>', 0, i)
        s = s[:j] + '<a href="Privacy.html" style="color: #FFFFFF">プライバシーポリシー</a>' + s[j:]
    s = s.replace('</head>', head_extra(f, s) + '</head>', 1)
    if f == 'Main.html': s = s.replace('</head>', clinic_ld() + '</head>', 1)
    s = s.replace('</head>', crumb_ld(f, s) + post_ld(f, s) + faq_ld(s) + job_ld(f) + '</head>', 1)
    LLM.append((f, page_name(s), (re.search(r'<meta name="description" content="([^"]*)"', s) or [None, ''])[1]))
    s = webp_imgs(s)
    open(os.path.join(OUT, out_name(f)), 'w', encoding='utf-8').write(s)
    written.append(out_name(f))

# AI（ChatGPT・Gemini など）向けの案内文 llms.txt：この院が何者で、どのページに何があるかを、事実だけで短く（11/11）
def llms_txt():
    grp = [('院について・料金・よくある質問', ['Main.html', 'Staff.html', 'Ryokin.html', 'Faq.html', 'System.html', 'Info.html', 'Recruit.html']),
           ('施術', ['Kotsupika.html', 'Hari.html', 'Biyoshin.html', 'Hivolt.html', 'Shock.html', 'Karada.html', 'Slim.html']),
           ('交通事故', ['Jiko.html']),
           ('症状・ケガ', ['Youtsu.html', 'Gikkuri.html', 'Kubikata.html', 'StraightNeck.html', 'Makigata.html', 'Nechigae.html', 'Zutsu.html', 'Zakotsu.html', 'Gojukata.html', 'Hiza.html', 'Nenza.html', 'Sports.html', 'Tentou.html', 'Yukikaki.html', 'Sango.html'])]
    by = {f: (n, d) for f, n, d in LLM}; used = set(); L = []
    L += ['# ' + SITE, '', '> 北海道江別市元町の整骨院・鍼灸院。骨格矯正「骨ぴか整体」と鍼灸、交通事故（自賠責保険）のケガの施術を行う。1978年開業。予約優先制（予約がなくても受付）。', '',
          '## 基本情報', '- 名称：はやしハリきゅう整骨院 江別本院（運営：株式会社ぴっかぴか）', '- 住所：〒067-0031 北海道江別市元町32-1（無料駐車場12台）', '- 電話：011-384-5454',
          '- 受付時間：9:00〜12:00／15:00〜19:00。日曜・祝日も受付', '- 休診：第1水曜日。ほかの水曜日は午後休診', '- 開業：1978年8月18日（会社設立 2014年）',
          '- 総括院長：林 恒博（柔道整復師・はり師・きゅう師）', '- 予約：LINE・WEB・電話。予約優先制', '- 交通事故：自賠責保険の施術に対応（江別本院で年間300件）', '- ホームページ：' + BASE, '']
    for title, fs in grp:
        rows = ['- [%s](%s)%s' % (by[f][0], BASE + ('' if f == 'Main.html' else f), '：' + by[f][1] if by[f][1] else '') for f in fs if f in by]
        used.update(fs)
        if rows: L += ['## ' + title] + rows + ['']
    rest = [f for f, n, d in LLM if f not in used and not f.startswith('BlogPost') and f not in ('Privacy.html', 'Omagari.html', 'Tentore.html', 'Taisou.html', 'Blog.html')]
    if rest: L += ['## そのほか'] + ['- [%s](%s)%s' % (by[f][0], BASE + f, '：' + by[f][1] if by[f][1] else '') for f in rest] + ['']
    posts = sorted([f for f in by if f.startswith('BlogPost')], key=lambda f: post_date.get(f, ''), reverse=True)[:20]
    if posts: L += ['## ブログ（新しい順）'] + ['- [%s](%s)（%s）' % (by[f][0], BASE + f, post_date.get(f, '')) for f in posts] + ['']
    return '\n'.join(L)
if not PREVIEW: open(os.path.join(OUT, 'llms.txt'), 'w', encoding='utf-8').write(llms_txt())
else: open(os.path.join(OUT, 'llms_preview.txt'), 'w', encoding='utf-8').write(llms_txt())   # 仮公開中は名前を変えて置く（中身の確かめ用）

# 2) sitemap・robots・404
def lastmod(n):
    f = 'Main.html' if n == 'index.html' else n
    return post_date.get(f, TODAY)
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for n in sorted(written):
    if n == '404.html': continue
    sm.append('<url><loc>%s</loc><lastmod>%s</lastmod></url>' % (BASE + ('' if n == 'index.html' else n), lastmod(n)))
sm.append('</urlset>')
open(os.path.join(OUT, 'sitemap.xml'), 'w').write('\n'.join(sm) + '\n')
open(os.path.join(OUT, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n' if PREVIEW else 'User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n' % BASE)
nf = rd('Main.html'); 
open(os.path.join(OUT, '404.html'), 'w', encoding='utf-8').write('<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ページが見つかりません｜%s</title><meta name="robots" content="noindex"><link rel="icon" href="%simg/logo.png"></head><body style="margin:0;font-family:\'Hiragino Sans\',sans-serif;background:#F2F6F4;color:#1B2A27"><div style="max-width:640px;margin:0 auto;padding:80px 24px;text-align:center"><img src="%simg/logo.png" alt="" style="width:72px;height:72px"><h1 style="font-size:24px">ページが見つかりません</h1><p>お探しのページは移動したか、なくなった可能性があります。</p><p><a href="%s" style="color:#17594F;font-weight:700">トップページへ</a></p></div></body></html>' % (SITE, BPATH, BPATH, BPATH))
# 3) 今のHP（GMO）の古いアドレス → 新しいページへ自動で案内（Googleの評価を引き継ぐ）
OLD = {
    'hari': '', 'hari/honin': '', 'hari/greeting': '#first', 'hari/access': '#access',
    'hari/about': 'Ryokin.html', 'hari/kotsupika': 'Kotsupika.html', 'hari/treatment': 'Jiko.html',
    'hari/faq': 'Faq.html', 'hari/staff': 'Staff.html', 'hari/news': 'Blog.html',
    'hari/recruit_info': 'Recruit.html', 'hari/recruit': 'Recruit.html', 'hari/serio-omagari': 'Omagari.html',
    'hari/form': 'Privacy.html', 'cookie': 'Privacy.html#pp7-h', '_old_hari': '', 'info': 'Info.html', 'slim': 'Slim.html',
    'taisou': 'Taisou.html', 'taisou/tentore': 'Tentore.html', 'system': 'System.html',
    'news': 'Blog.html', 'news/detail': 'Blog.html', 'list': 'Blog.html',
    # 10/28 旧サイトを全部たどって見つかった残りのページ
    'slim/biyoushin': 'Ryokin.html', 'slim/ems': 'Slim.html', 'slim/self': 'Slim.html', 'slim/news': 'Blog.html', 'slim/news/detail': 'Blog.html',
    'hari/contact': '#first', 'hari/treatment/column': 'Jiko.html', 'hari/treatment/column/detail': 'Jiko.html',
    'hari/staff/detail': 'Staff.html', 'hari/recruit/detail': 'Recruit.html',
}
SYM = {'73476': 'Zutsu.html', '55788': 'Kubikata.html', '63405': 'Youtsu.html', '63457': 'Kubikata.html',
       '64020': 'Hiza.html', '65662': '#symptom', '69433': 'Nenza.html', '76756': 'Karada.html',
       '76759': 'Gojukata.html', '76760': '#symptom', '82547': '#symptom', '84278': 'Karada.html',
       '87644': 'Kotsupika.html'}


def redirect(path, target, script=''):
    to = '../' * (path.count('/') + 1) + target
    os.makedirs(os.path.join(OUT, path), exist_ok=True)
    page = ('<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>%s</title>'
            '<meta name="robots" content="noindex"><link rel="canonical" href="%s">'
            '<meta http-equiv="refresh" content="0; url=%s">%s</head>'
            '<body><p>ページが移動しました。<a href="%s">新しいページへ</a></p></body></html>')
    open(os.path.join(OUT, path, 'index.html'), 'w', encoding='utf-8').write(page % (SITE, BASE + target, to, script, to))


for _p, _t in OLD.items():
    redirect(_p, _t)
_m = ','.join('"%s":"%s"' % kv for kv in SYM.items())
redirect('hari/symptoms', '#symptom',
         '<script>var m={%s},n=new URLSearchParams(location.search).get("no");if(m[n])location.replace("../../"+m[n])</script>' % _m)

print('build', TODAY, 'pages', len(written), 'hidden posts', len(hidden), sorted(hidden, key=lambda x: post_date[x])[:3], '...')
