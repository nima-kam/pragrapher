from genericpath import exists
import os
from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
from functools import wraps
from config import init_config
from tools.db_tool import init_tables, make_session, make_connection
from db_models.users import add_user, change_image, change_pass, check_one_user, edit_fname, get_one_user, UserModel
### pip install PyJWT to prevent error
import jwt
import re
import datetime
from flask_cors import CORS
from tools.image_tool import get_extension, is_filename_safe

from tools.token_tool import create_access_token, login_required

app = Flask(__name__)

app.config.update(
    DEBUG=True,
    SECRET_KEY="carbon_secret",
    SESSION_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_HTTPONLY=True,
    UPLOAD_FOLDER=os.path.join('', "static/uploads/")
)

configs = init_config()
MYSQL_HOST = configs['MYSQL_HOST']
MYSQL_USER = configs['MYSQL_USER']
MYSQL_PASSWORD = configs['MYSQL_PASSWORD']
MYSQL_DB = configs['MYSQL_DB']

CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
engine = None
try:
    engine = make_connection(MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB)
    init_tables(engine)
except Exception as e:
    print(e)
    exit(1)


def authorize(f):
    @wraps(f)
    def decorated_function(*args, **kws):
        token = None
        cookies = request.cookies.to_dict(flat=False)

        if cookies.get('x-access-token') is not None:
            token = request.cookies['x-access-token']
            if not token:
                return jsonify({'message': ' token is missing'}), 401

            try:
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
                current_user = get_one_user(data.get("name"), data.get('email'), engine=engine)
                if current_user is None:
                    return jsonify({"message": "User is missing"}), 401

            except jwt.DecodeError:
                print('decode_error')
                return jsonify({'message': 'Token is missing'}), 401

            except jwt.exceptions.ExpiredSignatureError:
                return jsonify({'message': 'Token has expired'}), 401

            return f(current_user, *args, **kws)
        else:
            return jsonify({'message': 'Not Logged In'}), 401

    return decorated_function


@app.route('/login', methods=['GET', 'POST'], endpoint="login")
def login():
    msg = ''
    print('444', request.cookies)
    if 'x-access-token' in request.cookies:
        token = request.cookies['x-access-token']
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = get_one_user(data.get("name"), data.get('email'), engine=engine)
            msg = 'congragulation'
            if current_user is None:
                return redirect(url_for('logout'))
            resp = make_response(redirect('profile.html'), 200)
            return jsonify({"message": "authorized already"}), 200
        except jwt.DecodeError:
            print('decodeerrr')
            redirect(url_for("logout"))
            # return jsonify({'message': 'Token is missing'}), 401

        except jwt.exceptions.ExpiredSignatureError:
            redirect(url_for("logout"))
            # return jsonify({'message': 'Token has expired'}), 401
    try:
        req_data = request.get_json()
        if request.method == 'POST' and 'username' in req_data and 'password' in req_data:
            username = req_data['username']
            password = req_data['password']
            account = check_one_user(username, password, engine)
            if account:
                email = account.email
                token = create_access_token(username, email, app.config['SECRET_KEY'])
                print("++++++++++++++++++++++ ANOTHER LOGIN +++++++++++++++++++++++", token)
                msg = 'Logged in successfully !'
                resp = make_response(jsonify({"message": msg, "token": token}), 200)
                resp.set_cookie('x-access-token', token.encode('UTF_8'),
                                expires=datetime.datetime.utcnow() + datetime.timedelta(days=1))
                print('\n\n', token.encode('UTF_8'))
                return resp

            else:
                return jsonify({'message': 'Incorrect username / password !'}), 401

    except Exception as e:
        print(e)
        return jsonify({'message': 'Something Wrong'}), 401
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


@app.route('/account/upload/pp', methods=['POST', 'GET'], endpoint="uploadpp")
@authorize
def uploadPp(current_user: UserModel):
    if request.method == 'POST':
        files = request.files
        file = files.get('file')

        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'file': 'No Part File'
            }), 400
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            return jsonify({
                'success': False,
                'file': 'No Selected File'
            }), 400
        if file:
            try:
                os.makedirs(app.config['UPLOAD_FOLDER'] + '/pp/', exist_ok=True)
            except:
                pass
            url = app.config['UPLOAD_FOLDER'] + '/pp/' + str(current_user.id) + get_extension(file.filename)
            try:
                os.remove(url)
            except:
                pass
            file.save(url)
            print('uuuu', url)
            change_image(current_user, url, engine)
        # return jsonify({
        #     'success': True,
        #     'file': 'Received'
        # })
        return redirect(url_for("myprofile")), 200
    else:
        return render_template('profile.html', data=current_user), 200


@app.route('/account/changepassword', methods=['GET', 'POST'], endpoint="changepassword")
@authorize
def change_password(current_user: UserModel):
    req_data = request.json
    if request.method == 'POST':
        res = change_pass(current_user, req_data['old_password'], req_data['new_password'], engine)
        if res:
            return redirect(url_for("logout"))
        else:
            return jsonify('wrong password')


@app.route('/account/myprofile', methods=['GET', 'POST'], endpoint="myprofile")
@authorize
def myprofile(current_user: UserModel):
    print(current_user)
    req_data = request.json
    if request.method == 'POST':
        edit_fname(current_user, req_data['fname'], engine)
        return redirect(url_for("myprofile"))
    else:
        make_response(jsonify(current_user.json))
        return render_template('profile.html', data=current_user)


@app.route('/register', methods=['GET', 'POST'], endpoint="register")
def register():
    msg = ''
    req_data = request.get_json()
    if request.method == 'POST' and 'username' in req_data and 'password' in req_data and 'email' in req_data:
        username = req_data['username']
        password = req_data['password']
        email = req_data['email']
        account = get_one_user(username, email, engine)
        if account:
            msg = 'Account Or Email already exists !'
            return jsonify({'message': msg}), 401

        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
            return jsonify({'message': msg}), 401

        elif not re.match(r'^[A-Za-z0-9_-]*$', username):
            msg = 'Username must contain only characters and numbers !'
            return jsonify({'message': msg}), 401

        elif not username or not password or not email:
            msg = 'Please fill out the form !'
            return jsonify({'message': msg}), 401

        else:
            add_user(username, email, password, engine)
            msg = 'You have successfully registered !'
            return jsonify({'message': msg}), 200

    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    response = jsonify({"message": msg})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
    # return jsonify({"message": msg}), 200


if __name__ == '__main__':
    app.run(use_reloader=True, host='0.0.0.0', threaded=True)
