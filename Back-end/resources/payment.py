import os
from flask_restful import Resource
from flask import request, redirect, make_response, url_for, jsonify, render_template
from http import HTTPStatus as hs
from typing import List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
from tools.token_tool import authorize
from tools.db_tool import make_session, Base
from db_models.users import change_user_image, edit_bio, get_notifications, get_one_user, add_user, change_pass, \
    edit_fname, edit_dob, \
    UserModel, delete_expired_notifications
from db_models.paragraph import paragraph_model, get_user_paragraphs
from db_models.payment import payment_model, DiscountModel
from tools.string_tools import gettext
from typing import Union, Dict, Tuple, List


class GetDiscount(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def get(self, current_user: UserModel, code: str):
        session = make_session(self.engine)
        discount = session.query(DiscountModel).get(code)
        if discount:
            result = {'code': discount.code, 'percent': discount.percent}
            if 'cost' in request.json:
                result['cost'] = (1 - discount.percent / 100) * request.json['cost']
            return result, hs.OK

        return {'message': 'could not find the discount'}, hs.NOT_FOUND


class CreteDiscount(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, current_user: UserModel):
        session = make_session(self.engine)
        body = request.json
        if 'code' not in body:
            return {'message': 'discount code in not specified correctly'}, hs.BAD_REQUEST
        if 'percent' not in body:
            return {'message': 'percent in not specified correctly'}, hs.BAD_REQUEST
        code = body['code']
        percent = body['percent']

        discount = DiscountModel(code, percent)
        try:
            session.add(discount)
            session.commit()
        except IntegrityError:
            session.rollback()
            return {'message': 'this discount code already exist'}, hs.BAD_REQUEST

        return {'message': 'discount code created successfully'}, hs.OK


class credit(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']

    @authorize
    def post(self, current_user: UserModel):
        """adding user credit"""
        req_data = request.json
        amount = 0
        try:
            amount = req_data["amount"]
        except:
            return {"message": gettext("credit_amount_needed")}, hs.BAD_REQUEST
        try:
            current_user.check_credit(amount)
        except:
            return {"message": gettext("credit_not_enough")}, hs.BAD_REQUEST

        new_c = add_credit(self.engine, current_user.id, amount, t_type=0)
        return {"message": gettext("credit_changed"), "credit": new_c}, hs.OK


def add_credit(engine, user_id: int, amount, t_type):
    """
        :param t_type: transaction_type -> 0 for charge money / 1 for discharge / 2 for sell book / 3 for buy book
    """
    session = make_session(engine)

    u: UserModel = session.query(UserModel).filter(UserModel.id == user_id).first()
    u.credit += amount
    session.flush()
    session.commit()
    save_charge_payment(engine, user_id, amount, t_type=t_type)
    return u.credit


def save_charge_payment(engine, user_id, amount, t_type):
    session = make_session(engine)
    pay = payment_model(user_id=user_id, amount=amount, transaction_type=t_type)
    session.add(pay)
    session.flush()
    session.commit()
