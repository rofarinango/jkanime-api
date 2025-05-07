from types import TracebackType
import cloudscraper
import js2py
import re, json
from dataclasses import dataclass
from enum import Flag, auto
from typing import Dict, List, Optional, Type, Union
from bs4 import BeautifulSoup, Tag
from urllib.parse import unquote, urlencode

class AnimeFLVParseError(Exception):
    pass

def parse_table(table: Tag):
    columns = list([x.string for x in table.thead.tr.find_all("th")])
    rows = []

    for row in table.tbody.find_all("tr"):
        values = row.find_all("td")
        if len(values) != len(columns):
            raise AnimeFLVParseError("Don't match values size with columns size")
        
        rows.append({h: x for h, x in zip(columns, values)})
    return rows

BASE_URL= "https://jkanime.net/"
SEARCH_URL = "https://jkanime.net/buscar/"
SEARCH_BY_CHARACTER_URL = "https://jkanime.net/letra/"
SCHEDULE_URL= "https://jkanime.net/horario/"
GENRE_URL="https://jkanime.net/genero/"
MOVIES_URL= "https://jkanime.net/tipo/pelicula"
OVAS_URL= "https://jkanime.net/tipo/ova"


@dataclass
class Episode:
    id: Union[str, int]
    anime: str
    image_preview: Optional[str] = None
    
@dataclass
class Anime:
    id: Union[str, int]
    title: str
    poster: Optional[str] = None
    banner: Optional[str] = None
    synopsis: Optional[str] = None
    rating: Optional[str] = None
    genres: Optional[str] = None
    debut: Optional[str] = None
    type: Optional[str] = None
    episodes: Optional[List[Episode]] = None
    
@dataclass
class DownloadLink:
    server: str
    url: str

class EpisodeFormat(Flag):
    Subtitled = auto()
    Dubbed = auto()

class JKAnime(object):
    def __init__(self, *args, **kwargs):
        session = kwargs.get("session", None)
        self._scraper = cloudscraper.create_scraper(session)

    def close(self) -> None:
        self._scraper.close()
    
    def __enter__(self) -> "JKAnime":
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
            format: EpisodeFormat = EpisodeFormat.Subtitled,
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

        #print(soup)

        server_names = extract_server_names_from_script(response.text)
        print(server_names)
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
            name = server_names[i] if i < len(server_names) else f"Server {i+1}"
            #print(server['iframe'])
            server_list.append({'server': name, 'iframe': get_video_url(server['iframe'])})

        
        return server_list
        


# Helper function to extract the name servers from script
def extract_server_names_from_script(response):
    # Find the JS variable
    match = re.search(r"var servers = (\[.*?\]);", response, re.DOTALL)
    if not match:
        return []
    servers_json = match.group(1)
    servers = json.loads(servers_json)
    return [server['server'] for server in servers]


# Helper function to get the video url requesting the underlying iframe page
def get_video_url(iframe_url, base_url="https://jkanime.net"):
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
    print("##### FROM_GET_VIDEO_URL ########")
    print(soup)

    # Step 1.5: Check if the response contains an iframe with a direct video URL
    iframe = soup.find('iframe')
    if iframe and iframe.has_attr('src'):
        video_url = iframe['src']
        if video_url.startswith('http'):
            return video_url

    # Step 2: Try to find a <video> tag
    video = soup.find('video')
    #print(video)
    if video:
        source = video.find('source')
        if source and source.has_attr('src'):
            return source['src']
    
    # Step 3: If not, try extract and run the obfuscated JS
    scripts = soup.find('script')
    if len(scripts) > 1:
        script_content = scripts[1].string or scripts[1].text
        if script_content:
            # Try to extract the assignment to ss (the video URL)
            # regex it out:
            match = re.search(r"ss\s*=\s*['\"]([^'\"]+)['\"]", script_content)
            if match:
                return match.group(1)
            # Otherwise, try to run the JS (if it's not too obfuscated)
            try:
                context = js2py.EvalJs()
                context.execute(script_content)
                if hasattr(context, 'ss'):
                    return context.__subclasshook__
            except Exception as e:
                print("JS execution failed:", e)
    
    return None
# Testing code Main function

if __name__ == "__main__":
    # Example usage: vigilante-boku-no-hero-academia-illegals and episode 1
    anime_id = "vigilante-boku-no-hero-academia-illegals"
    episode_number = 1

    with JKAnime() as jk:
        try:
            servers = jk.get_video_servers(anime_id, episode_number)
            print("Download links found:")
            for link in servers:
                print(f"Server: {link['server']}, URL: {link['iframe']}")
        except Exception as e:
            print(f"Error: {e}")