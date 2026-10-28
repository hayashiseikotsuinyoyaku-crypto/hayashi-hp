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
    'Youtsu.html': ['BlogPost.html', 'BlogPost3.html', 'BlogPost8.html', 'BlogPost7.html', 'BlogPost22.html'],
    'Gikkuri.html': ['BlogPost3.html', 'BlogPost.html', 'BlogPost8.html', 'BlogPost22.html'],
    'Yukikaki.html': ['BlogPost.html', 'BlogPost3.html', 'BlogPost8.html'],
    'Kubikata.html': ['BlogPost2.html', 'BlogPost5.html'],
    'Zutsu.html': ['BlogPost5.html', 'BlogPost2.html'],
    'Nechigae.html': ['BlogPost5.html', 'BlogPost2.html'],
    'Gojukata.html': ['BlogPost20.html', 'BlogPost2.html'],
    'Hiza.html': ['BlogPost17.html', 'BlogPost13.html'],
    'Tentou.html': ['BlogPost4.html'],
    'Nenza.html': ['BlogPost23.html', 'BlogPost4.html'],
    'Sports.html': ['BlogPost23.html', 'BlogPost13.html'],
    'Zakotsu.html': ['BlogPost7.html', 'BlogPost3.html'],
    'Karada.html': ['BlogPost7.html', 'BlogPost9.html'],
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
    ogimg = BASE + 'img/' + (img.group(1) if img and 'logo' not in img.group(1) else 'logo.png')
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
         'parentOrganization': {'@type': 'Organization', 'name': '株式会社ぴっかぴか'}}
    return '<script type="application/ld+json">' + _json.dumps(d, ensure_ascii=False) + '</script>\n'
written = []
for f in pages:
    if f == 'Sp.html' or f in hidden: continue
    s = rd(f)
    if f in RELATED:
        s = s.replace('<footer', blog_section('関連するブログ', visible_latest(RELATED[f]), bg='#F7FAF9') + '<footer', 1)
    if f == 'Main.html':
        sp = rd('Sp.html'); spb = body_of(sp)
        s = s.replace('<section id="access"', blog_section('新着ブログ', LATEST) + '<section id="access"', 1)
        spb = spb.replace('<section style="background: #FFFFFF; padding: 28px 16px 120px', blog_section('新着ブログ', LATEST, sp=True, bg='#F7FAF9') + '<section style="background: #FFFFFF; padding: 28px 16px 120px', 1)
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
