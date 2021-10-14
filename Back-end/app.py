from flask import Flask
from flask_restful import Api
from resources.login import *

app = Flask(__name__)
api = Api(app=app)

api.add_resource(Login, "/authenticate")
api.add_resource(Register, "/register")

if __name__ == '__main__':
    app.run()
