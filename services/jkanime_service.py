from typing import List, Optional, Union
from models.anime import Anime
from models.episode import Episode
from utils.scraper import JKAnimeScraper

class JKAnimeService:
    def __init__(self):
        self.__scraper = JKAnimeScraper()
    
    def search_anime(self, query: str, page: int) -> List[Anime]:
        """
        Search for anime by query and page number
        """
        return self.__scraper.search_anime(query, page)
    
    def get_video_servers(self, anime_id: str, episode: int) -> List[Episode]:
        """
        Get video servers for a specific anime episode
        """
        return self._scraper.get_video_servers(anime_id, episode)

