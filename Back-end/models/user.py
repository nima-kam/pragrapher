from setting import db, app_bcrypt
import datetime
import re


class UserModel(db.Model):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.VARCHAR(100), nullable=False)
    email = db.Column(db.VARCHAR(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    reg_date = db.Column(db.DATE, name="register_date")

    def __init__(self, name, email, password: str, admin: bool):

        self.name = name
        if UserModel.checkEmail(email):
            self.email = email
        else:
            raise ValueError("Wrong Email format")
        self.password = UserModel.passwordHash(password=password)
        self.reg_date = datetime.date.today()

    @classmethod
    def check_email(cls, email) -> bool:
        '''
        pass the string into the fullmatch() method
        '''
        e_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return bool(re.match(e_regex, email))

    @classmethod
    def password_hash(cls, password) -> str:
        return app_bcrypt.generate_password_hash(password)

    def checkPassword(self, password) -> bool:
        return app_bcrypt.check_password_hash(self.password, password)
