import time
import re
import os
import urllib
from fake_useragent import UserAgent
import requests
from requests_html import HTMLSession
from lxml import etree
import numpy as np
import pandas as pd
from requests_toolbelt import threaded

class AuthenticatedDoubanSpiderMan(object):
    """Enhanced version of DoubanSpiderMan with proper authentication
    
    Based on the original GitHub repository with added authentication capabilities
    using cookie-based authentication instead of Selenium login automation.
    """

    def __init__(self, movie_id="1307690"):
        # ID for 蓝风筝 (The Blue Kite) by default
        self.movie_id = movie_id
        self.movie_url = f"https://movie.douban.com/subject/{self.movie_id}/"
        self.timeout = 20
        self.cookies_file = "douban_cookies.txt"
        self.debug_dir = "debug_output"
        
        # Create debug directory
        if not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)
        
        # Define locators from original DoubanSpiderMan
        self.locators = {
            'original_title': '//*[@id="content"]/h1/span[@property="v:itemreviewed"]/text()',
            'release_year': '//*[@id="content"]/h1/span[@class="year"]/text()',
            'poster_url': '//*[@id="mainpic"]/a/img/@src',
            'director': '//*[@id="info"]/span[1]/span[2]/a[@rel="v:directedBy"]/text()',
            'writer': '//*[@id="info"]/span[2]/span[@class="attrs"]/a[@*]/text()',
            'actor': '//*[@id="info"]/span[@class="actor"]//*[@rel="v:starring"]/text()',
            'genre': '//*[@id="info"]/span[@property="v:genre"]/text()',
            'region': '//*[@id="info"]/text()',
            'language': '//*[@id="info"]/text()',
            'release_date': '//*[@id="info"]/span[@property="v:initialReleaseDate"]/text()',
            'runtime': '//*[@id="info"]/span[@property="v:runtime"]/text()',
            'alternative_title': '//*[@id="info"]/text()',
            'imdb_id': '//*[@id="info"]/a[@rel="nofollow"]/text()',
            'vote_average': '//*[@id="interest_sectl"]/div/div[2]/strong/text()',
            'vote_count': '//*[@id="interest_sectl"]/div/div[2]/div/div[2]/a/span/text()',
            'vote_start5_percent': '//*[@id="interest_sectl"]/div/div[3]/div[1]/span[2]/text()',
            'vote_start4_percent': '//*[@id="interest_sectl"]/div/div[3]/div[2]/span[2]/text()',
            'vote_start3_percent': '//*[@id="interest_sectl"]/div/div[3]/div[3]/span[2]/text()',
            'vote_start2_percent': '//*[@id="interest_sectl"]/div/div[3]/div[4]/span[2]/text()',
            'vote_start1_percent': '//*[@id="interest_sectl"]/div/div[3]/div[5]/span[2]/text()',
            'tag': '//*[@id="content"]/div[@class="grid-16-8 clearfix"]/div[2]/div[@class="tags"]/div/a[@*]/text()',
            'watched_count': '//*[@id="subject-others-interests"]/div/a[1]/text()',
            'towatch_count': '//*[@id="subject-others-interests"]/div/a[2]/text()',
            'overview': '//*[@id="link-report"]//*[@property="v:summary"]/text()',
            'recommend_name': '//*[@id="recommendations"]/div/dl[@*]/dd/a/text()',
            'recommend_url': '//*[@id="recommendations"]/div/dl[@*]/dd/a/@href',
            # Review locators
            'short_review': '//*[@id="hot-comments"]/div[@*]/div/p/span/text()',
            'short_review_count': '//*[@id="comments-section"]/div[1]/h2/span/a/text()',
            'full_review_title': '//*[@class="reviews mod movie-content"]/div[2]/div[@*]/div/div[@class="main-bd"]/h2/a/text()',
            'full_review_short': '//*/div[@class="short-content"]/text()',
            'full_review_count': '//*[@id="content"]//*[@class="reviews mod movie-content"]/header//*/a[@href="reviews"]/text()',
            'full_review_link': '//*[@class="reviews mod movie-content"]/div[2]/div[@*]/div/div[@class="main-bd"]/h2/a/@href',
            'discussion_count': '//*[@id="content"]//*/div[@class="section-discussion"]/p/a/text()',
            'ask_count': '//*[@id="askmatrix"]//*/span[@class="pl"]/a/text()',
        }
        
        # Define columns for the dataframe
        self.columns = ['id'] + [val for val in self.locators]
        
        # Define columns for reviews dataframe
        self.review_columns = [
            'Username', 'Date', 'Time', 'Location of reviewer', 
            'Rating of film', 'Popularity of review', 'Content', 'Review Type'
        ]

    def get_headers(self):
        """
        Settings for headers with randomized user agent
        """
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
    
    def get_cookies(self):
        """
        Get cookies from file or user input
        """
        if os.path.exists(self.cookies_file):
            with open(self.cookies_file, 'r') as f:
                cookie_str = f.read().strip()
                if cookie_str:
                    return self.parse_cookie_string(cookie_str)
        
        print("\n=== MANUAL COOKIE INSTRUCTIONS ===")
        print("1. Open Chrome and navigate to Douban (https://www.douban.com)")
        print("2. Log in to your Douban account")
        print("3. Open Developer Tools (Option + Command + I on Mac, F12 on Windows)")
        print("4. Go to the 'Application' tab")
        print("5. In the left sidebar, expand 'Cookies' and click on 'https://www.douban.com'")
        print("6. Find the cookie named 'dbcl2' and other cookies")
        print("7. Copy the entire cookie string from all relevant cookies")
        print("8. Paste it below when prompted")
        
        cookie_str = input("\nEnter your Douban cookies (e.g., dbcl2=\"value\"; bid=value): ")
        if cookie_str:
            with open(self.cookies_file, 'w') as f:
                f.write(cookie_str)
            return self.parse_cookie_string(cookie_str)
        return {}
    
    def parse_cookie_string(self, cookie_string):
        """
        Parse cookie string into dictionary
        """
        cookies = {}
        if not cookie_string:
            return cookies
            
        cookie_pairs = cookie_string.split(';')
        for pair in cookie_pairs:
            if '=' in pair:
                name, value = pair.strip().split('=', 1)
                # Handle quoted values
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                cookies[name] = value
        return cookies
    
    def scrape_reviews(self, review_type="short", pages=5):
        """
        Scrape reviews (short or long) using authenticated requests
        """
        reviews_data = []
        cookies = self.get_cookies()
        
        # Determine URL pattern based on review type
        if review_type == "short":
            url_pattern = f"https://movie.douban.com/subject/{self.movie_id}/comments?start={{}}&limit=20&sort=new_score&status=P"
        else:  # long reviews
            url_pattern = f"https://movie.douban.com/subject/{self.movie_id}/reviews?start={{}}"
        
        for page in range(pages):
            page_url = url_pattern.format(page * 20)
            
            print(f"Scraping {review_type} reviews page {page+1}/{pages}")
            
            try:
                # Make request with cookies
                response = requests.get(
                    page_url,
                    headers=self.get_headers(),
                    cookies=cookies,
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
                        if cookies:
                            # Retry with new cookies
                            response = requests.get(
                                page_url,
                                headers=self.get_headers(),
                                cookies=cookies,
                                timeout=self.timeout
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
    
    def scrape_movie_details(self):
        """
        Scrape details about the movie using the original DoubanSpiderMan locators
        """
        cookies = self.get_cookies()
        
        try:
            # Make request with cookies
            response = requests.get(
                self.movie_url,
                headers=self.get_headers(),
                cookies=cookies,
                timeout=self.timeout
            )
            
            # Save response for debugging
            with open(f"{self.debug_dir}/movie_details.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            
            # Check if redirected to login page
            if "accounts.douban.com/passport/login" in response.url:
                print(f"Redirected to login page. Authentication cookies may be invalid or expired.")
                print("Trying to get new cookies...")
                if os.path.exists(self.cookies_file):
                    os.remove(self.cookies_file)
                cookies = self.get_cookies()
                if cookies:
                    # Retry with new cookies
                    response = requests.get(
                        self.movie_url,
                        headers=self.get_headers(),
                        cookies=cookies,
                        timeout=self.timeout
                    )
                    # Save retry response
                    with open(f"{self.debug_dir}/movie_details_retry.html", "w", encoding="utf-8") as f:
                        f.write(response.text)
                else:
                    print("No new cookies provided. Continuing without authentication.")
            
            # Parse the page
            root = etree.HTML(response.text)
            
            # Extract details using the locators
            results = {'id': self.movie_id}
            
            for locator in self.locators:
                try:
                    results[locator] = root.xpath(self.locators[locator])
                except Exception as e:
                    print(f"Error extracting {locator}: {e}")
                    results[locator] = []
            
            return results
            
        except Exception as e:
            print(f"Error scraping movie details: {e}")
            return {'id': self.movie_id}
    
    def crawl(self, short_review_pages=5, long_review_pages=3):
        """
        Scrape everything: movie details and reviews
        """
        print(f"Starting to scrape data for movie ID: {self.movie_id}")
        print(f"Movie URL: {self.movie_url}")
        
        # Get movie details
        print("Scraping movie details...")
        movie_details = self.scrape_movie_details()
        
        # Get short reviews
        short_reviews = self.scrape_reviews(review_type="short", pages=short_review_pages)
        
        # Get long reviews
        long_reviews = self.scrape_reviews(review_type="long", pages=long_review_pages)
        
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
        
        # Create movie details dataframe
        movie_df = pd.DataFrame([movie_details], columns=self.columns)
        
        # Create reviews dataframe
        if all_reviews:
            reviews_df = pd.DataFrame(all_reviews)
            return movie_df, reviews_df
        else:
            print("No reviews collected at all!")
            return movie_df, pd.DataFrame(columns=self.review_columns)
        
if __name__ == "__main__":
    # Create scraper for The Blue Kite movie
    douban_crawler = AuthenticatedDoubanSpiderMan(movie_id="1307690")
    
    # Scrape movie details and reviews
    movie_details_df, reviews_df = douban_crawler.crawl(short_review_pages=5, long_review_pages=3)
    
    # Save movie details to CSV
    movie_details_df.to_csv('blue_kite_details.csv', index=False, encoding='utf-8-sig')
    print(f"Saved movie details to blue_kite_details.csv")
    
    # Save reviews to CSV
    if not reviews_df.empty:
        reviews_df.to_csv('blue_kite_reviews.csv', index=False, encoding='utf-8-sig')
        print(f"Saved {len(reviews_df)} reviews to blue_kite_reviews.csv")
        
        # Show first few reviews
        print("\nSample of reviews:")
        print(reviews_df.head())
    else:
        print("No reviews were collected to save.")