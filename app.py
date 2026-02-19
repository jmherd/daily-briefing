# app.py
# This is the Streamlit UI — the only file that deals with what the user sees.
# It calls run_briefing() from briefing_engine and displays the results.

import streamlit as st
from briefing_engine import run_briefing
from config import NEWS_TOPICS

# --- PAGE CONFIGURATION ---
# This must be the first Streamlit command in the file.
st.set_page_config(
    page_title="Daily Briefing",
    page_icon="☀️",
    layout="centered"
)

# --- HEADER ---
st.title("☀️ Your Daily Briefing")
st.caption("Personalized news and weather, summarized by AI.")
st.divider()

# --- GENERATE BUTTON ---
# st.session_state persists data between interactions on the same page.
# Without it, every button click would wipe the previous results.
if "briefing_data" not in st.session_state:
    st.session_state.briefing_data = None

col1, col2 = st.columns([2, 1])
with col1:
    generate_btn = st.button("🔄 Generate My Briefing", type="primary", use_container_width=True)
with col2:
    if st.session_state.briefing_data:
        st.caption(f"Last generated at {st.session_state.briefing_data['generated_at']}")

# --- MAIN LOGIC ---
if generate_btn:
    with st.spinner("Fetching weather, news, and generating your briefing..."):
        try:
            st.session_state.briefing_data = run_briefing()
        except Exception as e:
            st.error(f"Something went wrong: {e}")

# --- DISPLAY RESULTS ---
if st.session_state.briefing_data:
    data = st.session_state.briefing_data

    # AI Summary — the star of the show
    st.subheader("📋 Your Briefing")
    st.markdown(data["briefing"])
    st.divider()

    # Weather details in a clean metric row
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

    # News headlines organized by topic with clickable links
    st.subheader("📰 Headlines")
    news = data["news"]
    
    for topic in NEWS_TOPICS:
        articles = news.get(topic, [])
        with st.expander(f"{topic.title()} ({len(articles)} articles)"):
            if not articles:
                st.write("No articles found for this topic.")
            else:
                for article in articles:
                    st.markdown(f"**[{article['title']}]({article['url']})**")
                    st.caption(f"Source: {article['source']}")
                    st.write("")