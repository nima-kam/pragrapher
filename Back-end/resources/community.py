import os
from http import HTTPStatus as hs
import sqlalchemy as db
from flask_restful import Resource, reqparse
from flask import request, redirect, make_response, url_for, jsonify
from typing import List, Tuple, Dict
from db_models.paragraph import paragraph_model

from db_models.users import get_one_user
from tools.db_tool import engine, make_session
from tools.image_tool import get_extension
from tools.token_tool import authorize, community_role

from db_models.community import add_community, add_community_member, change_community_data, change_community_image, \
    change_community_member_subscribe, get_community, get_community_member_subscribe, get_role, \
    community_model, delete_member, add_notification_for_new_join
from db_models.community import community_member as cmm
from db_models.book import book_model
from tools.string_tools import gettext


class community(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user, name):
        comu = get_community(name, self.engine)
        if comu is None:
            msg = gettext("community_not_found")
            return {'message': msg}, hs.NOT_FOUND
        res = make_response(jsonify(comu.json))
        return res

    @authorize
    def patch(self, current_user, name):
        start = 0
        end = 4
        parags = self.search_community_best_paragraphs(name, start, end)
        res = make_response(jsonify(parags))
        return res

    @authorize
    @community_role(1, 2)
    def put(self, current_user, name, req_community, mem_role):
        start = 0
        end = 0
        req_data = request.json
        try:
            print(req_data['start_off'])
            start = int(req_data['start_off'])
        except:
            msg = gettext("search_item_needed").format("start_off")
            return {'message': msg}, hs.BAD_REQUEST

        try:
            print(req_data['end_off'])
            end = int(req_data['end_off'])

        except:
            msg = gettext("search_item_needed").format("end_off")
            return {'message': msg}, hs.BAD_REQUEST
        parags = self.search_community_paragraphs(name, start, end)
        res = make_response(jsonify(parags))
        return res

    def search_community_best_paragraphs(self, c_name: str, start, end):
        session = make_session(self.engine)

        coms: List[paragraph_model] = session.query(paragraph_model).filter(
            db.and_(paragraph_model.replied_id == "",
                    paragraph_model.community_name == c_name)) \
            .order_by(paragraph_model.ima_count.desc()).slice(start, end).all()

        res = []
        for row in coms:
            res.append(row.json)

        return res

    def search_community_paragraphs(self, c_name: str, start, end):
        session = make_session(self.engine)

        coms: List[paragraph_model] = session.query(paragraph_model).filter(
            db.and_(paragraph_model.replied_id == "",
                    paragraph_model.community_name == c_name)).order_by(
            paragraph_model.date.desc()).slice(start, end).all()

        res = []
        for row in coms:
            res.append(row.json)

        return res


class community_admin(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    @community_role(1, 2)
    def get(self, current_user, name, req_community, mem_role):
        return jsonify(message=mem_role == 1)

    @authorize
    @community_role(1)
    def delete(self, current_user, name, req_community, mem_role):
        print("\n\n\nhere here \n\n\n")
        req_data = request.json
        try:
            print(req_data['username'])
        except:
            msg = gettext("user_name_needed")
            return {'message': msg}, hs.BAD_REQUEST
        user = get_one_user(req_data['username'], "-", self.engine)
        if user is None:
            return {'message': gettext("user_not_found")}, hs.NOT_FOUND
        print("what you want" , user.json)
        role = get_role(user.id, req_community.id, self.engine)
        if role == -1:
            return {'message': gettext("user_not_found")}, 404
        delete_member(user.id, req_community.id, self.engine)
        return {"message": gettext("user_left_successfully").format(req_community.name)}, hs.OK
        

class show_community(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user):
        """return user communities"""
        res = self.get_user_community_list(current_user)
        return make_response(jsonify(res), hs.OK)

    def get_user_community_list(self, current_user):
        session = make_session(self.engine)
        print("\n\n\n here \n\n\n")

        coms: List[cmm] = session.query(cmm).filter(
            cmm.m_id == current_user.id).all()
        res = []
        for row in coms:
            x: community_model = session.query(community_model).filter(
                community_model.id == row.c_id).first()
            res.append(x.json)

        return res


class create_community(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, current_user):
        req_data = request.json
        name = ""
        bio = ""
        try:
            print(req_data["name"])
            name = req_data["name"]
        except:
            return {"message": gettext("community_name_needed")}, hs.BAD_REQUEST

        try:
            print(req_data["bio"])
            bio = req_data["bio"]
        except:
            return {"message": gettext("community_bio_needed")}, hs.BAD_REQUEST

        # check if community name not repeated **
        comu = get_community(name, self.engine)
        if comu is not None:
            return make_response(jsonify(message=gettext("community_name_exist")), 401)
        cm = add_community(name, bio, current_user, self.engine)
        return jsonify(message=gettext("community_add_success"), res=cm.json)


class community_member(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    @community_role(-1)
    def get(self, current_user, name, req_community, mem_role):
        comu = req_community

        if comu is None:
            msg = gettext("community_not_found")
            return {'message': msg}, hs.NOT_FOUND
        # role = get_role(current_user.id, comu.id, self.engine)
        role = mem_role
        # if role == -1:
            # return make_response(jsonify(message=gettext("permission_denied")), 403)
        members = comu.get_members_json()
        res = make_response(jsonify(members), hs.OK)
        return res

    @authorize
    @community_role(1, 2)
    def put(self, current_user, name, req_community, mem_role):
        """
        for subscribing a community
        :param current_user:
        :param name:
        :param req_community:
        :param mem_role:
        :return:
        """
        comu = req_community
        if comu is None:
            return {'message': gettext("community_not_found")}, hs.NOT_FOUND
        change_community_member_subscribe(
            current_user, req_community, self.engine)
        return {'message': gettext("community_member_subscribe_changed")}, 200

    @authorize
    @community_role(1, 2)
    def patch(self, current_user, name, req_community, mem_role):
        comu = req_community
        if comu is None:
            return {'message': gettext("community_not_found")}, hs.NOT_FOUND
        res = get_community_member_subscribe(
            current_user, req_community, self.engine)
        return {'res': res, "message": "subscribe status"}, 200

    @authorize
    def post(self, current_user, name):
        print("\n\n\n post com_mem HELL AWAITS 1 \n\n\n")
        req_data = request.json
        try:
            print(req_data['username'])
        except:
            msg = gettext("user_name_needed")
            return {'message': msg}, hs.BAD_REQUEST
        # check if community name not repeated **
        # comu = get_community(req_data['name'], self.engine)
        session = make_session(self.engine)
        comu: community_model = session.query(community_model).filter(
            community_model.name == name).first()
        if comu is None:
            return {'message': gettext("community_not_found")}, hs.NOT_FOUND
        print("\n\n\n HELL AWAITS 3 \n\n\n")
        user = get_one_user(req_data['username'], "-", self.engine)
        print("\n\n\n HELL AWAITS 3.5 \n\n\n")
        if user is None:
            return {'message': gettext("user_not_found")}, hs.NOT_FOUND
        if user.id != current_user.id:
            return {'message':gettext("permission_denied")}
        print("\n\n\n HELL AWAITS 3.75 {} \n\n\n".format(user.json))
        role = get_role(user.id, comu.id, self.engine)
        print("\n\n\n HELL AWAITS 4 \n\n\n")
        if role != -1:
            return {'message': gettext("user_username_exists")}, 401
        cm = add_community_member(comu.id, user, 2, comu.name, self.engine)
        print("\n\n\n HELL AWAITS 5 \n\n\n")

        add_notification_for_new_join(comu, user, self.engine)
        return make_response(jsonify(message=gettext("community_member_add_success")))


class community_leave(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    @community_role(1, 2)
    def delete(self, current_user, name, req_community: community_model, mem_role):
        if mem_role == 2:
            delete_member(current_user.id, req_community.id, self.engine)
            return {"message": gettext("user_left_successfully")}, hs.OK

        return {"message": gettext("permission_denied")}, hs.BAD_REQUEST


class community_picture(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    @community_role(1)
    def post(self, current_user, name, req_community, mem_role):
        """insert or change current community picture"""
        req_data = request.form

        comu = req_community

        if comu == None:
            msg = gettext("community_not_found")
            return {'message': msg}, 402
        # role = get_role(current_user.id, comu.id, self.engine)
        role = mem_role
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
                os.makedirs(os.getcwd() + gettext('UPLOAD_FOLDER') +
                            '/community_pp/', exist_ok=True)
            except Exception as e:
                print('error in upload ', e)
                pass
            url = gettext('UPLOAD_FOLDER') + 'community_pp/' + \
                  str(name) + get_extension(file.filename)
            try:
                os.remove(url)
            except:
                pass
            file.save(os.getcwd() + url)
            change_community_image(current_user, name, url, self.engine)
            return jsonify(message=gettext("upload_success"))


class community_data(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    @community_role(1)
    def post(self, current_user, name, req_community: community_model, mem_role):
        """change community description and public/private """

        desc = ""
        isPrivate = False
        req_data = request.json
        try:
            print(req_data["description"])
            desc = req_data["description"]
        except:
            msg = gettext("item_not_found").format("description")
            return {'message': msg}, hs.BAD_REQUEST

        try:
            print(req_data["is_private"])
            isPrivate = req_data["is_private"]
        except:
            msg = gettext("item_not_found").format("is_private")
            return {'message': msg}, hs.BAD_REQUEST

        return change_community_data(req_community.name, desc, isPrivate, self.engine)


class best_community(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user):
        """return 5 best community"""
        req_data = request.args
        start = 0
        end = 6
        try:
            start: int = int(req_data.get("start_off", 0))
            end: int = int(req_data.get("end_off", 6))
        except:
            msg = gettext("search_item_optional").format("start_off and end_off")
            return {"message": msg}, hs.BAD_REQUEST

        res = self.get_best_community(start, end)
        return res

    def get_best_community(self, start, end):
        session = make_session(self.engine)

        coms: List[community_model] = session.query(community_model).order_by(community_model.member_count.desc()) \
            .slice(start, end).all()
        res = []
        for c in coms:
            res.append(c.json)
        return res
