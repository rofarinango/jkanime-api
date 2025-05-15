import cloudscraper
import js2py
import re
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Type
from types import TracebackType
from models.anime import Anime
from models.episode import Episode
from core.constants import BASE_URL, SEARCH_URL


class JKAnimeScraper:
    def __init__(self, *args, **kwargs):
        session = kwargs.get("session", None)
        self._scraper = cloudscraper.create_scraper(session)

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
    
    def get_video_servers(
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

        response = self._scraper.get(f"{BASE_URL}{id}/{episode}")
        soup = BeautifulSoup(response.text, "lxml")
        scripts = soup.find_all("script")

        servers = []              
        # Find the script with 'var video = [];'
        for script in scripts:
            content = script.string or script.text
            if content and "var video = [];" in content:
                # Extract all iframe src URLs
                matches = re.findall(r"video\[(\d+)\] = '<iframe class=\"player_conte\" src=\"([^\"]+)\"", content)
                for idx, iframe_url in matches:
                    servers.append({'iframe': iframe_url})
                
                # Extract the servers array
                servers_match = re.search(r"var servers = (\[.*?\]);", content, re.DOTALL)
                if servers_match:
                    servers_json = servers_match.group(1)
                    servers_data = json.loads(servers_json)
                    for server in servers_data:
                        if server['server'] != 'Mediafire': #Skip as is direct donwload
                            iframe_url = f"/c1.php?u={server['remote']}&s={server['server'].lower()}"
                            servers.append({'iframe': iframe_url})
        server_list = []
        for i, server in enumerate(servers):
            server_list.append(get_video_url(server['iframe']))
        return server_list
    
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

# Helper function to get the video url requesting the underlying iframe page
def get_video_url(iframe_url, base_url=BASE_URL):
    # Step 1: Fetch the iframe page
    scraper = cloudscraper.create_scraper()
    # If the iframe is relative, prepend the base_url
    if iframe_url.startswith('/'):
        iframe_url = base_url.rstrip('/') + iframe_url
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': base_url,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    response = scraper.get(iframe_url, headers=headers)
    soup = BeautifulSoup(response.text, "lxml")

    # Step 1.5: Check if the response contains an iframe with a direct video URL
    # Get server name from script tag
    script_tag = soup.find('script')
    if script_tag:
        script_content = script_tag.string or script_tag.text
        match = re.search(r"var servername = \"([^\"]+)\";", script_content)
        if match:
            server_name = match.group(1)
        else:
            server_name = None

    iframe = soup.find('iframe')
    if iframe and iframe.has_attr('src'):
        video_url = iframe['src']
        if video_url.startswith('http'):
            return {'server': server_name, 'url': video_url}
    
    # Step 3: If not, try extract and run the obfuscated JS
    scripts = soup.find('script')
    if len(scripts) > 1:
        script_content = scripts[1].string or scripts[1].text
        if script_content:
            # Try to extract the assignment to ss (the video URL)
            # regex it out:
            match = re.search(r"ss\s*=\s*['\"]([^'\"]+)['\"]", script_content)
            if match:
                return {'server': server_name, 'url': match.group(1)}
            # Otherwise, try to run the JS (if it's not too obfuscated)
            try:
                context = js2py.EvalJs()
                context.execute(script_content)
                if hasattr(context, 'ss'):
                    return {'server': server_name, 'url': context.__subclasshook__ }
            except Exception as e:
                print("JS execution failed:", e)
    
    return None