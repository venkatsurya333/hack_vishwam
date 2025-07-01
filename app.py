import streamlit as st
from streamlit_js_eval import get_geolocation
from streamlit_folium import st_folium
import folium
import requests
import re

# -------------------- Page Setup --------------------
st.set_page_config(page_title="📍 JanmaBhoomi Cultural Explorer", layout="wide")
st.title("🇮🇳 JanmaBhoomi — Discover India's Local Stories")

# -------------------- State Init --------------------
if "location" not in st.session_state:
    st.session_state["location"] = None
if "city" not in st.session_state:
    st.session_state["city"] = None
if "show_map" not in st.session_state:
    st.session_state["show_map"] = False

# -------------------- Helper: Get city from lat/lon --------------------
def get_city_name(lat, lon):
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "jsonv2", "lat": lat, "lon": lon},
            headers={"User-Agent": "StreamlitApp/1.0"}
        )
        address = response.json().get("address", {})
        return address.get("city") or address.get("town") or address.get("village") or address.get("state")
    except:
        return "Unknown"

# -------------------- Location Picker Section --------------------
st.subheader("📍 Step 1: Pick Your Location")

gps = get_geolocation()
if gps and "coords" in gps:
    lat = gps["coords"]["latitude"]
    lon = gps["coords"]["longitude"]
    if st.button("📍 Detect My City"):
        st.session_state["location"] = (lat, lon)
        st.session_state["city"] = get_city_name(lat, lon)

# Toggle Map View
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🗺️ Show Map", disabled=st.session_state["show_map"]):
        st.session_state["show_map"] = True
with col2:
    if st.button("❌ Hide Map", disabled=not st.session_state["show_map"]):
        st.session_state["show_map"] = False

# Show Map if toggled
if st.session_state["show_map"]:
    default_center = st.session_state["location"] or (20.5937, 78.9629)
    m = folium.Map(location=default_center, zoom_start=6)
    if st.session_state["location"]:
        folium.Marker(st.session_state["location"], popup="Selected").add_to(m)
    map_output = st_folium(m, height=400, width=600)
    if map_output and map_output.get("last_clicked"):
        clicked_lat = map_output["last_clicked"]["lat"]
        clicked_lon = map_output["last_clicked"]["lng"]
        st.session_state["location"] = (clicked_lat, clicked_lon)
        st.session_state["city"] = get_city_name(clicked_lat, clicked_lon)

# Display selected city
if st.session_state["city"]:
    st.success(f"🏙️ Selected City: **{st.session_state['city']}**")
    auto_place = st.session_state["city"]
else:
    st.info("📌 No city selected. You can still manually enter one.")
    auto_place = ""

st.divider()

# -------------------- JanmaBhoomi Cultural Explorer --------------------

# --- Language + Place Input ---
st.subheader("🌐 Step 2: Explore the Culture of a Place")
lang = st.selectbox("Choose Language", ["English", "Telugu", "Hindi"])
place = st.text_input("Enter the name of an Indian place", value=auto_place)

# --- Wikipedia Summary Fetch ---
def fetch_summary(place):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{place}"
    res = requests.get(url)
    if res.status_code == 200:
        return res.json().get("extract", "No summary available.")
    return "Could not fetch summary."

def translate_text(text, lang):
    translations = {
        "Telugu": "[TE] " + text,
        "Hindi": "[HI] " + text
    }
    return translations.get(lang, text)

def fetch_image(place):
    commons_api = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "pageimages",
        "format": "json",
        "titles": place,
        "pithumbsize": 600
    }
    res = requests.get(commons_api, params=params).json()
    pages = res.get("query", {}).get("pages", {})
    for page_id in pages:
        return pages[page_id].get("thumbnail", {}).get("source", None)
    return None

def fetch_specific_summary(title):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    res = requests.get(url)
    if res.status_code == 200:
        return res.json().get("extract", "")
    return ""

def fetch_political_significance(place):
    titles_to_try = [
        f"Politics of {place}",
        f"{place} politics",
        f"{place} (Lok Sabha constituency)",
        f"Political history of {place}",
        f"History of {place}"
    ]
    for title in titles_to_try:
        summary = fetch_specific_summary(title)
        if summary and len(summary) > 50:
            return summary
    return "No notable political information found for this place."

def detect_languages(place):
    place = place.lower()
    telugu_states = ["andhra", "telangana", "hyderabad", "visakhapatnam", "vijayawada", "warangal"]
    hindi_states = ["uttar", "madhya", "bihar", "rajasthan", "delhi", "lucknow", "patna"]
    languages = set(["English"])
    for region in telugu_states:
        if region in place:
            languages.add("Telugu")
    for region in hindi_states:
        if region in place:
            languages.add("Hindi")
    return ", ".join(sorted(languages))

def extract_proper_nouns(text):
    return list(set(re.findall(r'\b(?:[A-Z][a-z]+\s?){1,4}', text)))

# --- Main Display ---
if st.button("Explore"):
    if not place:
        st.warning("Please enter a place name.")
    else:
        with st.spinner("Fetching cultural info..."):
            image_url = fetch_image(place)
            if image_url:
                st.image(image_url, caption=f"Image of {place}", use_container_width=True)

            summary = fetch_summary(place)
            final_summary = translate_text(summary, lang)

            st.markdown("### 🧾 Knowledge Card")
            with st.container():
                st.markdown(
                    f"""
                    <div style="border:2px solid #ccc; padding:1.5rem; border-radius:15px; background-color:#f9f9f9;">
                        <h3>{place.title()}</h3>
                        <p>{final_summary}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("### 📚 Cultural Insights")
            st.subheader("📌 What is this place famous for?")
            st.write(fetch_specific_summary(place))

            st.subheader("🗺️ Popular Tourist Attractions")
            tourism = fetch_specific_summary(f"Tourist attractions in {place}")
            if tourism:
                proper_nouns = extract_proper_nouns(tourism)
                linked_text = tourism
                for phrase in sorted(proper_nouns, key=len, reverse=True):
                    wiki_title = phrase.strip().replace(" ", "_")
                    linked_text = linked_text.replace(phrase, f"[{phrase}](https://en.wikipedia.org/wiki/{wiki_title})", 1)
                st.markdown(linked_text, unsafe_allow_html=True)
            else:
                st.info("No tourist info found.")

            st.subheader("🏛️ Cultural or Historical Importance")
            culture = fetch_specific_summary(f"Culture of {place}")
            if not culture or len(culture) < 30:
                culture = fetch_specific_summary(f"History of {place}")
            st.write(culture)

            st.subheader("🎓 Educational Institutions")
            edu_text = fetch_specific_summary(f"Education in {place}") or fetch_specific_summary(f"Colleges in {place}")
            edu_points = [pt.strip() for pt in edu_text.split('.') if len(pt.strip()) > 20]
            if edu_points:
                for pt in edu_points:
                    st.markdown(f"- {pt}.")
            else:
                st.info("No detailed educational info available.")

            st.subheader("🏛️ Political Significance")
            st.write(fetch_political_significance(place))

            st.subheader("🗣️ Languages Commonly Spoken")
            st.write(detect_languages(place))
            # --- Download Knowledge Card ---
            download_text = f"""{place.title()} - Cultural Summary ({lang})\n\n{final_summary}\n
---\n📌 Famous For:\n{fetch_specific_summary(place)}\n
🗺️ Tourist Attractions:\n{tourism}\n
🏛️ Cultural Importance:\n{culture}\n
🎓 Educational Institutions:\n{"".join("- " + p + "\n" for p in edu_points)}\n
🏛️ Political Significance:\n{fetch_political_significance(place)}\n
🗣️ Languages Spoken:\n{detect_languages(place)}\n
Source: Wikipedia/Wikimedia"""

            st.download_button(
                label="📥 Download Knowledge Card",
                data=download_text,
                file_name=f"{place}_summary.txt",
                mime="text/plain"
            )
# Footer
st.markdown("---")
st.caption("🔗 Cultural data sourced from Wikipedia & Wikimedia APIs.")
