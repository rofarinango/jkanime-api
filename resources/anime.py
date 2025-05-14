from flask import request
from flask_restful import Resource
from http import HTTPStatus
from main import JKAnime
from models.anime import Anime

class AnimeResource(Resource):
    def get(seld, query, page):
        pass