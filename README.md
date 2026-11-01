# 🛡️ ResQNet — Intelligent Hazard Detection & Alert System

ResQNet (powered by KavachAI) is a hyper-localized disaster risk assessment and automated multilingual alert platform designed to protect transit commuters, outdoor workers, and civilians. By combining real-time weather telemetries, geospatial routing, heat-stress indices (WBGT), and Meta's WhatsApp API with Google Gemini LLMs and Google Text-to-Speech (gTTS), ResQNet automatically synthesizes and dispatches actionable audio advisories in 12 Indian regional languages during critical hazard events.

---

## 📐 Architecture & Dataflow Diagram

```
                 +---------------------------------------------------------+
                 |                 User Interface (Streamlit)               |
                 |  - GPS Origin / Manual Search                           |
                 |  - Destination Landmark                                 |
                 |  - Transport Mode (Car, Cycle, Walk)                   |
                 |  - Activity Level & Apparel Selection                   |
                 |  - Regional Language Selection (12 Indian Languages)   |
                 +----------------------------+----------------------------+
                                              |
                                              v
                 +---------------------------------------------------------+
                 |              Geospatial Corridor Engine                 |
                 |  - Reverse Geocoding & OpenStreetMap Waypoints          |
                 |  - Route Waypoint Extraction & Transit ETAs             |
                 +----------------------------+----------------------------+
                                              |
                                              v
                 +---------------------------------------------------------+
                 |              Telemetry & Risk Assessment                |
                 |  - Batch Weather Fetch (Open-Meteo API)                |
                 |  - Active Disaster Alert Cross-matching                |
                 |  - WBGT Heat Stress & Hazard Flag Calculation           |
                 +----------------------------+----------------------------+
                                              |
                                              v
                                   Is Hazard Alert Triggered?
                                         /         \
                                       YES          NO
                                       /             \
                                      v               v
  +---------------------------------------+   +-------------------------------+
  |       Gemini 1.5 Safety Agent         |   |    Display Safe Status UI     |
  |  - Synthesizes Hydration & Advisory    |   |  - Suppress WhatsApp Delivery |
  |  - Outputs Regional Audio Script      |   +-------------------------------+
  +-------------------+-------------------+
                      |
                      v
  +---------------------------------------+
  |      Audio & Dispatch Pipeline        |
  |  - gTTS Audio Synthesis (MP3)         |
  |  - Render Audio Player on UI          |
  |  - Meta WhatsApp Business API Engine  |
  +-------------------+-------------------+
                      |
                      v
  +---------------------------------------+
  |    Target Subscriber WhatsApp Device  |
  |  - Receives Voice Advisory Message    |
  +---------------------------------------+
```

---

## ✨ Core Features

- 📍 **Smart Corridor Routing**: Real-time GPS auto-detection or manual location resolution with route waypoint interpolation.
- 🌡️ **WBGT Risk Assessment Engine**: Calculates Wet Bulb Globe Temperature (WBGT), wind gusts, and precipitation hazards tailored to apparel, activity level, and local climate acclimatization.
- 🗣️ **Multilingual Audio Generation**: Generates contextual safety advisories across 12 regional Indian languages (Hindi, Bengali, Telugu, Tamil, Marathi, Gujarati, Kannada, Malayalam, Odia, Punjabi, Urdu, English).
- 📱 **Automated WhatsApp Audio Delivery**: Integrates Meta's WhatsApp Business API to deliver urgent audio alerts directly to subscriber devices during hazardous conditions.
- 🔒 **Private & Refresh-Proof Profiles**: Browser URL state hydration (`st.query_params`) ensures user profiles remain private to individual devices while persisting across page reloads without requiring server-side storage.

---

## 📂 Source Code Manifest

```
ResQNet/
├── app.py                      # Main Streamlit Application GUI & Dispatch Logic
├── requirements.txt            # Python Dependencies Specification
├── .env.example                # Template for Local Environment Variables
├── src/
│   ├── agent.py                # Google Gemini LLM Prompt & Schedule Generator
│   ├── database.py             # SQLite Data Storage Helpers
│   ├── location_service.py     # OpenStreetMap Geocoding & Route Waypoint Calculators
│   ├── risk_engine.py          # WBGT Heat Stress & Hazard Classification Model
│   ├── weather_api.py          # Open-Meteo Weather Data Integrator
│   └── whatsapp_service.py     # Meta WhatsApp Media Upload & Dispatch Service
└── README.md                   # System Documentation
```

---

## ⚙️ Environment Variables Configuration

Create a `.env` file in the root directory for local development:

```env
# Required for Safety Advisory Agent
GEMINI_API_KEY=your_google_gemini_api_key_here

# Required for Meta WhatsApp Alerts
WHATSAPP_TOKEN=your_meta_whatsapp_access_token_here
WHATSAPP_PHONE_ID=your_meta_whatsapp_phone_number_id_here
```

### Deploying Secrets to Streamlit Community Cloud:
1. Open your app dashboard on [Streamlit Community Cloud](https://share.streamlit.io).
2. Click the **3 dots (`...`)** next to your app $\rightarrow$ **Settings** $\rightarrow$ **Secrets**.
3. Add your keys in TOML format:
```toml
GEMINI_API_KEY = "your_google_gemini_api_key_here"
WHATSAPP_TOKEN = "your_meta_whatsapp_access_token_here"
WHATSAPP_PHONE_ID = "your_meta_whatsapp_phone_number_id_here"
```

---

## 🚀 Quickstart & Local Installation Guide

### Prerequisites
- Python 3.9, 3.10, or 3.11 installed.
- Git installed.

### 1. Clone Repository
```bash
git clone https://github.com/your-username/ResQNet.git
cd ResQNet
```

### 2. Create Virtual Environment & Install Dependencies
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Run Application Locally
```bash
streamlit run app.py
```

Open `http://localhost:8501` in your web browser.

---

## 📱 Meta WhatsApp API Setup Guide

To deliver live voice alerts to mobile devices:

1. Visit the [Meta for Developers Portal](https://developers.facebook.com/).
2. Create an App under **Other** $\rightarrow$ **Business** and select the **WhatsApp** product.
3. Under **WhatsApp** $\rightarrow$ **API Setup**:
   - Copy the **Temporary Access Token** to `WHATSAPP_TOKEN`.
   - Copy the **Phone Number ID** to `WHATSAPP_PHONE_ID`.
4. Click **Manage phone number list** under the **To** field to add and verify test recipient numbers via OTP.

---

## 🛠️ Built With

- [Streamlit](https://streamlit.io/) — Interactive Web Interface Framework
- [Google Gemini API](https://ai.google.dev/) — Generative AI Advisory Engine
- [gTTS (Google Text-to-Speech)](https://pypi.org/project/gTTS/) — Multilingual Audio Generator
- [Meta WhatsApp Business API](https://developers.facebook.com/docs/whatsapp) — Urgent Voice Alert Broadcast Service
- [Open-Meteo API](https://open-meteo.com/) — High-Precision Weather Telemetry