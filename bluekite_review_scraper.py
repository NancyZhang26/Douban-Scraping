import time
import re
import os
import requests
from fake_useragent import UserAgent
from lxml import etree
import numpy as np
import pandas as pd
from urllib.parse import urljoin
import random
import json
from datetime import datetime

class BluekiteReviewScraper:
    """Scraper for reviews of 蓝风筝 (The Blue Kite) movie on Douban
    
    Uses advanced browser fingerprinting and session management to bypass restrictions
    """
    
    def __init__(self):
        # The Blue Kite (蓝风筝) movie ID on Douban
        self.movie_id = "1303967"  # ID for 蓝风筝
        self.movie_url = f"https://movie.douban.com/subject/{self.movie_id}/"
        self.timeout = 20
        self.cookies_file = "douban_cookies.txt"
        self.debug_dir = "debug_output"
        
        # Create debug directory
        if not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)
            
        # Define columns for reviews dataframe
        self.review_columns = [
            'Username', 'Date', 'Time', 'Location of reviewer', 
            'Rating of film', 'Popularity of review', 'Content', 'Review Type'
        ]
        
        # Initialize a persistent session
        self.session = requests.Session()
        
        # Pre-define common browser fingerprints to randomly choose from
        self.browser_fingerprints = [
            {
                "browser": "Chrome",
                "os": "Windows",
                "version": "121.0.6167.160",
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "accept_language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7"
            },
            {
                "browser": "Edge",
                "os": "Windows",
                "version": "121.0.2277.128",
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
                "accept_language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
            },
            {
                "browser": "Firefox",
                "os": "Windows",
                "version": "122.0",
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
                "accept_language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3"
            },
            {
                "browser": "Safari",
                "os": "MacOS",
                "version": "16.4",
                "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
                "accept_language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
        ]
        
        # Choose a random fingerprint for this session
        self.current_fingerprint = random.choice(self.browser_fingerprints)
        
        # Build common referers list to mimic natural browsing
        self.referers = [
            "https://www.douban.com/",
            "https://movie.douban.com/",
            "https://movie.douban.com/tag/电影/",
            "https://movie.douban.com/explore",
            "https://www.douban.com/search?q=蓝风筝",
            "https://movie.douban.com/tag/中国/",
            "https://movie.douban.com/chart"
        ]
        
    def get_headers(self, referer=None):
        """Get realistic browser headers to avoid detection"""
        # Use random referer from list if not specified
        if not referer:
            referer = random.choice(self.referers)
            
        # Vary Accept parameter slightly
        accepts = [
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        ]
        
        # Create headers that look like a realistic browser
        headers = {
            'User-Agent': self.current_fingerprint["ua"],
            'Accept': random.choice(accepts),
            'Accept-Language': self.current_fingerprint["accept_language"],
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': referer,
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin' if 'douban.com' in referer else 'cross-site',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': random.choice(['max-age=0', 'no-cache']),
            'sec-ch-ua': f'"Not_A Brand";v="99", "{self.current_fingerprint["browser"]}";v="{self.current_fingerprint["version"]}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{self.current_fingerprint["os"]}"',
            'DNT': random.choice(['1', '0']),
            'Priority': random.choice(['u=0, i', 'u=1, i'])
        }
        
        # Add a slight randomization to headers - sometimes browsers don't send all headers
        if random.random() > 0.3:
            for key in ['DNT', 'Priority', 'Sec-Fetch-User']:
                if key in headers and random.random() > 0.7:
                    del headers[key]
                    
        return headers
    
    def get_cookies(self):
        """Get cookies from file or user input with improved parsing"""
        if os.path.exists(self.cookies_file):
            with open(self.cookies_file, 'r') as f:
                cookie_str = f.read().strip()
                if cookie_str:
                    cookies = self.parse_cookie_string(cookie_str)
                    # Update session cookies
                    self.session.cookies.update(cookies)
                    return cookies
        
        print("\n=== DETAILED COOKIE INSTRUCTIONS ===")
        print("1. Open Chrome and navigate to Douban (https://www.douban.com)")
        print("2. Log in to your Douban account")
        print("3. Open Developer Tools (Option + Command + I on Mac, F12 on Windows)")
        print("4. Go to the 'Application' tab")
        print("5. In the left sidebar, expand 'Cookies' and click on 'https://www.douban.com'")
        print("6. Look for cookies like 'dbcl2', 'bid', 'ck', 'll', 'ap', '__utma', etc.")
        print("7. There are two ways to get cookies:")
        print("   a) Use Chrome's copy as cURL and paste below, I'll extract cookies")
        print("   b) Manually copy all cookies in the format: name=value; name2=value2")
        
        cookie_input = input("\nEnter your Douban cookies or cURL command: ")
        
        # Try to parse as cURL command
        if cookie_input.startswith("curl "):
            cookies = self.parse_curl(cookie_input)
        else:
            cookies = self.parse_cookie_string(cookie_input)
            
        if cookies:
            # Save to file
            with open(self.cookies_file, 'w') as f:
                f.write(cookie_input)
            
            # Update session cookies
            self.session.cookies.update(cookies)
            return cookies
        return {}
    
    def parse_curl(self, curl_command):
        """Extract cookies from a cURL command (copied from Chrome)"""
        cookies = {}
        
        # Look for --cookie or -b flag
        cookie_match = re.search(r'(?:--cookie|-b)\s+["\']?([^"\']+)["\']?', curl_command)
        if cookie_match:
            cookies = self.parse_cookie_string(cookie_match.group(1))
        
        # Also look for -H "Cookie: xxx" format
        header_matches = re.findall(r'-H\s+["\']([^"\']+)["\']', curl_command)
        for header in header_matches:
            if header.startswith("Cookie:"):
                cookie_str = header[len("Cookie:"):].strip()
                cookies.update(self.parse_cookie_string(cookie_str))
        
        return cookies
    
    def parse_cookie_string(self, cookie_string):
        """Parse cookie string into dictionary with improved handling"""
        cookies = {}
        if not cookie_string:
            return cookies
            
        # Handle multiple formats (some might have spaces after semicolons, some might not)
        cookie_pairs = re.split(r';\s*', cookie_string)
        for pair in cookie_pairs:
            if '=' in pair:
                name, value = pair.split('=', 1)
                name = name.strip()
                # Handle quoted values
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                cookies[name] = value
        return cookies
    
    def simulate_human_browsing(self):
        """Simulate human browsing behavior before accessing movie page"""
        # This function simulates a natural browsing pattern to avoid bot detection
        start_pages = [
            "https://www.douban.com/",
            "https://movie.douban.com/",
            "https://movie.douban.com/explore"
        ]
        
        # Choose a random starting point
        start_url = random.choice(start_pages)
        print(f"Simulating human browsing starting from {start_url}")
        
        try:
            # Visit home page first
            print("Visiting Douban homepage...")
            response = self.session.get(
                start_url,
                headers=self.get_headers(),
                timeout=self.timeout
            )
            
            # Sleep like a human would after loading a page
            self.human_sleep(1, 3)
            
            # Maybe visit a category page
            if random.random() > 0.3:
                cat_pages = [
                    "https://movie.douban.com/tag/中国",
                    "https://movie.douban.com/tag/经典",
                    "https://movie.douban.com/explore"
                ]
                cat_url = random.choice(cat_pages)
                print(f"Browsing category page: {cat_url}")
                response = self.session.get(
                    cat_url,
                    headers=self.get_headers(referer=start_url),
                    timeout=self.timeout
                )
                
                # Update referrer
                last_url = cat_url
                self.human_sleep(2, 4)
            else:
                last_url = start_url
                
            # Now simulate searching for our movie
            search_term = "蓝风筝" if random.random() > 0.5 else "田壮壮"
            print(f"Searching for {search_term}...")
            search_url = f"https://www.douban.com/search?q={search_term}"
            response = self.session.get(
                search_url,
                headers=self.get_headers(referer=last_url),
                timeout=self.timeout
            )
            
            # Save debug output
            with open(f"{self.debug_dir}/search_page.html", "w", encoding="utf-8") as f:
                f.write(response.text)
                
            self.human_sleep(1, 3)
            
            # Now we're ready to visit the movie page with a natural browsing history
            print("Now proceeding to movie page with human-like browsing history...")
            return True
        
        except Exception as e:
            print(f"Error during human browsing simulation: {e}")
            return False
    
    def human_sleep(self, min_seconds=1, max_seconds=5):
        """More realistic human-like waiting periods"""
        # Humans don't wait in perfect intervals
        base_time = random.uniform(min_seconds, max_seconds)
        # Add some extra randomness - sometimes humans pause longer
        if random.random() > 0.8:
            base_time += random.uniform(1, 3)
        
        print(f"Waiting {base_time:.2f} seconds...")
        time.sleep(base_time)
    
    def verify_login(self, cookies):
        """Verify if the cookies provide authenticated access with improved detection"""
        try:
            # First simulate some human browsing
            self.simulate_human_browsing()
            
            # Try to access the movie page
            print("Verifying login by accessing movie page...")
            response = self.session.get(
                self.movie_url,
                headers=self.get_headers(referer="https://www.douban.com/search?q=蓝风筝"),
                timeout=self.timeout
            )
            
            # Force response encoding to UTF-8 for Chinese characters
            response.encoding = 'utf-8'
            
            # Save the page for debugging - with proper encoding
            with open(f"{self.debug_dir}/main_page.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            
            # Check if we're redirected to login page
            if "accounts.douban.com/passport/login" in response.url:
                print("Login verification failed: redirected to login page")
                return False
                
            # Check if there's content indicating we're logged in
            if '您尚未登录' in response.text or '请先登录' in response.text:
                print("Login verification failed: login prompt found on page")
                return False
            
            # Check for robot detection
            if '机器人' in response.text or 'robot' in response.text.lower():
                print("Bot detection triggered! The site thinks we're a robot.")
                return False
                
            # Look for the movie title to confirm we can access content
            root = etree.HTML(response.text)
            title_elem = root.xpath('//h1/span[@property="v:itemreviewed"]/text()')
            
            # Also try other title selectors
            if not title_elem:
                title_elem = root.xpath('//h1/text()')
            if not title_elem:
                title_elem = root.xpath('//title/text()')
                
            if title_elem:
                print(f"Login verification successful. Page title: {title_elem[0]}")
                return True
            else:
                print("Login verification failed: couldn't find page title")
                return False
                
        except Exception as e:
            print(f"Login verification error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def scrape_reviews(self, review_type="short", pages=5):
        """
        Scrape reviews (short or long) using authenticated requests
        
        Args:
            review_type (str): Type of reviews to scrape ("short" or "long")
            pages (int): Number of pages to scrape
            
        Returns:
            list: List of review dictionaries
        """
        reviews_data = []
        cookies = self.get_cookies()
        
        # Verify login before proceeding
        if not self.verify_login(cookies):
            print("Failed to verify login. Please check your cookies and try again.")
            return []
        
        # Determine URL pattern based on review type
        if review_type == "short":
            # For short reviews - add randomization to sort parameter
            sort_options = ["new_score", "time", "useful"]
            sort_param = random.choice(sort_options)
            url_pattern = f"https://movie.douban.com/subject/{self.movie_id}/comments?start={{}}&limit=20&sort={sort_param}&status=P"
        else:
            # For long reviews
            url_pattern = f"https://movie.douban.com/subject/{self.movie_id}/reviews?start={{}}"
        
        # Add some randomization to the number of pages to scrape
        actual_pages = pages
        if random.random() > 0.7:
            # Sometimes scrape 1-2 fewer pages to look more human-like
            actual_pages = max(1, pages - random.randint(0, 2))
            
        for page in range(actual_pages):
            # Real humans don't always go through pages in perfect order
            if random.random() > 0.9 and page > 0:
                # Sometimes go back a page
                start_idx = max(0, (page - 1) * 20)
                print(f"Acting like a human: going back to a previous page...")
            else:
                start_idx = page * 20
                
            page_url = url_pattern.format(start_idx)
            
            print(f"Scraping {review_type} reviews page {page+1}/{actual_pages} (start={start_idx})")
            
            try:
                # Choose random referer - either previous page or movie main page
                if page == 0:
                    referer = self.movie_url
                else:
                    referer = url_pattern.format((page-1) * 20)
                
                # Make request with session cookies
                response = self.session.get(
                    page_url,
                    headers=self.get_headers(referer=referer),
                    timeout=self.timeout
                )
                
                # Save response for debugging
                with open(f"{self.debug_dir}/{review_type}_reviews_page_{page}.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                
                # Check if redirected to login page
                if "accounts.douban.com/passport/login" in response.url:
                    print(f"Redirected to login page. Authentication cookies may be invalid or expired.")
                    # If this is the first page and cookies failed, ask for new cookies
                    if page == 0:
                        print("Trying to get new cookies...")
                        if os.path.exists(self.cookies_file):
                            os.remove(self.cookies_file)
                        cookies = self.get_cookies()
                        self.session.cookies.update(cookies)
                        if cookies:
                            # Verify the new cookies
                            if not self.verify_login(cookies):
                                print("Failed to verify login with new cookies.")
                                return reviews_data
                                
                            # Retry with new cookies
                            response = self.session.get(
                                page_url,
                                headers=self.get_headers(referer=referer),
                                timeout=self.timeout
                            )
                            # Save retry response
                            with open(f"{self.debug_dir}/{review_type}_reviews_page_{page}_retry.html", "w", encoding="utf-8") as f:
                                f.write(response.text)
                        else:
                            print("No new cookies provided. Aborting.")
                            return reviews_data
                
                # Check for bot detection
                if '机器人' in response.text or 'robot' in response.text.lower():
                    print("Bot detection triggered! The site thinks we're a robot.")
                    print("Trying to recover by waiting longer and changing our fingerprint...")
                    
                    # Change our browser fingerprint
                    self.current_fingerprint = random.choice(self.browser_fingerprints)
                    
                    # Wait longer to appear less bot-like
                    self.human_sleep(30, 60)
                    
                    # Try again with new fingerprint
                    response = self.session.get(
                        page_url,
                        headers=self.get_headers(referer=referer),
                        timeout=self.timeout
                    )
                    
                    # Check if recovery worked
                    if '机器人' in response.text or 'robot' in response.text.lower():
                        print("Still detected as a bot after retry. Consider using a different IP or waiting longer.")
                        return reviews_data
                
                # Parse the page
                root = etree.HTML(response.text)
                
                # Extract items based on review type
                if review_type == "short":
                    # Parse short reviews - multiple selectors for robustness
                    items = root.xpath('//div[@class="comment-item"]')
                    
                    # Try alternative selectors if needed
                    if not items:
                        items = root.xpath('//div[contains(@class, "comment")]')
                    if not items:
                        items = root.xpath('//div[@class="list"]/div')
                    
                    print(f"Found {len(items)} short reviews on page {page+1}")
                    
                    if not items:
                        print("No comment items found. Page might be restricted or structure changed.")
                        # Save the page source for inspection
                        with open(f"{self.debug_dir}/{review_type}_reviews_page_{page}_no_items.html", "w", encoding="utf-8") as f:
                            f.write(response.text)
                            
                        # Try to extract page content to understand the issue
                        page_title = root.xpath('//title/text()')
                        print(f"Page title: {page_title[0] if page_title else 'Not found'}")
                        
                        # Check if page indicates it's empty
                        empty_notifications = root.xpath('//p[contains(@class, "pl")]/text()')
                        if empty_notifications:
                            print(f"Page message: {empty_notifications[0]}")
                    
                    for i, item in enumerate(items):
                        try:
                            # Extract user info - multiple selectors for robustness
                            username = "Unknown"
                            for selector in ['.//a[@class="comment-info"]/text()', 
                                            './/span[@class="comment-info"]/a/text()',
                                            './/div[@class="avatar"]/a/@title',
                                            './/span[contains(@class, "comment-info")]/a/text()']:
                                username_elem = item.xpath(selector)
                                if username_elem:
                                    username = username_elem[0]
                                    break
                            
                            # Extract date/time - try multiple selectors
                            date_raw = ""
                            for selector in ['.//span[@class="comment-time"]/text()',
                                           './/span[@class="comment-date"]/text()',
                                           './/span[contains(@class, "time")]/text()']:
                                date_elem = item.xpath(selector)
                                if date_elem:
                                    date_raw = date_elem[0].strip()
                                    break
                            
                            # Split date and time
                            date_parts = date_raw.split()
                            date = date_parts[0] if len(date_parts) > 0 else ""
                            time_value = date_parts[1] if len(date_parts) > 1 else ""
                            
                            # Extract rating - multiple selectors and classes
                            rating = "No rating"
                            for selector in ['.//span[contains(@class, "allstar")]/@class',
                                           './/span[contains(@class, "rating")]/@class',
                                           './/span[contains(@class, "star")]/@class']:
                                rating_class = item.xpath(selector)
                                if rating_class:
                                    rating_text = rating_class[0]
                                    if 'allstar10' in rating_text or 'rating10' in rating_text or 'star10' in rating_text:
                                        rating = '1 star'
                                    elif 'allstar20' in rating_text or 'rating20' in rating_text or 'star20' in rating_text:
                                        rating = '2 stars'
                                    elif 'allstar30' in rating_text or 'rating30' in rating_text or 'star30' in rating_text:
                                        rating = '3 stars'
                                    elif 'allstar40' in rating_text or 'rating40' in rating_text or 'star40' in rating_text:
                                        rating = '4 stars'
                                    elif 'allstar50' in rating_text or 'rating50' in rating_text or 'star50' in rating_text:
                                        rating = '5 stars'
                                    break
                            
                            # Extract content - multiple selectors
                            content = ""
                            for selector in ['.//span[@class="short"]/text()',
                                           './/p[@class="comment-content"]/text()',
                                           './/div[@class="comment"]/p/text()',
                                           './/*[contains(@class, "comment")]/text()']:
                                content_elem = item.xpath(selector)
                                if content_elem:
                                    content = ' '.join([c.strip() for c in content_elem if c.strip()])
                                    break
                            
                            # Extract votes/popularity - multiple selectors
                            votes = "0"
                            for selector in ['.//span[@class="votes"]/text()',
                                           './/span[contains(@class, "vote-count")]/text()',
                                           './/a[contains(@class, "btn")]/span/text()']:
                                votes_elem = item.xpath(selector)
                                if votes_elem:
                                    votes = votes_elem[0].strip()
                                    break
                            
                            # Try to get location if available
                            location = "N/A"
                            for selector in ['.//span[@class="comment-location"]/text()',
                                           './/span[contains(@class, "from")]/text()']:
                                location_elem = item.xpath(selector)
                                if location_elem:
                                    location = location_elem[0].strip()
                                    break
                            
                            review = {
                                'Username': username,
                                'Date': date,
                                'Time': time_value,
                                'Location of reviewer': location,
                                'Rating of film': rating,
                                'Popularity of review': votes,
                                'Content': content,
                                'Review Type': 'Short'
                            }
                            reviews_data.append(review)
                            
                        except Exception as e:
                            print(f"Error parsing short review {i} on page {page+1}: {e}")
                            continue
                else:
                    # Parse long reviews - multiple selectors for robustness
                    items = root.xpath('//div[contains(@class, "review-item")]')
                    
                    # Try alternative selectors if no items found
                    if not items:
                        items = root.xpath('//div[contains(@class, "review")]')
                    if not items:
                        items = root.xpath('//div[@class="review-list"]/div/div')
                    
                    print(f"Found {len(items)} long reviews on page {page+1}")
                    
                    if not items:
                        print("No review items found. Page might be restricted or structure changed.")
                        # Try a broader search
                        items = root.xpath('//div[contains(@class, "main")]//div[contains(@class, "review") or contains(@class, "content")]')
                        print(f"Using broader search, found {len(items)} possible review items")
                        
                    for i, item in enumerate(items):
                        try:
                            # Extract user info - try multiple possible selectors
                            username = "Unknown"
                            for selector in ['.//a[@class="name"]/text()', './/a[contains(@href, "/people/")]/text()',
                                            './/header/a/text()', './/h3/a/text()', './/span[@class="author"]/a/text()']:
                                username_elem = item.xpath(selector)
                                if username_elem:
                                    username = username_elem[0]
                                    break
                            
                            # Extract date/time - try multiple selectors
                            date_raw = ""
                            for selector in ['.//span[@class="main-meta"]/text()', './/span[@class="time"]/text()',
                                           './/header/span/text()', './/span[@class="review-time"]/text()',
                                           './/span[contains(@class, "date")]/text()']:
                                date_elem = item.xpath(selector)
                                if date_elem:
                                    date_raw = date_elem[0].strip()
                                    break
                                    
                            # Parse date and time
                            date_parts = date_raw.split()
                            date = date_parts[0] if len(date_parts) > 0 else ""
                            time_value = date_parts[1] if len(date_parts) > 1 else ""
                            
                            # Extract rating - try multiple selectors
                            rating = "No rating"
                            for selector in ['.//span[contains(@class, "allstar")]/@class', './/span[contains(@class, "rating")]/@class',
                                           './/header//span[contains(@class, "star")]/@class', './/span[contains(@class, "rate")]/@class']:
                                rating_class = item.xpath(selector)
                                if rating_class:
                                    if 'allstar10' in rating_class[0] or 'rating-star-10' in rating_class[0] or 'star10' in rating_class[0]:
                                        rating = '1 star'
                                    elif 'allstar20' in rating_class[0] or 'rating-star-20' in rating_class[0] or 'star20' in rating_class[0]:
                                        rating = '2 stars'
                                    elif 'allstar30' in rating_class[0] or 'rating-star-30' in rating_class[0] or 'star30' in rating_class[0]:
                                        rating = '3 stars'
                                    elif 'allstar40' in rating_class[0] or 'rating-star-40' in rating_class[0] or 'star40' in rating_class[0]:
                                        rating = '4 stars'
                                    elif 'allstar50' in rating_class[0] or 'rating-star-50' in rating_class[0] or 'star50' in rating_class[0]:
                                        rating = '5 stars'
                                    break
                            
                            # Extract content - try multiple possible selectors
                            content = ""
                            for selector in ['.//div[@class="short-content"]/text()', './/p[@class="content"]/text()',
                                           './/div[@class="review-content"]/text()', './/div[@class="review-content"]//p/text()',
                                           './/div[contains(@class, "content")]//text()']:
                                content_elem = item.xpath(selector)
                                if content_elem:
                                    content = ' '.join([c.strip() for c in content_elem if c.strip()])
                                    # Remove "展开" text that often appears at the end
                                    content = re.sub(r'\s*\(展开\)\s*$', '', content)
                                    break
                                    
                            # If content is still empty, try a more general approach
                            if not content:
                                for content_container in ['.//div[@class="short-content"]', './/div[@class="review-content"]',
                                                        './/div[contains(@class, "content")]']:
                                    content_elems = item.xpath(f'{content_container}//text()')
                                    if content_elems:
                                        content = ' '.join([text.strip() for text in content_elems if text.strip()])
                                        content = re.sub(r'\s*\(展开\)\s*$', '', content)
                                        break
                            
                            # Extract votes/popularity
                            votes = "0"
                            for selector in ['.//span[@class="votes"]/text()', './/a[contains(@class, "action")]/span/text()',
                                           './/a[@class="action-btn up"]/span/text()', './/span[contains(@class, "useful")]/text()']:
                                votes_elem = item.xpath(selector)
                                if votes_elem:
                                    votes = votes_elem[0].strip()
                                    break
                            
                            # Extract reviewer location if available
                            location = "N/A"
                            for selector in ['.//span[@class="loc"]/text()', './/span[contains(@class, "location")]/text()']:
                                loc_elem = item.xpath(selector)
                                if loc_elem:
                                    location = loc_elem[0].strip()
                                    break
                            
                            review = {
                                'Username': username,
                                'Date': date,
                                'Time': time_value,
                                'Location of reviewer': location,
                                'Rating of film': rating,
                                'Popularity of review': votes,
                                'Content': content,
                                'Review Type': 'Long'
                            }
                            reviews_data.append(review)
                            
                        except Exception as e:
                            print(f"Error parsing long review {i} on page {page+1}: {e}")
                            continue
            
            except Exception as e:
                print(f"Error scraping {review_type} reviews page {page+1}: {e}")
                continue
                
            # Add human-like delay between requests
            if page < actual_pages - 1:  # No need to wait after the last page
                # Use gamma distribution for more human-like timing
                # This creates a distribution that clusters around the mean but has occasional longer waits
                delay = np.random.gamma(shape=3, scale=2)  # Mean around 6 seconds
                
                # Sometimes humans take even longer breaks
                if random.random() > 0.85:
                    print("Taking a slightly longer break to seem more human-like...")
                    delay += random.uniform(5, 15)
                    
                print(f"Waiting {delay:.2f} seconds before next request...")
                time.sleep(delay)
                
                # Sometimes simulate the user looking at specific reviews
                if random.random() > 0.7 and reviews_data:
                    print("Simulating clicking on a specific review...")
                    # Just sleep a bit longer - we don't actually need to visit the review page
                    extra_wait = random.uniform(3, 8)
                    time.sleep(extra_wait)
                
        return reviews_data
        
    def scrape_all_reviews(self, short_pages=5, long_pages=3):
        """
        Scrape both short and long reviews
        
        Args:
            short_pages (int): Number of pages of short reviews to scrape
            long_pages (int): Number of pages of long reviews to scrape
            
        Returns:
            DataFrame: DataFrame containing all reviews
        """
        print(f"Starting to scrape reviews for The Blue Kite (ID: {self.movie_id})")
        print(f"Movie URL: {self.movie_url}")
        
        # Generate current timestamp for logs and filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Try different strategies if the default one fails
        all_reviews = []
        retry_attempts = 0
        max_retries = 2
        
        while retry_attempts <= max_retries and not all_reviews:
            try:
                # First simulate natural browsing to warm up cookies and session
                self.simulate_human_browsing()
                
                # Get short reviews
                short_reviews = self.scrape_reviews(review_type="short", pages=short_pages)
                
                # Get long reviews
                long_reviews = self.scrape_reviews(review_type="long", pages=long_pages)
                
                # Combine all reviews
                if short_reviews:
                    print(f"Collected {len(short_reviews)} short reviews")
                    all_reviews.extend(short_reviews)
                else:
                    print("No short reviews collected")
                    
                if long_reviews:
                    print(f"Collected {len(long_reviews)} long reviews")
                    all_reviews.extend(long_reviews)
                else:
                    print("No long reviews collected")
                    
                # If we got no reviews but haven't tried all strategies yet
                if not all_reviews and retry_attempts < max_retries:
                    retry_attempts += 1
                    print(f"\nNo reviews collected. Trying alternate strategy (attempt {retry_attempts}/{max_retries})...")
                    
                    # Change fingerprint for retry
                    self.current_fingerprint = random.choice(self.browser_fingerprints)
                    
                    # Try a different approach - use API if possible
                    if retry_attempts == 1:
                        print("Trying to use API method instead of scraping HTML...")
                        # Mobile API sometimes works better
                        api_url = f"https://m.douban.com/rexxar/api/v2/movie/{self.movie_id}/interests?count=20&start=0&order_by=hot"
                        headers = self.get_headers()
                        headers.update({
                            'Referer': f'https://m.douban.com/movie/subject/{self.movie_id}/',
                            'X-Requested-With': 'XMLHttpRequest'
                        })
                        
                        try:
                            response = self.session.get(api_url, headers=headers, timeout=self.timeout)
                            data = json.loads(response.text)
                            
                            # Save the API response
                            with open(f"{self.debug_dir}/api_response_{timestamp}.json", "w", encoding="utf-8") as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                                
                            # Process API responses if successful
                            if 'interests' in data:
                                for item in data['interests']:
                                    try:
                                        username = item.get('user', {}).get('name', 'Unknown')
                                        rating_value = item.get('rating', {}).get('value', 'No rating')
                                        if rating_value:
                                            rating = f"{rating_value} stars"
                                        else:
                                            rating = "No rating"
                                            
                                        content = item.get('comment', '')
                                        created_at = item.get('create_time', '')
                                        
                                        # Parse date and time if available
                                        date = ''
                                        time_value = ''
                                        if created_at:
                                            try:
                                                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                                date = dt.strftime('%Y-%m-%d')
                                                time_value = dt.strftime('%H:%M:%S')
                                            except:
                                                date = created_at
                                                
                                        review = {
                                            'Username': username,
                                            'Date': date,
                                            'Time': time_value,
                                            'Location of reviewer': item.get('user', {}).get('loc', {}).get('name', 'N/A'),
                                            'Rating of film': rating,
                                            'Popularity of review': str(item.get('useful_count', 0)),
                                            'Content': content,
                                            'Review Type': 'API'
                                        }
                                        all_reviews.append(review)
                                    except Exception as e:
                                        print(f"Error parsing API review: {e}")
                                        continue
                                        
                                print(f"Collected {len(all_reviews)} reviews via API")
                            else:
                                print("API response didn't contain review data")
                                
                        except Exception as e:
                            print(f"Error using API: {e}")
                    
                    # Wait longer before next retry
                    wait_time = random.uniform(45, 90)
                    print(f"Waiting {wait_time:.2f} seconds before next attempt...")
                    time.sleep(wait_time)
                
            except Exception as e:
                print(f"Error during scraping process: {e}")
                import traceback
                traceback.print_exc()
                
                retry_attempts += 1
                if retry_attempts <= max_retries:
                    print(f"\nError occurred. Trying again (attempt {retry_attempts}/{max_retries})...")
                    time.sleep(random.uniform(30, 60))
                
        # Convert to DataFrame
        if all_reviews:
            df_reviews = pd.DataFrame(all_reviews)
            
            # Save to CSV with timestamp to avoid overwriting previous results
            filename = f'blue_kite_reviews_{timestamp}.csv'
            df_reviews.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"Saved {len(df_reviews)} reviews to {filename}")
            
            return df_reviews
        else:
            print("No reviews collected at all after multiple attempts!")
            print("This could be due to various reasons:")
            print("1. The content might be restricted or censored")
            print("2. Douban's bot detection might be very aggressive")
            print("3. The movie page structure might have changed")
            print("4. There might be IP-based restrictions")
            
            print("\nSuggestions:")
            print("1. Try using a VPN with a Chinese IP address")
            print("2. Make sure you have valid cookies from an authenticated Douban session")
            print("3. Try scraping at off-peak hours")
            print("4. Consider using a browser automation tool like Selenium instead")
            
            return pd.DataFrame(columns=self.review_columns)

    def try_browser_spoofing(self):
        """Advanced method to try browser fingerprint spoofing"""
        print("Attempting browser fingerprint spoofing techniques...")
        
        # Create more advanced headers that mimic Chrome's fingerprint exactly
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Referer': 'https://www.douban.com/',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            # Try to include common browser headers in exactly the right order
            'dnt': '1',
            'Pragma': 'no-cache',
            'viewport-width': '1920'
        }
        
        # Try to access main page with these headers
        try:
            print("Attempting access with spoofed Chrome fingerprint...")
            response = self.session.get(
                self.movie_url,
                headers=headers,
                timeout=self.timeout
            )
            
            # Save the response
            with open(f"{self.debug_dir}/spoofed_chrome_response.html", "w", encoding="utf-8") as f:
                f.write(response.text)
                
            # Check if we got past bot detection
            if '机器人' not in response.text and 'robot' not in response.text.lower():
                print("Successfully bypassed bot detection with spoofed fingerprint!")
                return True
            else:
                print("Still detected as a bot with spoofed fingerprint.")
                return False
                
        except Exception as e:
            print(f"Error during browser spoofing attempt: {e}")
            return False

if __name__ == "__main__":
    try:
        # Create scraper
        scraper = BluekiteReviewScraper()
        
        # Get user input for number of pages to scrape
        try:
            print("\nThere are reportedly 18946 short reviews and 300+ long reviews.")
            print("NOTE: Scraping too many pages at once may trigger rate limiting.")
            short_pages = int(input("How many pages of short reviews to scrape? (recommend 5-10): ") or "5")
            long_pages = int(input("How many pages of long reviews to scrape? (recommend 3-5): ") or "3")
        except ValueError:
            print("Invalid input, using default values: 5 pages of short reviews, 3 pages of long reviews")
            short_pages = 5
            long_pages = 3
        
        # First try regular scraping
        reviews_df = scraper.scrape_all_reviews(short_pages=short_pages, long_pages=long_pages)
        
        # If that fails, try browser spoofing
        if reviews_df.empty:
            print("\nRegular scraping failed. Trying advanced browser spoofing technique...")
            if scraper.try_browser_spoofing():
                # Try one more time with browser spoofing
                reviews_df = scraper.scrape_all_reviews(short_pages=short_pages, long_pages=long_pages)
        
        if not reviews_df.empty:
            # Show first few reviews
            print("\nSample of reviews:")
            print(reviews_df.head())
            
            # Show statistics
            print("\nReview Statistics:")
            if 'Rating of film' in reviews_df.columns:
                print("Ratings distribution:")
                print(reviews_df['Rating of film'].value_counts())
            
            if 'Review Type' in reviews_df.columns:
                print("\nReview types:")
                print(reviews_df['Review Type'].value_counts())
        else:
            print("Failed to scrape reviews after multiple attempts.")
            print("This might be due to website restrictions, especially for politically sensitive content.")
            print("Consider using a specialized tool like Selenium with a full browser instance.")
    
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Saving any collected data...")
        # Could add code here to save partial results if desired
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()