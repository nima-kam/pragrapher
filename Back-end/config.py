
def init_config():
    config = {}
    config['MYSQL_HOST'] = 'localhost'
    config['MYSQL_USER'] = 'manager'
    config['MYSQL_PASSWORD'] = 'strong_password'
    config['MYSQL_DB'] = 'pragrapher'
    return config

jwt_secret_key = 'strong_jwt_password'