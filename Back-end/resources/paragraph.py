import os
from http import HTTPStatus as hs
from flask_restful import Resource, reqparse
from flask import request, make_response, jsonify
from db_models.paragraph import add_paragraph, get_one_paragraph
from db_models.users import get_one_user
from tools.db_tool import engine
from tools.image_tool import get_extension
from tools.token_tool import authorize

from db_models.community import  get_community, get_role
from db_models.paragraph import change_impression
from tools.string_tools import gettext


class paragraph(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self , current_user):
        req_data = request.json
        try:
            print(req_data['p_id'])
        except:
            msg = gettext("paragraph_id_needed")
            return {'message': msg}, hs.BAD_REQUEST
        parag = get_one_paragraph(req_data['p_id'], self.engine)
        if parag == None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND
        res = make_response(jsonify(parag.json))
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
        if comu is None:
            return make_response(jsonify(message=gettext("community_not_found")), 401)
        role = get_role(current_user.id , comu.id , self.engine)
        if role == -1:
            return make_response(jsonify(message = gettext("permission_denied")) , 403)
        print("\n\n here22 \n\n")
        
        cm= add_paragraph(req_data['text'],req_data['ref'] , current_user.id,comu.id, self.engine)
        return jsonify(message=gettext("paragraph_add_success"))



class impression(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self , current_user):
        req_data = request.json
        try:
            print(req_data['p_id'])
        except:
            msg = gettext("paragraph_id_needed")
            return {'message': msg}, hs.BAD_REQUEST
        parag = get_one_paragraph(req_data['p_id'], self.engine)
        if parag == None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND
        res = make_response(jsonify(parag.json))
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
            print(req_data['p_id'])
        except:
            msg = gettext("paragraph_id_needed")
            return {'message': msg}, hs.BAD_REQUEST

        # check if community name not repeated **
        comu = get_community(req_data['c_name'], self.engine)
        if comu is None:
            return make_response(jsonify(message=gettext("community_not_found")), 401)
        role = get_role(current_user.id , comu.id , self.engine)
        if role == -1:
            return make_response(jsonify(message = gettext("permission_denied")) , 403)
        parag = get_one_paragraph(req_data['p_id'], self.engine)
        if parag == None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND
        cm= change_impression(current_user ,parag , self.engine)
        print("impression : " , cm)
        return jsonify(message=gettext("paragraph_impression_change_success"))