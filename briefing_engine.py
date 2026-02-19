# briefing_engine.py
# This file handles all data fetching and AI summarization.
# It's the "brain" of the app — the UI calls functions from here.

import requests
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv
import os
from datetime import datetime
from config import CITY, UNITS, NEWS_TOPICS, MAX_NEWS_ARTICLES_PER_TOPIC, BRIEFING_TONE

load_dotenv()

def get_anthropic_client():
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
    except:
        key = os.environ.get("ANTHROPIC_API_KEY")
    return Anthropic(api_key=key)

def get_weather():
    """Fetch current weather for the configured city."""
    try:
        api_key = st.secrets.get("OPENWEATHER_API_KEY")
    except:
        api_key = None
    api_key = api_key or os.environ.get("OPENWEATHER_API_KEY")
    url = "https://api.openweathermap.org/data/2.5/weather"
    
    params = {
        "q": CITY,
        "appid": api_key,
        "units": UNITS
    }
    
    response = requests.get(url, params=params)
    
    # If something goes wrong (bad API key, city not found), 
    # return a message instead of crashing the whole app.
    if response.status_code != 200:
        return {"error": f"Weather fetch failed: {response.status_code}"}
    
    data = response.json()
    
    # Pull out only what we need — the API returns a lot of data we don't use.
    return {
        "city": data["name"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "description": data["weather"][0]["description"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"]
    }


def get_news():
    """Fetch top headlines for each configured topic."""
    try:
        api_key = st.secrets.get("NEWS_API_KEY")
    except:
        api_key = None
    api_key = api_key or os.environ.get("NEWS_API_KEY")
    if not api_key:
        return {"error": "News API key not found"}
    url = "https://newsapi.org/v2/everything"
    
    all_articles = {}
    
    for topic in NEWS_TOPICS:
        params = {
            "q": topic,
            "apiKey": api_key,
            "language": "en",
            "sortBy": "publishedAt",        # Most recent first
            "pageSize": MAX_NEWS_ARTICLES_PER_TOPIC
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            all_articles[topic] = []
            continue
        
        data = response.json()
        
        # Extract just the headline and source for each article.
        articles = []
        for article in data.get("articles", []):
            articles.append({
                "title": article["title"],
                "source": article["source"]["name"],
                "url": article["url"]
            })
        
        all_articles[topic] = articles
    
    return all_articles

def generate_briefing(weather_data, news_data):
    """Send all fetched data to Claude and get back a morning briefing."""
    
    client = get_anthropic_client()  # Add this line
    today = datetime.now().strftime("%A, %B %d, %Y")
    
    # Build a clean text summary of the news to hand to Claude.
    news_text = ""
    for topic, articles in news_data.items():
        news_text += f"\n{topic.upper()}:\n"
        if not articles:
            news_text += "  No articles found.\n"
        else:
            for article in articles:
                news_text += f"  - {article['title']} ({article['source']})\n"
    
    # Handle case where weather fetch failed
    if "error" in weather_data:
        weather_text = "Weather data unavailable."
    else:
        unit_symbol = "°F" if UNITS == "imperial" else "°C"
        speed_unit = "mph" if UNITS == "imperial" else "m/s"
        weather_text = (
            f"{weather_data['city']}: {weather_data['temperature']}{unit_symbol}, "
            f"feels like {weather_data['feels_like']}{unit_symbol}, "
            f"{weather_data['description']}, "
            f"humidity {weather_data['humidity']}%, "
            f"wind {weather_data['wind_speed']} {speed_unit}"
        )
    
    # This is the prompt we send to Claude.
    # Notice how we're injecting all the real data into it.
    prompt = f"""Today is {today}.

Here is the current weather:
{weather_text}

Here are today's top headlines by topic:
{news_text}

Please write a {BRIEFING_TONE} morning briefing based on this information. 
Structure it as follows:
1. A warm, one-sentence greeting that acknowledges the day and weather.
2. A weather summary with any practical advice (what to wear, weather watch, etc).
3. A brief summary of the most interesting or important news across all topics — 
   look for connections between stories if any exist.
4. A single closing thought or question worth thinking about today.

Keep the total length to around 200-250 words. Be specific, not generic."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",   # Cheapest Claude model — perfect for this
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return message.content[0].text


def run_briefing():
    """Master function that orchestrates everything. The UI calls this one function."""
    weather = get_weather()
    print("WEATHER:", weather)  # Add this line
    news = get_news()
    print("NEWS:", news)  # Add this line
    briefing = generate_briefing(weather, news)
    
    return {
        "weather": weather,
        "news": news,
        "briefing": briefing,
        "generated_at": datetime.now().strftime("%I:%M %p")
    }