def init_config():
    config = {
        "MAIL_SERVER": 'smtp.gmail.com',
        "MAIL_PORT": 465,
        "MAIL_USE_TLS": False,
        "MAIL_USE_SSL": True,
        "MAIL_DEFAULT_SENDER": "paragrapher",
        "MAIL_USERNAME": 'paragrapher.info@gmail.com',
        "MAIL_PASSWORD": 'CSn2020.info',
        'MYSQL_HOST': 'localhost',
        'MYSQL_USER': 'root',
        'MYSQL_PASSWORD': '',
        'MYSQL_DB': 'pragrapher'
    }
    return config


jwt_secret_key = 'strong_jwt_password'
