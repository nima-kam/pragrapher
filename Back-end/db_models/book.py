import sqlalchemy as db
from tools.db_tool import make_session, Base
from sqlalchemy.orm import relationship
from typing import List

import datetime

class book_model(Base):
    __tablename__ = "book"
    id = db.Column(db.VARCHAR(250), primary_key=True)
    name = db.Column(db.VARCHAR(250), nullable=False)
    genre = db.Column(db.VARCHAR(100), nullable=False)
    reserved = db.Column(db.Boolean,default=False, nullable=False)
    reserved_time = db.Column(db.DATETIME, nullable=True)
    reserved_by = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=True)

    author = db.Column(db.VARCHAR(200), nullable=False)
    modified_time = db.Column(db.DATETIME, nullable=False)
    description = db.Column(db.VARCHAR(250), nullable=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    community_id = db.Column(db.VARCHAR(
        30), db.ForeignKey("community.id"), nullable=False)
    community_name = db.Column(db.VARCHAR(200), nullable=False)
    image = db.Column(db.VARCHAR(250), nullable=True)

    def __init__(self, name, genre, author, community_id, community_name, description, seller_id ):
        self.id = community_id + "," + datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.name = name
        self.genre = genre
        self.author = author
        self.community_id = community_id
        self.community_name = community_name
        self.modified_time = datetime.datetime.now()
        self.description = description
        self.seller_id = seller_id

    @property
    def json(self):

        dic = {"id": self.id,
               "name": self.name,
               "genre": self.genre,
               "author": self.author,
               "modified_time": str(self.modified_time),
               "reserved_time": str(self.reserved_time),
               "description": self.description,
               "seller_id": self.seller_id,
               "community_id": self.community_id,
               "community_name": self.community_name,
               "image": self.image
               }
        return dic


def add_book(name, genre, author, community_id, community_name, description, seller_id , engine):
    session = make_session(engine)
    jwk_user = book_model(name=name, genre=genre, description=description, seller_id=seller_id, community_id=community_id,
                               community_name=community_name,author=author)
    session.add(jwk_user)
    session.commit()
    return jwk_user.json