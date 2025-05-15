from flask import Flask
from flask_restful import Api
from resources.anime import AnimeResource


def create_app():
    app = Flask(__name__)
    api = Api(app)
    
    # Register routes
    api.add_resource(AnimeResource, '/animes/<string:query>/<int:page>')

    return app

# Testing main flask app

if __name__ == '__main__':
    app = create_app()
    app.run()