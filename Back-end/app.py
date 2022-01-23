import os
from sqlalchemy import engine
from endpoints import init_endpoints
from flask import Flask
from flask_restful import Api
from config import init_config
from tools.db_tool import init_db
from tools.string_tools import *
from flask_cors import CORS
from tools.mail_tools import init_mail, send_mail

app = Flask(__name__)

app.config.update(
    DEBUG=True,
    SECRET_KEY="carbon_secret",
    SESSION_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_HTTPONLY=True,
    UPLOAD_FOLDER=os.path.join('', "static/uploads/")
)

configs = init_config()
MYSQL_HOST = configs['MYSQL_HOST']
MYSQL_USER = configs['MYSQL_USER']
MYSQL_PASSWORD = configs['MYSQL_PASSWORD']
MYSQL_DB = configs['MYSQL_DB']

api = Api()

CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
engine = init_db(MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB)
mail = init_mail(app, configs['MAIL_USERNAME'], configs['MAIL_PASSWORD'])
init_endpoints(api, engine, mail, configs['MAIL_USERNAME'], configs)
print("endpoints added")

# send_mail(mail , configs['MAIL_USERNAME'] , ['gekolig286@hagendes.com'])
api.init_app(app)
if __name__ == '__main__':
    app.run(use_reloader=True, host='0.0.0.0', port=8080)
