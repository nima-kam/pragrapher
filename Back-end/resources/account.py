from flask_restful import Resource
from flask import request, redirect, make_response, url_for, jsonify, render_template
import jwt
from config import jwt_secret_key
from tools.db_tool import engine
from tools.token_tool import authorize

from db_models.users import get_one_user, add_user, change_pass, edit_fname
from tools.string_tools import gettext



class myprofile(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']
    @authorize
    def get(self, current_user):
        """:return current user info"""
        print(current_user)
        req_data = request.json
        res = make_response(jsonify(current_user.json))
        return res

    @authorize
    def post(self, current_user):
        """insert or change current user fname"""
        print(current_user)
        req_data = request.json
        edit_fname(current_user, req_data['fname'], self.engine)
        return redirect(url_for("myprofile"))


class password(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']
    @authorize
    def post(self, current_user):
        """change current_user password"""
        req_data = request.json
        res = change_pass(current_user, req_data['old_password'], req_data['new_password'], self.engine)
        if res:
            return redirect(url_for("logout"))
        else:
            return jsonify(message=gettext("wrong_pass"))
