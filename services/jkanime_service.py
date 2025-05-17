from typing import List, Optional, Union, Dict
from models.anime import Anime
from models.episode import Episode
from utils.scraper import JKAnimeScraper

class JKAnimeService:
    EPISODES_PER_PAGE = 12
    _instance = None
    _initialized = False
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JKAnimeService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.__scraper = JKAnimeScraper()
            self._initialized = True
    
    def search_anime(self, query: str, page: int) -> List[Anime]:
        """
        Search for anime by query and page number
        """
        return self.__scraper.search_anime(query, page)
    
    def get_video_servers(self, anime_id: str, episode: int) -> List[Episode]:
        """
        Get video servers for a specific anime episode
        """
        return self.__scraper.get_video_servers(anime_id, episode)
    
    async def get_episodes_by_anime_id(self, anime_id: Union[str, int], page: int = 1) -> Dict:
        """
        Get episodes for an anime with pagination
        Returns a dictionary containing episodes and pagination info
        """
        try:
            # Calculate episode ranges
            start_episode = ((page - 1) * self.EPISODES_PER_PAGE) + 1
            end_episode = page * self.EPISODES_PER_PAGE

             # Scrap episodes for the current page
            result = await self.__scraper.get_episodes_by_anime_id(anime_id, page)
            
            if not result['episodes']:
                raise Exception(f"No episodes found for anime {anime_id} on page {page}")
                
            return result
        except Exception as e:
            raise Exception(f"Error fetching episodes: {str(e)}")

