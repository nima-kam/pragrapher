from flask import Flask
from flask_restful import Api
from resources.login import *
from setting import *

app = create_app(__name__)
api = Api(app=app)

api.add_resource(Login, "/auth")
api.add_resource(Register, "/register")

if __name__ == '__main__':
    app.run()
