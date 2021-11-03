import sqlalchemy as db
from flask import redirect, url_for
from sqlalchemy.sql.functions import user
from sqlalchemy.orm import backref
from tools.db_tool import make_session, Base, engine
from tools.crypt_tool import app_bcrypt
from sqlalchemy.ext.declarative import declarative_base
import re
import datetime
import uuid


class community_model(Base):
    __tablename__ = "community"
    id = db.Column(db.VARCHAR(30), primary_key=True)
    name = db.Column(db.VARCHAR(36))
    creation_date = db.Column(db.DATE, name="creation_date")
    image = db.Column(db.VARCHAR(150), nullable=True)
    members = db.Relation("community_member", backref=backref("community"))

    def __init__(self, *args, **kwargs):
        super.__init__(*args, **kwargs)
        self.id = uuid.uuid4()


class community_member(Base):
    m_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    role = db.Column(db.SMALLINT, nullable=False, default=2)  # role 1 for admin | role 2 for member

    c_id = db.Column(db.VARCHAR(30), db.ForeignKey("community.id"))
