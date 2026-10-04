"""Windows RSS digest. Python 3.10+, standard library only."""
import argparse
import sys
import os
import concurrent.futures
import contextlib
import datetime as dt
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import parsedate_to_datetime, format_datetime, make_msgid
import html
import json
import logging
from pathlib import Path
import smtplib
import socket
import sqlite3
import ssl
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from ui import render, browser_preview, words

BASE = Path(__file__).resolve().parent
TZ = dt.timezone(dt.timedelta(hours=8), 'Asia/Shanghai')
def now(): return dt.datetime.now(TZ)
def esc(s): return html.escape(str(s), quote=True)
def stamp(d): return d.astimezone(TZ).isoformat()

def connect(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.executescript('''
    CREATE TABLE IF NOT EXISTS articles(url TEXT PRIMARY KEY,title TEXT,published TEXT,first_seen TEXT,sections TEXT,sent TEXT);
    CREATE TABLE IF NOT EXISTS sources(url TEXT PRIMARY KEY,name TEXT,status TEXT,count INTEGER,checked TEXT);
    CREATE TABLE IF NOT EXISTS batches(id TEXT PRIMARY KEY,status TEXT,urls TEXT,message_id TEXT,created TEXT);
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
    ''')
    return c

def canonical(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ('http', 'https') or p.hostname not in ('bloomberg.com', 'www.bloomberg.com'):
        raise ValueError('Not a Bloomberg article link')
    return urllib.parse.urlunsplit(('https','www.bloomberg.com',p.path.rstrip('/'),'',''))

def fetch(source):
    req = urllib.request.Request(source['url'], headers={'User-Agent':'PersonalNewsDigest/1.0 (RSS reader)'})
    proxy=source.get('rss_proxy')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':proxy,'https':proxy})) if proxy else urllib.request.build_opener()
    with opener.open(req, timeout=25) as r:
        data = r.read(5_000_001)
    if len(data) > 5_000_000: raise ValueError('Feed too large')
    channel = ET.fromstring(data).find('channel')
    if channel is None: raise ValueError('Response is not RSS')
    name = channel.findtext('title', '').strip()
    if not name: raise ValueError('RSS has no channel title')
    entries, rejected = [], 0
    for item in channel.findall('item'):
        try:
            title = item.findtext('title','').strip()
            published = parsedate_to_datetime(item.findtext('pubDate',''))
            if not title or published.tzinfo is None: raise ValueError('Missing title/date')
            url = canonical(item.findtext('link',''))
            entries.append((url,title,stamp(published)))
        except (ValueError, TypeError, AttributeError): rejected += 1
    return name, entries, rejected

def collect(c, cfg, clock):
    def one(s):
        try: return s, fetch(dict(s,rss_proxy=cfg.get('rss_proxy'))), None
        except Exception as e: return s, None, type(e).__name__ + ': ' + str(e)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for source, result, error in ex.map(one, cfg['sources']):
            name, entries, rejected = result if result else (source['name'], [], 0)
            status = error or ('partial: %d invalid entries' % rejected if rejected else ('ok' if entries else 'empty'))
            c.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?)', (source['url'],name,status,len(entries),stamp(clock)))
            for url,title,published in entries:
                old = c.execute('SELECT sections FROM articles WHERE url=?',(url,)).fetchone()
                sections = set(json.loads(old[0])) if old else set()
                # Source channel labels only. Never infer sections from headline keywords.
                sections.add(name)
                c.execute('''INSERT INTO articles VALUES(?,?,?,?,?,NULL)
                    ON CONFLICT(url) DO UPDATE SET title=excluded.title,sections=excluded.sections''',
                    (url,title,published,stamp(clock),json.dumps(sorted(sections))))
    c.commit()

def select_articles(c, clock, floor):
    return [dict(x) for x in c.execute('SELECT * FROM articles WHERE sent IS NULL AND published>=? AND published<=? ORDER BY published DESC',(stamp(floor),stamp(clock)))]

def filter_sections(articles, sections):
    if not sections:return articles
    wanted=set(sections)
    return [a for a in articles if wanted.intersection(json.loads(a['sections']))]

def period(article, clock):
    d = dt.datetime.fromisoformat(article['published']).astimezone(TZ)
    if d.date() == clock.date(): return '今日新增'
    if d.date() == clock.date()-dt.timedelta(days=1) and d.hour >= 17: return '昨晚新增'
    return '较早未推送 · 补发'


def credential():
    path = BASE/'private'/'smtp.xml'
    command = "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); $c=Import-Clixml -LiteralPath '" + str(path).replace("'","''") + "'; @{user=$c.UserName;password=$c.GetNetworkCredential().Password}|ConvertTo-Json -Compress"
    powershell = str(Path(os.environ.get('SystemRoot', r'C:\Windows'))/'System32'/'WindowsPowerShell'/'v1.0'/'powershell.exe')
    result = subprocess.run([powershell,'-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,encoding='utf-8',check=True,creationflags=0x08000000)
    return json.loads(result.stdout)


class ProxySMTPSSL(smtplib.SMTP_SSL):
    """SMTP over an HTTP CONNECT proxy; TLS remains end-to-end verified."""
    def __init__(self, *args, proxy, **kwargs):
        self.proxy = proxy
        super().__init__(*args, **kwargs)

    def _get_socket(self, host, port, timeout):
        sock = socket.create_connection((self.proxy['host'], int(self.proxy['port'])), timeout)
        try:
            target = f'{host}:{port}'
            if any(c in target for c in '\r\n'): raise ValueError('Invalid SMTP host')
            sock.sendall(f'CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n'.encode('ascii'))
            header = b''
            while not header.endswith(b'\r\n\r\n'):
                piece = sock.recv(1)
                if not piece: raise ConnectionError('Proxy closed the connection')
                header += piece
                if len(header) > 16384: raise ConnectionError('Proxy response too large')
            status = header.split(b'\r\n', 1)[0].split()
            if len(status) < 2 or status[1] != b'200':
                raise ConnectionError('Proxy refused SMTP tunnel')
            return self.context.wrap_socket(sock, server_hostname=host)
        except Exception:
            sock.close()
            raise

def smtp_connection(cfg):
    smtp_class = ProxySMTPSSL if cfg.get('smtp_proxy') else smtplib.SMTP_SSL
    options = {'proxy':cfg['smtp_proxy']} if cfg.get('smtp_proxy') else {}
    return smtp_class(cfg['smtp_host'],cfg['smtp_port'],context=ssl.create_default_context(),timeout=20,**options)

def prepare_message(cfg, subject, content, message_id, attachment=None):
    msg = EmailMessage()
    msg['From'],msg['To'],msg['Subject'] = cfg['sender'],cfg['recipient'],subject
    msg['Message-ID'],msg['Date'] = message_id,format_datetime(now())
    msg.set_content(words(cfg.get('language','en'))['plain'])
    msg.add_alternative(content,subtype='html')
    if attachment:
        msg.add_attachment(attachment.encode('utf-8'),maintype='text',subtype='html',filename='full-digest.html')
    # Catch encoding defects locally, before authentication or transmission.
    msg.as_bytes(policy=SMTP)
    return msg

class BeforeSendError(RuntimeError): pass

def mail(cfg, subject, content, message_id, attachment=None):
    try:
        cred = credential()
        if cred['user'].strip().lower()!=cfg['sender'].strip().lower():
            raise ValueError('Saved credential account differs from sender. Run start-setup.cmd.')
        msg=prepare_message(cfg,subject,content,message_id,attachment)
        s=smtp_connection(cfg)
    except Exception as e: raise BeforeSendError(friendly_error(e)) from e
    try:
        try:
            s.login(cred['user'],cred['password'])
        except Exception as e: raise BeforeSendError(friendly_error(e)) from e
        # Failures from this point can be ambiguous and must not auto-retry.
        s.send_message(msg)
    finally:
        # A failed QUIT after accepted DATA must not mark a successful send uncertain.
        s.close()

def friendly_error(error):
    if isinstance(error,BeforeSendError): return str(error)
    if isinstance(error,smtplib.SMTPAuthenticationError):
        return 'Gmail/SMTP rejected login. Check the sender account and its app password. Do not use your normal account password.'
    if isinstance(error,(TimeoutError,ConnectionError,OSError)) and not isinstance(error,FileNotFoundError):
        return 'Network connection failed. Keep your configured proxy running, verify its port, then run check.cmd.'
    if isinstance(error,subprocess.CalledProcessError):
        return 'Cannot read saved credentials. Use the same Windows account and PC, or run start-setup.cmd again.'
    if isinstance(error,UnicodeError): return 'Email encoding failed. Check sender/recipient addresses and use the latest version.'
    if isinstance(error,FileNotFoundError):return 'Configuration or credentials missing. Run start-setup.cmd first.'
    return str(error) if isinstance(error,(ValueError,RuntimeError)) else type(error).__name__+': operation failed; see private/run.log.'

def due_slot(clock, times):
    candidates=[]
    for days in (1,0):
        day=clock.date()-dt.timedelta(days=days)
        for t in times:
            h,m=map(int,t.split(':'))
            x=dt.datetime.combine(day,dt.time(h,m),TZ)
            if x<=clock: candidates.append(x)
    return max(candidates)

def deliver(c,cfg,clock,floor):
    slot=due_slot(clock,cfg['times'])
    if slot < dt.datetime.fromisoformat(cfg['activated_at']): return
    batch_id=stamp(slot)
    if c.execute('SELECT 1 FROM batches WHERE id=?',(batch_id,)).fetchone(): return
    # SMTP acknowledgement can be ambiguous: stop rather than automatically duplicate mail.
    if c.execute("SELECT 1 FROM batches WHERE status='sending'").fetchone():
        raise RuntimeError('Uncertain prior send. Inspect Sent mail and use resolve; automatic send paused.')
    sources=[dict(x) for x in c.execute('SELECT * FROM sources ORDER BY name')]
    relevant=[s for s in sources if not cfg.get('sections') or s['name'] in cfg['sections']]
    if not any(s['status']=='ok' for s in relevant): raise RuntimeError('No selected nonempty healthy feed; skip sending and retry next tick')
    articles=filter_sections(select_articles(c,clock,floor),cfg.get('sections',[]))
    language=cfg.get('language','en')
    t=words(language)
    label=t[{9:'morning',12:'noon',17:'evening'}.get(slot.hour,'digest')]
    full=render(articles,sources,clock,label,language=language,times=cfg['times'])
    short=full
    # Keep the body small, preserve every item in an HTML attachment.
    limit=min(len(articles),40)
    if len(full.encode('utf-8'))>70000 or len(articles)>40:
        short=render(articles[:limit],sources,clock,label+t['excerpt'],language=language,times=cfg['times'])
        while len(short.encode('utf-8'))>70000 and limit>1:
            limit//=2
            short=render(articles[:limit],sources,clock,label+t['excerpt'],language=language,times=cfg['times'])
    out=BASE/'private'/'archive';out.mkdir(exist_ok=True)
    (out/(slot.strftime('%Y%m%d-%H%M')+'.html')).write_text(full,encoding='utf-8')
    mid=make_msgid(domain='news-digest.local')
    interactive=browser_preview(articles,sources,clock,times=cfg['times'],preview=False)
    c.execute('INSERT INTO batches VALUES(?,?,?,?,?)',(batch_id,'sending',json.dumps([a['url'] for a in articles]),mid,stamp(clock)));c.commit()
    try:
        mail(cfg,f'The Brief | {slot:%m/%d %H:%M} | {len(articles)} {t["new"]}',short,mid,interactive)
    except BeforeSendError:
        c.execute('DELETE FROM batches WHERE id=?',(batch_id,));c.commit()
        raise
    with c:
        for a in articles: c.execute('UPDATE articles SET sent=? WHERE url=?',(stamp(clock),a['url']))
        c.execute("UPDATE batches SET status='sent' WHERE id=?",(batch_id,))

@contextlib.contextmanager
def locked(path):
    import msvcrt
    with open(path,'a+b') as f:
        f.seek(0);f.write(b'0');f.flush();f.seek(0)
        try: msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        except OSError: raise RuntimeError('Another digest process is running')
        try: yield
        finally: f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['collect','preview','tick','test-email','status','resolve','check'])
    p.add_argument('--batch');p.add_argument('--result',choices=['sent','retry'])
    args=p.parse_args()
    private=BASE/'private';private.mkdir(exist_ok=True)
    logging.basicConfig(filename=private/'run.log',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    cfg=json.loads((BASE/'config.json').read_text(encoding='utf-8-sig'))
    if args.command=='check':
        with smtp_connection(cfg) as s:
            s.noop()
            print('SMTP TLS connection verified. No login attempted, no email sent.')
        return
    clock=now()
    with locked(private/'run.lock'):
        c=connect(private/'state.sqlite3')
        if not c.execute("SELECT 1 FROM meta WHERE key='floor'").fetchone():
            floor=dt.datetime.combine(clock.date()-dt.timedelta(days=1),dt.time(17),TZ)
            c.execute("INSERT INTO meta VALUES('floor',?)",(stamp(floor),));c.commit()
        floor=dt.datetime.fromisoformat(c.execute("SELECT value FROM meta WHERE key='floor'").fetchone()[0])
        if args.command in ('collect','preview','tick'): collect(c,cfg,clock)
        if args.command=='preview':
            content=browser_preview(filter_sections(select_articles(c,clock,floor),cfg.get('sections',[])),[dict(s) for s in c.execute('SELECT * FROM sources ORDER BY name')],clock,times=cfg['times'])
            (BASE/'preview.html').write_text(content,encoding='utf-8');print('Preview: '+str(BASE/'preview.html'))
        elif args.command=='tick':
            if cfg.get('enabled'): deliver(c,cfg,clock,floor)
        elif args.command=='test-email':
            t=words(cfg.get('language','en'))
            mail(cfg,'The Brief | '+t['test_subject'],'<h1>The Brief.</h1><p>'+esc(t['test_body'])+'</p>',make_msgid(domain='news-digest.local'))
            print('SMTP server accepted test message; verify receipt in inbox.')
        elif args.command=='status':
            print('enabled:',cfg.get('enabled'));print('Sources:',[dict(x) for x in c.execute('SELECT * FROM sources')]);print('Batches:',[dict(x) for x in c.execute('SELECT id,status FROM batches ORDER BY id DESC LIMIT 10')])
        elif args.command=='resolve':
            if not args.batch or not args.result: p.error('resolve needs --batch and --result')
            row=c.execute("SELECT * FROM batches WHERE id=? AND status='sending'",(args.batch,)).fetchone()
            if not row: raise ValueError('No uncertain batch with that id')
            with c:
                if args.result=='sent':
                    for url in json.loads(row['urls']): c.execute('UPDATE articles SET sent=? WHERE url=?',(stamp(clock),url))
                    c.execute("UPDATE batches SET status='sent' WHERE id=?",(args.batch,))
                else: c.execute('DELETE FROM batches WHERE id=?',(args.batch,))
        c.close()
    logging.info('Completed %s',args.command)

if __name__=='__main__':
    try: main()
    except Exception:
        logging.exception('Digest failed')
        print('ERROR: '+friendly_error(sys.exc_info()[1]),file=sys.stderr)
        sys.exit(1)
