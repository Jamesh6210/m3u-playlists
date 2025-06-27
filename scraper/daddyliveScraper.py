from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import requests

def fetch_channel_index():
    url = 'https://thedaddy.to/24-7-channels.php'
    response = requests.get(url)
    if response.status_code == 200:
        with open('247channels.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("Downloaded 24/7 channel index successfully.")
    else:
        print(f"Failed to download page. Status code: {response.status_code}")

def get_stream_url(channel_url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(channel_url)
        time.sleep(3)  # Wait for network activity

        # Look for .m3u8 in network logs via JavaScript
        video_elements = driver.find_elements('tag name', 'script')
        for script in video_elements:
            if '.m3u8' in script.get_attribute('innerHTML'):
                content = script.get_attribute('innerHTML')
                start = content.find('https')
                end = content.find('.m3u8') + 5
                if start != -1 and end != -1:
                    return content[start:end]

    finally:
        driver.quit()
    return None



def get_all_channel_links(index_file):
    """
    Parses the DaddyLive 24/7 index HTML file and returns a list of (name, link) tuples.
    """
    with open(index_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        name = a.get_text(strip=True)
        if href.startswith('/24-7-channels/') and name:
            full_url = f"https://thedaddy.to{href}"
            links.append((name, full_url))
    
    return links

fetch_channel_index()
channel_list = get_all_channel_links('247channels.html')

if __name__ == '__main__':
    channel_list = get_all_channel_links('247channels.html')
    print(f"Found {len(channel_list)} channels")

    with open('out.m3u8', 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')

        for name, url in channel_list:
            print(f"Fetching: {name}")
            stream_url = get_stream_url(url)
            if stream_url:
                f.write(f'#EXTINF:-1,{name}\n')
                f.write(f'{stream_url}\n')
