import os
from sqlalchemy import engine
from endpoints import init_endpoints
from flask import Flask
from flask_restful import Api
from config import init_config
from tools.db_tool import init_db
from tools.string_tools import *
from flask_cors import CORS


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
init_endpoints(api, engine)
print("endpoints added")

if __name__ == '__main__':
    api.init_app(app)
    app.run(use_reloader=True, host='0.0.0.0', threaded=True)
