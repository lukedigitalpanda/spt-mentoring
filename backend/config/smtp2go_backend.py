import json
import urllib.request
import urllib.error

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

API_URL = 'https://api.smtp2go.com/v3/email/send'


class SMTP2GOEmailBackend(BaseEmailBackend):
    """
    Django email backend that sends via the SMTP2GO HTTP API.
    Reads the API key from EMAIL_HOST_PASSWORD (or pass api_key= directly).
    """

    def __init__(self, api_key=None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or getattr(settings, 'EMAIL_HOST_PASSWORD', '')

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            if self._send(message):
                sent += 1
        return sent

    def _send(self, message):
        payload = {
            'api_key': self.api_key,
            'sender': message.from_email,
            'to': message.to,
            'subject': message.subject,
        }

        if message.cc:
            payload['cc'] = message.cc
        if message.bcc:
            payload['bcc'] = message.bcc

        # Plain text body
        if getattr(message, 'content_subtype', 'plain') == 'html':
            payload['html_body'] = message.body
        else:
            payload['text_body'] = message.body

        # HTML alternative in multipart messages
        if hasattr(message, 'alternatives'):
            for content, mimetype in message.alternatives:
                if mimetype == 'text/html':
                    payload['html_body'] = content

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            API_URL,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                return result.get('data', {}).get('succeeded', 0) > 0
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            if not self.fail_silently:
                raise RuntimeError(f'SMTP2GO API error {e.code}: {body}') from e
            return False
        except Exception:
            if not self.fail_silently:
                raise
            return False
