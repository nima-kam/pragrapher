from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
from functools import wraps
from config import init_config
from tools.db_tool import init_tables, make_session, make_connection
from db_models.users import add_user, check_one_user, get_one_user
### pip install PyJWT to prevent error
import jwt
import re
import datetime

from tools.token_tool import create_access_token

app = Flask(__name__)

app.config.update(
    DEBUG=True,
    SECRET_KEY="carbon_secret",
    SESSION_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_HTTPONLY=True
)

configs = init_config()
MYSQL_HOST = configs['MYSQL_HOST']
MYSQL_USER = configs['MYSQL_USER']
MYSQL_PASSWORD = configs['MYSQL_PASSWORD']
MYSQL_DB = configs['MYSQL_DB']

engine = None
try:
    engine = make_connection(MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB)
    init_tables(engine)
except Exception as e:
    print(e)
    exit(1)


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if 'x-access-token' in request.cookies:
        token = request.cookies['x-access-token']
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            resp = make_response(render_template('index.html', msg=msg))
            return resp
        except jwt.DecodeError:
            print('decodeerrr')
            return jsonify({'message': 'Token is missing'}), 401

        except jwt.exceptions.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
    else:
        pass

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        account = check_one_user(username, password, engine)
        if account:
            token = create_access_token(username, app.config['SECRET_KEY'])
            print("++++++++++++++++++++++ ANOTHER LOGIN +++++++++++++++++++++++", token)
            msg = 'Logged in successfully !'
            resp = make_response(render_template('index.html', msg=msg), 200)
            resp.set_cookie('x-access-token', token.encode('UTF_8'),
                            expires=datetime.datetime.utcnow() + datetime.timedelta(days=1))
            return resp

        else:
            msg = 'Incorrect username / password !'
    return render_template('login.html', msg=msg)


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        account = get_one_user(username, email, engine)
        if account:
            msg = 'Account Or Email already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers !'
        elif not username or not password or not email:
            msg = 'Please fill out the form !'
        else:
            add_user(username, email, password, engine)
            msg = 'You have successfully registered !'
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg=msg)


if __name__ == '__main__':
    app.run(use_reloader=True, host='0.0.0.0', threaded=True)
