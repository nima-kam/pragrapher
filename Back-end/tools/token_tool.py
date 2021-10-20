from flask import Flask, jsonify, make_response, request
from functools import wraps
from db_models.users import get_one_user
import jwt
import datetime
 
# set to database engine
db_engine = None


# def login_required(f):
#     """
#     decorator for urls that need authentication
#     :param f: f(current_user, *args, **kwargs) the current_user in input is the user in token
#     :return:
#     """

#     @wraps(f)
#     def decorator(*args, **kwargs):
#         token = None
#         if 'x-access-tokens' in request.headers:
#             token = request.headers['x-access-tokens']

#         if not token:
#             return jsonify({'message': 'a valid token is missing'})
#         try:
#             data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
#             current_user = get_one_user(None, data.get('email'), engine=db_engine)
#         except:
#             return jsonify({'message': 'token is invalid'})

#         return f(current_user, *args, **kwargs)

#     return decorator


def create_access_token(name,SECRET_KEY, valid_days: float = 1):
    token = jwt.encode(
        {'name': name, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=valid_days)},
        SECRET_KEY, "HS256")
    return token
