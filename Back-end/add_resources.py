from app import api, app
from resources.account import *
from resources.main import *
from tools.string_tools import gettext


api.add_resource(login, gettext("url_login"), endpoint="login")
api.add_resource(register, gettext("url_register"), endpoint="register")
api.add_resource(logout, gettext("url_logout"), endpoint="logout")
api.add_resource(myprofile, gettext("url_myprofile"), endpoint="myprofile")
api.add_resource(password, gettext("url_change_pass"), endpoint="changepassword")


if __name__ == '__main__':
    app.app_context().push()
    api.init_app(app)
    app.run(use_reloader=True, host='0.0.0.0', threaded=True)