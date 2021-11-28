import os
from http import HTTPStatus as hs
from flask_restful import Resource, reqparse
from flask import request, make_response, jsonify
from db_models.paragraph import add_paragraph, add_reply, delete_paragraph, get_impression, get_one_paragraph, \
    paragraph_model, edit_paragraph
from db_models.users import UserModel
from tools.db_tool import engine
from tools.image_tool import get_extension
from tools.token_tool import authorize, community_role

from db_models.community import get_community, get_role, add_notification_to_subcribed
from db_models.paragraph import change_impression
from tools.string_tools import gettext


class paragraph(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def patch(self, current_user, c_name):

        print("\n\n\n\n\n\n\n\n\n here www\n\n\\n\n\n\n\n\n\n")
        req_data = request.json
        try:
            print(req_data['p_id'])
        except:
            msg = gettext("paragraph_id_needed")
            return {'message': msg}, hs.BAD_REQUEST
        print("\n\n\n\n\n\n\n\n\n here \n\n\\n\n\n\n\n\n\n")
        parag = get_one_paragraph(req_data['p_id'], self.engine)

        print("\n\n\n\n\n\n\n\n\n here1 \n\n\\n\n\n\n\n\n\n")
        if parag == None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND
        if parag.community_name != c_name:
            msg = gettext("paragraph_not_in_community")
            return {'message': msg}, hs.BAD_REQUEST

        print("\n\n\n\n\n\n\n\n\n here 3\n\n\\n\n\n\n\n\n\n")
        res = make_response(jsonify(parag.json))
        return res

    @authorize
    def delete(self, current_user, c_name):
        req_data = request.json
        try:
            print(req_data['p_id'])
        except:
            msg = gettext("paragraph_id_needed")
            return {'message': msg}, hs.BAD_REQUEST

        # check if community name not repeated **
        comu = get_community(c_name, self.engine)
        if comu is None:
            return make_response(jsonify(message=gettext("community_not_found")), 401)
        role = get_role(current_user.id, comu.id, self.engine)
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)

        parag: paragraph_model = get_one_paragraph(req_data['p_id'], self.engine)

        if role == 2:
            if parag.user_id != current_user.id:
                (jsonify(message=gettext("permission_denied")), 403)

        if parag == None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND
        cm = delete_paragraph(parag.id, self.engine)
        return jsonify(message=gettext("paragraph_delete_success"))

    @authorize
    def post(self, current_user: UserModel, c_name):
        req_data = request.json
        tags = ""
        author = ""

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

        tags = req_data.get('tags', None)
        author = req_data.get('author', current_user.name)

        # check if community name not repeated **
        comu = get_community(c_name, self.engine)
        if comu is None:
            return make_response(jsonify(message=gettext("community_not_found")), 401)

        role = get_role(current_user.id, comu.id, self.engine)
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)
        cm = add_paragraph(req_data['text'], req_data['ref'], current_user.id, comu.id, comu.name, tags, author,
                           self.engine)
        print(cm, "\n\n\n\n\n\n\n")
        add_notification_to_subcribed(comu, req_data['text'], self.engine)
        return make_response(jsonify(message=gettext("paragraph_add_success"),res=cm), 200)

    @authorize
    def put(self, current_user: UserModel, c_name):
        req_data = request.json

        try:
            print(req_data['text'])
            print(req_data['p_id'])
        except:
            msg = gettext("paragraph_item_needed").format("p_id and text")
            return make_response({'message': msg}, hs.BAD_REQUEST)

        ref = req_data.get("ref", None)
        author = req_data.get("author", None)

        tags = req_data.get('tags', None)

        parag: paragraph_model = get_one_paragraph(req_data['p_id'], self.engine)
        if parag is None:
            msg = gettext("paragraph_not_found")
            return make_response({'message': msg}, hs.NOT_FOUND)

        role = get_role(current_user.id, parag.community_id, self.engine)
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)
        if parag.user_id != current_user.id:
            return make_response(jsonify(message=gettext("permission_denied")), 403)
        else:
            edit_paragraph(parag.id, req_data.get("text"), ref, tags, author, self.engine)
            msg = gettext("paragraph_edited_success")
            return make_response(jsonify(message=msg), hs.ACCEPTED)

        # return (jsonify(message=gettext("permission_denied")), 403)


class impression(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def put(self, current_user , c_name):
        req_data = request.json

        try:
            print(req_data['p_id'])
        except:
            msg = gettext("paragraph_id_needed")
            return {'message': msg}, hs.BAD_REQUEST

        # check if community name not repeated **

        parag = get_one_paragraph(req_data['p_id'], self.engine)
        if parag == None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND
        comu = get_community(parag.community_name, self.engine)
        if comu is None:
            return make_response(jsonify(message=gettext("community_not_found")), 401)
        if comu.name != c_name:
            return make_response(jsonify(message=gettext("paragraph_not_in_community")), 401)

        role = get_role(current_user.id, comu.id, self.engine)
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)
        cm = get_impression(current_user, parag.id, self.engine)
        return jsonify(message=cm)

    @authorize
    def post(self, current_user, c_name):
        req_data = request.json

        try:
            print(req_data['p_id'])
        except:
            msg = gettext("paragraph_id_needed")
            return {'message': msg}, hs.BAD_REQUEST

        # check if community name not repeated **

        parag = get_one_paragraph(req_data['p_id'], self.engine)
        if parag == None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND
        comu = get_community(parag.community_name, self.engine)
        if comu is None:
            return make_response(jsonify(message=gettext("community_not_found")), 401)
        if comu.name != c_name:
            return make_response(jsonify(message=gettext("paragraph_not_in_community")), 401)

        role = get_role(current_user.id, comu.id, self.engine)
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)
        cm = change_impression(current_user, parag.id, self.engine)
        return jsonify(message=gettext("paragraph_impression_change_success"))


class reply(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user, c_name):
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
    def post(self, current_user, c_name):
        req_data = request.json
        # try:
        #     print(req_data['c_name'])
        # except:
        #     msg = gettext("community_name_needed")
        #     return {'message': msg}, hs.BAD_REQUEST
        try:
            print(req_data['p_id'])
        except:
            msg = gettext("paragraph_id_needed")
            return {'message': msg}, hs.BAD_REQUEST
        try:
            print(req_data['text'])
        except:
            msg = gettext("paragraph_text_needed")
            return {'message': msg}, hs.BAD_REQUEST

        # check if community name not repeated **
        comu = get_community(c_name, self.engine)
        if comu is None:
            return make_response(jsonify(message=gettext("community_not_found")), 401)
        role = get_role(current_user.id, comu.id, self.engine)
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)
        parag = get_one_paragraph(req_data['p_id'], self.engine)
        if parag == None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND
        cm = add_reply(current_user, comu.id, parag.id, req_data['text'], self.engine)
        return jsonify(message=gettext("paragraph_reply_add_success"))
