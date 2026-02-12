
import aiohttp
from bs4 import BeautifulSoup
from typing import Optional, Dict

async def fetch_og_tags(url: str) -> Dict[str, Optional[str]]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10, headers={'User-Agent': 'SafeBoxBot/1.0'}) as response:
                if response.status != 200:
                    return {}
                html = await response.text()
                
        soup = BeautifulSoup(html, 'html.parser')
        
        tags = {}
        
        # Helper to get content
        def get_content(prop):
            tag = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
            return tag['content'] if tag else None
            
        tags['title'] = get_content('og:title') or soup.find('title').string if soup.find('title') else None
        tags['description'] = get_content('og:description') or get_content('description')
        tags['image'] = get_content('og:image')
        tags['url'] = url
        
        # Clean up
        return {k: v for k, v in tags.items() if v}
        
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        return {}
