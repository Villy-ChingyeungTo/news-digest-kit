import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('digest',ROOT/'digest.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

class DigestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'private').mkdir()
        self.c=d.connect(':memory:')
        self.clock=dt.datetime(2026,10,4,9,0,tzinfo=d.TZ)
        self.floor=self.clock-dt.timedelta(days=2)
        self.cfg={'times':['09:00','12:00','17:00'],'activated_at':d.stamp(self.floor)}
        self.c.execute('INSERT INTO sources VALUES(?,?,?,?,?)',('feed','Bloomberg Markets','ok',1,d.stamp(self.clock)))
        self.url='https://www.bloomberg.com/news/articles/example'
        self.c.execute('INSERT INTO articles VALUES(?,?,?,?,?,NULL)',(self.url,'A & B <news>',d.stamp(self.clock-dt.timedelta(hours=13)),d.stamp(self.clock),json.dumps(['Bloomberg Markets'])))
        self.c.commit()
    def tearDown(self):self.c.close();self.temp.cleanup()
    def test_overnight_and_timezone(self):
        a=dict(self.c.execute('SELECT * FROM articles').fetchone())
        self.assertEqual(d.period(a,self.clock),'昨晚新增')
        self.assertEqual(d.due_slot(self.clock,self.cfg['times']),self.clock)
        self.assertEqual(d.due_slot(self.clock-dt.timedelta(hours=1),self.cfg['times']).hour,17)
    def test_success_then_no_duplicate_at_noon(self):
        with patch.object(d,'BASE',self.root),patch.object(d,'mail') as mail:
            d.deliver(self.c,self.cfg,self.clock,self.floor)
            d.deliver(self.c,self.cfg,self.clock,self.floor)
            self.assertEqual(mail.call_count,1)
            self.assertEqual(d.select_articles(self.c,self.clock+dt.timedelta(hours=3),self.floor),[])
    def test_uncertain_send_pauses_next_slot(self):
        with patch.object(d,'BASE',self.root),patch.object(d,'mail',side_effect=TimeoutError):
            with self.assertRaises(TimeoutError): d.deliver(self.c,self.cfg,self.clock,self.floor)
            with self.assertRaises(RuntimeError):d.deliver(self.c,self.cfg,self.clock+dt.timedelta(hours=3),self.floor)
        self.assertIsNone(self.c.execute('SELECT sent FROM articles').fetchone()[0])
    def test_before_send_failure_is_retriable(self):
        with patch.object(d,'BASE',self.root),patch.object(d,'mail',side_effect=d.BeforeSendError('network')):
            with self.assertRaises(d.BeforeSendError):d.deliver(self.c,self.cfg,self.clock,self.floor)
        self.assertEqual(self.c.execute('SELECT count(*) FROM batches').fetchone()[0],0)
        self.assertIsNone(self.c.execute('SELECT sent FROM articles').fetchone()[0])
    def test_render_escapes_external_content(self):
        a=dict(self.c.execute('SELECT * FROM articles').fetchone())
        h=d.render([a],[],self.clock)
        self.assertIn('A &amp; B &lt;news&gt;',h)
        self.assertIn('Last night',h)
        self.assertNotIn('<script',h)
    def test_all_sources_failed_no_send(self):
        self.c.execute("UPDATE sources SET status='HTTP 404'");self.c.commit()
        with patch.object(d,'mail') as mail:
            with self.assertRaises(RuntimeError):d.deliver(self.c,self.cfg,self.clock,self.floor)
            mail.assert_not_called()
    def test_cross_section_dedup(self):
        self.cfg['sources']=[{'name':'a','url':'a'},{'name':'b','url':'b'}]
        def feed(s): return s['name'],[(self.url,'Title',d.stamp(self.clock))],0
        with patch.object(d,'fetch',side_effect=feed):d.collect(self.c,self.cfg,self.clock)
        rows=self.c.execute('SELECT * FROM articles').fetchall()
        self.assertEqual(len(rows),1)
        self.assertTrue({'a','b'}.issubset(set(json.loads(rows[0]['sections']))))
    def test_canonical_rejects_foreign_links(self):
        with self.assertRaises(ValueError):d.canonical('javascript:alert(1)')
        self.assertEqual(d.canonical(self.url+'?tracking=x'),self.url)

    def test_three_locales_and_script_free_email(self):
        from ui import render, TEXT
        a=dict(self.c.execute('SELECT * FROM articles').fetchone())
        for language in TEXT:
            content=render([a],[],self.clock,language=language)
            self.assertIn('lang="'+language+'"',content)
            self.assertIn(TEXT[language]['overnight'],content)
            self.assertIn('A &amp; B &lt;news&gt;',content)
            self.assertNotIn('<script',content)
            self.assertNotIn('<select',content)

    def test_browser_variants_filter_secondary_sections(self):
        from ui import browser_preview
        a=dict(self.c.execute('SELECT * FROM articles').fetchone())
        a['sections']=json.dumps(['Bloomberg Markets','Bloomberg Technology'])
        b=dict(a,title='Other headline',url=self.url+'2',sections=json.dumps(['Bloomberg Politics']))
        content=browser_preview([a,b],[],self.clock)
        payload=content.split('<script id="locale-data" type="application/json">')[1].split('</script>')[0]
        pages=json.loads(payload)
        for language in ('en','zh-Hans','zh-Hant'):
            filtered=pages[language]['bodies']['Bloomberg Technology']
            self.assertIn('A &amp; B &lt;news&gt;',filtered)
            self.assertNotIn('Other headline',filtered)
            self.assertIn('Other headline',pages[language]['bodies'][''])
        self.assertEqual(d.filter_sections([a,b],['Bloomberg Technology']),[a])
        self.assertEqual(d.filter_sections([a,b],[]),[a,b])

    def test_email_attaches_interactive_html(self):
        with patch.object(d,'BASE',self.root),patch.object(d,'mail') as mail:
            d.deliver(self.c,self.cfg,self.clock,self.floor)
            args=mail.call_args.args
            self.assertNotIn('<script',args[2])
            self.assertIn('section-select',args[4])
            self.assertIn('language-select',args[4])
            self.assertNotIn('PREVIEW · NOT SENT',args[4])

if __name__=='__main__':unittest.main()
