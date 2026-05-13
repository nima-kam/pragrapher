from app import app as application
from app import api

if __name__ == "__main__":
    api.init_app(application)
    application.run(use_reloader=True, host='0.0.0.0', port=8080)

