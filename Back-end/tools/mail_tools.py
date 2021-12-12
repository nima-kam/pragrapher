import os
from typing import List
from requests import Response, post
from flask_mail import Mail, Message

def init_mail(app , MAIL_USERNAME , MAIL_PASSWORD):
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=465,
        MAIL_USERNAME=MAIL_USERNAME,
        MAIL_PASSWORD=MAIL_PASSWORD,
        MAIL_USE_TLS=False,
        MAIL_USE_SSL=True

    )
    mail = Mail(app)
    return mail

def send_mail(mail , sender , emails):
    print("sending email")
    msg = Message('Hello', sender = sender, recipients = emails)
    msg.body = "Hello Flask message sent from Flask-Mail"
    mail.send(msg)

class MailException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class mail_handler:
    # MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY", None)
    # MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN", None)



    @classmethod
    def send_email(
             emails: List[str], subject: str, text: str, html: str
    ):
        FROM_TITLE = "Paragrapher"
        FROM_EMAIL = f"do-not-reply@paragrapher.ir"
        data = {
            "sender": f"{FROM_TITLE} <{FROM_EMAIL}>",
            "recipients": emails,
            "subject": subject,
            "body": text,
        }
        if html is not None:
            data["html"] = html
        msg = Message(**data)
        mail.send(msg)
        "sending email to {}".format(emails[0])
