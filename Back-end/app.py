from genericpath import exists
import os
from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
from functools import wraps
from config import init_config
from tools.db_tool import init_tables, make_session, make_connection
from db_models.users import add_user, check_one_user, edit_fname, get_one_user
### pip install PyJWT to prevent error
import jwt
import re
import datetime
from tools.image_tool import get_extension, is_filename_safe

from tools.token_tool import create_access_token, login_required

app = Flask(__name__)

app.config.update(
    DEBUG=True,
    SECRET_KEY="carbon_secret",
    SESSION_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_HTTPONLY=True,
    UPLOAD_FOLDER=os.path.join(app.root_path, "static/uploads/")
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
@app.route('/login', methods=['GET', 'POST'], endpoint="login")
def login():
    msg = ''
    if 'x-access-token' in request.cookies:
        token = request.cookies['x-access-token']
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            resp = make_response(render_template('index.html', msg=msg), 200)
            return resp
        except jwt.DecodeError:
            # print('decodeerrr')
            redirect(url_for("logout"))
            # return jsonify({'message': 'Token is missing'}), 401

        except jwt.exceptions.ExpiredSignatureError:
            redirect(url_for("logout"))
            # return jsonify({'message': 'Token has expired'}), 401

    req_data = request.get_json()
    if request.method == 'POST' and 'username' in req_data and 'password' in req_data:
        username = req_data['username']
        password = req_data['password']
        account = check_one_user(username, password, engine)
        email = account.email
        if account:
            token = create_access_token(username, email, app.config['SECRET_KEY'])
            print("++++++++++++++++++++++ ANOTHER LOGIN +++++++++++++++++++++++", token)
            msg = 'Logged in successfully !'
            resp = make_response(render_template('index.html', msg=msg), 200)
            resp.set_cookie('x-access-token', token.encode('UTF_8'),
                            expires=datetime.datetime.utcnow() + datetime.timedelta(days=1))
            return resp

        else:
            msg = 'Incorrect username / password !'
    return render_template('login.html', msg=msg)


@app.route('/logout', endpoint="logout")
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    resp = make_response(redirect(url_for('login')), 200)
    resp.set_cookie('x-access-token', '',
                    expires=0)
    return resp


@app.route('account/upload/pp', methods=['POST', 'GET'], endpoint="uploadpp")
@login_required(app.config['SECRET_KEY'], engine)
def uploadPp(current_user):
    if request.method == 'POST':
        files = request.files
        file = files.get('file')
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'file': 'No Part File'
            })
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            return jsonify({
                'success': False,
                'file': 'No Selected File'
            })
        if file and is_filename_safe(file.filename):
            try:
                os.makedirs(app.config['UPLOAD_FOLDER'] + '/pp/', exist_ok=True)
            except:
                pass
            file.save(app.config['UPLOAD_FOLDER'] + '/pp/' + str(current_user.id) + get_extension(file.filename))
        # return jsonify({
        #     'success': True,
        #     'file': 'Received'
        # })
        return redirect('/profile')
    else:
        return render_template('profile.html', data=current_user), 200


@app.route('/account/myprofile', methods=['GET', 'POST'], endpoint="myprofile")
@login_required(app.config['SECRET_KEY'], engine)
def myprofile(current_user):
    print(current_user)
    req_data = request.json
    if request.method == 'POST':
        edit_fname(current_user, req_data['fname'], engine)
        return redirect(url_for("myprofile"))
    else:
        return render_template('profile.html', data=current_user)


@app.route('/register', methods=['GET', 'POST'],endpoint="register")
def register():
    msg = ''
    code: int = 401
    req_data = request.get_json()
    if request.method == 'POST' and 'username' in req_data and 'password' in req_data and 'email' in req_data:
        username = req_data['username']
        password = req_data['password']
        email = req_data['email']
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
            code = 200
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg=msg), code


if __name__ == '__main__':
    app.run(use_reloader=True, host='0.0.0.0', threaded=True)
