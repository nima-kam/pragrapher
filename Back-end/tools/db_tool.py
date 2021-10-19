from flask import sessions
import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def make_connection(username , password , host , db_name):
    engine = db.create_engine('mysql+pymysql://{}:{}@{}/{}'.format(username , password , host  , db_name ), echo=True)
    return engine 

def make_session(engine):
    Session = db.orm.sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    return session

def init_tables(engine):
    Base.metadata.create_all(engine)
