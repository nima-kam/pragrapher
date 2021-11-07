import os
from http import HTTPStatus as hs
from flask_restful import Resource, reqparse
from flask import request, redirect, make_response, url_for, jsonify, render_template
from db_models.users import get_one_user
from tools.db_tool import engine
from tools.image_tool import get_extension
from tools.token_tool import authorize

from db_models.community import add_community, add_community_member, change_community_image, get_community, get_role
from tools.string_tools import gettext


class paragraph(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user):
        req_data = request.json
        try:
            print(req_data['name'])
        except:
            msg = gettext("community_name_needed")
            return {'message': msg}, hs.BAD_REQUEST
        comu = get_community(req_data['name'], self.engine)
        if comu == None:
            msg = gettext("community_not_found")
            return {'message': msg}, hs.NOT_FOUND
        res = make_response(jsonify(comu.json))
        return res

    @authorize
    def post(self, current_user):
        req_data = request.json
        try:
            print(req_data['c_name'])
        except:
            msg = gettext("community_name_needed")
            return {'message': msg}, hs.BAD_REQUEST
        try:
            print(req_data['text'])
        except:
            msg = gettext("paragraph_text_needed")
            return {'message': msg}, hs.BAD_REQUEST
        try:
            print(req_data['ref'])
        except:
            msg = gettext("paragraph_ref_needed")
            return {'message': msg}, hs.BAD_REQUEST

        # check if community name not repeated **
        comu = get_community(req_data['c_name'], self.engine)
        if comu is not None:
            return make_response(jsonify(message=gettext("community_name_exist")), 401)
        role = get_role(current_user.id , comu.id , self.engine)
        if role == -1:
            return make_response(jsonify(message = gettext("permission_denied")) , 403)
        cm= add_community(req_data['name'], current_user.id, self.engine)
        return jsonify(message=gettext("community_add_success"))