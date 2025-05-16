from flask_restful import Resource, reqparse
from http import HTTPStatus
from services.jkanime_service import JKAnimeService

class EpisodeListResource(Resource):
    def __init__(self):
        self.service = JKAnimeService()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('page', type=int, default=1, location='args')

    def get(self, anime_id: str):
        try:
            # Get page from query parameters
            args = self.parser.parse_args()
            page = args['page']

            # Validate page number
            if page < 1:
                return {'error': 'Page number must be grater than 0'}, HTTPStatus.BAD_REQUEST
            
            # Get episodes with pagination
            result = self.service.get_episodes_by_anime_id(anime_id, page)

            if result['episodes']:
                return {
                    'data': result['episodes'],
                    'pagination': result['pagination']
                }
            return {'message': 'episodes not found'}, HTTPStatus.NOT_FOUND
        except Exception as e:
            return {'error': str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

class EpisodeResource(Resource):
    def __init__(self):
        self.service = JKAnimeService()
    
    def get(self, anime_id: str, number: int):
        try:
            episode = self.service.get_video_servers(anime_id, number)
            if episode:
                return {'data': episode}
            return {'message': 'episode not found'}, HTTPStatus.NOT_FOUND
        
        except Exception as e:
            return {'error': str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR
        