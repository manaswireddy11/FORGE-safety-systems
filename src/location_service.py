import math
import requests
import streamlit as st
from typing import Tuple, Optional, List, Dict, Any

@st.cache_data(ttl=3600, show_spinner=False)
def reverse_geocode(lat: float, lon: float) -> str:
    """
    Converts GPS latitude and longitude coordinates into a precise human-readable local area name.
    """
    url = "https://api.bigdatacloud.net/data/reverse-geocode-client"
    params = {
        "latitude": lat,
        "longitude": lon,
        "localityLanguage": "en"
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Priority: Specific suburb/locality -> City -> District -> State
        locality = (
            data.get("locality") or 
            data.get("city") or 
            data.get("localityInfo", {}).get("informative", [{}])[0].get("name", "")
        )
        state = data.get("principalSubdivision", "")
        country = data.get("countryName", "")

        parts = [p for p in [locality, state, country] if p]
        if parts:
            return ", ".join(parts)
        return f"Location ({lat:.4f}, {lon:.4f})"
    except Exception:
        return f"Location ({lat:.4f}, {lon:.4f})"

def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Helper function to calculate straight-line distance in kilometers."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@st.cache_data(ttl=1800, show_spinner=False)
def get_route_waypoints(
    start_lat: float, 
    start_lon: float, 
    end_lat: float, 
    end_lon: float, 
    mode: str = "Car"
) -> List[Dict[str, Any]]:
    """
    Fetches route waypoints via OSRM geometry with mode-aware ETA recalculation for:
    'Car' (45 km/h), 'Cycle' (15 km/h), or 'Walk' (4.5 km/h).
    """
    # Target speeds (km/h) for precise mode-based duration estimation
    speed_map = {
        "Car": 45.0,
        "Cycle": 15.0,
        "Walk": 4.5
    }
    target_speed = speed_map.get(mode, 45.0)
    
    # Query OSRM standard driving route for road layout
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
    params = {"overview": "full", "geometries": "geojson"}
    
    distance_km = 0.0
    coordinates = []

    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("routes"):
                route = data["routes"][0]
                distance_km = route["distance"] / 1000.0
                coordinates = route["geometry"]["coordinates"]  # [[lon, lat], ...]
    except Exception:
        pass  # Fallback logic handles network issues or OSRM downtime

    # Fallback to Haversine distance with 30% winding factor if OSRM fails
    if distance_km == 0.0 or not coordinates:
        direct_dist = _haversine_distance_km(start_lat, start_lon, end_lat, end_lon)
        distance_km = direct_dist * 1.3
        coordinates = [[start_lon, start_lat], [end_lon, end_lat]]

    # Recalculate total transit duration dynamically based on selected transport mode speed
    total_duration_mins = int((distance_km / target_speed) * 60)

    # Dynamic checkpoint sampling
    if distance_km < 25.0:
        num_samples = 4
    elif distance_km < 150.0:
        num_samples = 6
    else:
        num_samples = 8

    step = max(1, len(coordinates) // (num_samples - 1))
    sampled_coords = coordinates[::step]
    
    if coordinates[-1] not in sampled_coords:
        sampled_coords.append(coordinates[-1])
        
    waypoints = []
    total_points = len(sampled_coords)
    
    for idx, (lon, lat) in enumerate(sampled_coords):
        ratio = idx / max(1, total_points - 1)
        eta_mins = int(total_duration_mins * ratio)
        
        if idx == 0:
            name = "Origin"
        elif idx == total_points - 1:
            name = "Destination"
        else:
            location_label = reverse_geocode(lat, lon)
            name = f"Checkpoint {idx}: {location_label.split(',')[0]}"

        waypoints.append({
            "latitude": lat,
            "longitude": lon,
            "eta_minutes": eta_mins,
            "name": name,
            "total_distance_km": round(distance_km, 1),
            "total_duration_mins": total_duration_mins
        })
        
    return waypoints

@st.cache_data(ttl=3600, show_spinner=False)
def geocode_location_name(location_query: str) -> Optional[Tuple[float, float, str]]:
    """
    Converts a location query (City/Area/Landmark name OR raw "lat, lon" coordinates) 
    into (latitude, longitude, display_name).
    """
    if not location_query or not location_query.strip():
        return None

    query_str = location_query.strip()

    # 1. Handle Raw Numeric Coordinates Input (e.g., "20.1523, 85.6674")
    try:
        parts = [p.strip() for p in query_str.replace(",", " ").split() if p.strip()]
        if len(parts) == 2:
            lat = float(parts[0])
            lon = float(parts[1])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                display_name = reverse_geocode(lat, lon)
                return lat, lon, display_name
    except ValueError:
        pass  # Not raw numeric coordinates, proceed to text search

    # 2. Primary Text Search via Open-Meteo (City, Town, Landmark)
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": query_str,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        results = response.json().get("results")
        
        if results:
            match = results[0]
            display_name = f"{match.get('name')}, {match.get('admin1', '')} ({match.get('country', '')})".strip(", ")
            return match["latitude"], match["longitude"], display_name
    except Exception:
        pass

    # 3. Fallback Search via OpenStreetMap Nominatim for specific landmarks/local areas
    try:
        nom_url = "https://nominatim.openstreetmap.org/search"
        nom_params = {"q": query_str, "format": "json", "limit": 1}
        nom_headers = {"User-Agent": "FORGE-KavachAI-SafetyAgent/1.0"}
        res = requests.get(nom_url, params=nom_params, headers=nom_headers, timeout=5)
        if res.status_code == 200 and res.json():
            match = res.json()[0]
            lat = float(match["lat"])
            lon = float(match["lon"])
            area_name = reverse_geocode(lat, lon)
            return lat, lon, f"{query_str} ({area_name})"
    except Exception as e:
        st.warning(f"⚠️ Geocoding service error: {e}")

    return None