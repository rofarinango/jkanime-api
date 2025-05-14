from typing import List, Optional, Union
from models.anime import Anime
from utils.scraper import JKAnimeScraper

class JKAnimeService:
    def __init__(self):
        self.__scraper = JKAnimeScraper()
    
    def search_anime(self, query: str, page: int) -> List[Anime]:
        pass