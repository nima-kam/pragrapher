import datetime
import os
import time
from http import HTTPStatus as hs
from flask_restful import Resource
import sqlalchemy as db
from flask import request, make_response, jsonify
from sqlalchemy.sql.elements import Null
from sqlalchemy.sql.expression import null
from db_models.book import add_book, change_book_image, get_one_book, edit_book, book_model, delete_book, \
    check_reserved_book, user_reserved_count
from db_models.paragraph import add_paragraph, add_reply, delete_paragraph, get_impression, get_one_paragraph, \
    paragraph_model, edit_paragraph
from db_models.users import UserModel, add_notification, get_one_user
from tools.db_tool import engine
from tools.image_tool import get_extension
from tools.token_tool import authorize, community_role
from tools.db_tool import make_session

from db_models.community import get_community, get_role, add_notification_to_subcribed
from db_models.paragraph import change_impression

from resources.payment import add_credit

from tools.string_tools import gettext
from typing import List


class get_user_books(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, current_user: UserModel):
        session = make_session(self.engine)
        req_data = request.json

        try:
            start: int = int(req_data["start_off"])
            end: int = int(req_data["end_off"])
            print("start ", start, "   end   ", end)
        except:
            msg = gettext("search_item_needed").format("start_off and end_off")
            return {"message": msg}, hs.BAD_REQUEST

        books: List[book_model] = session.query(book_model).filter(book_model.seller_id == current_user.id).order_by(
            book_model.modified_time.desc()).slice(start, end)

        res = []
        for b in books:
            if b.reserved == False:
                res.append(b.json)
        return {"message": gettext("book_found"), "books": res}, hs.OK


class book(Resource):
    """add a book for sell and edit or delete it"""

    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def patch(self, current_user: UserModel, c_name):
        """get the community all books info"""
        req_date = request.args
        try:
            start: int = int(req_date["start_off"])
            end: int = int(req_date["end_off"])
            print("start ", start, "   end   ", end)
        except:
            msg = gettext("search_item_needed").format("start_off and end_off")
            return {"message": msg}, hs.BAD_REQUEST
        try:
            min_price: int = (req_date.get("min", 0))
            max_price: int = (req_date.get("max", 100000000))
            sort: str = req_date.get("sort", "date")
        except:
            msg = gettext("search_item_optional").format("min/max price and sort by")
            return {"message": msg}, hs.BAD_REQUEST

        res = self.get_books(community_name=c_name, start=start, end=end, min_price=min_price, max_price=max_price,
                             sort_by=sort, current_user=current_user)

        return {"message": gettext("book_found"), "books": res}, hs.OK

    @authorize
    def post(self, current_user: UserModel, c_name):
        print("jjjjjjjjjjjjjjjjjjjj")
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
        add_notification(current_user.id, current_user.email, "کتاب{}به فروشگاه اضافه شد".format(req_data['name']),
                         "کتاب جدید اضافه شد", "/community/{}/ShowBook/{}".format(comu.name, cm['id']), self.engine)
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
        if cbook is None:
            return {"message": gettext("book_not_found")}, hs.NOT_FOUND
        if cbook.seller_id == current_user.id:
            book_js = edit_book(cbook, b_name, genre, author, price=price, description=desc, engine=self.engine)
            msg = gettext("book_edit_success")
            return {"message": msg, "book": book_js}, hs.OK
        else:
            return make_response(jsonify(message=gettext("permission_denied")), 403)

    @authorize
    def delete(self, current_user, c_name):
        req_data = request.json
        b_id = None
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
            cbook = get_one_book(book_id=b_id, community_name=c_name, engine=self.engine)
            if cbook != None:
                return make_response(jsonify(message=gettext("book_not_found")), 404)

            if current_user.id == cbook.seller_id:
                delete_book(cbook)
                msg = gettext("store_item_delete").format("Book")
                return {"message": msg}, hs.OK
            else:
                return make_response(jsonify(message=gettext("permission_denied")), 403)

    def get_books(self, community_name, start, end, min_price=0, max_price: int = None, sort_by="date",
                  current_user=None):
        session = make_session(self.engine)
        update_reserved_bytime(session)

        print("st type ", type(start))
        if max_price is None:
            if sort_by == "date":
                books: List[book_model] = session.query(book_model).filter(db.and_(
                    db.and_(book_model.community_name == community_name, book_model.price > min_price),
                    book_model.reserved is False)) \
                    .order_by(book_model.modified_time.desc()).slice(start, end)


        else:
            if sort_by == "date":
                books: List[book_model] = session.query(book_model).filter(
                    db.and_(book_model.community_name == community_name
                            , book_model.price > min_price, book_model.price < max_price)) \
                    .order_by(book_model.modified_time.desc()).slice(start, end)
        res = []
        for b in books:
            if b.reserved is False:  # and b.reserved_by != current_user.id
                dic = b.json
                if current_user is not None:
                    dic["editable"] = (b.seller_id == current_user.id)
                res.append(dic)
        return res


class book_buy(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, current_user: UserModel, c_name):
        req_data = request.json
        session = make_session(self.engine)

        try:
            b_id = req_data["book_id"]
        except:
            msg = gettext("book_item_needed").format("book_id")
            return {'message': msg}, hs.BAD_REQUEST

        cbook: book_model = session.query(book_model).filter(
            db.and_(book_model.id == b_id, book_model.community_name == c_name)).first()
        if cbook is None:
            return {"message": gettext("book_not_found")}, hs.NOT_FOUND
        if cbook.price > current_user.credit:
            return make_response(jsonify(message=gettext("book_not_enough_credit")), 400)
        print(cbook.json)
        if cbook.buyer_id is not None:
            return make_response(jsonify(message=gettext("book_selled")), 400)
        if cbook.reserved and cbook.reserved_by != current_user.id:
            return make_response({"message": gettext("book_person_reserved")}, hs.BAD_REQUEST)

        user: UserModel = session.query(UserModel).filter(UserModel.id == cbook.seller_id).first()
        if user is None:
            return {'message': gettext("user_not_found") + "(seller user)"}, hs.NOT_FOUND

        user_credit = add_credit(self.engine, current_user.id, -1 * cbook.price, 3)  # change buyer credit
        add_credit(self.engine, cbook.seller_id, amount=cbook.price, t_type=2)  # change seller credit
        print("\n\n\n\n", current_user.credit, "\n\n\n")
        add_notification(current_user.id, current_user.email, "کتاب {} خریداری شد".format(cbook.name)
                         , "خرید موفق", cbook.id, self.engine)

        add_notification(user.id, user.email, "کتاب {} فروخته شد".format(cbook.name), "فروش موفق"
                         , cbook.id, self.engine)
        cbook.buyer_id = current_user.id
        cbook.reserved = False
        cbook.reserved_time = None
        cbook.reserved_by = None
        session.flush()
        session.commit()
        return {"message": "success", "new_credit": user_credit}


class book_picture(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, current_user, c_name):
        """insert or change current community picture"""
        b_id = None
        try:
            b_id = request.args.get('book_id')
            if b_id == None:
                msg = gettext("book_item_needed").format("book_id")

                return {'message': msg}, hs.BAD_REQUEST
            b_id = str(b_id)
        except:
            msg = gettext("book_item_needed").format("book_id")

            return {'message': msg}, hs.BAD_REQUEST

        comu = get_community(c_name, self.engine)
        if comu is None:
            return make_response(jsonify(message=gettext("community_not_found")), 404)

        role = get_role(current_user.id, comu.id, self.engine)
        if role == -1:
            return make_response(jsonify(message=gettext("permission_denied")), 403)

        cbook = get_one_book(book_id=b_id, community_name=c_name, engine=self.engine)
        if cbook == None:
            return make_response(jsonify(message=gettext("book_not_found")), 404)
        if current_user.id != cbook.seller_id:
            return make_response(jsonify(message=gettext("permission_denied")), 403)

        # role = get_role(current_user.id, comu.id, self.engine)
        files = request.files
        file = files.get('file')
        if 'file' not in request.files:
            return make_response(jsonify(message=gettext("upload_no_file")), 400)
        print("\n\n\nhere here here\n\n\n")
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            return jsonify(message=gettext("upload_no_filename")), 400
        if file:
            try:
                os.makedirs(os.getcwd() + gettext('UPLOAD_FOLDER') +
                            '/book_pp/', exist_ok=True)
            except Exception as e:
                print('error in upload ', e)
                pass
            url = gettext('UPLOAD_FOLDER') + 'book_pp/' + \
                  str(b_id) + get_extension(file.filename)
            try:
                os.remove(url)
            except:
                pass
            file.save(os.getcwd() + url)
            change_book_image(b_id, url, self.engine)
            return jsonify(message=gettext("upload_success"))


def update_reserved_bytime(session):
    b: List[book_model] = session.query(book_model).filter(True == book_model.reserved).all()
    seconds_in_day = 24 * 60 * 60
    expire = 60 * 30
    for row in b:
        now = datetime.datetime.now()
        diff = now - row.reserved_time
        if (diff.seconds + (diff.days * seconds_in_day)) >= expire:
            row.reserved_by = None
            row.reserved = False
    session.flush()
    session.commit()


class reserve_book(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']
        self.max_limit = kwargs["max_reserve"]

    @authorize
    def get(self, current_user: UserModel):
        """
        :param current_user:
        :return: current user basket
        """
        session = make_session(self.engine)
        print("before before \n\n\n")

        update_reserved_bytime(session)
        print("after after \n\n\n")
        b: List[book_model] = session.query(book_model).filter(current_user.id == book_model.reserved_by).all()
        res = []
        for row in b:
            res.append(row.json)

        if not res:
            return {"message": gettext("book_reserve_empty")}, hs.NOT_FOUND
        msg = gettext("book_found")
        return {'message': msg, "res": res}, hs.OK

    @authorize
    def post(self, current_user: UserModel):
        req_data = request.json

        try:
            b_id = req_data["id"]  # book_id
        except:
            msg = gettext("book_item_needed").format("id")
            return {'message': msg}, hs.BAD_REQUEST
        try:
            b: book_model = check_reserved_book(book_id=b_id, engine=self.engine)
        except:
            return {"message": gettext("book_not_found")}, hs.NOT_FOUND

        if b.buyer_id is not None:
            return {"message": gettext("book_selled")}, hs.BAD_REQUEST

        if b.reserved_by == current_user.id:
            new_book = self.change_reserve(b.id, current_user)
            msg = gettext("book_reserve_changed")
            return {'message': msg, "book": new_book.json}, hs.OK

        elif b.reserved:
            msg = gettext("book_person_reserved")
            return {'message': msg}, hs.BAD_REQUEST

        else:
            r_count = user_reserved_count(current_user, self.engine)
            if r_count >= self.max_limit:
                return {"message": gettext("book_reserve_limit")}, hs.BAD_REQUEST
            new_book = self.change_reserve(b.id, current_user)
            msg = gettext("book_reserve_changed")
            return {'message': msg, "book": new_book.json}, hs.OK

    def change_reserve(self, book_id, current_user):
        session = make_session(self.engine)
        session.expire_on_commit = False
        b: book_model = session.query(book_model).filter(book_id == book_model.id).first()
        print("\b\n\n\n is res  : ", b.reserved_by, " \n\n current :", current_user.id)
        if b.reserved_by == current_user.id:
            b.reserved_by = None
            b.reserved = False
        elif b.reserved:
            raise PermissionError
        else:
            b.reserved_by = current_user.id
            b.reserved = True
            b.reserved_time = datetime.datetime.now()

        session.flush()
        session.commit()
        return b

    ## it is for buy from basket (ids should be - seprated)
    @authorize
    def patch(self, current_user: UserModel):
        """ search all books reserved by the user"""
        # req_data = request.json
        session = make_session(self.engine)
        # b_ids = None
        # try:
        #     b_ids = req_data["book_id"]
        #     b_ids = b_ids.split('-')
        # except:
        #     msg = gettext("book_item_needed").format("book_id")
        #     return {'message': msg}, hs.BAD_REQUEST

        allBooks = []
        allPrice = 0
        # for b_id in b_ids:
        #     cbook: book_model = session.query(book_model).filter(book_model.id == b_id).first()
        #     if cbook == None:
        #         msg = gettext("book_not_found")
        #         return {'message': msg}, hs.BAD_REQUEST
        #     allBooks.append(cbook)
        #     allPrice += cbook.price

        allBooks: List[book_model] = session.query(book_model).filter(book_model.reserved_by == current_user.id).all()
        print("\n\n\n reserve books: ", allBooks, "\n")
        if allBooks is None or len(allBooks) == 0:
            return {"message": gettext("book_reserve_empty")}, hs.NOT_FOUND
        for b in allBooks:
            if b.buyer_id is not None:
                return {"message": gettext("book_selled")}, hs.BAD_REQUEST
            allPrice += b.price

        print("\n\n\n", allPrice, current_user.credit, '\n\n\n')

        if allPrice > current_user.credit:
            return make_response(jsonify(message=gettext("book_not_enough_credit") + '({} toman)'.format(allPrice)),
                                 400)

        for cbook in allBooks:

            if cbook.buyer_id is not None and cbook.buyer_id != null:  # ***
                return make_response(jsonify(message=gettext("book_selled")), 400)

            user: UserModel = session.query(UserModel).filter(UserModel.id == cbook.seller_id).first()
            if user is None:
                return {'message': gettext("user_not_found") + "(seller user)"}, hs.NOT_FOUND

            user_credit = add_credit(self.engine, current_user.id, -1 * cbook.price, 3)  # change buyer credit
            add_credit(self.engine, cbook.seller_id, amount=cbook.price, t_type=2)  # change seller credit
            print("\n\n\n\n", current_user.credit, "\n\n\n")
            add_notification(current_user.id, current_user.email, "کتاب {} خریداری شد".format(cbook.name), "خرید موفق"
                             , cbook.id, self.engine)

            add_notification(user.id, user.email, "کتاب {} فروخته شد".format(cbook.name),
                             "فروش موفق", cbook.id, self.engine)
            cbook.buyer_id = current_user.id
            cbook.reserved = False
            cbook.reserved_time = None
            cbook.reserved_by = None
            session.flush()
            session.commit()
        return {"message": "success", "new_credit": user_credit}

    # def get_book(self, book_id):
    #     session = make_session(self.engine)
    #     b: book_model = session.query(book_model).filter(book_id == book_model.id).first()
    #     return b


class book_info(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user, b_id):
        session = make_session(self.engine)
        b: book_model = session.query(book_model).filter(b_id == book_model.id).first()
        if b is None:
            return {"message": "NOT FOUND"}, hs.NOT_FOUND
        dic = b.json
        dic["editable"] = (b.seller_id == current_user.id)
        return {"book": dic}, hs.OK


class book_store(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user):
        req_date = request.args
        try:

            start: int = int(req_date.get("start_off", 0))
            end: int = int(req_date.get("end_off", 5))
            print("start ", start, "   end   ", end)
            # name: str = req_date.get("book_name")
            min_price: int = (req_date.get("min", 0))
            max_price: int = (req_date.get("max", 100000000))
            sort: str = req_date.get("sort", "date")
        except:
            msg = gettext("search_item_optional").format("book name, min/max price and sort by")
            return {"message": msg}, hs.BAD_REQUEST

        res = self.get_books(start=start, end=end, min_price=min_price, max_price=max_price, sort_by=sort,
                             current_user=current_user)
        if res is None:
            return {"message": gettext("book_not_found"), "res": res}, hs.NOT_FOUND
        return {"res": res}, hs.OK

    def get_books(self, start, end, min_price=0, max_price: int = None, sort_by="date", current_user=None):
        session = make_session(self.engine)
        update_reserved_bytime(session)

        print("st type ", start)
        if max_price is None:
            if sort_by == "date":
                books: List[book_model] = session.query(book_model).filter(db._and(
                    db.and_(book_model.price > min_price),
                    book_model.reserved is False)) \
                    .order_by(book_model.modified_time.desc()).slice(start, end)

        else:
            if sort_by == "date":
                books: List[book_model] = session.query(book_model).filter(
                    db.and_(book_model.price > min_price, book_model.price < max_price)) \
                    .order_by(book_model.modified_time.desc()).slice(start, end)

        res = []
        for b in books:
            if b.reserved is False or b.reserved_by == current_user.id:
                dic = b.json
                dic["editable"] = (b.seller_id == current_user.id)
                res.append(dic)
        return res


class related_paragraph(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user, b_id):
        req_date = request.args
        try:
            start: int = int(req_date.get("start_off", 0))
            end: int = int(req_date.get("end_off", 4))
        except:
            msg = gettext("search_item_optional").format("start_off and end_off")
            return {"message": msg}, hs.BAD_REQUEST

        b: book_model = self.get_book(b_id)
        if b is None:
            return {"message": "NOT FOUND"}, hs.NOT_FOUND
        related = self.get_related_book_name(b_name=b.name, start=start, end=end)

        return {"res": related}, hs.OK

    def get_book(self, b_id):
        session = make_session(self.engine)
        b: book_model = session.query(book_model).filter(b_id == book_model.id).first()
        return b

    def get_related_book_name(self, b_name, start=0, end=5):
        session = make_session(self.engine)

        paras: List[paragraph_model] = session.query(paragraph_model).filter(paragraph_model.ref_book == b_name) \
            .order_by(paragraph_model.ima_count.desc()).slice(start, end)

        res = []
        for p in paras:
            res.append(p.json)
        return res


class related_books(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user, b_id):
        req_date = request.args
        try:
            start: int = int(req_date.get("start_off", 0))
            end: int = int(req_date.get("end_off", 4))
        except:
            msg = gettext("search_item_optional").format("start_off and end_off")
            return {"message": msg}, hs.BAD_REQUEST

        b: book_model = self.get_book(b_id)
        if b is None:
            return {"message": "NOT FOUND"}, hs.NOT_FOUND
        related = self.get_related_book(genre=b.genre, author=b.author, start=start, end=end)

        return {"res": related}, hs.OK

    def get_book(self, b_id):
        session = make_session(self.engine)
        b: book_model = session.query(book_model).filter(b_id == book_model.id).first()
        return b

    def get_related_book(self, genre, author, start=0, end=5):
        session = make_session(self.engine)

        books: List[book_model] = session.query(book_model) \
            .filter(db.or_(book_model.genre == genre, book_model.author == author)) \
            .slice(start, end)

        res = []
        for p in books:
            res.append(p.json)
        return res
