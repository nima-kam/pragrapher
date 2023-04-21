import sqlalchemy as db
from db_models.users import UserModel
from tools.db_tool import make_session, Base
from sqlalchemy.orm import relationship
from typing import List

import datetime


class book_model(Base):
    __tablename__ = "book"
    id = db.Column(db.VARCHAR(250), primary_key=True)
    name = db.Column(db.VARCHAR(250), nullable=False)
    genre = db.Column(db.VARCHAR(100), nullable=False)
    reserved = db.Column(db.Boolean, default=False, nullable=False)
    reserved_time = db.Column(db.DATETIME, nullable=True)
    reserved_by = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=True)

    price = db.Column(db.Integer, nullable=False)
    author = db.Column(db.VARCHAR(200), nullable=False)
    modified_time = db.Column(db.DATETIME, nullable=False)
    description = db.Column(db.VARCHAR(250), nullable=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    buyer_id = db.Column(db.ForeignKey('Users.id'), nullable=True)

    community_id = db.Column(db.VARCHAR(30),
                             db.ForeignKey("community.id"), nullable=False)
    community_name = db.Column(db.VARCHAR(200), nullable=False)
    image = db.Column(db.VARCHAR(250), nullable=True)

    def __init__(self, name, genre, author, community_id, community_name, description, price, seller_id):
        self.id = community_id + "," + datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.name = name
        self.genre = genre
        self.author = author
        self.community_id = community_id
        self.community_name = community_name
        self.modified_time = datetime.datetime.now()
        self.description = description
        self.seller_id = seller_id
        self.price = price

    @property
    def json(self):
        dic = {"id": self.id,
               "name": self.name,
               "genre": self.genre,
               "author": self.author,
               "price": self.price,
               "modified_time": str(self.modified_time),
               "reserved_time": str(self.reserved_time),
               "reserved": self.reserved,
               "description": self.description,
               "seller_id": self.seller_id,
               "community_id": self.community_id,
               "community_name": self.community_name,
               "image": self.image
               }
        if self.buyer_id is None:
            dic["sold"] = False
        else:
            dic["sold"] = True
        return dic


def add_book(name, genre, author, community_id, community_name, description, price, seller_id, engine):
    session = make_session(engine)
    jwk_user = book_model(name=name, genre=genre, description=description, seller_id=seller_id,
                          community_id=community_id,
                          community_name=community_name, price=price, author=author)
    session.add(jwk_user)
    session.commit()
    return jwk_user.json


def get_one_book(book_id, community_name, engine):
    session = make_session(engine)
    book: book_model = session.query(book_model).filter(
        db.and_(book_model.id == book_id, book_model.community_name == community_name)).first()
    return book


def change_book_image(id, url, engine):
    session = make_session(engine)
    session.query(book_model).filter(book_model.id ==
                                     id).update({book_model.image: url})
    session.flush()
    session.commit()
    return "ok", 200


def edit_book(book: book_model, name, genre, author, price, description, engine):
    session = make_session(engine)
    b: book_model = session.query(book_model).filter(
        db.and_(book_model.id == book.id)).first()

    if name is not None:
        b.name = name
    if genre is not None:
        b.genre = genre
    if author is not None:
        b.author = author
    if description is not None:
        b.description = description
    if price is not None:
        b.price = price
    session.flush()
    session.commit()
    return b.json


def delete_book(book: book_model, engine):
    session = make_session(engine)
    b: book_model = session.query(book_model).filter(
        db.and_(book_model.id == book.id)).first()

    session.delete(b)
    session.flush()
    session.commit()


def check_reserved_book(book_id, engine):
    session = make_session(engine)
    session.expire_on_commit = False
    b: book_model = session.query(book_model).filter(
        db.and_(book_model.id == book_id)).first()

    if (b.reserved and b.reserved_time + datetime.timedelta(minutes=31) < datetime.datetime.now()) or b.buyer_id is not None:
        b.reserved = False
        b.reserved_by = None
    elif not b.reserved and b.reserved_by is not None \
            and b.reserved_time + datetime.timedelta(minutes=31) > datetime.datetime.now():
        b.reserved = True

    session.flush()
    session.commit()
    return b


def user_reserved_count(user: UserModel, engine):
    session = make_session(engine)
    count: int = session.query(book_model).filter(book_model.reserved_by == user.id).count()
    return count
