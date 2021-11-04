from flask_restful import Resource , reqparse
from flask import request, redirect, make_response, url_for, jsonify, render_template
from tools.db_tool import engine
from tools.token_tool import authorize

from db_models.community import add_community
from tools.string_tools import gettext

class community(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']
    @authorize
    def get(self,name ,  current_user):
        req_data = request.json
        
        res = make_response(jsonify(current_user.json))
        return res

    @authorize
    def post(self, current_user):
        req_data = request.json
        add_community( req_data['name'] , current_user.id , self.engine)
        return redirect("/community/{}".format(req_data['name']))