import re
import time
import requests
from bs4 import BeautifulSoup
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
import os
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Referer': 'https://daddylive.mp/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def setup_selenium():
    """Configure Selenium Wire with headless Chrome."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])

    # Selenium Wire options
    seleniumwire_options = {
        'suppress_connection_errors': True,
    }

    # Set up ChromeDriver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options,
        seleniumwire_options=seleniumwire_options
    )

    # Set cookies
    driver.get('https://daddylive.mp')
    driver.add_cookie({'name': 'accept', 'value': 'true'})
    return driver

def get_channel_list(url):
    """Fetch and parse the channel list from 24-7-channels.php."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        channels = []
        for link in soup.find_all('a', href=re.compile(r'/stream/stream-\d+\.php')):
            channel_name = link.text.strip() or link.get('title', 'Unknown')
            channel_url = 'https://daddylive.mp' + link['href']
            channels.append({'name': channel_name, 'url': channel_url})
        logging.info(f"Found {len(channels)} channels.")
        return channels[:3]  # Limit to 3 channels
    except Exception as e:
        logging.error(f"Error fetching channel list: {e}")
        return []

def get_m3u8_url(driver, player_url):
    """Capture M3U8 URL using Selenium Wire or fallback parsing."""
    m3u8_url = None
    debug_dir = 'debug'
    os.makedirs(debug_dir, exist_ok=True)

    try:
        # Clear previous requests
        del driver.requests

        # Load player page
        logging.info(f"Loading player page: {player_url}")
        driver.get(player_url)
        time.sleep(2)

        # Wait for player elements
        try:
            WebDriverWait(driver, 20).until(
                EC.any_of(
                    EC.presence_of_element_located((By.TAG_NAME, 'iframe')),
                    EC.presence_of_element_located((By.TAG_NAME, 'video'))
                )
            )
            logging.info(f"Player element detected for {player_url}")
        except:
            logging.warning(f"No player element detected for {player_url}")

        # Simulate play button click
        try:
            play_button = driver.find_elements(By.CSS_SELECTOR, 'button.play, [id*="play"], .vjs-play-control, video')
            if play_button:
                play_button[0].click()
                logging.info("Clicked play button or video")
                time.sleep(10)  # Wait for stream
        except:
            logging.debug("No play button or video clickable")

        # Check dynamic iframe src changes
        try:
            iframe_src = driver.execute_script("""
                var iframe = document.querySelector('iframe');
                return iframe ? iframe.src : null;
            """)
            logging.info(f"Dynamic iframe src: {iframe_src}")
        except:
            logging.debug("No dynamic iframe src found")

        # Capture network requests
        network_requests = []
        for request in driver.requests:
            if request.response and request.url:
                network_requests.append(request.url)
                if any(ext in request.url.lower() for ext in ['.m3u8', '.m3u', '.ts']):
                    m3u8_url = request.url
                    logging.info(f"Found stream URL via Selenium Wire: {m3u8_url}")
                    break

        # Save page source and network requests before iframe
        with open(f"{debug_dir}/{player_url.split('/')[-1]}.html", 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        with open(f"{debug_dir}/{player_url.split('/')[-1]}_network.json", 'w', encoding='utf-8') as f:
            json.dump(network_requests, f, indent=2)

        # Fallback 1: Iframe
        if not m3u8_url:
            logging.info(f"No stream via network for {player_url}. Trying iframe.")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            iframe = soup.find('iframe')
            if iframe and iframe.get('src'):
                iframe_url = iframe['src']
                if not iframe_url.startswith(('javascript:', 'about:', '#')):
                    logging.info(f"Loading iframe: {iframe_url}")
                    del driver.requests
                    driver.get(iframe_url)
                    time.sleep(10)

                    # Save iframe source
                    with open(f"{debug_dir}/{player_url.split('/')[-1]}_iframe.html", 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)

                    # Check network requests in iframe
                    for request in driver.requests:
                        if request.response and any(ext in request.url.lower() for ext in ['.m3u8', '.m3u', '.ts']):
                            m3u8_url = request.url
                            logging.info(f"Found stream in iframe network: {m3u8_url}")
                            break

                    # Search iframe source
                    if not m3u8_url:
                        page_source = driver.page_source
                        m3u8_match = re.search(r'(https?://[^\s"\']+\.(m3u8|m3u|ts)[^\s"\']*)', page_source, re.IGNORECASE)
                        if m3u8_match:
                            m3u8_url = m3u8_match.group(1)
                            logging.info(f"Found stream in iframe source: {m3u8_url}")

        # Fallback 2: Video/source tags
        if not m3u8_url:
            logging.info(f"No stream in iframe for {player_url}. Trying video/source tags.")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            for elem in soup.find_all(['video', 'source']):
                src = elem.get('src')
                if src and any(ext in src.lower() for ext in ['.m3u8', '.m3u', '.ts']):
                    m3u8_url = src
                    logging.info(f"Found stream in video/source tag: {m3u8_url}")
                    break

        # Fallback 3: Script parsing
        if not m3u8_url:
            logging.info(f"No stream in video tags for {player_url}. Trying scripts.")
            for script in soup.find_all('script'):
                if script.string:
                    m3u8_match = re.search(r'(https?://[^\s"\']+\.(m3u8|m3u|ts)[^\s"\']*)', script.string, re.IGNORECASE)
                    if m3u8_match:
                        m3u8_url = m3u8_match.group(1)
                        logging.info(f"Found stream in script: {m3u8_url}")
                        break

        # Fallback 4: JavaScript extraction
        if not m3u8_url:
            logging.info(f"No stream in scripts for {player_url}. Trying JavaScript.")
            try:
                js_urls = driver.execute_script(r"""
                    var urls = [];
                    var scripts = document.getElementsByTagName('script');
                    for (var i = 0; i < scripts.length; i++) {
                        if (scripts[i].innerText.match(/\\.(m3u8|m3u|ts)/i)) {
                            var matches = scripts[i].innerText.match(/https?:\/\/[^\\s"']+\\.(m3u8|m3u|ts)[^\\s"']*/g);
                            if (matches) urls = urls.concat(matches);
                        }
                    }
                    return urls;
                """)
                if js_urls:
                    m3u8_url = js_urls[0]
                    logging.info(f"Found stream via JavaScript: {m3u8_url}")
            except Exception as e:
                logging.warning(f"JavaScript extraction failed: {e}")

        # Log failure
        if not m3u8_url:
            logging.error(f"Failed to find stream for {player_url}. Network requests: {len(network_requests)}")

        return m3u8_url

    except Exception as e:
        logging.error(f"Error processing {player_url}: {e}")
        return None

def generate_m3u8_playlist(channels):
    """Generate an M3U8 playlist file."""
    playlist = ['#EXTM3U']
    for channel in channels:
        if channel.get('m3u8_url'):
            playlist.append(
                f'#EXTINF:-1 tvg-name="{channel["name"]}" group-title="DaddyLive",{channel["name"]}\n'
                f'{channel["m3u8_url"]}|Referer=https://daddylive.mp/|User-Agent={HEADERS["User-Agent"]}'
            )
    with open('daddylive.m3u8', 'w', encoding='utf-8') as f:
        f.write('\n'.join(playlist))
    logging.info(f"Generated daddylive.m3u8 with {len(playlist)//2} channels")

def main():
    channels_url = 'https://daddylive.mp/24-7-channels.php'
    driver = setup_selenium()
    try:
        channels = get_channel_list(channels_url)
        if not channels:
            logging.error("No channels found. Exiting.")
            return

        for channel in channels:
            logging.info(f"Processing: {channel['name']} ({channel['url']})")
            m3u8_url = get_m3u8_url(driver, channel['url'])
            channel['m3u8_url'] = m3u8_url

        generate_m3u8_playlist(channels)
    finally:
        driver.quit()

if __name__ == '__main__':
    main()