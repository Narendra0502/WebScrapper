
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time
import requests
import base64
from io import BytesIO

# Initialize Flask app
app = Flask(__name__)

# Initialize MongoDB connection
# Load environment variables
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

# Use environment variable for MongoDB connection
mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = client['Scraper']
events_collection = db['events']
subscribers_collection = db['subscribers']

def scrape_events():
    # Set up Selenium WebDriver with headless option
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Use this for Render deployment
    driver = webdriver.Chrome(options=options)
    
    # Open the target website
    url = "https://www.eventbrite.com/d/australia--sydney/events/"
    driver.get(url)

    # Wait for the page to load
    time.sleep(2)

    full_html = driver.page_source
    soup = BeautifulSoup(full_html, "html.parser")

    main_contents = soup.find("div", class_="main-content")
    popular = main_contents.find("div", class_="popular_events--bucket-wrapper")
    cards = popular.find_all("div", class_="small-card-mobile eds-l-pad-all-2")

    # Clear existing events
    events_collection.delete_many({})

    # Process and store events
    for card in cards:
        detail = card.find('div', class_="Stack_root__1ksk7")
        a_tag = detail.find('a')
        p_tags = detail.find_all('p')
        
        # Find image element
        img_element = card.find('img')
        image_url = img_element.get('src') if img_element else None
        image_data = None
        
        # Download and encode image if available
        if image_url:
            try:
                response = requests.get(image_url)
                if response.status_code == 200:
                    image_data = base64.b64encode(response.content).decode('utf-8')
            except Exception as e:
                print(f"Error downloading image: {e}")

        event_data = {
            'title': a_tag.text,
            'url': a_tag.get('href'),
            'date': p_tags[0].text,
            'location': p_tags[1].text,
            'price': p_tags[2].text,
            'image_url': image_url,
            'image_data': image_data,
            'last_updated': datetime.now().isoformat()
        }
        events_collection.insert_one(event_data)

    # Close the browser
    driver.quit()

# Flask Routes
@app.route('/')
def index():
    # First scrape the events
    try:
        scrape_events()
    except Exception as e:
        print(f"Scraping error: {e}")
        
    # Then fetch and display them
    events = list(events_collection.find())
    return render_template('index.html', events=events)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')
    ticket_url = request.form.get('ticket_url')
    
    # Store email in MongoDB
    subscriber_data = {
        'email': email,
        'ticket_url': ticket_url,
        'timestamp': datetime.now().isoformat()
    }
    subscribers_collection.insert_one(subscriber_data)
    
    return redirect(ticket_url)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
