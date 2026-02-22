# app.py
# This is the Streamlit UI — the only file that deals with what the user sees.
# It calls run_briefing() from briefing_engine and displays the results.

import streamlit as st
from briefing_engine import run_briefing
from config import load_profiles, save_profiles

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Daily Briefing",
    page_icon="☀️",
    layout="centered"
)

# --- SESSION STATE ---
if "briefing_data" not in st.session_state:
    st.session_state.briefing_data = None
if "selected_profile_name" not in st.session_state:
    st.session_state.selected_profile_name = None

# --- SIDEBAR: PROFILE MANAGEMENT ---
with st.sidebar:
    st.title("👤 Profiles")
    profiles = load_profiles()
    profile_names = list(profiles.keys())

    if profile_names:
        # Ensure the stored selection is still valid after edits/deletes
        if st.session_state.selected_profile_name not in profile_names:
            st.session_state.selected_profile_name = profile_names[0]

        idx = profile_names.index(st.session_state.selected_profile_name)
        chosen = st.selectbox("Active Profile", profile_names, index=idx)

        # Clear briefing when the user switches profiles
        if chosen != st.session_state.selected_profile_name:
            st.session_state.selected_profile_name = chosen
            st.session_state.briefing_data = None
            st.rerun()

        profile = profiles[chosen]
        st.caption(f"📍 {profile['city']} · {profile['units'].title()}")

        # Edit current profile
        with st.expander("✏️ Edit Profile"):
            with st.form("edit_profile_form"):
                e_city = st.text_input("City", value=profile["city"])
                e_units = st.selectbox(
                    "Units", ["imperial", "metric"],
                    index=0 if profile["units"] == "imperial" else 1
                )
                e_topics = st.text_area(
                    "Topics (one per line)",
                    value="\n".join(profile["topics"]),
                    height=200
                )
                e_tone = st.text_input("Briefing Tone", value=profile["briefing_tone"])
                e_max = st.number_input(
                    "Max articles per topic", min_value=1, max_value=10,
                    value=profile["max_articles_per_topic"]
                )
                if st.form_submit_button("💾 Save Changes"):
                    profiles[chosen] = {
                        "city": e_city,
                        "units": e_units,
                        "topics": [t.strip() for t in e_topics.splitlines() if t.strip()],
                        "briefing_tone": e_tone,
                        "max_articles_per_topic": int(e_max)
                    }
                    save_profiles(profiles)
                    st.session_state.briefing_data = None
                    st.success("Profile saved!")
                    st.rerun()

        # Delete — only shown when more than one profile exists
        if len(profile_names) > 1:
            if st.button("🗑️ Delete Profile", use_container_width=True):
                del profiles[chosen]
                save_profiles(profiles)
                st.session_state.selected_profile_name = list(profiles.keys())[0]
                st.session_state.briefing_data = None
                st.rerun()
    else:
        profile = None
        chosen = None
        st.info("No profiles yet. Create one below.")

    st.divider()

    # Add new profile
    with st.expander("➕ New Profile"):
        with st.form("new_profile_form"):
            n_name = st.text_input("Profile Name", placeholder="e.g. Jane")
            n_city = st.text_input("City", value="New York, US")
            n_units = st.selectbox("Units", ["imperial", "metric"])
            n_topics = st.text_area(
                "Topics (one per line)",
                value="technology\nbusiness\nworld news",
                height=150
            )
            n_tone = st.text_input("Briefing Tone", value="professional but conversational")
            n_max = st.number_input("Max articles per topic", min_value=1, max_value=10, value=3)

            if st.form_submit_button("✅ Create Profile"):
                if not n_name:
                    st.error("Profile name is required.")
                elif n_name in profiles:
                    st.error(f"'{n_name}' already exists.")
                else:
                    profiles[n_name] = {
                        "city": n_city,
                        "units": n_units,
                        "topics": [t.strip() for t in n_topics.splitlines() if t.strip()],
                        "briefing_tone": n_tone,
                        "max_articles_per_topic": int(n_max)
                    }
                    save_profiles(profiles)
                    st.session_state.selected_profile_name = n_name
                    st.session_state.briefing_data = None
                    st.success(f"Profile '{n_name}' created!")
                    st.rerun()

# --- HEADER ---
st.title("☀️ Your Daily Briefing")
if profile:
    st.caption(f"Profile: **{chosen}** · {profile['city']}")
else:
    st.caption("Create a profile in the sidebar to get started.")
st.divider()

# --- GENERATE BUTTON ---
col1, col2 = st.columns([2, 1])
with col1:
    generate_btn = st.button(
        "🔄 Generate My Briefing",
        type="primary",
        use_container_width=True,
        disabled=(profile is None)
    )
with col2:
    if st.session_state.briefing_data:
        st.caption(f"Last generated at {st.session_state.briefing_data['generated_at']}")

# --- MAIN LOGIC ---
if generate_btn and profile:
    with st.spinner("Fetching weather, news, and generating your briefing..."):
        try:
            st.session_state.briefing_data = run_briefing(profile)
        except Exception as e:
            st.error(f"Something went wrong: {e}")

# --- DISPLAY RESULTS ---
if st.session_state.briefing_data:
    data = st.session_state.briefing_data

    # AI Summary
    st.subheader("📋 Your Briefing")
    st.markdown(data["briefing"])
    st.divider()

    # Weather details
    st.subheader("🌤️ Weather Details")
    weather = data["weather"]
    if "error" not in weather:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Temperature", f"{weather['temperature']}°")
        col2.metric("Feels Like", f"{weather['feels_like']}°")
        col3.metric("Humidity", f"{weather['humidity']}%")
        col4.metric("Wind", f"{weather['wind_speed']} mph")
    else:
        st.warning(weather["error"])
    st.divider()

    # News headlines by topic
    st.subheader("📰 Headlines")
    news = data["news"]
    for topic in profile["topics"]:
        articles = news.get(topic, [])
        with st.expander(f"{topic.title()} ({len(articles)} articles)"):
            if not articles:
                st.write("No articles found for this topic.")
            else:
                for article in articles:
                    st.markdown(f"**[{article['title']}]({article['url']})**")
                    st.caption(f"Source: {article['source']}")
                    st.write("")
