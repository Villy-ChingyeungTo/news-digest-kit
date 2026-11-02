import unittest
import test_digest as base
d=base.d
from unittest.mock import patch, Mock

class RecoveryTests(unittest.TestCase):
    setUp=base.DigestTests.setUp
    tearDown=base.DigestTests.tearDown
    def test_reconcile_sent_missing_and_failed_search(self):
        import datetime as dt
        for status, ids, expected in [('OK',[b'123'],'sent'),('OK',[b''],None),('NO',[b''], 'sending')]:
            self.c.execute('DELETE FROM batches')
            self.c.execute('INSERT INTO batches VALUES(?,?,?,?,?)',('old','sending','[]','<old@example.com>',d.stamp(self.clock-dt.timedelta(hours=1))))
            self.c.commit()
            with patch.object(d,'credential',return_value={'user':'x@example.com','password':'x'}), patch.object(d.imaplib.IMAP4_SSL,'__init__',return_value=None), patch.object(d.imaplib.IMAP4_SSL,'__enter__') as enter, patch.object(d.imaplib.IMAP4_SSL,'__exit__',return_value=False):
                client=enter.return_value
                client.list.return_value=('OK',[b'(\\Sent) "/" "[Gmail]/Sent Mail"'])
                client.select.return_value=('OK',[b'1'])
                client.uid.return_value=(status,ids)
                if status=='NO':
                    with self.assertRaises(RuntimeError): d.reconcile_gmail(self.c,{'smtp_host':'smtp.gmail.com'},self.clock)
                else: d.reconcile_gmail(self.c,{'smtp_host':'smtp.gmail.com'},self.clock)
            row=self.c.execute('SELECT status FROM batches').fetchone()
            self.assertEqual(row[0] if row else None,expected)

    def test_connection_failure_can_retry(self):
        with patch.object(d,'BASE',self.root), patch.object(d,'credential',return_value={'user':'x@example.com','password':'x'}), patch.object(d.smtplib,'SMTP_SSL',side_effect=TimeoutError):
            self.cfg.update(sender='x@example.com',recipient='x@example.com',smtp_host='smtp.example.com',smtp_port=465)
            with self.assertRaises(d.BeforeSendError): d.deliver(self.c,self.cfg,self.clock,self.floor)
        self.assertEqual(self.c.execute('SELECT count(*) FROM batches').fetchone()[0],0)
        self.assertIsNone(self.c.execute('SELECT sent FROM articles').fetchone()[0])

    def test_quit_failure_after_acceptance_is_success(self):
        self.cfg.update(sender='x@example.com',recipient='x@example.com',smtp_host='smtp.example.com',smtp_port=465)
        with patch.object(d,'BASE',self.root), patch.object(d,'credential',return_value={'user':'x@example.com','password':'x'}), patch.object(d.smtplib,'SMTP_SSL') as smtp:
            smtp.return_value.quit.side_effect=TimeoutError
            d.deliver(self.c,self.cfg,self.clock,self.floor)
            self.assertEqual(self.c.execute('SELECT status FROM batches').fetchone()[0],'sent')
            smtp.return_value.send_message.assert_called_once()
            d.deliver(self.c,self.cfg,self.clock,self.floor)
            smtp.return_value.send_message.assert_called_once()

    def test_interrupted_preparation_is_retried(self):
        self.c.execute('INSERT INTO batches VALUES(?,?,?,?,?)',(d.stamp(self.clock),'preparing','[]','<x>',d.stamp(self.clock)))
        self.c.commit()
        with patch.object(d,'BASE',self.root), patch.object(d,'mail',side_effect=lambda *a,**k:k['accepted']()) as mail:
            d.deliver(self.c,self.cfg,self.clock,self.floor)
            mail.assert_called_once()
        self.assertEqual(self.c.execute('SELECT status FROM batches').fetchone()[0],'sent')

    def test_idle_sleep_request_restored(self):
        with patch.object(d.ctypes,'windll',create=True) as windll:
            windll.kernel32.SetThreadExecutionState.return_value=0x80000000
            with self.assertRaises(ValueError):
                with d.keep_awake(): raise ValueError('test')
            self.assertEqual([c.args[0] for c in windll.kernel32.SetThreadExecutionState.call_args_list],[0x80000001,0x80000000])
