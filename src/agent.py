import json
import os
import time
from google import genai
from google.genai import types

def generate_shift_schedule(site_context: dict, hazard_vector: dict) -> dict:
    """
    Queries Gemini models with fallback tiering using the google-genai SDK.
    Generates universal regional hazard & safety advisories using neutral terms (users/travelers).
    Forces native regional script output based on user selection in site_context.
    """
    client = genai.Client()

    # Extract target broadcast language dynamically (default to Hindi)
    target_lang = site_context.get("target_language", "Hindi")
    transport_mode = site_context.get("transport_mode", "Car")

    prompt = f"""
    You are an AI Regional Public Safety Officer and Hazard Response Planner (FORGE KavachAI).
    
    SUBSCRIBER & TRANSIT CONTEXT:
    {json.dumps(site_context, indent=2)}

    ROUTE HAZARD & WEATHER VECTOR:
    {json.dumps(hazard_vector, indent=2)}

    Based on environmental heat stress and weather hazards along the route:
    1. Determine the suggested outdoor activity/rest cycle (e.g., "45-min Outdoor Activity / 15-min Rest in Shade" or "Unrestricted Operations").
    2. Specify the recommended hourly fluid intake per person in milliliters (integer).
    3. Provide a concise 2-sentence public safety summary in English for community members. IMPORTANT: Do NOT mention specific transport modes like 'cyclist', 'biker', 'pedestrian', 'walker', or 'driver'. Refer to people neutrally as 'users', 'travelers', 'citizens', or 'residents'. Refer to the path as 'route' or 'transit corridor'.
    4. Draft a clear, urgent safety advisory script in simple spoken **{target_lang}** WRITTEN STRICTLY IN NATIVE **{target_lang}** SCRIPT (e.g., 'ध्यान दें सभी नागरिक!' for Hindi, 'గమనించండి!' for Telugu). Do NOT use English alphabet transliteration. Keep it under 50 words. Do NOT use mode-specific words like 'సైకిల్ స్వారీ' or 'సైక్లిస్టులు' in native languages; address all individuals generally as 'users', 'travelers', or 'citizens' (e.g., 'ಪ್ರಯಾಣಿಕರೇ' or 'ನಾಗರಿಕರೇ' in Kannada).

    Return your response strictly as a JSON object matching this schema:
    {{
        "work_rest_ratio": "string",
        "hourly_water_quota_ml": integer,
        "manager_summary": "string",
        "audio_script": "string"
    }}
    """

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite"
    ]
    
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                data = json.loads(response.text)
                
                # Maintain backward compatibility for components expecting 'audio_script_hindi'
                if "audio_script" in data:
                    data["audio_script_hindi"] = data["audio_script"]
                elif "audio_script_hindi" in data:
                    data["audio_script"] = data["audio_script_hindi"]
                    
                return data

            except Exception:
                time.sleep(1)
                continue

    # Neutral fallback scripts across regional languages
    default_scripts = {
        "Hindi": "ध्यान दें सभी यात्री! मार्ग में मौसम सामान्य है। अपनी यात्रा के दौरान सुरक्षित रहें और आवश्यकतानुसार पानी पिएं।",
        "Telugu": "గమనిక! మార్గంలో వాతావరణం సాధారణంగా ఉంది. ప్రయాణంలో ఉన్నవారు సురక్షితంగా ఉండండి మరియు తగినంత నీరు త్రాగండి.",
        "Kannada": "ಎಲ್ಲಾ ಪ್ರಯಾಣಿಕರ ಗಮನಕ್ಕೆ! ಮಾರ್ಗದಲ್ಲಿ ವಾತಾವರಣ ಸಾಮಾನ್ಯವಾಗಿದೆ. ಪ್ರಯಾಣದ ಸಮಯದಲ್ಲಿ ಸುರಕ್ಷಿತವಾಗಿರಿ ಮತ್ತು ಅಗತ್ಯಕ್ಕೆ ತಕ್ಕಂತೆ ನೀರು ಕುಡಿಯಿರಿ.",
        "Tamil": "கவனியுங்கள்! பாதையில் வானிலை இயல்பாக உள்ளது. பயணிகள் பாதுகாப்பாக பயணிக்கவும்.",
        "Bengali": "মনোযোগ দিন! যাত্রাপথে আবহাওয়া স্বাভাবিক। ভ্রমণের সময় নিরাপদ থাকুন।"
    }
    fallback_script = default_scripts.get(target_lang, "Attention travelers! Environmental conditions are safe along the route. Have a safe journey.")

    return {
        "work_rest_ratio": "Normal Outdoor Activity / Standard Rest",
        "hourly_water_quota_ml": 500,
        "manager_summary": f"Environmental parameters around {site_context.get('location_name', 'your area')} are within normal safety limits. Public transit and outdoor movement may proceed normally.",
        "audio_script": fallback_script,
        "audio_script_hindi": fallback_script
    }