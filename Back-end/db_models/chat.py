import time
from tools.db_tool import Base
import sqlalchemy as db


class MessageModel(Base):
    __tablename__ = 'message'
    id = db.Column(db.INT, primary_key=True, autoincrement=True)
    from_user = db.Column(db.INT, nullable=False)
    to_user = db.Column(db.INT, nullable=False)
    timestamp = db.Column(db.TIMESTAMP, nullable=False)
    content = db.Column(db.VARCHAR(4096))

    def __init__(self, __from_user, __to_user, __content):
        self.from_user = __from_user
        self.to_user = __to_user
        self.content = __content
        self.timestamp = time.time()
