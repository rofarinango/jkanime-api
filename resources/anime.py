from flask import request
from flask_restful import Resource, reqparse
from http import HTTPStatus
from services.jkanime_service import JKAnimeService
from models.anime import Anime


class AnimeListResource(Resource):
    def __init__(self):
        self.service = JKAnimeService()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('page', type=int, default=1, location='args')
    

    def get(self):
        try:
            # Get page from query parameters
            args = self.parser.parse_args()
            page = args['page']

            if page < 1:
                return {'error': 'Page number must be greater than 0'}, HTTPStatus.BAD_REQUEST
            
            result = self.service.get_all(page)

            if result['titles']:
                return {
                    'data': result['titles'],
                    'pagination': result['pagination']
                }
            return {'message': 'titles not found'}, HTTPStatus.NOT_FOUND
        except Exception as e:
            return {'error': str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

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