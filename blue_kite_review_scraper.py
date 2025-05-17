import time
import re
from lxml import etree
import pandas as pd
import numpy as np
import requests
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import getpass

class BlueKiteScraper:
    """
    Scraper for Blue Sky movie reviews on Douban
    """
    def __init__(self):
        # First we need to find the movie ID by searching for "The Blue Kite" on Douban
        self.movie_id = None  # Will be set after searching
        self.movie_url = None  # Will be set after finding the movie
        self.driver = None  # Will be set up for login and subsequent scraping
        
        # Define XPaths for short reviews
        self.short_review_locators = {
            'username': '//div[@class="comment-item"]//a[@class="comment-info"]/text()',
            'date': '//div[@class="comment-item"]//span[@class="comment-time"]/text()',
            'rating': '//div[@class="comment-item"]//span[contains(@class, "rating")]/@class',
            'content': '//div[@class="comment-item"]//span[@class="short"]/text()',
            'votes': '//div[@class="comment-item"]//span[@class="votes"]/text()',
            'location': None  # Douban short reviews don't typically show location
        }
        
        # Define XPaths for long reviews
        self.long_review_locators = {
            'username': '//div[@class="review-item"]//a[@class="name"]/text()',
            'date': '//div[@class="review-item"]//span[@class="main-meta"]/text()',
            'rating': '//div[@class="review-item"]//span[contains(@class, "rating")]/@class',
            'content': '//div[@class="review-item"]//div[@class="short-content"]/text()',
            'votes': '//div[@class="review-item"]//a[contains(@class, "action-item")][1]/span/text()',
            'location': None  # Douban reviews don't typically show location
        }
        
    def get_headers(self):
        """Settings for headers"""
        ua = UserAgent()
        user_agent = ua.random
        headers = {'user-agent': user_agent}
        return headers
        
    def set_chrome_options(self, proxies=False):
        """Chrome webdriver settings"""
        chrome_options = Options()
        chrome_options.add_argument(f'--user-agent={self.get_headers()["user-agent"]}')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1200,900')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        return chrome_options
        
    def login_to_douban(self, username=None, password=None):
        """
        Log in to Douban using Selenium
        """
        # Set up Chrome driver
        chrome_options = self.set_chrome_options()
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get("https://accounts.douban.com/passport/login")
        
        # Wait for the login page to load
        time.sleep(3)
        
        try:
            # Switch to password login if needed
            password_login_tab = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//li[contains(text(), "密码登录")]'))
            )
            password_login_tab.click()
            time.sleep(1)
            
            # Get credentials if not provided
            if not username:
                username = input("Enter your Douban username/email/phone: ")
            if not password:
                password = getpass.getpass("Enter your Douban password: ")
            
            # Find username and password input fields
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//input[@id="username"]'))
            )
            password_field = self.driver.find_element(By.XPATH, '//input[@id="password"]')
            
            # Input credentials
            username_field.send_keys(username)
            password_field.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, '//a[contains(@class, "btn-account")]')
            login_button.click()
            
            # Wait for login process
            time.sleep(5)
            
            # Check if login was successful by looking for user avatar or profile link
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//a[@class="bn-more"]'))
                )
                print("Login successful!")
                return True
            except:
                print("Login failed. Please check your credentials.")
                return False
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def find_movie(self, movie_name="蓝风筝"):
        """
        Search for the movie and get its Douban ID
        """
        if not self.driver:
            print("Please login first using login_to_douban() method")
            return False
            
        try:
            # Navigate to search page
            search_url = f"https://www.douban.com/search?q={movie_name}"
            self.driver.get(search_url)
            
            # Wait for search results to load
            time.sleep(3)
            
            # Look for movie links in search results
            movie_links = self.driver.find_elements(By.XPATH, '//div[@class="result"]//a[contains(@href, "movie.douban.com/subject/")]')
            
            if not movie_links:
                print("No movie found with that name. Try searching for '蓝风筝' (Chinese name).")
                return False
                
            # Click the first result (most relevant)
            movie_links[0].click()
            
            # Wait for movie page to load
            time.sleep(3)
            
            # Get current URL which contains the movie ID
            current_url = self.driver.current_url
            self.movie_id = re.findall(r'subject/(\d+)', current_url)[0]
            self.movie_url = current_url
            
            print(f"Found movie: {current_url}")
            print(f"Movie ID: {self.movie_id}")
            
            return True
            
        except Exception as e:
            print(f"Error finding movie: {e}")
            return False
            
    def scrape_short_reviews(self, pages=5):
        """
        Scrape short reviews for the movie
        """
        if not self.movie_id:
            print("Movie ID not set. Please find the movie first.")
            return None
            
        if not self.driver:
            print("Driver not initialized. Please login first.")
            return None
            
        reviews_data = []
        
        for page in range(pages):
            page_url = f"https://movie.douban.com/subject/{self.movie_id}/comments?start={page*20}&limit=20&sort=new_score&status=P"
            
            print(f"Scraping short reviews page {page+1}/{pages}")
            
            try:
                self.driver.get(page_url)
                time.sleep(np.random.randint(2, 5) + np.random.random())
                
                # Parse the page content
                html = self.driver.page_source
                root = etree.HTML(html)
                
                # Extract review elements
                comment_items = root.xpath('//div[@class="comment-item"]')
                
                for item in comment_items:
                    try:
                        # Extract data from each review
                        username = item.xpath('.//a[@class="comment-info"]/text()')[0] if item.xpath('.//a[@class="comment-info"]/text()') else "Unknown"
                        date_raw = item.xpath('.//span[@class="comment-time"]/text()')[0].strip() if item.xpath('.//span[@class="comment-time"]/text()') else ""
                        
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
                        content = item.xpath('.//span[@class="short"]/text()')[0].strip() if item.xpath('.//span[@class="short"]/text()') else ""
                        votes = item.xpath('.//span[@class="votes"]/text()')[0] if item.xpath('.//span[@class="votes"]/text()') else "0"
                        
                        review = {
                            'Username': username,
                            'Date': date,
                            'Time': time_value,
                            'Location of reviewer': 'N/A',  # Not available in short reviews
                            'Rating of film': rating,
                            'Popularity of review': votes,
                            'Content': content,
                            'Review Type': 'Short'
                        }
                        reviews_data.append(review)
                    except Exception as e:
                        print(f"Error parsing review item: {e}")
                        continue
                
            except Exception as e:
                print(f"Error scraping short reviews page {page+1}: {e}")
                continue
                
        return reviews_data
        
    def scrape_long_reviews(self, pages=3):
        """
        Scrape long reviews for the movie
        """
        if not self.movie_id:
            print("Movie ID not set. Please find the movie first.")
            return None
            
        if not self.driver:
            print("Driver not initialized. Please login first.")
            return None
            
        reviews_data = []
        
        for page in range(pages):
            page_url = f"https://movie.douban.com/subject/{self.movie_id}/reviews?start={page*20}"
            
            print(f"Scraping long reviews page {page+1}/{pages}")
            
            try:
                self.driver.get(page_url)
                time.sleep(np.random.randint(3, 6) + np.random.random())
                
                # Parse the page content
                html = self.driver.page_source
                root = etree.HTML(html)
                
                # Extract review elements
                review_items = root.xpath('//div[@class="review-item"]')
                
                for item in review_items:
                    try:
                        # Extract data from each review
                        username = item.xpath('.//a[@class="name"]/text()')[0] if item.xpath('.//a[@class="name"]/text()') else "Unknown"
                        date_raw = item.xpath('.//span[@class="main-meta"]/text()')[0].strip() if item.xpath('.//span[@class="main-meta"]/text()') else ""
                        
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
                        content = item.xpath('.//div[@class="short-content"]/text()')[0].strip() if item.xpath('.//div[@class="short-content"]/text()') else ""
                        votes = item.xpath('.//a[contains(@class, "action-btn")][1]/span/text()')[0] if item.xpath('.//a[contains(@class, "action-btn")][1]/span/text()') else "0"
                        
                        review = {
                            'Username': username,
                            'Date': date_raw,
                            'Time': '',  # Long reviews typically don't show time
                            'Location of reviewer': 'N/A',  # Not available in reviews
                            'Rating of film': rating,
                            'Popularity of review': votes,
                            'Content': content,
                            'Review Type': 'Long'
                        }
                        reviews_data.append(review)
                    except Exception as e:
                        print(f"Error parsing review item: {e}")
                        continue
                
            except Exception as e:
                print(f"Error scraping long reviews page {page+1}: {e}")
                continue
                
        return reviews_data
        
    def scrape_all_reviews(self, short_pages=5, long_pages=3):
        """
        Scrape both short and long reviews
        """
        # Get short reviews
        short_reviews = self.scrape_short_reviews(pages=short_pages)
        
        # Get long reviews
        long_reviews = self.scrape_long_reviews(pages=long_pages)
        
        # Combine all reviews
        all_reviews = []
        if short_reviews:
            all_reviews.extend(short_reviews)
        if long_reviews:
            all_reviews.extend(long_reviews)
            
        # Convert to DataFrame
        df_reviews = pd.DataFrame(all_reviews)
        
        return df_reviews
        
    def cleanup(self):
        """
        Close the browser and clean up resources
        """
        if self.driver:
            self.driver.quit()
            self.driver = None
        
if __name__ == "__main__":
    # Create scraper
    scraper = BlueKiteScraper()
    
    try:
        # Login to Douban
        if scraper.login_to_douban():
            # Find the movie (The Blue Kite)
            if scraper.find_movie("蓝风筝"):
                # Scrape reviews
                reviews_df = scraper.scrape_all_reviews(short_pages=3, long_pages=2)
                
                if reviews_df is not None and not reviews_df.empty:
                    # Save to CSV
                    reviews_df.to_csv('blue_kite_reviews.csv', index=False, encoding='utf-8-sig')
                    print(f"Saved {len(reviews_df)} reviews to blue_kite_reviews.csv")
                    
                    # Show first few reviews
                    print("\nSample of reviews:")
                    print(reviews_df.head())
                else:
                    print("No reviews found or error during scraping.")
            else:
                print("Failed to find the movie.")
        else:
            print("Failed to login to Douban.")
    finally:
        # Always clean up resources
        scraper.cleanup()