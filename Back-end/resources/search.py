from http import HTTPStatus as hs
from typing import List

from flask import request, make_response
from flask_restful import Resource
from sqlalchemy import or_, and_

from db_models.book import book_model
from db_models.community import community_member, community_model
from db_models.paragraph import paragraph_model, POD
from db_models.users import UserModel
from tools.db_tool import make_session
from tools.string_tools import gettext
from tools.token_tool import authorize, community_role


class suggestion(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def put(self, current_user):
        typer = ''
        text = ''
        try:
            typer = request.args.get('type')
            if typer == None:
                msg = gettext("search_item_needed").format("type")

                return {'message': msg}, hs.BAD_REQUEST
            typer = str(typer)
        except:
            msg = gettext("search_item_needed").format("type")

            return {'message': msg}, hs.BAD_REQUEST
        try:
            text = request.args.get('text')
            if text == None:
                text = ""
            text = str(text)
        except:
            text = ""

        if typer == "tag":
            res = self.suggest_tag(text=text)

        elif typer == "author":
            res = self.suggest_author(text=text)

        elif typer == "book":
            res = self.suggest_book(text=text)

        else:
            msg = gettext("search_type_invalid")
            return {'message': msg}, hs.NOT_FOUND
        return make_response({"message": "item founded", 'res': res}, hs.OK)

    def suggest_book(self, text):
        session = make_session(self.engine)

        coms: List[paragraph_model] = session.query(paragraph_model).filter(
            paragraph_model.ref_book.like("%{}%".format(text))).order_by(paragraph_model.ima_count.desc()) \
            .slice(0, 4).all()

        authors: List[book_model] = session.query(book_model).filter(
            book_model.name.like("%{}%".format(text))).order_by(book_model.modified_time.desc()) \
            .slice(0, 4).all()

        res = []
        for row in coms:
            if text == "" or row.ref_book.startswith(text):
                res.append(row.ref_book)

        for row in authors:
            if text == "" or row.name.startswith(text):
                res.append(row.name)
        return res

    def suggest_author(self, text):
        session = make_session(self.engine)

        coms: List[paragraph_model] = session.query(paragraph_model).filter(
            paragraph_model.author.like("%{}%".format(text))).order_by(paragraph_model.ima_count.desc()) \
            .slice(0, 4).all()

        authors: List[book_model] = session.query(book_model).filter(
            book_model.author.like("%{}%".format(text))).order_by(book_model.modified_time.desc()) \
            .slice(0, 4).all()

        res = []
        for row in coms:
            if text == "" or row.author.startswith(text):
                res.append(row.author)

        for row in authors:
            if text == "" or row.author.startswith(text):
                res.append(row.author)
        return res

    def suggest_tag(self, text):
        session = make_session(self.engine)

        coms: List[paragraph_model] = session.query(paragraph_model).filter(
            paragraph_model.tags.like("%{}%".format(text))).order_by(paragraph_model.ima_count.desc()) \
            .slice(0, 4).all()

        res = []
        for row in coms:
            tags = row.tags
            tags = tags.split(',')
            for tag in tags:
                if text == "":
                    print(tag)
                    res.append(tag)
                else:
                    if tag.startswith(text):
                        res.append(tag)
        return res


class searcher(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def put(self, current_user):
        typer = ''
        text = ''
        try:
            typer = request.args.get('type')
            if typer is None:
                msg = gettext("search_item_needed").format("type")

                return {'message': msg}, hs.BAD_REQUEST
            typer = str(typer)
        except:
            msg = gettext("search_item_needed").format("type")

            return {'message': msg}, hs.BAD_REQUEST
        try:
            text = request.args.get('text')
            if text is None:
                msg = gettext("search_item_needed").format("text")

                return {'message': msg}, hs.BAD_REQUEST
            text = str(text)
        except:
            msg = gettext("search_item_needed").format("text")
            return {'message': msg}, hs.BAD_REQUEST

        print("$$$", text)
        req_data = request.json
        start = None
        end = None
        tags = None
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

        try:
            print(req_data['tags'])
            tags = req_data['tags']

        except:
            pass

        if tags != None:
            try:
                tags = str(tags)
                tags = tags.split(',')
            except:
                msg = gettext("tag_format_invalid")
                return {'message': msg}, hs.BAD_REQUEST

        allComs = self.get_user_community_list(current_user)

        if typer == "community":
            res = self.search_community(text=text, start=start, end=end)

        elif typer == "author":
            res = self.search_author(text=text, start=start, end=end, allComs=allComs)

        elif typer == "book":
            res = self.search_book(text=text, start=start, end=end, allComs=allComs, tags=tags)

        elif typer == "store":
            res = self.search_store(text=text, start=start, end=end)

        else:
            msg = gettext("search_type_invalid")
            return {'message': msg}, hs.NOT_FOUND
        return make_response({"message": "item founded", 'res': res}, hs.OK)

    def search_store(self, text: str, start, end):
        session = make_session(self.engine)

        coms: List[book_model] = session.query(book_model).filter(
            book_model.name.like("%{}%".format(text))) \
            .order_by(book_model.modified_time.desc()) \
            .slice(start, end).all()

        res = []
        for row in coms:
            if row.buyer_id is None:
                res.append(row.json)

        return res

    def search_community(self, text: str, start, end):
        session = make_session(self.engine)

        coms: List[community_model] = session.query(community_model).filter(
            community_model.name.like("%{}%".format(text))).order_by(community_model.member_count.desc()) \
            .slice(start, end).all()

        res = []
        for row in coms:
            res.append(row.json)

        return res

    def get_user_community_list(self, current_user):
        session = make_session(self.engine)

        coms: List[community_member] = session.query(community_member).filter(
            community_member.m_id == current_user.id).all()
        res = []
        for row in coms:
            res.append(row.c_id)

        return res

    def search_author(self, text, start, end, allComs):
        session = make_session(self.engine)

        coms: List[paragraph_model] = session.query(paragraph_model).filter(
            and_(paragraph_model.author.like("%{}%".format(text)), paragraph_model.replied_id == "")) \
            .order_by(paragraph_model.ima_count.desc()) \
            .slice(start, end).all()

        res = []
        for row in coms:
            if row.community_id in allComs:
                res.append(row.json)

        return res

    def search_book(self, text, start, end, allComs, tags):
        session = make_session(self.engine)
        # search paragraph books
        coms = []
        if tags is not None and len(tags) > 0:
            filters = [paragraph_model.tags.like("%{}%".format(tag)) for tag in tags]
            coms: List[paragraph_model] = session.query(paragraph_model).filter(and_(
                paragraph_model.ref_book.like("%{}%".format(text)), or_(*filters))).order_by(
                paragraph_model.ima_count.desc()) \
                .slice(start, end).all()
        else:
            coms: List[paragraph_model] = session.query(paragraph_model).filter(
                paragraph_model.ref_book.like("%{}%".format(text))).order_by(paragraph_model.ima_count.desc()) \
                .slice(start, end).all()

        res = []
        for row in coms:
            if row.community_id in allComs:
                res.append(row.json)

        return res


class community_searcher(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user, name):
        session = make_session(self.engine)
        comu = session.query(community_model).filter(community_model.name == name).first()
        if comu is None:
            return {'message': gettext("community_not_found")}, hs.NOT_FOUND
        admin = session.query(community_member).filter(
            and_(community_member.c_id == comu.id, community_member.role == 1)).first()
        coms: List[community_member] = session.query(community_member).filter(
            community_member.m_id == admin.m_id).slice(0, 10).all()
        res = []
        for row in coms:
            temp = session.query(community_model).filter(community_model.id == row.c_id).first()
            res.append(temp.json)

        return make_response({"message": "item founded", 'res': res}, hs.OK)

    @authorize
    @community_role(1, 2)
    def put(self, current_user, name, req_community: community_model, mem_role):

        try:
            text: str = request.args.get('text', "")
            if text is None or text == "":
                msg = gettext("search_item_needed").format("text")

                return {'message': msg}, hs.BAD_REQUEST
        except:
            msg = gettext("search_item_needed").format("text")
            return {'message': msg}, hs.BAD_REQUEST

        try:
            s_type: str = request.args.get('type', "")
            if s_type is None or s_type == "":
                msg = gettext("search_item_needed").format("type")

                return {'message': msg}, hs.BAD_REQUEST

        except:
            msg = gettext("search_item_needed").format("type")
            return {'message': msg}, hs.BAD_REQUEST

        req_data = request.json
        start = None
        end = None
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

        if s_type == 'paragraph':
            res = self.search_community_paragraph(text, req_community, start, end)
        elif s_type == 'store':
            res = self.search_community_book(text=text, current_user=current_user, community=req_community, start=start,
                                             end=end)
        return make_response({"message": "item founded", 'res': res}, hs.OK)

    def search_community_paragraph(self, text, community: community_model, start_off=1, end_off=201):
        session = make_session(self.engine)
        print("")
        paras: List[paragraph_model] = session.query(paragraph_model).filter(
            and_(paragraph_model.community_id == community.id,
                 or_(paragraph_model.replied_id == ""),
                 or_(paragraph_model.author.like("%{}%".format(text)),
                     paragraph_model.ref_book.like("%{}%".format(text)))
                 )).order_by(paragraph_model.date).slice(start_off, end_off).all()

        res = []
        for p in paras:
            res.append(p.json)
            print(p.json)

        return res

    def search_community_book(self, text, current_user: UserModel, community: community_model, start=0, end=51):
        session = make_session(self.engine)

        books: List[book_model] = session.query(book_model).filter(
            and_(book_model.community_id == community.id,
                 book_model.name.like("%{}%".format(text)))) \
            .slice(start, end)

        res = []
        for b in books:
            dic = b.json
            dic["editable"] = b.seller_id == current_user.id
            dic["reservable"] = not b.reserved or b.reserved_by == current_user.id
            res.append(dic)
        return res


class pod_searcher(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    def put(self):
        date = None
        try:
            req_data = request.json
            start = req_data["start_off"]
            end = req_data["end_off"]
            if request.args is not None:
                date = request.args.get("date", None)
            else:
                return {"message": gettext("search_item_needed").format("date")}, hs.BAD_REQUEST
            if date is None:
                return {"message": gettext("search_item_needed").format("date")}, hs.BAD_REQUEST

        except:
            return {"message": gettext("search_item_needed").format("start_off and end_off")}, hs.BAD_REQUEST
        print("\n\n\n\gggggg\n\n\n\n")

        # wrong right
        tdate = ""
        p = date.split("-")
        tdate = f"{p[0]}-0{p[1]}-0{p[2]}"
        print("\n\n\n\ntdatd;dd;slf ", tdate)
        date = tdate

        self.update_pod(date)
        res = self.search_pod(date=date, start_off=start, end_off=end)
        print('res  ', res)
        return {"res": res}, hs.OK

    def get_all_community_list(self):
        session = make_session(self.engine)

        coms: List[community_model] = session.query(community_model).all()
        res = []
        for row in coms:
            res.append(row.id)

        return res

    def add_pod(self, date, parag, session):
        jwk_user = POD(date=date, paragraph=parag)
        session.add(jwk_user)
        session.commit()

    def update_pod(self, date):

        allComs = self.get_all_community_list()
        session = make_session(self.engine)
        pointer = 0
        for c_id in allComs:
            current_pod: POD = session.query(POD).filter(and_(POD.date.like("%{}%".format(date)), POD.c_id == c_id)) \
                .first()
            if current_pod is not None:
                print(f"\n\n\n pod of day {date} :", current_pod.json)
                continue
            print(f"\nnot found pod \n\n\\n\n")

            parag: paragraph_model = session.query(paragraph_model) \
                .filter(and_(paragraph_model.community_id == c_id,
                             paragraph_model.replied_id == "",
                             paragraph_model.date.like("%{}%".format(date)))) \
                .order_by(paragraph_model.ima_count.desc(), paragraph_model.date.desc()
                          ).first()
            print("\n\n\ncommunity ", date, "\n\n\n paragd nulll", parag)

            if parag is not None:
                print("\n\n\n parag", parag.json)
                pod: POD = session.query(POD).filter(
                    and_(POD.date.like("%{}%".format(date)), POD.p_id == parag.id)).first()
                if pod is None:
                    self.add_pod(date, parag, session)

    def search_pod(self, date=None, start_off=0, end_off=101):
        session = make_session(self.engine)

        data_stm: List[POD] = session.query(POD).filter(POD.date.like('%' + date + '%')) \
            .order_by(POD.date.desc()).slice(start_off, end_off).all()

        res = []
        print(f"\n\n\n {start_off} in {end_off} search : ", res, "\n\ntttt\n")
        for i in data_stm:
            x = i.json
            x['user'] = {}
            user: UserModel = session.query(UserModel).filter(UserModel.id == i.paragraph.user_id).first()
            x['user'] = user.json
            res.append(x)

        return res
