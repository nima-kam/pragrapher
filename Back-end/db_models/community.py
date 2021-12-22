import sqlalchemy as db
from flask import redirect, url_for
from sqlalchemy.sql.expression import and_
from sqlalchemy.sql.functions import user
from sqlalchemy.orm import backref, session
from db_models.paragraph import paragraph_model
from tools.db_tool import make_session, Base
from tools.crypt_tool import app_bcrypt
from sqlalchemy.ext.declarative import declarative_base
from tools.string_tools import gettext
from sqlalchemy.orm import relationship
from db_models.users import UserModel, add_notification
import datetime
from typing import List
import persiantools.jdatetime as jdate


class community_model(Base):
    __tablename__ = "community"
    id = db.Column(db.VARCHAR(30), primary_key=True)
    name = db.Column(db.VARCHAR(36), unique=True)
    creation_date = db.Column(db.DATE, name="creation_date")
    image = db.Column(db.VARCHAR(150), nullable=True)
    members = relationship("community_member", backref=backref("community"), lazy="dynamic",
                           cascade="all, delete-orphan")
    member_count = db.Column(db.Integer, default=0, nullable=False)
    description = db.Column(db.VARCHAR(250), nullable=True)
    private = db.Column(db.Boolean, default=False)

    def __init__(self, name, bio, m_id, engine):
        self.id = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.name = name
        self.description = bio
        self.creation_date = datetime.date.today()
        # add_community_member(c_id=self.id, user_id=m_id , role = 1 , engine=engine)

    @property
    def json(self):
        dic = {"name": self.name,
               "creation_year": str(self.creation_date.strftime('%Y')),
               "creation_month": str(self.creation_date.strftime('%m')),
               "jalali_date": jdate.JalaliDate.to_jalali(self.creation_date).strftime("%c"),
               "date": str(self.creation_date),
               "avatar": self.image,
               "member_count": self.member_count,
               "description": self.description,
               "links": {
                   "community_page": gettext("link_community_page").format(self.name)
               }
               }
        return dic

    def get_members_json(self):
        print('\n\n\n before in members json ')
        mems: List[community_member] = self.members
        memlist = []
        print('\n\n\nin members json ', mems)
        for m in mems:
            mem: UserModel = m.member
            js = mem.public_json
            js["role"] = m.role
            memlist.append(js)

        return memlist

    def get_one_member(self, user_id):
        for member in self.members:
            if member.m_id == user_id:
                return member
        return None


def change_community_data(c_name, description, isPrivate, engine):
    session = make_session(engine)
    print("\n\nchange ", c_name, " \ndes ", description)
    session.query(community_model).filter(community_model.name == c_name).update(
        {community_model.description: description})
    session.flush()
    session.commit()
    return "ok", 200


def change_community_image(current_user: UserModel, name, url, engine):
    session = make_session(engine)
    session.query(community_model).filter(community_model.name ==
                                          name).update({community_model.image: url})
    session.flush()
    session.commit()
    return "ok", 200


class community_member(Base):
    __tablename__ = "community_member"
    id = db.Column(db.VARCHAR(30), primary_key=True)
    m_id = db.Column(db.Integer, db.ForeignKey("Users.id"), nullable=False)
    # role 1 for admin | role 2 for member
    role = db.Column(db.SMALLINT, nullable=False, default=2)
    c_id = db.Column(db.VARCHAR(30), db.ForeignKey(
        "community.id"), nullable=False)
    subscribed = db.Column(db.BOOLEAN, default=False)
    __table_args__ = (
        db.UniqueConstraint("c_id", "m_id", name="member_community_u"),
    )

    def __init__(self, c_id, m_id, role=2):
        self.id = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.c_id = c_id
        self.m_id = m_id
        self.role = role

    # community info for user

    @property
    def community_json(self):
        dic = {"c_id": self.c_id,
               "m_id": self.m_id,
               "role": self.role,
               "subscribed": self.subscribed,
               "community": self.community.json,
               }
        return dic

    @property
    def json(self):
        dic = {"c_id": self.c_id,
               "m_id": self.m_id,
               "role": self.role,
               "subscribed": self.subscribed,
               }
        return dic


def get_role(user_id, community_id, engine):
    session = make_session(engine)
    print("\n\n\n HELL AWAITS before query \n\n\n")
    mem_c: community_member = session.query(community_member).filter(
        db.and_(community_member.m_id == user_id, community_member.c_id == community_id)).first()
    print("\n\n\n HELL AWAITS after query \n\n\n")
    if mem_c is None:
        return -1
    return mem_c.role


def delete_member(user_id, community_id, engine):
    session = make_session(engine)
    mem_c: community_member = session.query(community_member).filter(
        db.and_(community_member.m_id == user_id, community_member.c_id == community_id)).first()
    session.delete(mem_c)
    com: community_model = session.query(community_model).filter(
        community_model.id == community_id).first()
    com.member_count -= 1
    session.flush()
    session.commit()


def get_community(name, engine):
    session = make_session(engine)
    our_community: community_model = session.query(
        community_model).filter((community_model.name == name)).first()
    return our_community


def add_community(name, bio, user: UserModel, engine):
    session = make_session(engine)
    jwk_user = community_model(name=name, bio=bio, m_id=user.id, engine=engine)
    session.add(jwk_user)
    session.commit()
    add_community_member(jwk_user.id, user, 1, name, engine)
    return jwk_user


def add_notification_to_subcribed(comu: community_model, text, paragraph_link, engine):
    """
    text: paragraph text
    paragraph_link: front link to paragraph
    """
    session = make_session(engine)
    res: List[community_member] = session.query(community_member).filter(
        and_(community_member.c_id == comu.id, community_member.subscribed == True)).all()
    for row in res:
        user: UserModel = session.query(UserModel).filter(
            UserModel.id == row.m_id).first()
        add_notification(user.id, user.email, text,
                         'پاراگراف جدیدی به جامعه ی {} اضافه شد'.format(comu.name), paragraph_link, engine)
    session.commit()


def add_notification_for_new_join(comu: community_model, new_user: UserModel, engine):
    session = make_session(engine)

    admin: UserModel = session.query(UserModel).filter(
        db.and_(community_member.c_id == comu.id, community_member.role == 1, UserModel.id == community_member.m_id)) \
        .first()

    add_notification(admin.id, admin.email,
                     'عضو جدیدی به جامعه ی {} وارد شد'.format(comu.name), "عضو جدید"
                     , gettext("link_user").format(new_user.name), engine)


def add_community_member(c_id, user: UserModel, role, c_name, engine):
    session = make_session(engine)
    jwk_user = community_member(c_id=c_id, m_id=user.id, role=role)
    com: community_model = session.query(community_model).filter(
        community_model.id == c_id).first()
    com.member_count += 1
    session.add(jwk_user)
    session.commit()
    add_notification(user_id=user.id, email=user.email, text="به جامعه {} خوش امدید".format(c_name),
                     subject='خوش امدگویی', related_info=c_name, engine=engine)


def change_community_member_subscribe(user: UserModel, comu: community_model, engine):
    session = make_session(engine)
    com: community_member = session.query(community_member).filter(
        and_(community_member.m_id == user.id, community_member.c_id == comu.id)).first()
    if com.subscribed:
        com.subscribed = False
    else:
        com.subscribed = True
    session.flush()
    session.commit()


def get_community_member_subscribe(user: UserModel, comu: community_model, engine):
    session = make_session(engine)
    com: community_member = session.query(community_member).filter(
        and_(community_member.m_id == user.id, community_member.c_id == comu.id)).first()

    return com.subscribed
