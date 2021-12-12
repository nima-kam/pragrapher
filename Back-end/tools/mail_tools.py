import os
from typing import List
from requests import Response, post
from flask_mail import Mail, Message

mail = Mail()


class MailException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class mail_handler:
    # MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY", None)
    # MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN", None)

    FROM_TITLE = "Paragrapher"
    FROM_EMAIL = f"do-not-reply@paragrapher.ir"

    @classmethod
    def send_email(
            cls, emails: List[str], subject: str, text: str, html: str
    ):
        data = {
            # "sender": f"{cls.FROM_TITLE} <{cls.FROM_EMAIL}>",
            "recipients": emails,
            "subject": subject,
            "body": text,
        }
        if html is not None:
            data["html"] = html
        msg = Message(**data)
        mail.send(msg)
