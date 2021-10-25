import sqlalchemy as db
from flask import redirect, url_for
from sqlalchemy.sql.functions import user
from tools.db_tool import make_session, Base
from tools.crypt_tool import app_bcrypt
from sqlalchemy.ext.declarative import declarative_base
import re
import datetime

changed_s = "{} changed successfully"


class UserModel(Base):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    f_name = db.Column(db.VARCHAR(150), nullable=True)
    name = db.Column(db.VARCHAR(150), nullable=False, unique=True)
    email = db.Column(db.VARCHAR(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    reg_date = db.Column(db.DATE, name="register_date")
    image = db.Column(db.VARCHAR(150), nullable=True)

    def __init__(self, username, email, password: str):

        self.name = username
        if self.check_email(email):
            self.email = email
        else:
            raise ValueError("Wrong Email format")
        self.password = password_hash(password=password)
        self.reg_date = datetime.date.today()

    def check_email(self, email) -> bool:
        """
        pass the string into the match() method
        """
        e_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return bool(re.match(e_regex, email))

    @property
    def json(self):
        dic = {"username": self.name,
               "register_date": self.reg_date,
               "profile_name": self.f_name,
               "avatar": self.image,
               "email": self.email,
               }
        return dic


def change_pass(current_user: UserModel, old_pass, new_pass, engine):
    """
    Gets a user check if the old pass is correct and save new pass
    and redirect to logout
    """
    if checkPassword(current_user.password, old_pass):
        new_pass_hash = password_hash(new_pass)
        session = make_session(engine)
        current_user.password = new_pass_hash
        session.commit()
        redirect(url_for("logout"))

    else:
        return "password is wrong", 401


def password_hash(password) -> str:
    return app_bcrypt.generate_password_hash(password)


def checkPassword(password1, password2) -> bool:
    # first arg is the hashed password the second one is the one to be checked
    return app_bcrypt.check_password_hash(password1, password2)


def add_user(name, email, password, engine):
    session = make_session(engine)
    jwk_user = UserModel(username=name, email=email, password=password)
    session.add(jwk_user)
    session.commit()


def check_one_user(username, password, engine):
    session = make_session(engine)
    our_user = session.query(UserModel).filter(UserModel.name == username).first()
    if our_user:
        password1 = our_user.password
        if checkPassword(password1, password):
            return our_user
        else:
            return None
    return None


def get_one_user(username, email, engine):
    session = make_session(engine)
    our_user = session.query(UserModel).filter((UserModel.name == username) | (UserModel.email == email)).first()
    return our_user


def edit_fname(current_user: UserModel, f_name, engine):
    session = make_session(engine)
    session.query(UserModel).filter(UserModel.id == current_user.id).update({UserModel.f_name: f_name})
    session.flush()
    session.commit()
    return changed_s.format("first name"), 200

def change_image(current_user: UserModel, url, engine):
    session = make_session(engine)
    session.query(UserModel).filter(UserModel.id == current_user.id).update({UserModel.image: url})
    session.flush()
    session.commit()
    return changed_s.format("image"), 200


def change_username(current_user: UserModel, new_username, engine):
    """If is available change the name otherwise return error message"""
    session = make_session(engine)
    same_user = get_one_user(new_username, None, engine)
    if same_user is None:
        current_user.name = new_username
        session.commit()
        return "username changed successfully", 200
    return "username exist already", 401


def edit_image(current_user: UserModel, image, engine):
    session = make_session(engine)
    current_user.image = image
    session.commit()
    return changed_s.format("image"), 200
