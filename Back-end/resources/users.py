import os
from flask_restful import Resource
from flask import request, redirect, make_response, url_for, jsonify, render_template
from http import HTTPStatus as hs
import jwt
from sqlalchemy.orm.base import NOT_EXTENSION
from config import jwt_secret_key
from tools.db_tool import engine
from tools.image_tool import get_extension
from tools.mail_tools import send_mail
from tools.token_tool import authorize

from db_models.users import change_user_image, edit_bio, get_notifications, get_one_user, add_user, change_pass, \
    edit_fname, edit_dob, \
    UserModel, delete_expired_notifications, get_by_username
from db_models.paragraph import paragraph_model, get_user_paragraphs
from tools.string_tools import gettext
from typing import Union, Dict, Tuple, List


class public_profile(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user: UserModel, u_name):
        u = get_by_username(u_name, self.engine)
        if u is None:
            msg = gettext("user_not_found")
            return {"message": msg}, hs.NOT_FOUND

        return {"profile": u.public_json}, hs.OK
