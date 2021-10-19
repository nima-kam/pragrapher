import sqlalchemy as db
from tools.db_tool import  make_session , Base
from tools.crypt_tool import app_bcrypt
from sqlalchemy.ext.declarative import declarative_base

import re
import datetime




class UserModel(Base):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.VARCHAR(100), nullable=False)
    email = db.Column(db.VARCHAR(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    reg_date = db.Column(db.DATE, name="register_date")

    def __init__(self, name, email, password: str):

        self.name = name
        if self.check_email(email):
            self.email = email
        else:
            raise ValueError("Wrong Email format")
        self.password = password_hash(password=password)
        self.reg_date = datetime.date.today()

    def check_email(self , email) -> bool:
        '''
        pass the string into the fullmatch() method
        '''
        e_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return bool(re.match(e_regex, email))

def password_hash( password) -> str:
        return app_bcrypt.generate_password_hash(password)

def checkPassword(password1 , password2) -> bool:
        return app_bcrypt.check_password_hash(password1, password2)

def add_user(name , email , password , engine):
    session = make_session(engine)
    jwk_user = UserModel(name=name, email=email , password=password)
    session.add(jwk_user)
    session.commit()

def check_one_user(username , password , engine):
    session = make_session(engine)
    our_user = session.query(UserModel).filter(UserModel.name==username).first()
    if our_user:
        password1 = our_user.password 
        if checkPassword(password1 , password):
            return our_user
        else:
            return None
    return None

def get_one_user(username, email  , engine):
    session = make_session(engine)
    our_user = session.query(UserModel).filter((UserModel.name==username) | (UserModel.email==email)).first()
    return our_user