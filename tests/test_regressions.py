import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from unittest.mock import patch,MagicMock
from email.policy import SMTP
from email.utils import make_msgid
import smtplib
import ssl
import digest as d

class MailRegressionTests(unittest.TestCase):
    def setUp(self):
        self.cfg={'sender':'sender@example.com','recipient':'recipient@example.com','smtp_host':'smtp.gmail.com','smtp_port':465,'language':'en'}
    def test_chinese_machine_name_does_not_break_mime(self):
        with patch('socket.getfqdn',return_value='测试的电脑'):
            mid=make_msgid(domain='news-digest.local')
            for language in ('en','zh-Hans','zh-Hant'):
                self.cfg['language']=language
                m=d.prepare_message(self.cfg,'中文測試','<p>新闻與新聞</p>',mid,'<p>附件</p>')
                self.assertTrue(m['Message-ID'].isascii())
                self.assertIn(b'MIME-Version',m.as_bytes(policy=SMTP))
    def test_auth_failure_is_safe_before_send(self):
        with patch.object(d,'credential',return_value={'user':'sender@example.com','password':'dummy'}),patch.object(d,'smtp_connection') as connection:
            connection.return_value.login.side_effect=smtplib.SMTPAuthenticationError(535,b'rejected')
            with self.assertRaises(d.BeforeSendError):d.mail(self.cfg,'test','body',make_msgid(domain='news-digest.local'))
            connection.return_value.send_message.assert_not_called()
            connection.return_value.close.assert_called_once()
    def test_transmission_failure_remains_ambiguous(self):
        with patch.object(d,'credential',return_value={'user':'sender@example.com','password':'dummy'}),patch.object(d,'smtp_connection') as connection:
            connection.return_value.send_message.side_effect=TimeoutError()
            with self.assertRaises(TimeoutError):d.mail(self.cfg,'test','body',make_msgid(domain='news-digest.local'))
    def test_account_mismatch_never_connects(self):
        with patch.object(d,'credential',return_value={'user':'other@example.com','password':'dummy'}),patch.object(d,'smtp_connection') as connection:
            with self.assertRaises(d.BeforeSendError):d.mail(self.cfg,'test','body',make_msgid(domain='news-digest.local'))
            connection.assert_not_called()
    def test_proxy_tls_verifies_original_server(self):
        sock=MagicMock();header=b'HTTP/1.1 200 Connection established\r\n\r\n'
        sock.recv.side_effect=[bytes([b]) for b in header]
        client=object.__new__(d.ProxySMTPSSL);client.proxy={'host':'127.0.0.1','port':7890};client.context=MagicMock()
        with patch.object(d.socket,'create_connection',return_value=sock):
            client._get_socket('smtp.gmail.com',465,20)
        client.context.wrap_socket.assert_called_once_with(sock,server_hostname='smtp.gmail.com')
        self.assertIn(b'CONNECT smtp.gmail.com:465',sock.sendall.call_args.args[0])
    def test_proxy_rejection_closes_socket(self):
        sock=MagicMock();sock.recv.side_effect=[bytes([b]) for b in b'HTTP/1.1 403 Forbidden\r\n\r\n']
        client=object.__new__(d.ProxySMTPSSL);client.proxy={'host':'127.0.0.1','port':7890};client.context=MagicMock()
        with patch.object(d.socket,'create_connection',return_value=sock):
            with self.assertRaises(ConnectionError):client._get_socket('smtp.gmail.com',465,20)
        sock.close.assert_called_once();client.context.wrap_socket.assert_not_called()

if __name__=='__main__':unittest.main()
