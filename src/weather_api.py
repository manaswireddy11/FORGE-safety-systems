import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import streamlit as st
from typing import List, Dict, Any

# Configure resilient HTTP session with retries for network stability
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))
session.mount("http://", HTTPAdapter(max_retries=retries))


def fetch_active_disasters(lat: float, lon: float) -> List[str]:
    """
    Queries Open-Meteo Flood API, Weather Alerts, and USGS Earthquakes.
    Detects both official warnings and physical river discharge/flash flood conditions.
    """
    disaster_flags = []
    
    # 1. Open-Meteo River Flood API (Detects Riverine Flooding & High Discharge)
    try:
        flood_url = "https://flood-api.open-meteo.com/v1/flood"
        flood_params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ["river_discharge", "river_discharge_mean"],
            "forecast_days": 1
        }
        f_res = session.get(flood_url, params=flood_params, timeout=4)
        if f_res.status_code == 200:
            f_data = f_res.json().get("daily", {})
            discharge = f_data.get("river_discharge", [0])[0] or 0
            mean_discharge = f_data.get("river_discharge_mean", [0])[0] or 0
            
            # Trigger alert if discharge significantly exceeds historical mean or is very high
            if discharge > 50.0 and discharge > (mean_discharge * 2.0):
                disaster_flags.append(f"🌊 HIGH_FLOOD_DISCHARGE ({round(discharge, 1)} m³/s)")
    except Exception:
        pass

    # 2. Open-Meteo Weather & Severe Alerts
    try:
        alert_url = "https://api.open-meteo.com/v1/forecast"
        alert_params = {
            "latitude": lat,
            "longitude": lon,
            "warnings": "true",
            "current": ["rain", "precipitation"],
            "timezone": "auto"
        }
        a_res = session.get(alert_url, params=alert_params, timeout=4)
        if a_res.status_code == 200:
            data = a_res.json()
            warnings = data.get("warnings", [])
            for w in warnings:
                event_name = w.get("event", "Severe Event").upper()
                disaster_flags.append(f"🌊 SEVERE_DISASTER_ALERT ({event_name})")

            # Heavy Rain / Flash Flood fallback threshold (e.g., current rain > 15 mm/hr)
            current = data.get("current", {})
            rain_rate = current.get("precipitation", current.get("rain", 0.0))
            if rain_rate >= 15.0:
                disaster_flags.append(f"🌧️ FLASH_FLOOD_RISK ({rain_rate} mm/h)")
    except Exception:
        pass

    # 3. Real-Time Earthquake Monitoring (M4.5+ within 100km)
    try:
        eq_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        eq_params = {
            "format": "geojson",
            "latitude": lat,
            "longitude": lon,
            "maxradiuskm": 100,
            "minmagnitude": 4.5,
            "limit": 1
        }
        eq_res = session.get(eq_url, params=eq_params, timeout=3)
        if eq_res.status_code == 200:
            features = eq_res.json().get("features", [])
            if features:
                mag = features[0]["properties"]["mag"]
                place = features[0]["properties"]["place"]
                disaster_flags.append(f"🚨 EARTHQUAKE_ALERT (M{mag} - {place})")
    except Exception:
        pass

    return disaster_flags


@st.cache_data(ttl=900, show_spinner=False)
def fetch_batch_route_weather(waypoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fetches live weather metrics in small waypoint chunks. 
    Prevents ReadTimeout errors on long routes like Delhi-Hyderabad.
    """
    if not waypoints:
        return []

    processed_results = []
    
    # Process waypoints in small chunks of 3 coordinates to prevent payload timeouts
    chunk_size = 3
    for i in range(0, len(waypoints), chunk_size):
        chunk = waypoints[i:i + chunk_size]
        lats = ",".join([str(wp["latitude"]) for wp in chunk])
        lons = ",".join([str(wp["longitude"]) for wp in chunk])

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lats,
            "longitude": lons,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "wind_speed_10m",
                "wind_gusts_10m",
                "rain",
                "precipitation",
                "uv_index",
                "direct_normal_irradiance"
            ],
            "hourly": [
                "temperature_2m",
                "relative_humidity_2m",
                "wind_speed_10m",
                "wind_gusts_10m",
                "rain",
                "precipitation",
                "uv_index",
                "direct_normal_irradiance"
            ],
            "timezone": "auto"
        }

        try:
            response = session.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict):
                data = [data]

            for point in data:
                hourly = point.get("hourly", {})
                if hourly and "temperature_2m" in hourly:
                    if "precipitation" not in hourly and "rain" in hourly:
                        hourly["precipitation"] = hourly["rain"]
                    elif "rain" not in hourly and "precipitation" in hourly:
                        hourly["rain"] = hourly["precipitation"]
                        
                    if "uv_index" not in hourly:
                        if "direct_normal_irradiance" in hourly:
                            hourly["uv_index"] = [round(dni / 100.0, 1) for dni in hourly["direct_normal_irradiance"]]
                        else:
                            hourly["uv_index"] = [0.0] * len(hourly["temperature_2m"])
                            
                    processed_results.append(hourly)
                else:
                    current = point.get("current", {})
                    rain_val = current.get("precipitation", current.get("rain", 0.0))
                    uv_val = current.get("uv_index", 0.0)
                    processed_results.append({
                        "temperature_2m": [current.get("temperature_2m", 25.0)],
                        "relative_humidity_2m": [current.get("relative_humidity_2m", 50.0)],
                        "wind_speed_10m": [current.get("wind_speed_10m", 10.0)],
                        "wind_gusts_10m": [current.get("wind_gusts_10m", 15.0)],
                        "rain": [rain_val],
                        "precipitation": [rain_val],
                        "uv_index": [uv_val],
                        "direct_normal_irradiance": [0.0]
                    })
        except Exception:
            # Inject neutral baseline (25°C, 50% humidity) ONLY for the failed chunk
            for _ in chunk:
                processed_results.append({
                    "temperature_2m": [25.0],
                    "relative_humidity_2m": [50.0],
                    "wind_speed_10m": [10.0],
                    "wind_gusts_10m": [15.0],
                    "rain": [0.0],
                    "precipitation": [0.0],
                    "uv_index": [0.0],
                    "direct_normal_irradiance": [0.0]
                })

    return processed_results


@st.cache_data(ttl=900, show_spinner=False)
def fetch_live_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Single location weather fetch wrapper.
    """
    res = fetch_batch_route_weather([{"latitude": lat, "longitude": lon}])
    return res[0] if res else {}