from re import search
import resources
from resources.book import *
from resources.account import *
from resources.session import *
from resources.community import *
from resources.community import community_member as cm
from resources.paragraph import *
from resources.search import *
from resources.payment import *
from tools.string_tools import gettext



def init_endpoints(api ,engine):
    api.add_resource(login, gettext("url_login"), endpoint="login", resource_class_kwargs={'engine': engine})
    api.add_resource(register, gettext("url_register"), endpoint="register", resource_class_kwargs={'engine': engine})
    api.add_resource(logout, gettext("url_logout"), endpoint="logout", resource_class_kwargs={'engine': engine})

    api.add_resource(myprofile, gettext("url_myprofile"), endpoint="myprofile", resource_class_kwargs={'engine': engine})
    api.add_resource(myparagraphs, gettext("url_myparagraph"), endpoint="myparagraph", resource_class_kwargs={'engine': engine})
    api.add_resource(fname, gettext("url_fname"), endpoint="fname" , resource_class_kwargs={'engine': engine})
    api.add_resource(password, gettext("url_change_pass"), endpoint="changepassword", resource_class_kwargs={'engine': engine})
    api.add_resource(bio, gettext("url_change_bio"), endpoint="changebio", resource_class_kwargs={'engine': engine})
    api.add_resource(dob, gettext("url_change_dob"), endpoint="changedob", resource_class_kwargs={'engine': engine})
    api.add_resource(profile_picture, gettext("url_upload_pp"), endpoint="uploadpp", resource_class_kwargs={'engine': engine})
    api.add_resource(Notifications, gettext("url_notifications") , endpoint="notifications", resource_class_kwargs={'engine': engine})
    
    api.add_resource(community, gettext("url_community"), endpoint="community", resource_class_kwargs={'engine': engine})
    api.add_resource(create_community, gettext("url_create_community"), endpoint="community_create", resource_class_kwargs={'engine': engine})
    api.add_resource(best_community, gettext("url_best_community"), endpoint="bestcommunity", resource_class_kwargs={'engine': engine})
    api.add_resource(community_picture, gettext("url_upload_community_picture"), endpoint="communityuploadpp", resource_class_kwargs={'engine': engine })
    api.add_resource(cm, gettext("url_community_member"), endpoint="communitymember", resource_class_kwargs={'engine': engine})
    api.add_resource(community_data, gettext("url_community_data"), endpoint="communitydescription", resource_class_kwargs={'engine': engine})
    api.add_resource(community_leave, gettext("url_community_leave"), endpoint="communityleave", resource_class_kwargs={'engine': engine})
    api.add_resource(show_community, gettext("url_community_show"), endpoint="communityshow", resource_class_kwargs={'engine': engine})


    api.add_resource(paragraph, gettext("url_paragraph"), endpoint="paragraph", resource_class_kwargs={'engine': engine})
    api.add_resource(impression, gettext("url_impression"), endpoint="impression", resource_class_kwargs={'engine': engine})
    api.add_resource(reply, gettext("url_reply"), endpoint="reply", resource_class_kwargs={'engine': engine})

    api.add_resource(searcher, gettext("url_search"), endpoint="search", resource_class_kwargs={'engine': engine })
    api.add_resource(community_searcher, gettext("url_community_search"), endpoint="community_search", resource_class_kwargs={'engine': engine})
    api.add_resource(pod_searcher, gettext("url_pod_search"), endpoint="pod_search", resource_class_kwargs={'engine': engine})
    api.add_resource(suggestion, gettext("url_suggestion"), endpoint="suggestion", resource_class_kwargs={'engine': engine})


    api.add_resource(credit, gettext("url_credit_change"), endpoint="credit", resource_class_kwargs={'engine': engine})

    api.add_resource(book, gettext("url_book"), endpoint="book", resource_class_kwargs={'engine': engine})
    api.add_resource(book_picture, gettext("url_book_picture"), endpoint="book_picture", resource_class_kwargs={'engine':engine})
    api.add_resource(reserve_book, gettext("url_book_reserve"), endpoint="book_reserve", resource_class_kwargs={'engine':engine})
    # api.add_resource(book_store, gettext("url_book_store"), endpoint="book_store", resource_class_kwargs={'engine': engine})

