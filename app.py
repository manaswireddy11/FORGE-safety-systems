import os
import io
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv, find_dotenv
from gtts import gTTS
from streamlit_geolocation import streamlit_geolocation
from streamlit_local_storage import LocalStorage

# Force load environment variables right at startup
load_dotenv(find_dotenv(), override=True)

from src.whatsapp_service import send_whatsapp_audio
from src.location_service import geocode_location_name, reverse_geocode, get_route_waypoints
from src.risk_engine import calculate_hourly_hazards
from src.agent import generate_shift_schedule
from src.weather_api import fetch_batch_route_weather, fetch_active_disasters

st.set_page_config(page_title="ResQNet: KavachAI", page_icon="🛡️", layout="wide")
st.title("🛡️ ResQNet-Intelligent Hazard Detection & Alert System")

# Initialize LocalStorage client for per-browser persistent memory
local_storage = LocalStorage()

# Fetch persistent saved profiles for THIS specific browser
saved_profiles_raw = local_storage.getItem("resqnet_user_profiles")
try:
    user_profiles = json.loads(saved_profiles_raw) if saved_profiles_raw else []
except Exception:
    user_profiles = []

# Initialize Session State Variables
if "start_location_text" not in st.session_state:
    st.session_state.start_location_text = ""
if "gps_attempted" not in st.session_state:
    st.session_state.gps_attempted = False

st.sidebar.header("📍 Corridor & Regional Locations")

# 1. Hidden Browser GPS Trigger
geo_data = streamlit_geolocation()

if geo_data and geo_data.get("latitude") and geo_data.get("longitude"):
    if not st.session_state.gps_attempted:
        detected_lat = geo_data["latitude"]
        detected_lon = geo_data["longitude"]
        detected_name = reverse_geocode(detected_lat, detected_lon)
        st.session_state.start_location_text = detected_name
        st.session_state.gps_attempted = True
        st.rerun()

# 2. Origin & Destination Inputs
start_query = st.sidebar.text_input(
    "🟢 Start Location / Origin:",
    value=st.session_state.start_location_text,
    placeholder="Auto-detected GPS or type origin city..."
)

dest_query = st.sidebar.text_input(
    "🔴 Destination / Target Area (Optional):",
    placeholder="Type destination city, area, or landmark..."
)

start_resolved = geocode_location_name(start_query) if start_query.strip() else None
dest_resolved = geocode_location_name(dest_query) if dest_query.strip() else None

if start_resolved:
    st.sidebar.success(f"🟢 Origin: {start_resolved[2]}")
elif start_query.strip():
    st.sidebar.error("❌ Origin location not found.")

if dest_resolved:
    st.sidebar.success(f"🔴 Destination: {dest_resolved[2]}")
elif dest_query.strip():
    st.sidebar.error("❌ Destination location not found.")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Subscriber Profile & Activity Configuration")

# Mode of Transport Dropdown
transport_mode = st.sidebar.selectbox("🚗 Mode of Transport", ["Car", "Cycle", "Walk"])

# Mapped UI inputs for civilian context
activity_level_label = st.sidebar.selectbox(
    "Activity Level", 
    ["Light (Walking, Resting)", "Moderate (Commuting, Jogging)", "Heavy (Strenuous Outdoor Effort)"]
)
clothing_label = st.sidebar.selectbox(
    "Apparel / Clothing Worn", 
    ["Light / Breathable Cotton", "Heavy Outerwear / Layers", "Impermeable Rainwear"]
)
is_acclimatized = st.sidebar.checkbox(
    "Accustomed to Local Climate?", 
    value=True, 
    help="Uncheck for tourists or unacclimatized visitors."
)

# Internal mapping back to risk_engine key format
severity_mapping = {
    "Light (Walking, Resting)": "Light",
    "Moderate (Commuting, Jogging)": "Moderate",
    "Heavy (Strenuous Outdoor Effort)": "Heavy"
}
ppe_mapping = {
    "Light / Breathable Cotton": "Standard",
    "Heavy Outerwear / Layers": "HighVis_Vest",
    "Impermeable Rainwear": "Tyvek_Suit"
}

work_severity = severity_mapping[activity_level_label]
ppe_type = ppe_mapping[clothing_label]

indian_languages = {
    "Hindi": "hi", "Bengali": "bn", "Telugu": "te", "Tamil": "ta",
    "Marathi": "mr", "Gujarati": "gu", "Kannada": "kn", "Malayalam": "ml",
    "Odia": "or", "Punjabi": "pa", "Urdu": "ur", "English (India)": "en"
}

# 3. Subscriber Registration Form (Saves into User's Browser Memory)
with st.sidebar.expander("👤 Register Subscriber Profile"):
    new_name = st.text_input("Subscriber Name:")
    new_phone = st.text_input("Phone Number (+91...):", placeholder="+919876543210")
    new_lang = st.selectbox("Preferred Language:", list(indian_languages.keys()))
    
    if st.button("Save Subscriber Profile"):
        if new_name and new_phone:
            # Append profile object to local browser list
            new_profile = {"name": new_name, "phone": new_phone, "language": new_lang}
            user_profiles.append(new_profile)
            local_storage.setItem("resqnet_user_profiles", json.dumps(user_profiles))
            st.success(f"Registered {new_name} successfully to your device!")
            st.rerun()
        else:
            st.warning("Please fill in all fields.")

# 4. Profile Management & Individual Deletion
if user_profiles:
    with st.sidebar.expander("🗑️ Manage My Saved Profiles"):
        delete_options = [f"{p['name']} ({p['phone']})" for p in user_profiles]
        profile_to_delete = st.selectbox("Select Profile to Remove:", delete_options)
        
        if st.button("Delete Selected Profile"):
            idx_to_remove = delete_options.index(profile_to_delete)
            removed_item = user_profiles.pop(idx_to_remove)
            local_storage.setItem("resqnet_user_profiles", json.dumps(user_profiles))
            st.success(f"Removed profile '{removed_item['name']}'!")
            st.rerun()

# 5. Target Subscriber Selection Dropdown
if user_profiles:
    subscriber_options = {f"{p['name']} ({p['phone']}, {p['language']})": p for p in user_profiles}
    selected_subscriber_label = st.sidebar.selectbox("Select Target Subscriber Profile", list(subscriber_options.keys()))
    selected_subscriber = subscriber_options[selected_subscriber_label]
    
    target_worker_name = selected_subscriber["name"]
    target_worker_phone = selected_subscriber["phone"]
    target_lang_name = selected_subscriber["language"]
else:
    st.sidebar.info("💡 Register a subscriber above to send automated WhatsApp broadcasts.")
    target_worker_name = "Default User"
    target_worker_phone = None
    target_lang_name = st.sidebar.selectbox("Regional Broadcast Language", list(indian_languages.keys()), index=0)

target_lang_code = indian_languages[target_lang_name]

# Helper function to check for unsafe/hazard alert conditions
def is_alert_condition(primary_risk: dict, plan: dict) -> bool:
    has_hazard_flags = len(primary_risk.get("hazard_flags", [])) > 0
    high_heat_stress = primary_risk.get("effective_wbgt_c", 0) >= 28.0
    return has_hazard_flags or high_heat_stress

# 6. Main Execution Button
if st.button("🚀 Run Full Safety Engine & Agent"):
    if not start_resolved:
        st.error("Please enter a valid Start Location.")
    elif not os.environ.get("GEMINI_API_KEY"):
        st.error("Please set your GEMINI_API_KEY environment variable!")
    else:
        start_lat, start_lon, start_name = start_resolved
        
        if not dest_resolved:
            dest_lat, dest_lon, dest_name = start_lat, start_lon, start_name
            waypoints = [{
                "latitude": start_lat, "longitude": start_lon,
                "eta_minutes": 0, "name": start_name,
                "total_distance_km": 0, "total_duration_mins": 0
            }]
            st.info(f"ℹ️ Area Assessment for **{start_name}**")
        else:
            dest_lat, dest_lon, dest_name = dest_resolved
            get_route_waypoints.clear()
            with st.spinner(f"Calculating transit route checkpoints for {transport_mode}..."):
                waypoints = get_route_waypoints(start_lat, start_lon, dest_lat, dest_lon, mode=transport_mode)

        if not waypoints:
            waypoints = [{
                "latitude": start_lat, "longitude": start_lon,
                "eta_minutes": 0, "name": start_name,
                "total_distance_km": 0, "total_duration_mins": 0
            }]

        route_hazards = []
        with st.spinner("Evaluating weather risks along transit route..."):
            try:
                all_w_data = fetch_batch_route_weather(waypoints)
                for wp, w_data in zip(waypoints, all_w_data):
                    r_vec = calculate_hourly_hazards(
                        hourly_data=w_data, hour_idx=0,
                        ppe_type=ppe_type, is_acclimatized=is_acclimatized
                    )
                    r_vec["checkpoint_name"] = wp["name"]
                    r_vec["eta_minutes"] = wp["eta_minutes"]

                    active_disasters = fetch_active_disasters(wp["latitude"], wp["longitude"])
                    if active_disasters:
                        r_vec["hazard_flags"].extend(active_disasters)

                    route_hazards.append(r_vec)
            except Exception as e:
                st.error(f"❌ Failed to fetch route weather: {e}")
                st.stop()

        if dest_resolved and waypoints:
            total_dist = waypoints[0].get("total_distance_km", 0)
            total_time = waypoints[0].get("total_duration_mins", 0)
            st.info(f"🛣️ Transit Corridor ({transport_mode}): **{total_dist} km** (~{total_time} mins) | Monitored across **{len(waypoints)}** checkpoints.")

        map_df = pd.DataFrame([{"lat": wp["latitude"], "lon": wp["longitude"]} for wp in waypoints])
        st.subheader("🗺️ Transit Route Map")
        st.map(map_df, zoom=9)

        st.subheader("📊 Route Weather Hazard Profile")
        cols = st.columns(len(route_hazards))
        for idx, (col, r) in enumerate(zip(cols, route_hazards)):
            with col:
                st.markdown(f"**{r['checkpoint_name']}**")
                st.caption(f"ETA: +{r['eta_minutes']} mins")
                st.metric("WBGT", f"{r['effective_wbgt_c']} °C")
                st.metric("Wind", f"{r['wind_gusts_kmh']} km/h")
                st.metric("Rain", f"{r['rain_mm']} mm")
                if r["hazard_flags"]:
                    for h in r["hazard_flags"]:
                        st.error(f"⚠️ {h}")
                else:
                    st.success("✅ Safe")

        primary_risk = route_hazards[-1]
        all_route_hazards = list(set([h for r in route_hazards for h in r["hazard_flags"]]))
        primary_risk["hazard_flags"] = all_route_hazards

        site_context = {
            "work_severity": work_severity,
            "ppe_type": ppe_type,
            "transport_mode": transport_mode,
            "is_acclimatized": is_acclimatized,
            "location_name": f"Route from {start_name} to {dest_name}" if dest_resolved else start_name,
            "target_language": target_lang_name
        }
        
        with st.spinner(f"Generating public safety advisory in {target_lang_name}..."):
            try:
                plan = generate_shift_schedule(site_context, primary_risk)
                st.markdown("---")
                st.subheader("📋 Public Safety & Outdoor Advisory")
                st.write(f"**Activity/Rest Guidance:** {plan['work_rest_ratio']}")
                st.write(f"**Hydration Quota:** {plan['hourly_water_quota_ml']} mL/hour")
                st.info(f"**Public Safety Note:** {plan['manager_summary']}")
        
                script_text = plan.get('audio_script', plan.get('audio_script_hindi', ''))
                st.warning(f"**{target_lang_name} Regional Broadcast Script:** {script_text}")

                # --- CONDITIONAL BROADCAST ENGINE ---
                st.markdown("---")
                st.subheader(f"🔊 {target_lang_name} Audio Advisory & Dispatch Engine")
                
                alert_triggered = is_alert_condition(primary_risk, plan)

                if alert_triggered:
                    st.error(f"🚨 **UNSAFE CONDITIONS DETECTED**: Active hazard warnings present")
                    
                    if script_text:
                        tts = gTTS(text=script_text, lang=target_lang_code, slow=False)
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        fp.seek(0)
                        audio_bytes = fp.getvalue()
                        
                        st.audio(audio_bytes, format="audio/mp3")
                        
                        if target_worker_phone:
                            with st.spinner(f"Sending Urgent WhatsApp voice alert to {target_worker_name} ({target_worker_phone})..."):
                                load_dotenv(find_dotenv(), override=True)
                                
                                token_check = os.environ.get("WHATSAPP_TOKEN")
                                phone_id_check = os.environ.get("WHATSAPP_PHONE_ID")

                                if not token_check or not phone_id_check:
                                    st.error(f"⚠️ Keys not detected in app.py! Token: {bool(token_check)}, Phone ID: {bool(phone_id_check)}")
                                
                                sent = send_whatsapp_audio(target_worker_phone, audio_bytes, script_text)
                                if sent:
                                    st.success(f"📱 WhatsApp hazard audio alert sent to {target_worker_phone}!")
                                else:
                                    st.info(f"ℹ️ Simulated Alert Dispatch: Audio alert prepared for {target_worker_phone}. (Set WHATSAPP_TOKEN & WHATSAPP_PHONE_ID environment variables for live delivery).")
                        else:
                            st.warning("⚠️ Register and select a subscriber profile in the sidebar to test WhatsApp alerts.")
                else:
                    st.success("✅ **SAFE ENVIRONMENTAL CONDITIONS**: Weather and corridor parameters are normal.")
                    st.info("ℹ️ WhatsApp broadcast skipped. Audio alerts are dispatched to subscriber devices strictly during unsafe or elevated risk conditions.")

            except Exception as e:
                st.error(f"Pipeline Execution Failed: {e}")