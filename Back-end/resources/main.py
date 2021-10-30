from flask_restful import Resource
from flask import request, redirect, make_response, url_for, jsonify
import jwt
import datetime
from app import engine, authorize, app
from db_models.users import get_one_user, add_user, check_one_user,UserModel
from tools.token_tool import create_access_token
from tools.string_tools import gettext


class login(Resource):

    @classmethod
    def post(cls):
        msg = ''
        print('cookies:', request.cookies)
        if 'x-access-token' in request.cookies:
            token = request.cookies['x-access-token']
            try:
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
                current_user:UserModel = get_one_user(data.get("name"), data.get('email'), engine=engine)
                msg = 'congragulation'
                if current_user is None:
                    return redirect(url_for('logout'))
                return {"message": gettext("user_already_logged_in").format(username=current_user.name)}, 200
            except jwt.DecodeError:
                print('decodeerrr')
                redirect(url_for("logout"))

            except jwt.exceptions.ExpiredSignatureError:
                redirect(url_for("logout"))
        try:
            req_data = request.get_json()
            if 'username' in req_data and 'password' in req_data:
                username = req_data['username']
                password = req_data['password']
                account = check_one_user(username, password, engine)
                if account:
                    email = account.email
                    token = create_access_token(username, email, app.config['SECRET_KEY'])
                    print("++++++++++++++++++++++ ANOTHER LOGIN +++++++++++++++++++++++", token)
                    msg = gettext("user_logged_in").format(username=username)
                    resp = make_response(jsonify(message=msg, token=token), 200)
                    resp.set_cookie('x-access-token', token.encode('UTF_8'),
                                    expires=datetime.datetime.utcnow() + datetime.timedelta(days=1))
                    print('\n\n', token.encode('UTF_8'))
                    return resp

                else:
                    return {'message': gettext("user_not_found")}, 401

        except Exception as e:
            print(e)
            return {'message': 'Something Wrong'}, 401
