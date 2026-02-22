# briefing_engine.py
# This file handles all data fetching and AI summarization.
# It's the "brain" of the app — the UI calls functions from here.

import requests
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()


def get_anthropic_client():
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
    except:
        key = os.environ.get("ANTHROPIC_API_KEY")
    return Anthropic(api_key=key)


def get_weather(profile: dict) -> dict:
    """Fetch current weather for the profile's city."""
    try:
        api_key = st.secrets.get("OPENWEATHER_API_KEY")
    except:
        api_key = None
    api_key = api_key or os.environ.get("OPENWEATHER_API_KEY")

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": profile["city"],
        "appid": api_key,
        "units": profile["units"]
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return {"error": f"Weather fetch failed: {response.status_code}"}

    data = response.json()
    return {
        "city": data["name"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "description": data["weather"][0]["description"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"]
    }


def get_news(profile: dict) -> dict:
    """Fetch top headlines for each topic in the profile."""
    try:
        api_key = st.secrets.get("NEWS_API_KEY")
    except:
        api_key = None
    api_key = api_key or os.environ.get("NEWS_API_KEY")
    if not api_key:
        return {"error": "News API key not found"}

    url = "https://newsapi.org/v2/everything"
    all_articles = {}

    for topic in profile["topics"]:
        params = {
            "q": topic,
            "apiKey": api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": profile["max_articles_per_topic"]
        }

        response = requests.get(url, params=params)

        if response.status_code != 200:
            all_articles[topic] = []
            continue

        data = response.json()
        articles = []
        for article in data.get("articles", []):
            articles.append({
                "title": article["title"],
                "source": article["source"]["name"],
                "url": article["url"]
            })

        all_articles[topic] = articles

    return all_articles


def generate_briefing(weather_data: dict, news_data: dict, profile: dict) -> str:
    """Send all fetched data to Claude and get back a morning briefing."""
    client = get_anthropic_client()
    today = datetime.now().strftime("%A, %B %d, %Y")

    news_text = ""
    for topic, articles in news_data.items():
        news_text += f"\n{topic.upper()}:\n"
        if not articles:
            news_text += "  No articles found.\n"
        else:
            for article in articles:
                news_text += f"  - {article['title']} ({article['source']})\n"

    if "error" in weather_data:
        weather_text = "Weather data unavailable."
    else:
        unit_symbol = "°F" if profile["units"] == "imperial" else "°C"
        speed_unit = "mph" if profile["units"] == "imperial" else "m/s"
        weather_text = (
            f"{weather_data['city']}: {weather_data['temperature']}{unit_symbol}, "
            f"feels like {weather_data['feels_like']}{unit_symbol}, "
            f"{weather_data['description']}, "
            f"humidity {weather_data['humidity']}%, "
            f"wind {weather_data['wind_speed']} {speed_unit}"
        )

    prompt = f"""Today is {today}.

Here is the current weather:
{weather_text}

Here are today's top headlines by topic:
{news_text}

Please write a {profile['briefing_tone']} morning briefing based on this information.
Structure it as follows:
1. A warm, one-sentence greeting that acknowledges the day and weather.
2. A weather summary with any practical advice (what to wear, weather watch, etc).
3. A brief summary of the most interesting or important news across all topics —
   look for connections between stories if any exist.
4. A single closing thought or question worth thinking about today.

Keep the total length to around 200-250 words. Be specific, not generic."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


def run_briefing(profile: dict) -> dict:
    """Master function that orchestrates everything. The UI calls this one function."""
    weather = get_weather(profile)
    news = get_news(profile)
    briefing = generate_briefing(weather, news, profile)

    return {
        "weather": weather,
        "news": news,
        "briefing": briefing,
        "generated_at": datetime.now().strftime("%I:%M %p")
    }
