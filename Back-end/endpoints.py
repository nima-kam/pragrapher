from resources.account import *
from resources.session import *
from tools.string_tools import gettext



def init_endpoints(api ,engine):
    api.add_resource(login, gettext("url_login"), endpoint="login" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(register, gettext("url_register"), endpoint="register" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(logout, gettext("url_logout"), endpoint="logout" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(myprofile, gettext("url_myprofile"), endpoint="myprofile" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(password, gettext("url_change_pass"), endpoint="changepassword" , resource_class_kwargs={ 'engine': engine })

