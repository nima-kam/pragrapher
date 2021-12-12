def init_config():
    config = {"MAIL_SERVER": 'smtp.gmail.com',
              "MAIL_PORT": 465,
              "MAIL_USE_TLS": False,
              "MAIL_USE_SSL": True,
              "MAIL_DEFAULT_SENDER": "paragrapher",
              "MAIL_USERNAME": 'YOUR_GMAIL',
              "MAIL_PASSWORD": 'YOUR_PASSWORD',
              'MYSQL_HOST': 'localhost',
              'MYSQL_USER': 'manager',
              'MYSQL_PASSWORD': 'strong_password',
              'MYSQL_DB': 'pragrapher'}
    return config


jwt_secret_key = 'strong_jwt_password'
