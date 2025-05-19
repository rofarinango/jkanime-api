import cloudscraper
import re
import json
import aiohttp
import asyncio
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Type, Union
from types import TracebackType
from models.anime import Anime
from models.episode import Episode
from core.constants import BASE_URL, SEARCH_URL, DIRECTORY_URL
from async_lru import alru_cache

class JKAnimeScraper:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kargs):
        if cls._instance is None:
            cls._instance = super(JKAnimeScraper, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, *args, **kwargs):
        if not self._initialized:
            session = kwargs.get("session", None)
            self._scraper = cloudscraper.create_scraper(session)
            self._headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': BASE_URL,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            self._initialized = True

    def close(self) -> None:
        self._scraper.close()
    
    def __enter__(self) -> "JKAnimeScraper":
        return self
    
    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()
    
    @alru_cache(maxsize=100)
    async def get_video_servers(
            self,
            id: str,
            episode: int,
            **kwargs,
    ) -> List[Dict[str, str]]:
        """
        Get in video servers, this work only using the iframe element.
        Return a list of dictionaries.

        :param id: Anime id, like as 'nanatsu-no-taizai'.
        :param episode: Episode id, like as '1'.
        :rtype: list
        """

        try:
             # Add cache hit/miss debug
            cache_info = self.get_video_servers.cache_info()
            print(f"DEBUG: Cache stats - Hits: {cache_info.hits}, Misses: {cache_info.misses}, Size: {cache_info.currsize}")
            
            print(f"DEBUG: Fetching data for {id} episode {episode}")
                
            response = self._scraper.get(f"{BASE_URL}{id}/{episode}")
            soup = BeautifulSoup(response.text, "lxml")

            # Find the specific script containing video information
            target_script = soup.find("script", string=lambda s: s and "var video = [];" in s)
            if not target_script:
                return []
            
            content = target_script.string or target_script.text
            servers = []

            # Extract servers array in one pass
            servers_match = re.search(r"var servers = (\[.*?\]);", content, re.DOTALL)
            if servers_match:
                try:
                    servers_data = json.loads(servers_match.group(1))
                    for server in servers_data:
                        iframe_url = f"/c1.php?u={server['remote']}&s={server['server'].lower()}"
                        servers.append({'iframe': iframe_url})
                except json.JSONDecodeError:
                    pass

            # Process servers concurrently
            tasks = []
            for server in servers:
                task = asyncio.create_task(self._get_video_url_async(server['iframe']))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results
        
        except Exception as e:
            print(f"Error getting video servers: {str(e)}")
            return []


    @alru_cache(maxsize=100)
    async def _get_video_url_async(self, iframe_url: str) -> Optional[Dict[str, str]]:
        """
        Get video URL from an iframe URL.
        Returns a dictionary containing server name and video URL.
        """
        try:
            print(f"DEBUG: Fetching data for {iframe_url}")

            
            if iframe_url.startswith('/'):
                iframe_url = BASE_URL.rstrip('/') + iframe_url
            
            # Create a new session for each request
            async with aiohttp.ClientSession() as session:
                async with session.get(iframe_url, headers=self._headers) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, "lxml")

                    # Extract server name
                    server_name = None
                    script_tag = soup.find('script')
                    if script_tag:
                        script_content = script_tag.string or script_tag.text
                        match = re.search(r"var servername = \"([^\"]+)\";", script_content)
                        if match:
                            server_name = match.group(1)

                    # Try to get video URL from iframe first
                    iframe = soup.find('iframe')
                    if iframe and iframe.has_attr('src'):
                        video_url = iframe['src'].strip()
                        if video_url.startswith('http'):
                            return {'server': server_name, 'url': video_url}
                        
                    return None

        except Exception as e:
            print(f"Error getting video URL: {str(e)}")
            return None
    
    def clear_cache(self):
        """Clear cache"""
        self.get_video_servers.cache_clear()
        self._get_video_url_async.cache_clear()


    def search_anime(self, query: str = None, page: int = None) -> List[Anime]:
        """
        Search in jkanime.net by query.
        :param query: Query Information: eg. "Boku no Hero Academia"
        :param page: Page of the information return.
        :rtype: list[AnimeInfo]
        """
        if page is not None and not isinstance(page, int):
            raise TypeError
        
        response = self._scraper.get(f"{SEARCH_URL}{query}/{page}")
        soup = BeautifulSoup(response.text, "lxml")

        anime_items = []
        anime_items = soup.find_all('div', class_='anime__item')
        results = []

        for item in anime_items:
            # Extract info from anime
            # Id
            title_id = item.find('h5')
            if title_id:
                a_tag = title_id.find('a')
                if a_tag:
                    href = a_tag.get('href')
                    id = href.strip('/').split('/')[-1]
            # Title
            title_elem = item.find('div', class_='title')
            if title_elem:
                title_text = title_elem.text.strip()
            # Image
            img_elem = item.find('div', class_="anime__item__pic")
            if img_elem:
                img_url = img_elem.get('data-setbg')

            # Synopsis
            p_elem = item.find('p')
            if p_elem:
                synopsis = p_elem.text.strip()
            
            # Type (Anime, Movie, OVA)
            li_elem = item.find('li', class_="anime")
            if li_elem:
                type = li_elem.text.strip()
            
            # Create anime object with all the obtained parameters
            anime = Anime(id, title_text, img_url, synopsis, type)
            results.append(anime)
        return results
    
    @alru_cache(maxsize=100)
    async def get_episodes_by_anime_id(self, anime_id: Union[str, int], page: int) -> Dict:
        try:
            response = self._scraper.get(f"{BASE_URL}{anime_id}")
            soup = BeautifulSoup(response.text, "lxml")
            anime_pagination = soup.find("div", class_='anime__pagination')
            if not anime_pagination:
                print(f"DEBUG: No pagination found for {anime_id}")
                return {'episodes': [], 'pagination': {}}
            # Find the a tag with the pagination number of page input
            pages = anime_pagination.find_all("a", class_="numbers")
            if not pages:
                print(f"DEBUG: No page numbers found for {anime_id}")
                return {'episodes': [], 'pagination': {}}

            # Find the requested page
            target_page = None
            for item in pages:
                if item.get('href') == f"#pag{page}":
                    target_page = item
                    break

            if not target_page:
                print(f"DEBUG: Page {page} not found for {anime_id}")
                return {'episodes': [], 'pagination': {}}

            # Get episode range
            episode_range = target_page.text.strip()
            if not episode_range:
                print(f"DEBUG: No episode range found for page {page}")
                return {'episodes': [], 'pagination': {}}

            try:
                start, end = map(int, episode_range.split('-'))
                episode_numbers = list(range(start, end+1))
                print(f"DEBUG: Episodes for page {page}: {episode_numbers}")
            except ValueError as e:
                print(f"DEBUG: Invalid episode range format: {episode_range}")
                return {'episodes': [], 'pagination': {}}

             # Process episodes sequentially with a small delay
            episodes = []
            for number in episode_numbers:
                try:
                    # Add a small delay between requests (0.5 seconds)
                    await asyncio.sleep(0.5)
                    episode_data = await self.get_video_servers(anime_id, number)
                    if episode_data:  # Only add if we got data
                        episodes.append(episode_data)
                    print(f"DEBUG: Got data for episode {number}")
                except Exception as e:
                    print(f"DEBUG: Error getting episode {number}: {str(e)}")
                    continue

            return {
                'episodes': episodes,
                'pagination': {
                    'current_page': page,
                    'total_episodes': len(episode_numbers),
                    'episode_range': f"{start}-{end}"
                }
            }

        except Exception as e:
            print(f"Error in get_episodes_by_anime_id: {str(e)}")
            print(f"DEBUG: Full error details: {e.__class__.__name__}: {str(e)}")
            return {'episodes': [], 'pagination': {}}
        
    def get_all(self, page):
        """
        Get titles by query page
        :param page: pagination number
        """
        try:
            print(f"DEBUG: Fetching data for page number {page} in directory")

            response = self._scraper.get(f"{DIRECTORY_URL}/{page}")
            soup = BeautifulSoup(response.text, "lxml")

            # Extract animes variable content
            titles = None
            target_script = soup.find("script", string=lambda s: s and "var animes =" in s)
            print(target_script)
            if not target_script:
                return []
            
            # Extract the animes array from the script contents
            script_content = target_script.string
            start_marker = "var animes ="
            start_idx = script_content.find(start_marker)
            start_idx += len(start_marker)
            print(start_idx)
            end_idx = script_content.find("var mode =")
            print(end_idx)
            if end_idx == -1:
                end_idx = script_content.find("function anime_status")

            animes_json = script_content[start_idx:end_idx].strip()
            print(animes_json)
            if animes_json.endswith(";"):
                animes_json = animes_json[:-1]
            
            # Parse the JSON data
            titles = json.loads(animes_json)
            print(f"DEBUG: Found {len(titles)} titles")
            print(titles)
            return titles
        

        except Exception as e:
            print(f"Error getting titles: {str(e)}")
            return []