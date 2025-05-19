from flask import Flask
from flask_restful import Api
from resources.anime import AnimeResource, AnimeListResource
from resources.episode import EpisodeListResource, EpisodeResource


def create_app():
    app = Flask(__name__)
    api = Api(app)
    
    # Register routes
    # Gell all titles from directory
    api.add_resource(AnimeListResource, '/animes')
    api.add_resource(AnimeResource, '/animes/<string:query>/<int:page>')
    # Get all episodes from anime_id route
    api.add_resource(EpisodeListResource, '/animes/<string:anime_id>/episodes')
    api.add_resource(EpisodeResource, '/animes/<string:anime_id>/episodes/<int:number>')


    return app

# Testing main flask app

if __name__ == '__main__':
    app = create_app()
    app.run(port=5000, debug=True)