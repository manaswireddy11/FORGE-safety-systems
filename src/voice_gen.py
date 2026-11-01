import streamlit as st
from gtts import gTTS
import io
import time

@st.cache_data(show_spinner=False)
def generate_regional_audio(text: str, lang_code: str = "hi") -> bytes:
    """
    Converts text to speech audio binary buffer using gTTS for any target language code.
    Includes connection retry logic to prevent WinError 10053 network crashes.
    Cached in memory based on exact input text and selected language.
    """
    if not text:
        return None

    for attempt in range(3):
        try:
            tts = gTTS(text=text, lang=lang_code, timeout=10)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            return audio_buffer.getvalue()  # Return raw bytes for clean caching
        except Exception:
            time.sleep(1)
            
    st.warning("⚠️ Could not synthesize audio due to network instability. Agent text advisory generated successfully.")
    return None


# Backward-compatibility wrapper for legacy calls
def generate_hindi_audio(text: str) -> bytes:
    return generate_regional_audio(text, lang_code="hi")