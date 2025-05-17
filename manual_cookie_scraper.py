import time
import re
import os
import json
from lxml import etree
import pandas as pd
import numpy as np
import requests
from fake_useragent import UserAgent

class ManualCookieBlueKiteScraper:
    """
    Simplified Blue Kite (蓝风筝) movie reviews scraper using manual cookies
    """
    def __init__(self):
        # The Blue Kite movie ID on Douban
        self.movie_id = "1307690"  # ID for 蓝风筝 (The Blue Kite)
        self.movie_url = f"https://movie.douban.com/subject/{self.movie_id}/"
        self.cookies_file = "douban_cookies.txt"
        self.debug_dir = "debug_output"
        
        # Create debug directory
        if not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)
        
    def get_headers(self):
        """Settings for headers with randomized user agent"""
        ua = UserAgent()
        user_agent = ua.random
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Referer': 'https://movie.douban.com/'
        }
        return headers
    
    def get_cookie_string(self):
        """
        Get cookie string from user input
        """
        if os.path.exists(self.cookies_file):
            with open(self.cookies_file, 'r') as f:
                return f.read().strip()
        
        print("\n=== MANUAL COOKIE INSTRUCTIONS ===")
        print("1. Open Chrome and navigate to Douban (https://www.douban.com)")
        print("2. Log in to your Douban account")
        print("3. After logging in, press F12 to open Developer Tools")
        print("4. Go to the 'Application' tab (you might need to click the >> icon to find it)")
        print("5. In the left sidebar, expand 'Cookies' and click on 'https://www.douban.com'")
        print("6. Find the cookie named 'dbcl2' or any that looks like an authentication cookie")
        print("7. Copy the entire cookie string from all relevant cookies")
        print("8. Paste it below when prompted")
        
        cookie_str = input("\nEnter your Douban cookies (or press Enter to skip): ")
        if cookie_str:
            with open(self.cookies_file, 'w') as f:
                f.write(cookie_str)
        return cookie_str
    
    def parse_cookie_string(self, cookie_string):
        """Parse cookie string into dictionary"""
        cookies = {}
        if not cookie_string:
            return cookies
            
        cookie_pairs = cookie_string.split(';')
        for pair in cookie_pairs:
            if '=' in pair:
                name, value = pair.strip().split('=', 1)
                cookies[name] = value
        return cookies
    
    def scrape_reviews(self, review_type="short", pages=5):
        """
        Scrape reviews (short or long) using requests with cookies
        """
        reviews_data = []
        cookies = self.parse_cookie_string(self.get_cookie_string())
        
        # Determine URL pattern based on review type
        if review_type == "short":
            url_pattern = f"https://movie.douban.com/subject/{self.movie_id}/comments?start={{}}0&limit=20&sort=new_score&status=P"
        else:  # long reviews
            url_pattern = f"https://movie.douban.com/subject/{self.movie_id}/reviews?start={{}}"
        
        for page in range(pages):
            page_url = url_pattern.format(page * 2)  # Start parameter is page * 20, but we format it as page * 2 + 0
            
            print(f"Scraping {review_type} reviews page {page+1}/{pages}")
            
            try:
                # Make request with cookies
                response = requests.get(
                    page_url,
                    headers=self.get_headers(),
                    cookies=cookies,
                    timeout=10
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
                        cookies = self.parse_cookie_string(self.get_cookie_string())
                        if cookies:
                            # Retry with new cookies
                            response = requests.get(
                                page_url,
                                headers=self.get_headers(),
                                cookies=cookies,
                                timeout=10
                            )
                            # Save retry response
                            with open(f"{self.debug_dir}/{review_type}_reviews_page_{page}_retry.html", "w", encoding="utf-8") as f:
                                f.write(response.text)
                        else:
                            print("No new cookies provided. Continuing without authentication.")
                
                # Parse the page
                root = etree.HTML(response.text)
                
                # Extract items based on review type
                if review_type == "short":
                    # Parse short reviews
                    items = root.xpath('//div[@class="comment-item"]')
                    print(f"Found {len(items)} short reviews on page {page+1}")
                    
                    for i, item in enumerate(items):
                        try:
                            # Extract user info
                            username_elem = item.xpath('.//a[@class="comment-info"]/text()')
                            username = username_elem[0] if username_elem else "Unknown"
                            
                            # Extract date/time
                            date_elem = item.xpath('.//span[@class="comment-time"]/text()')
                            date_raw = date_elem[0].strip() if date_elem else ""
                            
                            # Split date and time
                            date_parts = date_raw.split()
                            date = date_parts[0] if len(date_parts) > 0 else ""
                            time_value = date_parts[1] if len(date_parts) > 1 else ""
                            
                            # Extract rating
                            rating_class = item.xpath('.//span[contains(@class, "allstar")]/@class')
                            rating = "No rating"
                            if rating_class:
                                if 'allstar10' in rating_class[0]:
                                    rating = '1 star'
                                elif 'allstar20' in rating_class[0]:
                                    rating = '2 stars'
                                elif 'allstar30' in rating_class[0]:
                                    rating = '3 stars'
                                elif 'allstar40' in rating_class[0]:
                                    rating = '4 stars'
                                elif 'allstar50' in rating_class[0]:
                                    rating = '5 stars'
                            
                            # Extract content and votes
                            content_elem = item.xpath('.//span[@class="short"]/text()')
                            content = content_elem[0].strip() if content_elem else ""
                            
                            votes_elem = item.xpath('.//span[@class="votes"]/text()')
                            votes = votes_elem[0] if votes_elem else "0"
                            
                            review = {
                                'Username': username,
                                'Date': date,
                                'Time': time_value,
                                'Location of reviewer': 'N/A',
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
                    # Parse long reviews
                    items = root.xpath('//div[contains(@class, "review-item")]')
                    
                    # Try alternative selector if no items found
                    if not items:
                        items = root.xpath('//div[contains(@class, "review")]')
                        
                    print(f"Found {len(items)} long reviews on page {page+1}")
                    
                    for i, item in enumerate(items):
                        try:
                            # Extract user info - try multiple possible selectors
                            username = "Unknown"
                            for selector in ['.//a[@class="name"]/text()', './/a[contains(@href, "/people/")]/text()']:
                                username_elem = item.xpath(selector)
                                if username_elem:
                                    username = username_elem[0]
                                    break
                            
                            # Extract date
                            date_raw = ""
                            for selector in ['.//span[@class="main-meta"]/text()', './/span[@class="time"]/text()']:
                                date_elem = item.xpath(selector)
                                if date_elem:
                                    date_raw = date_elem[0].strip()
                                    break
                            
                            # Extract rating
                            rating = "No rating"
                            for selector in ['.//span[contains(@class, "allstar")]/@class', './/span[contains(@class, "rating")]/@class']:
                                rating_class = item.xpath(selector)
                                if rating_class:
                                    if 'allstar10' in rating_class[0] or 'rating-star-10' in rating_class[0]:
                                        rating = '1 star'
                                    elif 'allstar20' in rating_class[0] or 'rating-star-20' in rating_class[0]:
                                        rating = '2 stars'
                                    elif 'allstar30' in rating_class[0] or 'rating-star-30' in rating_class[0]:
                                        rating = '3 stars'
                                    elif 'allstar40' in rating_class[0] or 'rating-star-40' in rating_class[0]:
                                        rating = '4 stars'
                                    elif 'allstar50' in rating_class[0] or 'rating-star-50' in rating_class[0]:
                                        rating = '5 stars'
                                    break
                            
                            # Extract content - try multiple possible selectors
                            content = ""
                            for selector in ['.//div[@class="short-content"]/text()', './/p[@class="content"]/text()']:
                                content_elem = item.xpath(selector)
                                if content_elem:
                                    content = content_elem[0].strip()
                                    # Remove "展开" text that often appears at the end
                                    content = re.sub(r'\s*\(展开\)\s*$', '', content)
                                    break
                                    
                            # If content is still empty, try a more general approach
                            if not content:
                                content_elems = item.xpath('.//div[@class="short-content"]//text()')
                                if content_elems:
                                    content = ' '.join([text.strip() for text in content_elems if text.strip()])
                                    content = re.sub(r'\s*\(展开\)\s*$', '', content)
                            
                            # Extract votes/popularity
                            votes = "0"
                            for selector in ['.//span[@class="votes"]/text()', './/a[contains(@class, "action")]/span/text()']:
                                votes_elem = item.xpath(selector)
                                if votes_elem:
                                    votes = votes_elem[0]
                                    break
                            
                            review = {
                                'Username': username,
                                'Date': date_raw,
                                'Time': '',  # Long reviews typically don't show time
                                'Location of reviewer': 'N/A',
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
                
            # Add delay between requests
            time.sleep(np.random.randint(3, 5) + np.random.random())
                
        return reviews_data
    
    def scrape_all_reviews(self, short_pages=5, long_pages=3):
        """
        Scrape both short and long reviews
        """
        print(f"Starting to scrape reviews for The Blue Kite (ID: {self.movie_id})")
        print(f"Movie URL: {self.movie_url}")
        
        # Get short reviews
        short_reviews = self.scrape_reviews(review_type="short", pages=short_pages)
        
        # Get long reviews
        long_reviews = self.scrape_reviews(review_type="long", pages=long_pages)
        
        # Combine all reviews
        all_reviews = []
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
            
        # Convert to DataFrame
        if all_reviews:
            df_reviews = pd.DataFrame(all_reviews)
            return df_reviews
        else:
            print("No reviews collected at all!")
            return pd.DataFrame()
        
if __name__ == "__main__":
    # Create scraper and get reviews
    scraper = ManualCookieBlueKiteScraper()
    
    # Scrape reviews
    reviews_df = scraper.scrape_all_reviews(short_pages=5, long_pages=3)
    
    if not reviews_df.empty:
        # Save to CSV with UTF-8 encoding to properly handle Chinese characters
        reviews_df.to_csv('blue_kite_reviews.csv', index=False, encoding='utf-8-sig')
        print(f"Saved {len(reviews_df)} reviews to blue_kite_reviews.csv")
        
        # Show first few reviews
        print("\nSample of reviews:")
        print(reviews_df.head())
    else:
        print("Failed to scrape reviews or no reviews found.")
        print("Note: Douban might restrict access to reviews for this film.")
        print("Try accessing the movie page manually to check if reviews are visible.")