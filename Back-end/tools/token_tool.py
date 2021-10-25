from flask import Flask, jsonify, make_response, request
from functools import wraps
from db_models.users import get_one_user
import jwt
import datetime


def check_auth(secret_key, engine):
    if 'x-access-token' in request.cookies:
        token = request.cookies['x-access-token']
        try:
            data = jwt.decode(token, secret_key, algorithms=["HS256"])
            account = get_one_user(data['name'], data['email'], engine)
            return jsonify({'message': 'User is available',
                            "account": account}), 200
        except jwt.DecodeError:
            print('decodeerrr')
            return jsonify({'message': 'Token is missing'}), 401

        except jwt.exceptions.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
    else:
        return jsonify({'message': 'Not Logged In'}), 401




def login_required(secret_key, engine):
    def func_taker(f):
        """
        decorator for urls that need authentication
        :param f: f(current_user, *args, **kwargs) the current_user in input is the user in token
        :return:
        """

        @wraps(f)
        def decorator(*args, **kwargs):
            token = None
            if 'x-access-tokens' in request.cookies:
                token = request.cookies['x-access-tokens']

                if not token:
                    return jsonify({'message': ' token is missing'}), 401

                try:
                    data = jwt.decode(token, secret_key, algorithms=["HS256"])
                    current_user = get_one_user(data.get("name"), data.get('email'), engine=engine)
                    if current_user is None:
                        return jsonify({"message": "User is missing"}), 401

                except jwt.DecodeError:
                    print('decode_error')
                    return jsonify({'message': 'Token is missing'}), 401

                except jwt.exceptions.ExpiredSignatureError:
                    return jsonify({'message': 'Token has expired'}), 401

                return f(current_user, *args, **kwargs)
            else:
                return jsonify({'message': 'Not Logged In'}), 401

        return decorator


def create_access_token(name, email, SECRET_KEY, valid_days: float = 1):
    token = jwt.encode(
        {'name': name, 'email': email, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=valid_days)},
        SECRET_KEY, "HS256")
    return token
