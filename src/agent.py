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

    # Fallback with completely neutral phrasing across regional languages
    default_scripts = {
        "Hindi": "ध्यान दें सभी यात्री! मार्ग में तापमान बढ़ा हुआ है। अपनी यात्रा के दौरान पर्याप्त मात्रा में पानी पिएं और छाया में आराम करें।",
        "Telugu": "గమనిక! మార్గంలో ఉష్ణోగ్రతలు ఎక్కువగా ఉన్నాయి. ప్రయాణంలో ఉన్నవారు తగినంత నీరు త్రాగి, నీడలో విశ్రాంతి తీసుకోండి.",
        "Kannada": "ಎಲ್ಲಾ ಪ್ರಯಾಣಿಕರ ಗಮನಕ್ಕೆ! ಮಾರ್ಗದಲ್ಲಿ ತಾಪಮಾನ ಹೆಚ್ಚಾಗಿದೆ. ಪ್ರಯಾಣದ ಸಮಯದಲ್ಲಿ ಸಾಕಷ್ಟು ನೀರು ಕುಡಿಯಿರಿ ಮತ್ತು ನೆರಳಿನಲ್ಲಿ ವಿಶ್ರಾಂತಿ ಪಡೆಯಿರಿ.",
        "Tamil": "கவனியுங்கள்! பாதையில் அதிக வெப்பம் உள்ளது. பயணிகள் பயணத்தின் போது போதுமான அளவு தண்ணீர் குடிக்கவும்.",
        "Bengali": "মনোযোগ দিন! যাত্রাপথে তাপমাত্রা বেশি। ভ্রমণের সময় পর্যাপ্ত জল পান করুন।"
    }
    fallback_script = default_scripts.get(target_lang, "Attention travelers! Weather conditions are elevated along the route. Stay hydrated and rest in shade.")

    return {
        "work_rest_ratio": "Normal Outdoor Activity / Standard Rest",
        "hourly_water_quota_ml": 500,
        "manager_summary": f"Moderate environmental strain reported along the route near {site_context.get('location_name', 'your area')}. Users should stay hydrated and take periodic breaks.",
        "audio_script": fallback_script,
        "audio_script_hindi": fallback_script
    }