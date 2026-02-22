# briefing_engine.py
# This file handles all data fetching and AI summarization.
# It's the "brain" of the app — the UI calls functions from here.

import json
import requests
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv
import os
from datetime import datetime, date

load_dotenv()

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")


def get_anthropic_client():
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
    except:
        key = os.environ.get("ANTHROPIC_API_KEY")
    return Anthropic(api_key=key)


def _weather_emoji(description: str) -> str:
    """Map an OpenWeatherMap description string to a weather emoji."""
    desc = description.lower()
    if "thunder" in desc:
        return "⛈️"
    elif "snow" in desc:
        return "🌨️"
    elif "rain" in desc or "drizzle" in desc:
        return "🌧️"
    elif "mist" in desc or "fog" in desc or "haze" in desc:
        return "🌫️"
    elif "clear" in desc:
        return "☀️"
    elif "few clouds" in desc or "scattered" in desc:
        return "⛅"
    elif "cloud" in desc:
        return "☁️"
    return "🌡️"


@st.cache_data(ttl=1800)
def get_weather(profile: dict) -> dict:
    """Fetch current weather for the profile's city. Cached for 30 minutes."""
    try:
        api_key = st.secrets.get("OPENWEATHER_API_KEY")
    except:
        api_key = None
    api_key = api_key or os.environ.get("OPENWEATHER_API_KEY")

    response = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"q": profile["city"], "appid": api_key, "units": profile["units"]}
    )

    if response.status_code != 200:
        return {"error": f"Weather fetch failed: {response.status_code}"}

    data = response.json()
    return {
        "city": data["name"],
        "temperature": round(data["main"]["temp"]),
        "feels_like": round(data["main"]["feels_like"]),
        "description": data["weather"][0]["description"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"]
    }


@st.cache_data(ttl=1800)
def get_forecast(profile: dict) -> list:
    """Fetch today's forecast in 3-hour intervals (next 24 hours). Cached for 30 minutes."""
    try:
        api_key = st.secrets.get("OPENWEATHER_API_KEY")
    except:
        api_key = None
    api_key = api_key or os.environ.get("OPENWEATHER_API_KEY")

    response = requests.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={"q": profile["city"], "appid": api_key, "units": profile["units"], "cnt": 8}
    )

    if response.status_code != 200:
        return []

    entries = []
    for item in response.json().get("list", []):
        dt = datetime.fromtimestamp(item["dt"])
        time_str = dt.strftime("%I %p").lstrip("0")  # "3 PM", "12 PM"
        entries.append({
            "time": time_str,
            "temp": round(item["main"]["temp"]),
            "description": item["weather"][0]["description"],
            "emoji": _weather_emoji(item["weather"][0]["description"]),
            "pop": round(item.get("pop", 0) * 100),  # precipitation probability %
        })

    return entries


@st.cache_data(ttl=1800)
def get_news(profile: dict) -> dict:
    """Fetch top headlines for each topic in the profile. Cached for 30 minutes."""
    try:
        api_key = st.secrets.get("NEWS_API_KEY")
    except:
        api_key = None
    api_key = api_key or os.environ.get("NEWS_API_KEY")
    if not api_key:
        return {"error": "News API key not found"}

    all_articles = {}
    for topic in profile["topics"]:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": topic,
                "apiKey": api_key,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": profile["max_articles_per_topic"]
            }
        )

        if response.status_code != 200:
            all_articles[topic] = []
            continue

        articles = []
        for article in response.json().get("articles", []):
            articles.append({
                "title": article["title"],
                "source": article["source"]["name"],
                "url": article["url"]
            })
        all_articles[topic] = articles

    return all_articles


def stream_briefing(weather_data: dict, forecast_data: list, news_data: dict, profile: dict):
    """Generator that streams the morning briefing from Claude word by word."""
    client = get_anthropic_client()
    today = datetime.now().strftime("%A, %B %d, %Y")
    unit_symbol = "°F" if profile["units"] == "imperial" else "°C"
    speed_unit = "mph" if profile["units"] == "imperial" else "m/s"

    # Build weather text
    if "error" in weather_data:
        weather_text = "Weather data unavailable."
    else:
        weather_text = (
            f"{weather_data['city']}: {weather_data['temperature']}{unit_symbol}, "
            f"feels like {weather_data['feels_like']}{unit_symbol}, "
            f"{weather_data['description']}, "
            f"humidity {weather_data['humidity']}%, "
            f"wind {weather_data['wind_speed']} {speed_unit}"
        )

    # Build forecast text
    if forecast_data:
        forecast_lines = []
        for e in forecast_data:
            line = f"  {e['time']}: {e['temp']}{unit_symbol}, {e['description']}"
            if e["pop"] > 10:
                line += f", {e['pop']}% chance of rain"
            forecast_lines.append(line)
        forecast_text = "\n".join(forecast_lines)
    else:
        forecast_text = "Forecast unavailable."

    # Build news text
    news_text = ""
    for topic, articles in news_data.items():
        news_text += f"\n{topic.upper()}:\n"
        if not articles:
            news_text += "  No articles found.\n"
        else:
            for article in articles:
                news_text += f"  - {article['title']} ({article['source']})\n"

    prompt = f"""Today is {today}.

Current conditions:
{weather_text}

Today's forecast (next 24 hours):
{forecast_text}

Today's top headlines by topic:
{news_text}

Please write a {profile['briefing_tone']} morning briefing based on this information.
Structure it as follows:
1. A warm, one-sentence greeting that acknowledges the day and weather.
2. A weather summary with practical advice (what to wear, any notable changes during the day).
3. A brief summary of the most interesting or important news across all topics —
   look for connections between stories if any exist.
4. A single closing thought or question worth thinking about today.

Keep the total length to around 200-250 words. Be specific, not generic."""

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            yield text


def save_to_history(profile_name: str, data: dict) -> None:
    """Save a briefing to history.json, keeping the last 30 entries per profile."""
    try:
        history = {}
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)

        if profile_name not in history:
            history[profile_name] = []

        today = date.today().isoformat()
        entry = {
            "date": today,
            "generated_at": data["generated_at"],
            "briefing": data["briefing"]
        }

        # Replace today's entry if it already exists, then append
        history[profile_name] = [e for e in history[profile_name] if e["date"] != today]
        history[profile_name].append(entry)
        history[profile_name] = history[profile_name][-30:]  # keep last 30

        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass  # Don't crash the app if history save fails


def load_history(profile_name: str) -> list:
    """Load briefing history for a profile, sorted newest first."""
    try:
        if not os.path.exists(HISTORY_FILE):
            return []
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        entries = history.get(profile_name, [])
        return sorted(entries, key=lambda e: e["date"], reverse=True)
    except Exception:
        return []
