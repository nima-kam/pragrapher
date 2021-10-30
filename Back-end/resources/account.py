from flask_restful import Resource
from flask import request, redirect, make_response, url_for, jsonify, render_template
import jwt
from app import engine, authorize, app
from db_models.users import get_one_user, add_user, change_pass, edit_fname
from tools.string_tools import gettext


class myprofile(Resource):

    @authorize
    def get(self, current_user):
        """:return current user info"""
        print(current_user)
        req_data = request.json
        make_response(jsonify(current_user.json))
        return render_template('profile.html', data=current_user)

    @authorize
    def post(self, current_user):
        """insert or change current user fname"""
        print(current_user)
        req_data = request.json
        edit_fname(current_user, req_data['fname'], engine)
        return redirect(url_for("myprofile"))


class password(Resource):

    @authorize
    def put(self, current_user):
        """change current_user password"""
        req_data = request.json
        res = change_pass(current_user, req_data['old_password'], req_data['new_password'], engine)
        if res:
            return redirect(url_for("logout"))
        else:
            return jsonify(message=gettext("wrong_pass"))
