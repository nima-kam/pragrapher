import os
from http import HTTPStatus as hs
from flask_restful import Resource, reqparse
from flask import request, make_response, jsonify
from db_models.book import add_book, get_one_book, edit_book, book_model, delete_book
from db_models.paragraph import add_paragraph, add_reply, delete_paragraph, get_impression, get_one_paragraph, \
    paragraph_model, edit_paragraph
from db_models.users import UserModel, add_notification
from tools.db_tool import engine
from tools.image_tool import get_extension
from tools.token_tool import authorize, community_role

from db_models.community import get_community, get_role, add_notification_to_subcribed
from db_models.paragraph import change_impression
from tools.string_tools import gettext


class book(Resource):
    """add a book for sell and edit or delete it"""

    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, current_user: UserModel, c_name):
        req_data = request.json
        # name, genre, author, community_id, community_name, description, seller_id
        try:
            print(req_data['name'])
        except:
            msg = gettext("book_item_needed").format("name")
            return {'message': msg}, hs.BAD_REQUEST
        try:
            print(req_data['genre'])
        except:
            msg = gettext("book_item_needed").format("genre")
            return {'message': msg}, hs.BAD_REQUEST
        try:
            print(req_data['author'])
        except:
            msg = gettext("book_item_needed").format("author")
            return {'message': msg}, hs.BAD_REQUEST
        try:
            print(req_data['description'])
        except:
            msg = gettext("book_item_needed").format("description")
            return {'message': msg}, hs.BAD_REQUEST
        try:
            print(req_data['price'])
        except:
            msg = gettext("book_item_needed").format("price")
            return {'message': msg}, hs.BAD_REQUEST

        # check if community name not repeated **
        comu = get_community(c_name, self.engine)
        if comu is None:
            return make_response(jsonify(message=gettext("community_not_found")), 401)

        role = get_role(current_user.id, comu.id, self.engine)
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)
        cm = add_book(req_data['name'], req_data['genre'], req_data['author'], comu.id, comu.name,
                      req_data['description'], price=req_data['price'], seller_id=current_user.id,
                      engine=self.engine)
        print(cm, "\n\n\n\n\n\n\n")
        add_notification(current_user.id, current_user.email, "کتاب{}به فروشگاه اضافه شد".format(req_data['name']),
                         "کتاب جدید اضافه شد", self.engine)
        return make_response(jsonify(message=gettext("book_add_success"), res=cm), 200)

    @authorize
    def put(self, current_user: UserModel, c_name):
        req_data = request.json
        try:
            b_id = req_data["book_id"]
        except:
            msg = gettext("book_item_needed").format("book_id")
            return {'message': msg}, hs.BAD_REQUEST
        try:
            b_name = req_data.get('name', None)
            author = req_data.get('author', None)
            desc = req_data.get('description', None)
            genre = req_data.get('genre', None)
            price = req_data.get('price', None)
        except:
            msg = gettext("book_item_needed").format("items")
            return {'message': msg}, hs.BAD_REQUEST
        #
        # comu = get_community(c_name, self.engine)
        # if comu is None:
        #     return make_response(jsonify(message=gettext("community_not_found")), 401)
        #
        # role = get_role(current_user.id, comu.id, self.engine)
        # if role == -1:
        #     return make_response(jsonify(message=gettext("permission_denied")), 403)

        cbook: book_model = get_one_book(book_id=b_id, community_name=c_name, engine=self.engine)

        if cbook.seller_id == current_user.id:
            book_js = edit_book(cbook, b_name, genre, author,price=price, description=desc, engine=self.engine)
            msg = gettext("book_edit_success")
            return {"message": msg, "book": book_js}, hs.OK
        else:
            return make_response(jsonify(message=gettext("permission_denied")), 403)

    @authorize
    def delete(self, current_user, c_name):
        req_data = request.json
        try:
            b_id = req_data["book_id"]
        except:
            msg = gettext("book_item_needed").format("book_id")
            return {'message': msg}, hs.BAD_REQUEST

        comu = get_community(c_name, self.engine)
        if comu is None:
            return make_response(jsonify(message=gettext("community_not_found")), 401)

        role = get_role(current_user.id, comu.id, self.engine)
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)

        else:
            cbook = get_one_book(book_id=b_id, community_name=c_name, engine=engine)

            if role == 1 or current_user.id == cbook.seller_id:
                delete_book(cbook)
                msg = gettext("store_item_delete").format("Book")
                return {"message": msg}, hs.OK
            else:
                return make_response(jsonify(message=gettext("permission_denied")), 403)
