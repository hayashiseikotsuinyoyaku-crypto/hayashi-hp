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
import urllib.parse
BPATH = urllib.parse.urlparse(BASE).path or '/'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
shutil.copytree(os.path.join(SRC, 'img'), os.path.join(OUT, 'img'))
rd = lambda f: open(os.path.join(SRC, f), encoding='utf-8').read()
pages = sorted(f for f in os.listdir(SRC) if f.endswith('.html'))

# 1) ブログの日付
post_date = {}
for f in pages:
    if re.match(r'BlogPost\d*\.html$', f):
        m = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})"', rd(f))
        post_date[f] = m.group(1) if m else '0000-00-00'
hidden = {f for f, d in post_date.items() if d > TODAY}

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
    ogimg = BASE + 'img/' + (img.group(1) if img and 'logo' not in img.group(1) else 'logo.png')
    url = BASE + ('' if f == 'Main.html' else f)
    return ('<link rel="canonical" href="%s">\n<link rel="icon" href="./img/logo.png">\n<link rel="apple-touch-icon" href="./img/logo.png">\n'
            '<meta property="og:type" content="%s">\n<meta property="og:site_name" content="%s">\n<meta property="og:title" content="%s">\n'
            '<meta property="og:description" content="%s">\n<meta property="og:url" content="%s">\n<meta property="og:image" content="%s">\n'
            '<meta name="twitter:card" content="summary_large_image">\n' + ('<meta name="robots" content="noindex">\n' if PREVIEW else '')) % (url, 'website' if f == 'Main.html' else 'article', SITE, t, d, url, ogimg)

def body_of(s): return s[s.find('<body>') + 6: s.rfind('</body>')]
def head_of(s): return s[s.find('<head>') + 6: s.find('</head>')]

written = []
for f in pages:
    if f == 'Sp.html' or f in hidden: continue
    s = rd(f)
    if f == 'Main.html':
        sp = rd('Sp.html'); spb = body_of(sp)
        # スマホ版のidは重ならないように sp- を付ける（ページ内リンクも）
        ids = set(re.findall(r'id="([^"]+)"', spb)) - {'sp-menu'}
        for i in ids:
            spb = spb.replace('id="%s"' % i, 'id="sp-%s"' % i).replace('aria-labelledby="%s"' % i, 'aria-labelledby="sp-%s"' % i).replace('href="#%s"' % i, 'href="#sp-%s"' % i)
        k = spb.find('<nav aria-label="グループのページ"')
        if k > 0:
            e = spb.find('</nav>', k)
            spb = spb[:e] + '<a href="Privacy.html" style="color: #FFFFFF">プライバシーポリシー</a>' + spb[e:]
        sw = '<style>.v-sp{display:none}@media (max-width:767px){.v-pc{display:none}.v-sp{display:block}}</style>'
        sph = re.sub(r'<(meta|title)[^>]*>(?:.*?</title>)?', '', head_of(sp), flags=re.S)
        s = s.replace('</head>', sph + sw + '\n</head>', 1)
        s = s.replace('<body>', '<body>\n<div class="v-pc">', 1)
        s = s[:s.rfind('</body>')] + '</div>\n<div class="v-sp">' + spb + '</div>\n<script>(function(){var h=location.hash.slice(1),e;if(h&&matchMedia("(max-width:767px)").matches&&(e=document.getElementById("sp-"+h)))setTimeout(function(){e.scrollIntoView()},50)})()</script>\n</body>' + s[s.rfind('</body>') + 7:]
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
    s = fix_links(s)
    # すべてのページの一番下に「プライバシーポリシー」
    i = s.rfind('</footer>')
    if i > 0 and 'Privacy.html' not in s[s.rfind('<footer', 0, i):i]:
        j = s.rfind('</div>', 0, i)
        s = s[:j] + '<a href="Privacy.html" style="color: #FFFFFF">プライバシーポリシー</a>' + s[j:]
    s = s.replace('</head>', head_extra(f, s) + '</head>', 1)
    open(os.path.join(OUT, out_name(f)), 'w', encoding='utf-8').write(s)
    written.append(out_name(f))

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
