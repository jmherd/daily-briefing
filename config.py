# config.py
# Manages user profiles for the daily briefing app.
# Edit profiles.json directly, or use the in-app sidebar to create/edit profiles.

import json
import os

PROFILES_FILE = os.path.join(os.path.dirname(__file__), "profiles.json")


def load_profiles() -> dict:
    """Load all profiles from profiles.json. Returns empty dict if file missing."""
    if not os.path.exists(PROFILES_FILE):
        return {}
    with open(PROFILES_FILE, "r") as f:
        return json.load(f)


def save_profiles(profiles: dict) -> None:
    """Save all profiles to profiles.json."""
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2)
