# config.py
# This file holds all user preferences for the daily briefing.
# It's the only file you need to edit to personalize your experience.

# --- LOCATION ---
# Used to fetch your local weather.
# Find your city name at openweathermap.org — use the exact spelling they use.
CITY = "Tampa, US"          # Format: "City, CountryCode"
UNITS = "imperial"          # "imperial" for Fahrenheit, "metric" for Celsius

# --- NEWS TOPICS ---
# These are the subjects your briefing will pull headlines for.
# Keep it to 3-5 topics for a clean, readable briefing.
# Examples: "artificial intelligence", "supply chain", "Formula 1", "real estate"
NEWS_TOPICS = [
    "artificial intelligence",
    "technology",
    "business",
    "personal finance",
    "hiking",
    "golfing",
    "University of Florida football",
]

# --- BRIEFING PREFERENCES ---
# Controls the tone and length of your AI-generated summary.
BRIEFING_TONE = "professional but conversational"
MAX_NEWS_ARTICLES_PER_TOPIC = 3   # How many headlines to pull per topic