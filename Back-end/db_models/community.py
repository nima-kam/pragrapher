import sqlalchemy as db
from flask import redirect, url_for
from sqlalchemy.sql.functions import user
from sqlalchemy.orm import backref
from tools.db_tool import make_session, Base, engine
from tools.crypt_tool import app_bcrypt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import  relationship
from db_models.users import UserModel
import datetime



class community_model(Base):
    __tablename__ = "community"
    id = db.Column(db.VARCHAR(30), primary_key=True)
    name = db.Column(db.VARCHAR(36) , unique=True)
    creation_date = db.Column(db.DATE, name="creation_date")
    image = db.Column(db.VARCHAR(150), nullable=True)
    members = relationship("community_member", backref=backref("community"))

    def __init__(self, name, m_id  ,engine):
        self.id = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.name = name
        self.creation_date = datetime.date.today()
        #add_community_member(c_id=self.id, user_id=m_id , role = 1 , engine=engine)


class community_member(Base):
    __tablename__ = "community_member"
    id = db.Column(db.VARCHAR(30), primary_key=True )
    m_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique=True)
    role = db.Column(db.SMALLINT, nullable=False, default=2)  # role 1 for admin | role 2 for member
    c_id = db.Column(db.VARCHAR(30), db.ForeignKey("community.id"))

    def __init__(self, c_id, m_id , role = 2 ):
        self.id = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.c_id = c_id
        self.m_id = m_id
        self.role = role

def get_community(name,engine):
    session = make_session(engine)
    our_community = session.query(community_model).filter((community_model.name == name) ).first()
    return our_community


def add_community(name, user_id , engine):
    session = make_session(engine)
    jwk_user = community_model(name=name, m_id=user_id , engine=engine )
    session.add(jwk_user)
    session.commit()
    add_community_member(jwk_user.id , user_id , 1 , engine)

def add_community_member(c_id, user_id , role ,  engine):
    session = make_session(engine)
    jwk_user = community_member(c_id=c_id, m_id=user_id , role = role )
    session.add(jwk_user)
    session.commit()