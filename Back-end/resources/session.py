from flask_restful import Resource
from flask import request, redirect, make_response, url_for, session, jsonify
import jwt
import datetime
import re
from config import jwt_secret_key
from resources import account
from db_models.users import get_one_user, add_user, check_one_user, UserModel
from tools.mail_tools import send_mail
from tools.token_tool import create_access_token, authorize
from tools.string_tools import gettext


class login(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    def post(self):
        print("enter login with request", request.json)
        msg = ''
        if 'x-access-token' in request.cookies:
            token = request.cookies['x-access-token']
            try:
                data = jwt.decode(token, jwt_secret_key, algorithms=["HS256"])
                current_user: UserModel = get_one_user(data.get("name"), data.get('email'), engine=self.engine)
                print('cookies:', request.cookies)
                if current_user is None:
                    return redirect(url_for('logout'))
                return {"message": gettext("user_already_logged_in").format(username=current_user.name)}, 200
            except jwt.DecodeError:
                redirect(url_for("logout"))

            except jwt.exceptions.ExpiredSignatureError:
                redirect(url_for("logout"))
        try:
            req_data = request.get_json()
            if 'username' in req_data and 'password' in req_data:
                username = req_data['username']
                password = req_data['password']

                account: UserModel = check_one_user(username, password, self.engine)

                if account:
                    email = account.email
                    token = create_access_token(username, email, jwt_secret_key)
                    print("++++++++++++++++++++++ ANOTHER LOGIN +++++++++++++++++++++++", token)
                    msg = gettext("user_logged_in").format(username=username)
                    resp = make_response(jsonify(message=msg, token=token), 200)
                    resp.set_cookie('x-access-token', token.encode('UTF_8'),
                                    expires=datetime.datetime.utcnow() + datetime.timedelta(days=1))
                    print('\n\n', token.encode('UTF_8'))
                    return resp

                else:
                    return {'message': gettext("wrong_username_pass")}, 401

        except Exception as e:
            print("error", e)
            return {'message': 'Something Wrong'}, 401


class register(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']
        self.mail = kwargs['mail']
        self.mail_username = kwargs['mail_username']

    def post(self):
        print("in register post:", request.json)
        msg = ''
        req_data = request.get_json()
        if 'username' in req_data and 'password' in req_data and 'email' in req_data:
            username = req_data['username']
            password = req_data['password']
            email = req_data['email']
            account = get_one_user(username, email, self.engine)
            if account:
                msg = gettext("user_email_username_exists")
                return {'message': msg}, 401

            elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                msg = gettext("wrong_email_format")
                return {'message': msg}, 401

            elif not re.match(r'^[A-Za-z0-9_-]*$', username):
                msg = gettext("wrong_username_format")
                return {'message': msg}, 401

            elif not username or not password or not email:
                msg = 'Please fill out the form !'
                return jsonify({'message': msg}), 401

            else:
                add_user(username, email, password, self.engine)
                send_mail(self.mail, self.mail_username, [email], 'email_verfication.html',
                          'google.com')
                msg = gettext("user_registered")
                return {'message': msg}, 200

        else:
            msg = 'Please fill out the form !'
        response = make_response(jsonify(message=msg))
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


class logout(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    def get(self):
        session.pop('loggedin', None)
        session.pop('id', None)
        session.pop('username', None)
        resp = make_response(jsonify(message=gettext("user_logged_out")), 200)
        resp.set_cookie('x-access-token', '',
                        expires=0)
        return resp


class refresh_login(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, current_user: UserModel):
        email = current_user.email
        username = current_user.name
        token = create_access_token(username, email, jwt_secret_key)
        print("++++++++++++++++++++++ REFRESH LOGIN +++++++++++++++++++++++", token)

        msg = gettext("user_logged_in").format(username=username)
        resp = make_response(jsonify(message=msg, username=username, token=token), 200)
        resp.set_cookie('x-access-token', token.encode('UTF_8'),
                        expires=datetime.datetime.utcnow() + datetime.timedelta(days=1))
        print('\n\n', token.encode('UTF_8'))
        return resp
