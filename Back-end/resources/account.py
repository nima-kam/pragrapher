from flask_restful import Resource
from flask import request, redirect, make_response, url_for, jsonify
import jwt
from app import engine, authorize, app
from db_models.users import get_one_user, add_user


class myprofile(Resource):

    @classmethod
    @authorize
    def get(cls, current_user):
        pass

