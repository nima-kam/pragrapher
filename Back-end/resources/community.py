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


class community(Resource):
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
            print(req_data['name'])
        except:
            msg = gettext("community_name_needed")
            return {'message': msg}, hs.BAD_REQUEST
        # check if community name not repeated **
        comu = get_community(req_data['name'], self.engine)
        if comu is not None:
            return make_response(jsonify(message=gettext("community_name_exist")), 401)
        cm= add_community(req_data['name'], current_user.id, self.engine)
        return jsonify(message=gettext("community_add_success"))

class community_member(Resource):
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
        role = get_role(current_user.id , comu.id , self.engine)
        if role == -1:
            return make_response(jsonify(message = gettext("permission_denied")) , 403)
        members = comu.get_members_json()
        res = make_response(jsonify(members))
        return res

    @authorize
    def post(self, current_user):
        req_data = request.json
        try:
            print(req_data['name'])
        except:
            msg = gettext("community_name_needed")
            return {'message': msg}, hs.BAD_REQUEST
        try:
            print(req_data['username'])
        except:
            msg = gettext("user_name_needed")
            return {'message':msg} , hs.BAD_REQUEST
        # check if community name not repeated **
        comu = get_community(req_data['name'], self.engine)
        if comu is None:
            return {'message':gettext("community_not_found")}, hs.NOT_FOUND
        user = get_one_user(req_data['username'] , "-" , self.engine)
        if user is None:
            return {'message':gettext("user_not_found")}, hs.NOT_FOUND
        role = get_role(current_user.id, comu.id, self.engine)
        if role != -1:
            return {'message':gettext("user_username_exists")} , 401
        cm= add_community_member(comu.id , user.id , 2 , self.engine)
        return jsonify(message=gettext("community_member_add_success"))


class community_picture(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, current_user):
        """insert or change current community picture"""
        req_data = request.form
        try:
            print(req_data['name'])
        except:
            msg = gettext("community_name_needed")
            return {'message': msg}, 500
        comu = get_community(req_data['name'], self.engine)
        if comu == None:
            msg = gettext("community_not_found")
            return {'message': msg}, 402
        role = get_role(current_user.id, comu.id, self.engine)
        if role != 1:
            msg = gettext("permission_denied")
            return {'message': msg}, 403
        files = request.files
        file = files.get('file')
        if 'file' not in request.files:
            return jsonify(message=gettext("upload_no_file")), 400
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            return jsonify(message=gettext("upload_no_filename")), 400
        if file:
            try:
                os.makedirs(os.getcwd() + gettext('UPLOAD_FOLDER') + '/community_pp/', exist_ok=True)
            except Exception as e:
                print('error in upload ', e)
                pass
            url = gettext('UPLOAD_FOLDER') + 'community_pp/' + str(req_data['name']) + get_extension(file.filename)
            try:
                os.remove(url)
            except:
                pass
            file.save(os.getcwd() + url)
            change_community_image(current_user, req_data['name'], url, self.engine)
            return jsonify(message=gettext("upload_success"))