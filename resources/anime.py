from flask import request
from flask_restful import Resource
from http import HTTPStatus
from services.jkanime_service import JKAnimeService
from models.anime import Anime

class AnimeResource(Resource):
    def __init__(self):
        self.service = JKAnimeService()

    def get(self, query: str, page: int):
        try:
            search_results = self.service.search_anime(query, page)
            if search_results:
                return {
                    'data': [anime.data for anime in search_results]
                }
            return {'message': 'animes not found'}, HTTPStatus.NOT_FOUND
        except Exception as e:
            return {'error': str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR