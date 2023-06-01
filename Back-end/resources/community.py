import os
from http import HTTPStatus as hs
from flask_restful import Resource, reqparse
from flask import request, redirect, make_response, url_for, jsonify
from typing import List, Tuple, Dict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_models.paragraph import paragraph_model

from db_models.users import get_one_user, UserModel
from tools.db_tool import engine, make_session
from tools.image_tool import get_extension
from tools.token_tool import authorize, community_role

from db_models.community import add_community, add_community_member, change_community_data, change_community_image, \
    change_community_member_subscribe, get_community, get_community_member_subscribe, get_role, \
    community_model, delete_member, CommunityGroup, GroupUserRelation, CategoryModel, CommunityLikeUser
from db_models.community import community_member as cmm
from db_models.book import book_model
from tools.string_tools import gettext

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sender_email = 'karina.allahveran@gmail.com'
password = 'jzeffzksfzmsvnfv'


class EmailDiscountToTopUsers(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, _: UserModel):
        session: Session = make_session(self.engine)
        community_ = session.query(community_model).order_by(community_model.like_count).first()
        for i in community_.members:
            receiver_email = i.member.email
            subject = 'Discount Code From Pragrapher!'
            message = f'You have discount code because of' \
                      f' being in top community, your discount code: {request.json["discount_code"]}'

            try:
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = receiver_email
                msg['Subject'] = subject

                msg.attach(MIMEText(message, 'plain'))

                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login(sender_email, password)
                    server.send_message(msg)

            except Exception as e:
                return {'message': 'Error sending email', 'details': str(e)}

        return {'message': 'emails send successfully to users of top community'}, hs.OK


class LikeCommunity(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def put(self, current_user: UserModel, community_name: str):
        session: Session = make_session(self.engine)
        community_record: community_model = session.query(community_model).filter(
            community_model.name == community_name).first()
        like_user_record = session.query(CommunityLikeUser).filter(
            CommunityLikeUser.community_name == community_name and CommunityLikeUser.user_id == current_user.id).first()
        if like_user_record:
            return {'message': 'you have liked this community before'}, hs.NOT_ACCEPTABLE
        session.add(CommunityLikeUser(community_name=community_name, user_id=current_user.id))
        if not community_record:
            return {'message': f'could not find the community with name {community_name}'}, hs.BAD_REQUEST
        community_record.like_count += 1
        session.commit()
        return {
            'message': f'community {community_name} liked successfully, total likes = {community_record.like_count}'}


class CreateCategory(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, _: UserModel, community_name: str):
        body = request.json
        try:
            session: Session = make_session(self.engine)
            session.add(
                CategoryModel(community_name=community_name, name=body['name'], description=body['description']))
            session.commit()
            session.flush()
        except IntegrityError as e:
            return {'error': 'duplicated category'}, hs.BAD_REQUEST
        return {'message': f'category {body["name"]} created successfully for community {community_name}'}


class GetTopCommunities(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, _: UserModel):
        session: Session = make_session(self.engine)
        communities: List[community_model] = session.query(community_model).order_by(community_model.like_count).all()
        return {
            'communities': [
                {
                    'community_name': c.name,
                    'community_id': c.id,
                    'like_count': c.like_count
                } for c in communities
            ]
        }, hs.OK


class GetGroupDetails(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user, group):
        session = make_session(self.engine)
        _group = session.query(CommunityGroup).filter(CommunityGroup.name == group).first()
        if _group is None:
            return {'message': 'group does not exist'}, hs.NOT_FOUND
        members = session.query(GroupUserRelation).filter(GroupUserRelation.group == group).all()
        detailed_members = [
            {'id': member.user, 'name': session.query(UserModel).filter(UserModel.id == member.user).first().name}
            for member in members
        ]

        return {
            'members': detailed_members,
            'name': _group.name,
            'community': _group.community
        }, hs.OK


class AddMeToGroup(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def put(self, current_user):
        body = request.json
        if 'group' not in body:
            return {'message': 'group is not specified correctly'}, hs.BAD_REQUEST
        session = make_session(self.engine)
        group = body['group']
        _group = session.query(CommunityGroup).get(group)
        if _group is None:
            return {'message': 'specified group does not exist'}, hs.NOT_FOUND
        relation = GroupUserRelation(current_user.id, group)
        try:
            session.add(relation)
            session.commit()
        except IntegrityError:
            session.rollback()
            return {'message': 'you already is added to this group'}, hs.ALREADY_REPORTED
        return {'message': 'you are added to the target group successfully'}, hs.OK


class CreateGroup(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, current_user):
        body = request.json
        if 'name' not in body:
            return {'message': 'group name is not specified correctly'}, hs.BAD_REQUEST
        if 'community' not in body:
            return {'message': 'community id is not specified correctly'}, hs.BAD_REQUEST
        community_name = body['community']
        group_name = body['name']

        session = make_session(self.engine)
        _community = session.query(community_model).filter(community_model.name == community_name).first()
        if _community is None:
            return {'message': 'community does not exist'}, hs.NOT_FOUND
        group = CommunityGroup(group_name, community_name)
        try:
            session.add(group)
            session.commit()
        except IntegrityError:
            session.rollback()
            return {'message': 'this group already exist'}, hs.ALREADY_REPORTED
        return {'message': 'community group created successfully'}, hs.OK


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
            paragraph_model.community_name == c_name).order_by(paragraph_model.ima_count.desc()).slice(start,
                                                                                                       end).all()

        res = []
        for row in coms:
            res.append(row.json)

        return res

    def search_community_paragraphs(self, c_name: str, start, end):
        session = make_session(self.engine)

        coms: List[paragraph_model] = session.query(paragraph_model).filter(
            paragraph_model.community_name == c_name).order_by(paragraph_model.date.desc()).slice(start,
                                                                                                  end).all()

        res = []
        for row in coms:
            res.append(row.json)

        return res


class show_community(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user):
        res = self.get_user_community_list(current_user)
        return make_response(jsonify(res))

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
    @community_role(1, 2)
    def get(self, current_user, name, req_community, mem_role):
        comu = req_community

        if comu is None:
            msg = gettext("community_not_found")
            return {'message': msg}, hs.NOT_FOUND
        # role = get_role(current_user.id, comu.id, self.engine)
        role = mem_role
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)
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
        return {'res': res}, 200

    @authorize
    def post(self, current_user, name):
        print("\n\n\n HELL AWAITS 1 \n\n\n")
        req_data = request.json
        # try:
        #     print(req_data['name'])
        # except:
        #     msg = gettext("community_name_needed")
        #     return {'message': msg}, hs.BAD_REQUEST
        try:
            print(req_data['username'])
        except:
            msg = gettext("user_name_needed")
            return {'message': msg}, hs.BAD_REQUEST
        # check if community name not repeated **
        # comu = get_community(req_data['name'], self.engine)
        print("\n\n\n HELL AWAITS 2 \n\n\n")
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
        print("\n\n\n HELL AWAITS 3.75 {} \n\n\n".format(user.json))
        role = get_role(user.id, comu.id, self.engine)
        print("\n\n\n HELL AWAITS 4 \n\n\n")
        if role != -1:
            return {'message': gettext("user_username_exists")}, 401
        cm = add_community_member(comu.id, user, 2, comu.name, self.engine)
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
        # req_data = request.get_json()
        start = 1
        end = 6
        # try:
        #     start = req_data["start_off"]
        #     end = req_data["end_off"]
        # except:
        #     return {
        #         "message": gettext("search_item_needed").format("start_off and end_off both")
        #     }, hs.BAD_REQUEST

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
