"""Localized HTML email and an offline, three-language browser preview."""
import datetime as dt
import html
import json
import hashlib

TEXT = {
    'en': {
        'digest':'News digest', 'morning':'Morning edition', 'noon':'Midday edition', 'evening':'Evening edition',
        'today':'New today', 'overnight':'Last night', 'catchup':'Earlier stories · catch-up',
        'unknown':'Section not verified', 'read':'Read on Bloomberg ↗',
        'empty':'No eligible, unsent stories were collected for this edition. Check the source status below.',
        'preview':'PREVIEW · NOT SENT', 'personal':'PERSONAL NEWS DIGEST', 'daily':'THE DAILY EDIT',
        'tagline':'INFORMATION, IN ORDER.', 'new':'new stories', 'unsent':'unsent stories',
        'fields':'Original headline / Source section / Article',
        'source':'Source status · Items in latest fetch',
        'provenance':'Sections use official RSS channel names, not all article-page tags. General-feed stories are labeled Bloomberg.com; sections are not guessed. Public RSS does not provide complete news coverage. An empty feed does not mean there is no news.',
        'schedule':'Beijing time {times} · Morning editions include last night’s stories. An independent personal digest, not an official Bloomberg email.',
        'footer':'READ LESS NOISE. KNOW MORE.', 'ok':'Available', 'empty_status':'Empty feed',
        'failed':'Unavailable', 'partial':'Some entries could not be read',
        'excerpt':' · Excerpt; full list attached',
        'plain':'View this digest in an HTML-capable email client. The full list may be included as an HTML attachment.',
        'test_subject':'Setup test (not a news digest)',
        'test_body':'This is your sender and recipient configuration test. It does not mean scheduled delivery is enabled.',
        'language':'Language', 'hint':'Interface language only. Original headlines and Bloomberg section names are preserved.',
        'sample':'Design sample · Fictional headlines', 'demo':'DEMO / Fictional headlines', 'demo_status':'Design preview',
    },
    'zh-Hans': {
        'digest':'新闻简报', 'morning':'早间简报', 'noon':'午间简报', 'evening':'晚间简报',
        'today':'今日新增', 'overnight':'昨晚新增', 'catchup':'较早未推送 · 补发',
        'unknown':'板块待核实', 'read':'阅读 Bloomberg 原文 ↗',
        'empty':'本期没有收集到符合条件的未发送条目。请同时查看下方来源状态。',
        'preview':'预览 · 尚未发送', 'personal':'个人新闻简报', 'daily':'每日精选',
        'tagline':'资讯，井然有序。', 'new':'条新增', 'unsent':'条未发送新闻',
        'fields':'原始标题 / 来源板块 / 原文', 'source':'来源状态 · 本次抓取条数',
        'provenance':'板块采用官方 RSS 频道名称，不代表文章页面的全部标签。综合源标为 Bloomberg.com，不猜测板块。公开 RSS 无法保证全量覆盖；空列表不代表没有新闻。',
        'schedule':'北京时间 {times} · 早报包含昨晚新增。独立个人简报，非 Bloomberg 官方邮件。',
        'footer':'少一点杂音，多一分洞察。', 'ok':'可用', 'empty_status':'空列表',
        'failed':'暂不可用', 'partial':'部分条目未能读取', 'excerpt':' · 节选，完整清单见附件',
        'plain':'请使用支持 HTML 的邮箱查看简报。完整清单可能包含在 HTML 附件中。',
        'test_subject':'配置测试（不是新闻简报）', 'test_body':'这是发件与收件配置测试邮件，不代表定时发送已经启用。',
        'language':'界面语言', 'hint':'仅切换界面语言，新闻标题和 Bloomberg 板块名称保留原文。',
        'sample':'设计样例 · 虚构标题', 'demo':'演示 / 虚构标题', 'demo_status':'设计预览',
    },
    'zh-Hant': {
        'digest':'新聞簡報', 'morning':'早間簡報', 'noon':'午間簡報', 'evening':'晚間簡報',
        'today':'今日新增', 'overnight':'昨晚新增', 'catchup':'較早未推送 · 補發',
        'unknown':'板塊待核實', 'read':'閱讀 Bloomberg 原文 ↗',
        'empty':'本期沒有收集到符合條件的未傳送項目。請同時查看下方來源狀態。',
        'preview':'預覽 · 尚未傳送', 'personal':'個人新聞簡報', 'daily':'每日精選',
        'tagline':'資訊，井然有序。', 'new':'則新增', 'unsent':'則未傳送新聞',
        'fields':'原始標題 / 來源板塊 / 原文', 'source':'來源狀態 · 本次擷取數量',
        'provenance':'板塊採用官方 RSS 頻道名稱，不代表文章頁面的全部標籤。綜合來源標為 Bloomberg.com，不猜測板塊。公開 RSS 無法保證完整涵蓋；空清單不代表沒有新聞。',
        'schedule':'北京時間 {times} · 早報包含昨晚新增。獨立個人簡報，非 Bloomberg 官方郵件。',
        'footer':'少一點雜音，多一分洞察。', 'ok':'可用', 'empty_status':'空清單',
        'failed':'暫不可用', 'partial':'部分項目未能讀取', 'excerpt':' · 節選，完整清單見附件',
        'plain':'請使用支援 HTML 的郵件程式查看簡報。完整清單可能包含在 HTML 附件中。',
        'test_subject':'設定測試（不是新聞簡報）', 'test_body':'這是寄件與收件設定測試郵件，不代表定時傳送已經啟用。',
        'language':'介面語言', 'hint':'僅切換介面語言，新聞標題和 Bloomberg 板塊名稱保留原文。',
        'sample':'設計樣例 · 虛構標題', 'demo':'示範 / 虛構標題', 'demo_status':'設計預覽',
    },
}

def words(language='en'):
    return TEXT.get(language, TEXT['en'])

for code, values in {
    'en': {'section':'Section','all':'All sections','browse':'Browse by section','attached':'Open the attached HTML file in a browser to filter sections and switch languages.'},
    'zh-Hans': {'section':'新闻板块','all':'全部板块','browse':'按板块浏览','attached':'在浏览器中打开所附 HTML 文件，可筛选板块并切换语言。'},
    'zh-Hant': {'section':'新聞板塊','all':'全部板塊','browse':'按板塊瀏覽','attached':'在瀏覽器中開啟所附 HTML 檔案，可篩選板塊並切換語言。'},
}.items(): TEXT[code].update(values)

def esc(value): return html.escape(str(value), quote=True)

def category(article, clock):
    published=dt.datetime.fromisoformat(article['published']).astimezone(clock.tzinfo)
    if published.date()==clock.date():return 'today'
    if published.date()==clock.date()-dt.timedelta(days=1) and published.hour>=17:return 'overnight'
    return 'catchup'

def render(articles,sources,clock,label=None,preview=False,language='en',times=None,sample=False,group_section=None):
    language=language if language in TEXT else 'en'
    t=words(language)
    label=label or t['digest']
    if sample:label=t['sample']
    groups={}
    for a in articles:
        sections=json.loads(a['sections'])
        specific=[s for s in sections if s not in ('Bloomberg.com','Bloomberg')]
        primary=group_section or (specific or sections or [t['unknown']])[0]
        groups.setdefault((category(a,clock),primary),[]).append(a)
    body=''
    for key in ('overnight','today','catchup'):
        for (kind,section),items in sorted(groups.items()):
            if kind!=key:continue
            anchor='section-'+hashlib.sha256((key+section).encode()).hexdigest()[:12]
            body+=f'<tr><td id="{anchor}" class="pad" style="padding:28px 32px 8px"><div style="font:11px Arial;letter-spacing:2px;color:#63675b">{esc(t[key])}</div><h2 style="font:bold 24px Georgia;margin:8px 0 0">{esc(section)} <span style="font:12px Arial;color:#72766c">/ {len(items):02d}</span></h2></td></tr>'
            for a in items:
                sections=' / '.join(json.loads(a['sections']))
                time=dt.datetime.fromisoformat(a['published']).astimezone(clock.tzinfo).strftime('%m/%d %H:%M')
                body+=f'''<tr><td class="pad" style="padding:18px 32px;border-bottom:1px solid #dedfd5">
                <a href="{esc(a['url'])}" style="font:23px/1.3 Georgia,'Times New Roman',serif;color:#171b15;text-decoration:none;display:block">{esc(a['title'])}</a>
                <p style="font:11px/1.7 Arial;color:#676d60;margin:12px 0 8px">{esc(time)} UTC+8 &nbsp; · &nbsp; {esc(sections)}</p>
                <a href="{esc(a['url'])}" style="font:12px Arial;color:#284427;text-decoration:underline">{esc(t['read'])}</a></td></tr>'''
    if not articles:body=f'<tr><td class="pad" style="padding:32px">{esc(t["empty"])}</td></tr>'
    status=[]
    for s in sources:
        raw=s['status']
        state=t['ok'] if raw=='ok' else t['empty_status'] if raw=='empty' else t['partial'] if raw.startswith('partial:') else t['failed']
        name=s['name']
        if sample:name,state=t['demo'],t['demo_status']
        status.append(f'{esc(name)} — {esc(state)} ({s["count"]})')
    note=t['preview'] if preview else t['personal']
    schedule=t['schedule'].format(times=' / '.join(times or ['09:00','12:00','17:00']))
    navigation=[]
    for (kind,section), items in groups.items():
        anchor='section-'+hashlib.sha256((kind+section).encode()).hexdigest()[:12]
        navigation.append(f'<a href="#{anchor}" style="display:inline-block;margin:6px 12px 6px 0;font:12px Arial;color:#284427">{esc(section)} · {esc(t[kind])} ({len(items)})</a>')
    nav='<tr><td class="pad" style="padding:18px 32px;border-bottom:1px solid #dedfd5"><b style="font:13px Arial">'+esc(t['browse'])+'</b><br>'+''.join(navigation)+'</td></tr>' if navigation else ''
    attachment_note='' if preview else '<br>'+esc(t['attached'])
    return f'''<!doctype html><html lang="{language}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>The Brief — {esc(label)}</title>
    <style>@media(max-width:620px){{.pad{{padding-left:20px!important;padding-right:20px!important}}.mast{{font-size:52px!important}}}}</style></head>
    <body style="margin:0;background:#e8e9e1;color:#171b15"><div style="display:none;max-height:0;overflow:hidden">{esc(label)} · {len(articles)} {esc(t['new'])} · Bloomberg RSS</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:24px 8px">
    <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="width:100%;max-width:600px;background:#f8f8ef">
    <tr><td class="pad" style="padding:22px 32px;background:#c4f25a;font:11px Arial;letter-spacing:2px">{esc(t['daily'])} &nbsp; / &nbsp; {esc(note)}</td></tr>
    <tr><td class="pad" style="padding:30px 32px;background:#171b15;color:#f8f8ef"><div style="font:11px Arial;letter-spacing:3px;color:#c4f25a">{esc(t['tagline'])}</div>
    <h1 class="mast" style="font:normal 68px/1 Georgia;margin:18px 0">The Brief<span style="color:#c4f25a">.</span></h1>
    <div style="font:13px/1.8 Arial;color:#c4c8bc">{clock:%Y.%m.%d} &nbsp; / &nbsp; {clock:%H:%M} UTC+8 &nbsp; / &nbsp; {esc(label)}</div></td></tr>
    <tr><td class="pad" style="padding:22px 32px;border-bottom:2px solid #171b15;font:13px Arial"><strong style="font-size:26px">{len(articles):02d}</strong> &nbsp; {esc(t['unsent'])} &nbsp; · &nbsp; {esc(t['fields'])}</td></tr>
    {nav}{body}<tr><td class="pad" style="padding:28px 32px;background:#eef0e5;font:11px/1.9 Arial;color:#626958"><b>{esc(t['source'])}</b><br>{'<br>'.join(status)}<br><br>
    {esc(t['provenance'])}<br>{esc(schedule)}{attachment_note}</td></tr>
    <tr><td class="pad" style="padding:20px 32px;font:11px Arial;letter-spacing:2px">{esc(t['footer'])}</td></tr></table></td></tr></table></body></html>'''

def browser_preview(articles,sources,clock,times=None,sample=False,preview=True):
    pages={}
    sections=sorted({s for a in articles for s in json.loads(a['sections'])})
    counts={s:sum(s in json.loads(a['sections']) for a in articles) for s in sections}
    for lang in TEXT:
        variants={}
        for section in ['',*sections]:
            chosen=[a for a in articles if not section or section in json.loads(a['sections'])]
            document=render(chosen,sources,clock,preview=True,language=lang,times=times,sample=sample,group_section=section)
            if not preview:document=document.replace(esc(words(lang)['preview']),esc(words(lang)['personal']))
            variants[section]=document.split('<body',1)[1].split('>',1)[1].rsplit('</body>',1)[0]
        pages[lang]={'bodies':variants,
                     'title':'The Brief — '+words(lang)['sample' if sample else 'digest'],
                     'language':words(lang)['language'],'hint':words(lang)['hint'],
                     'section':words(lang)['section'],'all':words(lang)['all']}
    # Escape script delimiters; all source text within pages has already been HTML-escaped.
    payload=json.dumps(pages,ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    header='''<header style="max-width:600px;margin:24px auto 0;padding:0 16px;font:13px/1.6 Arial;color:#394033">
    <label id="language-label" for="language-select">Language</label>
    <select id="language-select" aria-describedby="language-hint" style="margin-left:12px;padding:10px 14px;border:1px solid #747b6c;background:#f8f8ef;color:#171b15;border-radius:6px;font:14px Arial">
    <option value="en">English</option><option value="zh-Hans">简体中文</option><option value="zh-Hant">繁體中文</option></select>
    <p id="language-hint" style="font-size:12px">Interface language only. Original headlines and Bloomberg section names are preserved.</p>
    <label id="section-label" for="section-select">Section</label>
    <select id="section-select" style="max-width:100%;margin:8px 0 0 12px;padding:10px 14px;border:1px solid #747b6c;background:#f8f8ef;color:#171b15;border-radius:6px;font:14px Arial">
    <option value="">All sections</option>'''+''.join(f'<option value="{esc(s)}">{esc(s)} ({counts[s]})</option>' for s in sections)+'''</select></header>'''
    script='''<script id="locale-data" type="application/json">'''+payload+'''</script><script>
    (() => {
      const pages = JSON.parse(document.getElementById('locale-data').textContent);
      const select = document.getElementById('language-select');
      const section = document.getElementById('section-select');
      function apply(language) {
        const page = pages[language] || pages.en;
        document.getElementById('digest-content').innerHTML = page.bodies[section.value] || page.bodies[''];
        document.documentElement.lang = pages[language] ? language : 'en';
        document.title = page.title;
        document.getElementById('language-label').textContent = page.language;
        document.getElementById('language-hint').textContent = page.hint;
        document.getElementById('section-label').textContent = page.section;
        section.options[0].textContent = page.all;
      }
      select.value = 'en';
      select.addEventListener('change', () => apply(select.value));
      section.addEventListener('change', () => apply(select.value));
      apply('en');
    })();</script>'''
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'''+esc(pages['en']['title'])+'''</title><style>@media(max-width:620px){.pad{padding-left:20px!important;padding-right:20px!important}.mast{font-size:52px!important}}</style></head><body style="margin:0;background:#e8e9e1;color:#171b15">'''+header+'<main id="digest-content">'+pages['en']['bodies']['']+'</main>'+script+'</body></html>'
