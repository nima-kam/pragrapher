from flask_restful import Resource
from flask import request
from db_models.chat import MessageModel
from db_models.users import UserModel
from tools.db_tool import make_session
from tools.token_tool import authorize
from http import HTTPStatus as hs


class CreateMessage(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def put(self, current_user: UserModel):
        _from = current_user.id
        body = request.json
        if 'to' not in body:
            return {'message': 'destination is not specified correctly'}, hs.BAD_REQUEST
        _to = body['to']
        content = body['content']
        message = MessageModel(_from, _to, content)
        session = make_session(self.engine)
        session.add(message)
        session.commit()
        return {'message': 'message created successfully'}, hs.OK



