import os

from flask import Flask, Blueprint
from flask_mongoengine import MongoEngine

from app.api import api
from app.api.endpoints.images_tasks import ns as images_tasks_namespace
from app.api.endpoints.text_tasks import ns as text_tasks_namespace
from app.utils import MongoEngineObjectIdJSONEncoder


def create_app(testing=False):
    app = Flask(__name__)
    initialize_app(app, testing=testing)
    return app


def get_config(testing=False):
    config = {
        'RESTPLUS_JSON': {'cls': MongoEngineObjectIdJSONEncoder},
        'MONGODB_SETTINGS': {
            'host': 'mongodb://db:27017/semantive' if not testing else 'mongomock://localhost:27017',
            'connect': False,
        }
    }
    return config


def configure_app(flask_app, testing=False):
    flask_app.config.from_mapping(get_config(testing=testing))


def initialize_app(flask_app, testing=False):
    configure_app(flask_app, testing=testing)
    MongoEngine(flask_app)

    blueprint = Blueprint('api', __name__, url_prefix='/api')
    api.init_app(blueprint)
    api.add_namespace(images_tasks_namespace)
    api.add_namespace(text_tasks_namespace)
    flask_app.register_blueprint(blueprint)


def main():
    app = create_app()
    app.run(debug=os.getenv('DEBUG', True))


if __name__ == '__main__':
    main()

