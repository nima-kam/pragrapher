import os
from http import HTTPStatus as hs
from flask_restful import Resource, reqparse
from flask import request, make_response, jsonify
from tools.db_tool import engine , make_session
from tools.token_tool import authorize, community_role

from db_models.community import get_community, get_role , community_model
from tools.string_tools import gettext

class searcher(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user):
        typer = ''
        text = ''
        try:
            typer = request.args.get('type')
            if typer == None:
                msg = gettext("search_type_needed")
                return {'message': msg}, hs.BAD_REQUEST
            typer = str(typer)
        except:
            msg = gettext("search_type_needed")
            return {'message': msg}, hs.BAD_REQUEST
        print("here**************")
        try:
            text = request.args.get('text')
            if text == None :
                msg = gettext("search_text_needed")
                return {'message': msg}, hs.BAD_REQUEST
            text = str(text)
        except:
            msg = gettext("search_text_needed")
            return {'message': msg}, hs.BAD_REQUEST
        print("$$$" , text)

        if typer == "community":
            session = make_session(self.engine)
            coms: community_model = session.query(community_model).filter(community_model.name.like("%{}%".format(text))).all()
            res = []
            for row in coms:
                 res.append(row.json)
            return {'message':res} , 200
        elif typer == "author":
            pass
        elif typer == "book":
            pass
        else:
            msg = gettext("search_type_invalid")
            return {'message': msg}, hs.NOT_FOUND