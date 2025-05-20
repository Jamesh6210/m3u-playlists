async def main():
    """Main entry point for the script."""
    # Parse command line arguments here if needed
    output_file = "Extra-channels-updated.m3u"
    base_playlist = None  # "original_playlist.m3u" if you have one
    headless = False  # Set to False for debugging - seeing the browser can help
    debug = True  # Enable saving HTML for debugging
    
    # Limit to a small number of channels for initial testing
    max_channels = 10  # Set to None to process all channels
    
    scraper = PlaylistScraper(
        output_file=output_file,
        base_playlist=base_playlist,
        headless=headless,
        debug=debug,
        max_channels=max_channels
    )
    
    await scraper.run()#!/usr/bin/env python3
"""
DaddyLive M3U8 Playlist Scraper

This script scrapes the 24/7 channels from https://daddylive.dad/24-7-channels.php,
extracts the m3u8 stream URLs, and creates an updated .m3u playlist file.
"""

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.async_api import async_playwright, Page, Browser, BrowserContext


class PlaylistScraper:
    """Scraper for m3u8 playlists from DaddyLive."""

    BASE_URL = "https://daddylive.dad"
    CHANNELS_URL = f"{BASE_URL}/24-7-channels.php"
    
    def __init__(self, 
                 output_file: str = "Extra-channels-updated.m3u",
                 base_playlist: Optional[str] = None,
                 headless: bool = True,
                 debug: bool = False,
                 max_channels: Optional[int] = None) -> None:
        """
        Initialize the scraper.
        
        Args:
            output_file: Path to save the updated playlist
            base_playlist: Optional path to a base playlist to maintain order
            headless: Whether to run the browser in headless mode
            debug: Enable debug mode (saves HTML for inspection)
            max_channels: Optional limit on how many channels to process (for testing)
        """
        self.output_file = output_file
        self.base_playlist = base_playlist
        self.headless = headless
        self.debug = debug
        self.max_channels = max_channels
        self.existing_channels = {}
        
    async def run(self) -> None:
        """Main method to run the scraper."""
        if self.base_playlist and os.path.exists(self.base_playlist):
            self.existing_channels = self._parse_base_playlist(self.base_playlist)
            print(f"Loaded {len(self.existing_channels)} channels from base playlist")
            
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await self._setup_browser_context(browser)
            try:
                page = await context.new_page()
                
                # Set up a console logger
                page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
                
                # Setup request interception to capture XHR/fetch requests with m3u8 URLs
                m3u8_urls = {}
                
                # Set up request interception to look for m3u8 URLs
                await self._setup_request_monitoring(page, m3u8_urls)
                
                # Get all channel links from main page
                channel_links = await self._get_channel_links(page)
                if not channel_links:
                    print("No channel links found. Attempting alternate method...")
                    # Try an alternate method if the first fails
                    channel_links = await self._get_channel_links_alt(page)
                
                print(f"Found {len(channel_links)} channel links")
                
                # Limit the number of channels if specified (useful for testing)
                if self.max_channels is not None and len(channel_links) > self.max_channels:
                    print(f"Limiting to {self.max_channels} channels for testing")
                    # Choose a few specific channels first if they exist
                    special_channels = ["51", "356", "357", "358", "302"]
                    special_found = []
                    regular_channels = []
                    
                    for channel in channel_links:
                        if channel[0] in special_channels:
                            special_found.append(channel)
                        else:
                            regular_channels.append(channel)
                    
                    # Fill remaining slots with regular channels
                    remaining_slots = self.max_channels - len(special_found)
                    if remaining_slots > 0:
                        regular_subset = regular_channels[:remaining_slots]
                        channel_links = special_found + regular_subset
                    else:
                        channel_links = special_found[:self.max_channels]
                
                # Process each channel to extract stream URLs
                channels_data = await self._process_channels(context, channel_links, m3u8_urls)
                
                # Print statistics
                found_streams = sum(1 for data in channels_data.values() if data.get('stream_url'))
                print(f"Found {found_streams} working streams out of {len(channel_links)} channels")
                
                # Generate and save the playlist
                await self._generate_playlist(channels_data)
                
            finally:
                await context.close()
                await browser.close()
    
    async def _setup_browser_context(self, browser: Browser) -> BrowserContext:
        """Setup browser context with necessary settings."""
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            # Remove the invalid permission
            # permissions=["autoplay_media"],
        )
        
        # Set extra HTTP headers to appear more like a real browser
        await context.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://daddylive.dad/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "sec-ch-ua": '"Google Chrome";v="123", "Not;A=Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        })
        
        # Configure context to permit autoplay
        # We'll handle this differently, as autoplay_policy is not directly settable
        await context.add_init_script("""
            // Override autoplay policy
            Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 1});
            // Allow autoplay
            HTMLMediaElement.prototype.play = (function(original) {
                return function() {
                    return original.apply(this, arguments);
                };
            })(HTMLMediaElement.prototype.play);
        """)
        
        return context
    
    async def _setup_request_monitoring(self, page: Page, m3u8_urls: Dict[str, str]) -> None:
        """Set up request interception to capture m3u8 URLs."""
        # Monitor requests for m3u8 files
        async def handle_request(request):
            url = request.url
            if '.m3u8' in url:
                # Extract the channel ID from the referrer URL
                referrer = request.headers.get('referer', '')
                match = re.search(r'stream-(\d+)\.php', referrer)
                if match:
                    channel_id = match.group(1)
                    m3u8_urls[channel_id] = url
                    print(f"Captured m3u8 URL for channel {channel_id}: {url}")
                else:
                    print(f"Found m3u8 URL but couldn't determine channel: {url}")
        
        # Also monitor responses which might contain m3u8 URLs
        async def handle_response(response):
            url = response.url
            if '.m3u8' in url:
                referrer = response.request.headers.get('referer', '')
                match = re.search(r'stream-(\d+)\.php', referrer)
                if match:
                    channel_id = match.group(1)
                    m3u8_urls[channel_id] = url
                    print(f"Captured m3u8 URL from response for channel {channel_id}: {url}")
                else:
                    print(f"Found m3u8 URL in response but couldn't determine channel: {url}")
            
            # For HTML responses, check for embedded m3u8 URLs
            if response.status == 200 and response.request.resource_type == 'document':
                try:
                    text = await response.text()
                    if 'm3u8' in text:
                        m3u8_matches = re.findall(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', text)
                        referrer = response.request.headers.get('referer', '')
                        match = re.search(r'stream-(\d+)\.php', referrer)
                        
                        if match and m3u8_matches:
                            channel_id = match.group(1)
                            m3u8_urls[channel_id] = m3u8_matches[0]
                            print(f"Extracted m3u8 URL from response content for channel {channel_id}: {m3u8_matches[0]}")
                except Exception as e:
                    pass
        
        # Setup page to handle all types of requests
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        # Set up a console logger to help with debugging
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    
    async def _get_channel_links(self, page: Page) -> List[Tuple[str, str]]:
        """
        Get all channel links from the main page.
        
        Returns:
            List of tuples (channel_id, channel_name)
        """
        print(f"Loading channels page: {self.CHANNELS_URL}")
        
        # Use extended timeout and wait for network idle
        await page.goto(self.CHANNELS_URL, timeout=60000)
        await page.wait_for_load_state("domcontentloaded", timeout=30000)
        
        # Give extra time for JavaScript to render content
        await asyncio.sleep(3)
        
        try:
            # First try waiting for specific elements to appear
            await page.wait_for_selector(".container", timeout=10000)
            print("Main container found on page")
        except Exception as e:
            print(f"Warning: Container selector not found: {e}")
        
        # Wait for network to be idle
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            print(f"Warning: networkidle timeout: {e}")
        
        # Additional sleep after networkidle
        await asyncio.sleep(5)
        
        if self.debug:
            html = await page.content()
            with open("debug_main_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Saved main page HTML to debug_main_page.html")
        
        # Try different selector strategies
        selectors = [
            "a[href^='stream/stream']",
            "a[href*='stream-']",
            ".channel-box a",
            "div.card a",
            ".container a[href*='stream']"
        ]
        
        channel_links = []
        for selector in selectors:
            try:
                print(f"Trying selector: {selector}")
                # Use evaluate to run JavaScript in the page context
                links = await page.evaluate(f"""() => {{
                    const elements = document.querySelectorAll("{selector}");
                    return Array.from(elements).map(el => [el.href, el.textContent.trim() || el.title || "Unknown Channel"]);
                }}""")
                
                if links:
                    print(f"Found {len(links)} links with selector: {selector}")
                    for href, name in links:
                        match = re.search(r'stream-(\d+)\.php', href)
                        if match:
                            channel_id = match.group(1)
                            # Clean up the name if needed
                            cleaned_name = name.strip()
                            if not cleaned_name:
                                cleaned_name = f"Channel {channel_id}"
                            channel_links.append((channel_id, cleaned_name))
                    
                    if channel_links:
                        break
            except Exception as e:
                print(f"Error with selector {selector}: {e}")
        
        # If still no links found, try using regex on the raw HTML
        if not channel_links:
            try:
                html = await page.content()
                stream_links = re.findall(r'href=[\'"]([^\'"]*stream-(\d+)\.php)[\'"]', html)
                title_matches = re.findall(r'href=[\'"]([^\'"]*stream-(\d+)\.php)[\'"][^>]*>([^<]+)', html)
                
                channel_map = {}
                # First, extract titles where available
                for match in title_matches:
                    url, channel_id, title = match[0], match[1], match[2].strip()
                    if title:
                        channel_map[channel_id] = title
                
                # Then process all links, using titles where available
                for match in stream_links:
                    url, channel_id = match[0], match[1]
                    name = channel_map.get(channel_id, f"Channel {channel_id}")
                    channel_links.append((channel_id, name))
                
                if channel_links:
                    print(f"Found {len(channel_links)} links using regex")
            except Exception as e:
                print(f"Error with regex extraction: {e}")
        
        return channel_links
    
    async def _get_channel_links_alt(self, page: Page) -> List[Tuple[str, str]]:
        """
        Alternative method to get channel links by brute-forcing URLs.
        This is a fallback if the normal extraction fails.
        """
        # If we know the range of channel IDs, we can generate URLs
        # This is a fallback method that makes assumptions about the site structure
        channel_links = []
        
        # Let's try checking the HTML source for pattern recognition
        html = await page.content()
        
        # Look for any patterns like stream-123.php in the HTML
        stream_matches = re.findall(r'stream-(\d+)\.php', html)
        if stream_matches:
            unique_ids = set(stream_matches)
            print(f"Found {len(unique_ids)} unique stream IDs in HTML source")
            for channel_id in unique_ids:
                # Use a generic name since we don't have the actual names
                channel_links.append((channel_id, f"Channel {channel_id}"))
        
        # If still no links found, generate some based on common ranges
        if not channel_links:
            print("Trying to generate channel IDs based on common ranges...")
            # This is a guess - we'll test IDs in a reasonable range
            for channel_id in range(300, 500):  # Adjust range as needed
                channel_links.append((str(channel_id), f"Channel {channel_id}"))
        
        return channel_links
    
    async def _process_channels(self, context: BrowserContext, 
                               channel_links: List[Tuple[str, str]], 
                               m3u8_urls: Dict[str, str]) -> Dict[str, dict]:
        """
        Process each channel to extract stream URLs.
        
        Args:
            context: Browser context
            channel_links: List of channel IDs and names
            m3u8_urls: Dict to store captured m3u8 URLs
            
        Returns:
            Dict mapping channel IDs to channel data
        """
        channels_data = {}
        
        # Process channels in batches to avoid overwhelming the system
        batch_size = 3  # Smaller batch size to reduce load
        
        for i in range(0, len(channel_links), batch_size):
            batch = channel_links[i:i+batch_size]
            tasks = []
            
            for channel_id, channel_name in batch:
                task = self._process_channel(context, channel_id, channel_name, m3u8_urls)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            for channel_id, channel_name, stream_url in results:
                if stream_url:
                    channels_data[channel_id] = {
                        'name': channel_name,
                        'stream_url': stream_url
                    }
            
            # Add a short delay between batches to avoid overwhelming the server
            await asyncio.sleep(2)
        
        return channels_data
    
    async def _process_channel(self, context: BrowserContext, 
                              channel_id: str, channel_name: str,
                              m3u8_urls: Dict[str, str]) -> Tuple[str, str, Optional[str]]:
        """
        Process a single channel to extract its stream URL.
        
        Args:
            context: Browser context
            channel_id: Channel ID
            channel_name: Channel name
            m3u8_urls: Dict of m3u8 URLs captured via request interception
            
        Returns:
            Tuple of (channel_id, channel_name, stream_url)
        """
        print(f"Processing channel {channel_id}: {channel_name}")
        stream_url = None
        
        channel_url = f"{self.BASE_URL}/stream/stream-{channel_id}.php"
        
        try:
            # Set up a listener for m3u8 URLs in this specific channel
            m3u8_for_channel = []
            
            page = await context.new_page()
            
            # Enhanced request interceptor specifically for this page
            async def intercept_m3u8(request):
                url = request.url
                if '.m3u8' in url:
                    print(f"Channel {channel_id} - Intercepted m3u8: {url}")
                    m3u8_for_channel.append(url)
            
            page.on("request", intercept_m3u8)
            
            # Set up response interception too
            async def intercept_response(response):
                url = response.url
                if '.m3u8' in url:
                    print(f"Channel {channel_id} - Intercepted m3u8 response: {url}")
                    m3u8_for_channel.append(url)
                    
                # Also check for iframe sources in responses
                if response.status == 200 and response.request.resource_type == 'document':
                    try:
                        text = await response.text()
                        if 'm3u8' in text:
                            matches = re.findall(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', text)
                            for match in matches:
                                print(f"Channel {channel_id} - Found m3u8 in response: {match}")
                                m3u8_for_channel.append(match)
                    except:
                        pass
            
            page.on("response", intercept_response)
            
            try:
                # Set up a listener for console messages (useful for debugging)
                page.on("console", lambda msg: print(f"CONSOLE ({channel_id}): {msg.text}"))
                
                # Navigate to the channel page with longer timeout
                print(f"Opening channel URL: {channel_url}")
                await page.goto(channel_url, timeout=45000, wait_until="domcontentloaded")
                
                # Wait for network to be mostly idle
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    print(f"Channel {channel_id} - networkidle timeout, continuing anyway")
                
                # Try clicking on the video area to initiate playback
                try:
                    await page.click('div#player', timeout=5000)
                    print(f"Channel {channel_id} - Clicked on player area")
                except:
                    try:
                        await page.click('video', timeout=5000)
                        print(f"Channel {channel_id} - Clicked on video element")
                    except:
                        print(f"Channel {channel_id} - No player element found to click")
                
                # Wait for possible AJAX or dynamic content
                await asyncio.sleep(3)
                
                # Save debug info for some channels
                if self.debug and (len(m3u8_for_channel) > 0 or channel_id in ["356", "357", "358", "51", "302"]):
                    html = await page.content()
                    with open(f"debug_channel_{channel_id}.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    print(f"Saved debug HTML for channel {channel_id}")
                
                # Check our intercepted URLs first
                if m3u8_for_channel:
                    stream_url = m3u8_for_channel[0]  # Take the first one
                    print(f"Channel {channel_id} - Using intercepted stream URL: {stream_url}")
                
                # Check global interception list
                elif channel_id in m3u8_urls:
                    stream_url = m3u8_urls[channel_id]
                    print(f"Channel {channel_id} - Using previously intercepted URL: {stream_url}")
                
                else:
                    # Enhanced methods to extract stream URLs
                    
                    # Method 1: Look at network resources
                    try:
                        resources = await page.evaluate("""
                            () => {
                                const resources = performance.getEntriesByType('resource');
                                return resources.map(r => r.name).filter(url => url.includes('.m3u8'));
                            }
                        """)
                        
                        if resources and len(resources) > 0:
                            stream_url = resources[0]
                            print(f"Channel {channel_id} - Found in performance resources: {stream_url}")
                    except Exception as e:
                        print(f"Error checking performance resources: {e}")
                    
                    # Method 2: Check for iframes and parse their content
                    if not stream_url:
                        try:
                            iframe_sources = await page.evaluate("""
                                () => {
                                    return Array.from(document.querySelectorAll('iframe')).map(f => f.src);
                                }
                            """)
                            
                            if iframe_sources:
                                for iframe_src in iframe_sources:
                                    if iframe_src:
                                        print(f"Channel {channel_id} - Found iframe: {iframe_src}")
                                        
                                        # Try to navigate to the iframe source
                                        try:
                                            iframe_page = await context.new_page()
                                            await iframe_page.goto(iframe_src, timeout=30000)
                                            iframe_html = await iframe_page.content()
                                            
                                            # Look for m3u8 links
                                            m3u8_matches = re.findall(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', iframe_html)
                                            if m3u8_matches:
                                                stream_url = m3u8_matches[0]
                                                print(f"Channel {channel_id} - Found in iframe: {stream_url}")
                                                
                                            await iframe_page.close()
                                            
                                            if stream_url:
                                                break
                                                
                                        except Exception as e:
                                            print(f"Error checking iframe {iframe_src}: {e}")
                                            try:
                                                await iframe_page.close()
                                            except:
                                                pass
                        except Exception as e:
                            print(f"Error checking iframes: {e}")
                    
                    # Method 3: Check for HLS.js configuration
                    if not stream_url:
                        try:
                            hls_config = await page.evaluate("""
                                () => {
                                    // Try to find HLS.js configuration
                                    if (window.hls && window.hls.url) {
                                        return window.hls.url;
                                    }
                                    
                                    // Look for common HLS.js patterns
                                    const scripts = document.querySelectorAll('script');
                                    for (const script of scripts) {
                                        if (script.textContent && script.textContent.includes('.m3u8')) {
                                            const m3u8Match = script.textContent.match(/(https?:[^"'\\s]+\\.m3u8[^"'\\s]*)/);
                                            if (m3u8Match) {
                                                return m3u8Match[1];
                                            }
                                        }
                                    }
                                    
                                    return null;
                                }
                            """)
                            
                            if hls_config:
                                stream_url = hls_config
                                print(f"Channel {channel_id} - Found in HLS config: {stream_url}")
                        except Exception as e:
                            print(f"Error checking HLS config: {e}")
                    
                    # Method 4: Check video elements deeply
                    if not stream_url:
                        try:
                            video_sources = await page.evaluate("""
                                () => {
                                    // Check video sources with full detail
                                    const sources = [];
                                    
                                    // Direct video elements
                                    const videos = document.querySelectorAll('video');
                                    for (const video of videos) {
                                        if (video.src && video.src.includes('.m3u8')) {
                                            sources.push(video.src);
                                        }
                                        
                                        // Check source elements
                                        const videoSources = video.querySelectorAll('source');
                                        for (const source of videoSources) {
                                            if (source.src && source.src.includes('.m3u8')) {
                                                sources.push(source.src);
                                            }
                                        }
                                        
                                        // Check currentSrc
                                        if (video.currentSrc && video.currentSrc.includes('.m3u8')) {
                                            sources.push(video.currentSrc);
                                        }
                                    }
                                    
                                    // Check object and embed elements too
                                    const objects = document.querySelectorAll('object, embed');
                                    for (const obj of objects) {
                                        if (obj.data && obj.data.includes('.m3u8')) {
                                            sources.push(obj.data);
                                        }
                                    }
                                    
                                    return sources;
                                }
                            """)
                            
                            if video_sources and len(video_sources) > 0:
                                stream_url = video_sources[0]
                                print(f"Channel {channel_id} - Found in video sources: {stream_url}")
                        except Exception as e:
                            print(f"Error checking video sources: {e}")
                    
                    # Method 5: Search in the page content for m3u8 URLs
                    if not stream_url:
                        try:
                            html = await page.content()
                            m3u8_matches = re.findall(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', html)
                            if m3u8_matches:
                                stream_url = m3u8_matches[0]
                                print(f"Channel {channel_id} - Found in HTML regex: {stream_url}")
                        except Exception as e:
                            print(f"Error searching for m3u8 in HTML: {e}")
                    
                    # Method 6: Check window objects deeply with explicit patterns
                    if not stream_url:
                        try:
                            stream_url = await page.evaluate("""
                                () => {
                                    // Common variable names that might contain stream URLs
                                    const varNames = ['streamUrl', 'stream_url', 'videoUrl', 'video_url', 
                                                     'hlsUrl', 'hls_url', 'source', 'src', 'url'];
                                    
                                    // Check global variables
                                    for (const name of varNames) {
                                        if (window[name] && typeof window[name] === 'string' && 
                                            window[name].includes('.m3u8')) {
                                            return window[name];
                                        }
                                    }
                                    
                                    // Check common objects
                                    const objNames = ['player', 'videoPlayer', 'config', 'options', 'settings'];
                                    for (const objName of objNames) {
                                        const obj = window[objName];
                                        if (obj && typeof obj === 'object') {
                                            for (const name of varNames) {
                                                if (obj[name] && typeof obj[name] === 'string' && 
                                                    obj[name].includes('.m3u8')) {
                                                    return obj[name];
                                                }
                                            }
                                        }
                                    }
                                    
                                    return null;
                                }
                            """)
                            
                            if stream_url:
                                print(f"Channel {channel_id} - Found in window objects: {stream_url}")
                        except Exception as e:
                            print(f"Error checking window objects: {e}")
                
                print(f"Channel {channel_id} stream URL: {stream_url}")
                
            except Exception as e:
                print(f"Error processing channel {channel_id}: {e}")
            
            finally:
                await page.close()
                
        except Exception as e:
            print(f"Failed to create page for channel {channel_id}: {e}")
        
        return channel_id, channel_name, stream_url
    
    def _parse_base_playlist(self, playlist_path: str) -> Dict[str, dict]:
        """
        Parse an existing M3U playlist to maintain channel order.
        
        Args:
            playlist_path: Path to the base playlist file
            
        Returns:
            Dict mapping channel IDs to channel data
        """
        channels = {}
        
        with open(playlist_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Skip the first line if it's the M3U header
        start_idx = 1 if lines and lines[0].strip() == '#EXTM3U' else 0
        
        i = start_idx
        while i < len(lines) - 1:
            line = lines[i].strip()
            if line.startswith('#EXTINF:'):
                # Extract channel name from the EXTINF line
                name_match = re.search(r'tvg-name="([^"]+)"', line)
                if not name_match:
                    name_match = re.search(r'#EXTINF:[^,]*,\s*(.*)', line)
                
                channel_name = name_match.group(1) if name_match else "Unknown Channel"
                
                # Next line should be the URL
                if i + 1 < len(lines):
                    url = lines[i + 1].strip()
                    
                    # Extract channel ID from the URL if possible
                    id_match = re.search(r'stream-(\d+)', url)
                    channel_id = id_match.group(1) if id_match else f"unknown_{i}"
                    
                    channels[channel_id] = {
                        'name': channel_name,
                        'stream_url': url,
                        'extinf': line,
                        'order': len(channels)  # Keep track of original order
                    }
                    
                    i += 2  # Skip the URL line
                    continue
            
            i += 1
            
        return channels
    
    async def _generate_playlist(self, new_channels: Dict[str, dict]) -> None:
        """
        Generate and save the updated M3U playlist.
        
        Args:
            new_channels: Dict mapping channel IDs to channel data
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            f.write(f'#PLAYLIST: DaddyLive 24/7 Channels (Updated: {now})\n')
            
            # First add channels that exist in the base playlist to maintain order
            added_channels = set()
            if self.existing_channels:
                # Sort by original order
                for channel_id, data in sorted(self.existing_channels.items(), 
                                              key=lambda item: item[1].get('order', 999999)):
                    # If we have an updated URL for this channel, use it
                    if channel_id in new_channels:
                        name = data['name']
                        stream_url = new_channels[channel_id]['stream_url']
                        
                        # Use the original EXTINF line if available, or create a new one
                        if 'extinf' in data:
                            extinf = data['extinf']
                        else:
                            extinf = f'#EXTINF:-1 tvg-name="{name}",{name}'
                        
                        f.write(f'{extinf}\n{stream_url}\n')
                        added_channels.add(channel_id)
            
            # Add any new channels that weren't in the base playlist
            for channel_id, data in new_channels.items():
                if channel_id not in added_channels:
                    name = data['name']
                    stream_url = data['stream_url']
                    extinf = f'#EXTINF:-1 tvg-name="{name}",{name}'
                    f.write(f'{extinf}\n{stream_url}\n')
            
        print(f"Playlist saved to {self.output_file}")


async def main():
    """Main entry point for the script."""
    # Parse command line arguments here if needed
    output_file = "Extra-channels-updated.m3u"
    base_playlist = None  # "original_playlist.m3u" if you have one
    headless = False  # Set to False for debugging - seeing the browser can help
    debug = True  # Enable saving HTML for debugging
    
    scraper = PlaylistScraper(
        output_file=output_file,
        base_playlist=base_playlist,
        headless=headless,
        debug=debug
    )
    
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())