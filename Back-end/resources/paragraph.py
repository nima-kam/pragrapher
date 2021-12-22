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
from db_models.paragraph import change_impression, get_paragraph_reply
from tools.string_tools import gettext


class paragraph(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def patch(self, current_user, c_name):

        req_data = request.json
        try:
            print(req_data['p_id'])
        except:
            msg = gettext("paragraph_id_needed")
            return {'message': msg}, hs.BAD_REQUEST
        parag = get_one_paragraph(req_data['p_id'], self.engine)

        print("\n\n\n\n\n\n\n\n\n here1 \n\n\\n\n\n\n\n\n\n")
        if parag is None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND
        if parag.community_name != c_name:
            msg = gettext("paragraph_not_in_community")
            return {'message': msg}, hs.BAD_REQUEST

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

        parag: paragraph_model = get_one_paragraph(
            req_data['p_id'], self.engine)

        if role == 2:
            if parag.user_id != current_user.id:
                (jsonify(message=gettext("permission_denied")), 403)

        if parag is None:
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
        cm = add_paragraph(req_data['text'], req_data['ref'], current_user.id, current_user.name, comu.id, comu.name,
                           tags, author, self.engine, avatar=current_user.image)
        print(cm, "\n\n\n\n\n\n\n")

        p_link = get_paragraph_link(p_id=cm["id"], c_name=cm["community_name"])

        add_notification_to_subcribed(comu, req_data['text'], p_link, self.engine)
        return make_response(jsonify(message=gettext("paragraph_add_success"), res=cm), 200)

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
        print("\n\n\n\n\n\n\n", ref, "\n\n\n\n\n\n\n")
        tags = req_data.get('tags', None)

        parag: paragraph_model = get_one_paragraph(
            req_data['p_id'], self.engine)
        if parag is None:
            msg = gettext("paragraph_not_found")
            return make_response({'message': msg}, hs.NOT_FOUND)

        role = get_role(current_user.id, parag.community_id, self.engine)
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)
        if parag.user_id != current_user.id:
            return make_response(jsonify(message=gettext("permission_denied")), 403)
        else:
            edit_paragraph(parag.id, req_data.get("text"),
                           ref, tags, author, self.engine)
            msg = gettext("paragraph_edited_success")
            return make_response(jsonify(message=msg), hs.ACCEPTED)

        # return (jsonify(message=gettext("permission_denied")), 403)


def get_paragraph_link(p_id, c_name):
    return gettext("link_front_paragraph").format(p_id=p_id, c_name=c_name)


class impression(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def put(self, current_user, c_name):
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
    def patch(self, current_user, c_name):
        req_data = request.json
        try:
            print(req_data['p_id'])
        except:
            msg = gettext("paragraph_id_needed")
            return {'message': msg}, hs.BAD_REQUEST
        parag = get_one_paragraph(req_data['p_id'], self.engine)
        if parag is None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND
        res = make_response(jsonify(parag.json))
        return res

    @authorize
    def post(self, current_user, c_name):
        req_data = request.json
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
        if parag is None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND
        cm = add_reply(current_user, comu.id, comu.name,
                       parag.id, req_data['text'], self.engine)
        print("\n\n\n comments is : ", cm, "\b\n\n\b")
        return make_response(jsonify(message=gettext("paragraph_reply_add_success"), reply=cm), hs.OK)


class paragraph_reply(Resource):

    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user, p_id, c_name):
        req_data = request.args
        print("\n nnnn00000000000\n\n\n")
        try:
            start: int = int(req_data.get("start_off", 0))
            end: int = int(req_data.get("end_off", 10))
        except:
            return {"message": "start"}, hs.BAD_REQUEST

        comu = get_community(c_name, self.engine)
        if comu is None:
            return make_response(jsonify(message=gettext("community_not_found")), 401)
        role = get_role(current_user.id, comu.id, self.engine)
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)

        parag = get_one_paragraph(paragraph_id=p_id, engine=self.engine)

        if parag is None:
            msg = gettext("paragraph_not_found")
            return {'message': msg}, hs.NOT_FOUND

        reps = get_paragraph_reply(p_id, start, end, engine=self.engine)

        return {"replies": reps}, hs.OK
