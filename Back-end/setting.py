from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
ma = Marshmallow()
app_bcrypt = Bcrypt()


def create_app(name):
    app = Flask(name)
    db.init_app(app)
    ma.init_app(app)

