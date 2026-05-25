# DigitalAgri — Smart Farming for Rwanda

DigitalAgri is a  platform designed to empower Rwandan agricultural cooperatives and farmers with data-driven insights. By leveraging machine learning and real-time weather data, the platform provides tailored crop recommendations, planting calendars, and analytical tools to optimize agricultural productivity across Rwanda's 30 districts.

---

## Getting Started

Follow these steps to set up the project on your local machine.

### 1. Clone the Repository
```bash
git clone <repository-url>
cd DigitalAgri
```

### 2. Create a Virtual Environment
It is recommended to use a virtual environment to manage dependencies.
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Requirements
Install the necessary Python packages using pip.
```bash
pip install -r requirements.txt
```

### 4. Run the Application
Start the Flask development server.
```bash
python app.py
```
The application will be available at `http://localhost:5000`.

> Note: If you want the weather feature to work with OpenWeatherMap, add this line below line 15. 
Add `OPENWEATHER_API_KEY at line 17  in `app.py` and configure your OpenWeather API key.

---

## User Guide

### 1. Signup as a Cooperative
- Navigate to the **Sign Up** page from the landing screen.
- Enter your cooperative name, email, phone number, and select your district.
- Once registered, you will be redirected to the Cooperative Dashboard.

### 2. Register a Farmer
- From the sidebar, click on **Farmers**.
- Use the "Add New Farmer" form to register farmers in your cooperative.
- Provide their name, phone number, district, farm size (Ha), and gender.

### 3. Look for Weather Forecast
- Navigate to the **Weather Forecast** section in the sidebar.
- Select a district to view real-time weather conditions and a 7-day forecast.
- This tool helps you advise farmers on the best time for planting and harvesting based on predicted rainfall and temperature.

### 4. Get AI Recommendations
- Go to the **Recommendation** page.
- Select a registered farmer and enter the farm details (district, season, soil pH, NPK levels, etc.).
- Click **Get Recommendation** to generate a machine learning-backed crop suggestion.

**Example Recommendation:**
- **District:** Musanze
- **Season:** Season A
- **Altitude:** 2100 m
- **Soil pH:** 6.2
- **Nitrogen (N):** 65 kg/ha
- **Phosphorus (P):** 45 kg/ha
- **Potassium (K):** 50 kg/ha
- **Rainfall:** 1200 mm
- **Temperature:** 18 °C
- **Humidity:** 75 %
- **Output:** The system might recommend **Irish Potato** (85% confidence) and **Beans** (12% confidence) based on the high altitude and volcanic soil typical of the Musanze region, validated against the official Rwanda Crop Whitelist.


---

## Project Structure
- `app.py`: Main Flask application and routing.
- `models.py`: Database models (Cooperatives, Farmers, Recommendations).
- `ml/`: Machine learning models and the `rwanda_crop_whitelist.json` data.
- `templates/`: HTML templates for the dashboard and analytics.
- `static/`: CSS, JavaScript, and image assets.

---

## Data Source
Crop recommendations are validated against the **NISR Seasonal Agricultural Survey 2024**.
[View Official Report](http://alpha.statistics.gov.rw/sites/default/files/documents/2025-02/SAS%202024%20Annual.pdf)
