import sqlalchemy as db
from flask import redirect, url_for
from sqlalchemy.sql.functions import user
from sqlalchemy.orm import backref
from tools.db_tool import make_session, Base, engine
from tools.crypt_tool import app_bcrypt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from tools.string_tools import gettext

import time
import re
import datetime

association_table = db.Table('association', Base.metadata,
                             db.Column(db.BIGINT, db.ForeignKey('paragraph.id'), name='p_id', primary_key=True),
                             db.Column(db.SMALLINT, db.ForeignKey('tags.id'), name='tag', primary_key=True)
                             )


class paragraph_model(Base):
    __tablename__ = "paragraph"
    id = db.Column(db.BIGINT, primary_key=True)
    p_text = db.Column(db.VARCHAR(250), nullable=False)
    ref_book = db.Column(db.VARCHAR(100))
    date = db.Column(db.DATETIME, nullable=False)
    replied_id = db.Column(db.BIGINT, db.ForeignKey("paragraph.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    community_id = db.Column(db.VARCHAR(30), db.ForeignKey("community.id"), nullable=False)
    tags = relationship("tags_model", secondary=association_table, backref="paragraph")
    # replies = relationship("paragraph_model", backref="replied")
    impressions = relationship("impressions", backref=backref("paragraph"), lazy="subquery",cascade="all, delete-orphan")
    
    ima_count = db.Column(db.BIGINT, default=0)

    @property
    def json(self):
        dic = {"id": self.id,
               "p_text": self.p_text,
               "ref_book": self.ref_book,
               "date": self.date,
               "replied_id":self.replied_id,
               "user_id":self.user_id,
               "community_id":self.community_id,
               "impressions":self.impressions
               }
        return dic
    def __init__(self, user_id, p_text, ref_book , community_id):
        self.id = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.p_text = p_text
        self.ref_book = ref_book
        self.user_id = user_id
        self.community_id = community_id
        self.date = datetime.datetime.now()

def get_one_paragraph(paragraph_id , engine):
    session = make_session(engine)
    parags: paragraph_model = session.query(paragraph_model).filter(paragraph_model.id == paragraph_id).first()
    if parags == None:
        return None
    print("parags by id: \n\n" , parags)
    return parags

def add_paragraph(text, ref, user_id, community_id, engine):
    session = make_session(engine)
    jwk_user = paragraph_model(p_text=text, ref_book=ref, user_id=user_id, community_id=community_id)
    session.add(jwk_user)
    session.commit()
    return jwk_user

def get_community_paragraphs(community_id , engine):
    session = make_session(engine)
    parags: paragraph_model = session.query(paragraph_model).filter(paragraph_model.community_id == community_id)
    if parags == None:
        return []
    print("parags by community: \n\n" , parags)
    return parags

# class POD(Base):
#     """
#     for saving the paragraph of the day for a community on a specified date
#     """
#     __tablename__ = "pod"
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     c_id = db.Column(db.VARCHAR(30), db.ForeignKey("community.id"), nullable=False)
#     date = db.Column(db.DATE, nullable=False)
#     p_id = db.Column(db.BIGINT, db.ForeignKey("paragraph.id"))
#     paragraph = relationship("paragraph_model", cascade="all, delete-orphan")

#     __table_args__ = (
#         db.UniqueConstraint("c_id", "date", name="date_community_u"),
#     )

#     def __init__(self, date, c_id, paragraph):
#         self.c_id = c_id
#         self.date = date
#         self.paragraph = paragraph


def change_impression(user, paragraph, engine, increment=True):
    """
    :param user:
    :param paragraph:
    :param increment: True for increase impression and False for delete
    :return:
    """
    pass


class impressions(Base):
    __tablename__ = "impressions"
    p_id = db.Column(db.BIGINT, db.ForeignKey("paragraph.id"), primary_key=True)
    u_id = db.Column(db.Integer, db.ForeignKey("Users.id"), primary_key=True)


class tags_model(Base):
    __tablename__ = "tags"
    id = db.Column(db.SMALLINT, primary_key=True)
    name = db.Column(db.VARCHAR(50), unique=True)

    def __init__(self, name):
        self.name = name

    @classmethod
    def get_tag(cls, name, engine):
        session = make_session(engine)
        a_tag = session.query(cls).filter(cls.name == name).first()
        return a_tag

    @classmethod
    def add_tag(cls, name: str, engine):
        a_tag = cls.get_tag(name, engine)
        if a_tag is not None:
            return False, gettext("item_name_exists").format(name)

        session = make_session(engine)
        new_tag = tags_model(name)
        session.add(new_tag)
        session.commit()
        return True, gettext("item_added").format("tag")
