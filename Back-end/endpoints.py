from resources.account import *
from resources.session import *
from resources.community import *
from resources.paragraph import *
from tools.string_tools import gettext



def init_endpoints(api ,engine):
    api.add_resource(login, gettext("url_login"), endpoint="login" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(register, gettext("url_register"), endpoint="register" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(logout, gettext("url_logout"), endpoint="logout" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(myprofile, gettext("url_myprofile"), endpoint="myprofile" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(password, gettext("url_change_pass"), endpoint="changepassword" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(bio, gettext("url_change_bio"), endpoint="changebio" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(dob, gettext("url_change_dob"), endpoint="changedob" , resource_class_kwargs={ 'engine': engine })

    api.add_resource(profile_picture, gettext("url_upload_pp"), endpoint="uploadpp" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(community, gettext("url_community"), endpoint="community" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(community_picture, gettext("url_upload_community_picture"), endpoint="communityuploadpp" , resource_class_kwargs={ 'engine': engine })
    api.add_resource(community_member, gettext("url_community_member"), endpoint="communitymember" , resource_class_kwargs={ 'engine': engine })

    api.add_resource(paragraph, gettext("url_paragraph"), endpoint="paragraph" , resource_class_kwargs={ 'engine': engine })
    
