from typing import List
import sqlalchemy as db
from tools.db_tool import make_session, Base
from tools.crypt_tool import app_bcrypt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from tools.string_tools import gettext

import re
import datetime


class payment_model(Base):
    __tablename__ = "payments"
    id = db.Column(db.BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey("Users.id"), nullable=False, onupdate="CASCADE")
    amount = db.Column(db.Integer, nullable=False)
    datetime = db.Column(db.DATETIME, nullable=False)
    t_type = db.Column(db.Integer, nullable=False)  # 0 for charge money / 1 for discharge /
    # 2 for sell book / 3 for buy book
    second_user_id = db.Column(db.ForeignKey("Users.id"), nullable=True, onupdate="CASCADE")

    def __init__(self, user_id, amount, transaction_type, id=None, second_user_id=None):
        """
        :param user_id: the user
        :param amount:
        :param id: payment id to be saved
        :param second_user_id: person who has bought/sold the book from user
        :param transaction_type -> 0 for charge money / 1 for discharge / 2 for sell book / 3 for buy book"""
        self.user_id = user_id
        self.amount = amount
        self.t_type = transaction_type
        # if transaction_type in [2, 3]:
        #     if second_user_id is None:
        #         raise ValueError(gettext("transaction_null_user"))
        #     self.second_user_id = second_user_id
        self.datetime = datetime.datetime.now()

    @property
    def json(self):
        dic = {
            "user_id": self.user_id,
            "time": self.datetime,
            "type": self.t_type,
            "amount": self.amount,

        }

        if self.second_user_id is not None:
            dic["second_id"] = self.second_user_id
        return dic
