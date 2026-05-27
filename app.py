from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from __init__ import create_app, db, bcrypt
from models import Admin, Cooperative, Farmer, Recommendation, Prediction, PlantingCalendar, Season, Gender
from ml.predictor import predict_crops, CROP_DISPLAY_NAMES
from sqlalchemy import func
import os
import requests
from datetime import datetime, timedelta

app = create_app()

# OpenWeatherMap API Configuration
# Get API key from environment variable or set it here
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', '')
# You can also set it directly here (not recommended for production):
OPENWEATHER_API_KEY = ""

# Define emojis and colors for crops globally
CROP_EMOJIS = {
    'Maize': '🌽', 'Beans': '🥜', 'Cassava': '🥚', 
    'Sweet Potato': '🍠', 'Sorghum': '🌾', 'Rice': '🍚',
    'Irish Potato': '🥔', 'Banana': '🍌', 'Wheat': '🌾',
    'Tomato': '🍅', 'Vegetables': '🥗', 'Coffee': '☕',
    'Sunflower': '🌻',
    # Handle common variants and lowercase/underscore names
    'maize': '🌽', 'beans': '🥜', 'cassava': '🥚',
    'sweet_potato': '🍠', 'sorghum': '🌾', 'rice': '🍚',
    'irish_potato': '🥔', 'banana': '🍌', 'wheat': '🌾',
    'tomato': '🍅', 'vegetables': '🥗', 'coffee': '☕',
    'sunflower': '🌻'
}

@app.context_processor
def inject_emojis():
    return dict(crop_emojis=CROP_EMOJIS)

# Rwanda districts list
RWANDA_DISTRICTS = [
    # Kigali City
    "Gasabo", "Kicukiro", "Nyarugenge",
    # Northern Province
    "Burera", "Gakenke", "Gicumbi", "Musanze", "Rulindo",
    # Southern Province
    "Gisagara", "Huye", "Kamonyi", "Muhanga", "Nyamagabe",
    "Nyanza", "Nyaruguru", "Ruhango",
    # Eastern Province
    "Bugesera", "Gatsibo", "Kayonza", "Kirehe", "Ngoma",
    "Nyagatare", "Rwamagana",
    # Western Province
    "Karongi", "Ngororero", "Nyabihu", "Nyamasheke",
    "Rubavu", "Rusizi", "Rutsiro",
]

# Alias
RWANDA_DISTRICTS_FOR_FARMERS = RWANDA_DISTRICTS

# Rwanda district coordinates (latitude, longitude, altitude in meters)
DISTRICT_COORDINATES = {
    # Kigali City
    "Kigali": {"lat": -1.9484, "lon": 29.8734, "alt": 1567},
    "Nyarugenge": {"lat": -1.9445, "lon": 29.8775, "alt": 1570},
    "Gasabo": {"lat": -1.9400, "lon": 29.8900, "alt": 1550},
    "Kicukiro": {"lat": -1.9550, "lon": 29.8500, "alt": 1560},
    # Northern Province
    "Burera": {"lat": -1.5500, "lon": 29.6500, "alt": 1900},
    "Gicumbi": {"lat": -1.7000, "lon": 29.7500, "alt": 1850},
    "Musanze": {"lat": -1.4897, "lon": 29.6233, "alt": 2100},
    "Rulindo": {"lat": -1.3700, "lon": 29.5500, "alt": 2000},
    # Southern Province
    "Gisagara": {"lat": -2.6000, "lon": 29.2500, "alt": 1900},
    "Huye": {"lat": -2.6000, "lon": 29.7500, "alt": 1700},
    "Kamonyi": {"lat": -2.1500, "lon": 29.9500, "alt": 1600},
    "Muhanga": {"lat": -2.0000, "lon": 30.0500, "alt": 1600},
    "Nyamagabe": {"lat": -2.5500, "lon": 29.5500, "alt": 2000},
    "Nyanza": {"lat": -2.4500, "lon": 29.6500, "alt": 1850},
    "Ruhango": {"lat": -2.3000, "lon": 29.7500, "alt": 1700},
    # Eastern Province
    "Bugesera": {"lat": -2.3500, "lon": 30.4500, "alt": 1400},
    "Gatsibo": {"lat": -2.0000, "lon": 30.5500, "alt": 1450},
    "Kayonza": {"lat": -2.0500, "lon": 30.9500, "alt": 1500},
    "Kirehe": {"lat": -1.7000, "lon": 31.5000, "alt": 1100},
    "Ngoma": {"lat": -2.2000, "lon": 30.4500, "alt": 1400},
    "Rwamagana": {"lat": -2.0000, "lon": 30.8000, "alt": 1400},
    # Western Province
    "Karongi": {"lat": -2.0500, "lon": 29.2500, "alt": 1300},
    "Ngororero": {"lat": -1.9500, "lon": 29.3500, "alt": 1700},
    "Nyabihu": {"lat": -1.8500, "lon": 29.4500, "alt": 1750},
    "Rubavu": {"lat": -1.5000, "lon": 29.2500, "alt": 1800},
    "Rutsiro": {"lat": -1.8000, "lon": 29.0500, "alt": 1550},
}

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('signin'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        role = request.form.get('role')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone_number = request.form.get('phone_number')
        district = request.form.get('district')
        
        # Validation
        if not all([name, email, password, confirm_password, district]):
            flash('All required fields must be filled.', 'error')
            return render_template('signup.html', districts=RWANDA_DISTRICTS)
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html', districts=RWANDA_DISTRICTS)
        
        # Check password length
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('signup.html', districts=RWANDA_DISTRICTS)
        
        # Check if user already exists in either table
        user_exists = Cooperative.query.filter_by(email=email).first() or \
                      Farmer.query.filter_by(email=email).first()
        if user_exists:
            flash('An account with this email already exists.', 'error')
            return render_template('signup.html', districts=RWANDA_DISTRICTS)
        
        # Hash password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        try:
            if role == 'cooperative':
                new_user = Cooperative(
                    name=name,
                    email=email,
                    password=hashed_password,
                    phone_number=phone_number,
                    district=district
                )
            else:  # farmer
                new_user = Farmer(
                    name=name,
                    email=email,
                    password=hashed_password,
                    phone_number=phone_number,
                    farmer_district=district
                )
            
            db.session.add(new_user)
            db.session.commit()
            
            # Auto-login after signup
            login_user(new_user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating your account. Please try again.', 'error')
            return render_template('signup.html', districts=RWANDA_DISTRICTS)
    
    return render_template('signup.html', districts=RWANDA_DISTRICTS)

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html')
        
        # Check across all user types
        user = Cooperative.query.filter_by(email=email).first() or \
               Farmer.query.filter_by(email=email).first() or \
               Admin.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            if hasattr(user, 'last_login'):
                user.last_login = db.func.current_timestamp()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('signin'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Traffic controller for different dashboards
    if isinstance(current_user, Cooperative):
        return cooperative_dashboard_view()
    elif isinstance(current_user, Farmer):
        return farmer_dashboard_view()
    else:
        # Admin dashboard
        total_cooperatives = Cooperative.query.count()
        total_farmers = Farmer.query.count()
        return render_template('cooperative/admin_dashboard.html',
                             total_cooperatives=total_cooperatives,
                             total_farmers=total_farmers)

def cooperative_dashboard_view():
    # Get dashboard statistics for Cooperative
    # Total farmers registered to THIS cooperative or all?
    # Requirement: "farmers that are required in cooperative and there is a table for that"
    total_farmers = Farmer.query.filter_by(cooperative_id=current_user.id).count()
    
    # Total recommendations for farmers in this cooperative
    total_recs = Recommendation.query.join(Farmer).filter(Farmer.cooperative_id == current_user.id).count()
    
    # Average farm size
    avg_farm_size = db.session.query(func.avg(Farmer.farm_size_hectares)).filter(Farmer.cooperative_id == current_user.id).scalar() or 0
    avg_farm_size = round(float(avg_farm_size), 1)
    
    colors = ['#22884F', '#3B82F6', '#F59E0B', '#8B5CF6', '#14B8A6', '#F43F5E']

    def get_seasonal_crop_data(season_enum=None):
        query = db.session.query(
            Prediction.crop_name, 
            func.count(Prediction.id).label('count')
        ).join(Recommendation).join(Farmer).filter(Farmer.cooperative_id == current_user.id)
        
        if season_enum:
            query = query.filter(Recommendation.season == season_enum)
            
        results = query.group_by(Prediction.crop_name).order_by(func.count(Prediction.id).desc()).limit(6).all()
        
        data = []
        for i, (name, count) in enumerate(results):
            lookup_name = name.strip()
            emoji = CROP_EMOJIS.get(lookup_name) or \
                    CROP_EMOJIS.get(lookup_name.replace('_', ' ').title()) or \
                    CROP_EMOJIS.get(lookup_name.lower()) or '🌱'
            
            data.append({
                'name': name.replace('_', ' ').title(),
                'emoji': emoji,
                'count': count,
                'color': colors[i % len(colors)]
            })
        return data

    seasonal_crops_data = {
        'total': get_seasonal_crop_data(None),
        'A': get_seasonal_crop_data(Season.A),
        'B': get_seasonal_crop_data(Season.B),
        'C': get_seasonal_crop_data(Season.C)
    }
    
    top_crops_data = seasonal_crops_data['total']

    # Confidence Score Distribution for this coop
    high_conf = Prediction.query.join(Recommendation).join(Farmer).filter(Farmer.cooperative_id == current_user.id, Prediction.confidence_score >= 60).count()
    med_conf = Prediction.query.join(Recommendation).join(Farmer).filter(Farmer.cooperative_id == current_user.id, Prediction.confidence_score >= 40, Prediction.confidence_score < 60).count()
    low_conf = Prediction.query.join(Recommendation).join(Farmer).filter(Farmer.cooperative_id == current_user.id, Prediction.confidence_score < 40).count()
    
    confidence_distribution = [
        {'label': 'High (60-100%)', 'val': high_conf, 'color': '#22884F'},
        {'label': 'Moderate (40-59%)', 'val': med_conf, 'color': '#3B82F6'},
        {'label': 'Low (<40%)', 'val': low_conf, 'color': '#F59E0B'}
    ]
        
    recent_recommendations = Recommendation.query.join(Farmer).filter(Farmer.cooperative_id == current_user.id).order_by(Recommendation.created_at.desc()).limit(5).all()
    
    return render_template('cooperative/cooperative_dashboard.html', 
                         total_farmers=total_farmers,
                         total_recs=total_recs,
                         avg_farm_size=avg_farm_size,
                         top_crops_data=top_crops_data,
                         seasonal_crops_data=seasonal_crops_data,
                         confidence_distribution=confidence_distribution,
                         recent_recommendations=recent_recommendations,
                         cooperative_name=current_user.name)

def farmer_dashboard_view():
    # Get personal dashboard statistics for Individual Farmer
    total_recs = Recommendation.query.filter_by(farmer_id=current_user.id).count()
    
    # Recent recommendations for THIS farmer
    recent_recommendations = Recommendation.query.filter_by(farmer_id=current_user.id).order_by(Recommendation.created_at.desc()).limit(5).all()
    
    # Get crop distribution for this farmer
    colors = ['#22884F', '#3B82F6', '#F59E0B', '#8B5CF6', '#14B8A6', '#F43F5E']

    def get_seasonal_crop_data(season_enum=None):
        query = db.session.query(
            Prediction.crop_name, 
            func.count(Prediction.id).label('count')
        ).join(Recommendation).filter(Recommendation.farmer_id == current_user.id)
        
        if season_enum:
            query = query.filter(Recommendation.season == season_enum)
            
        results = query.group_by(Prediction.crop_name).order_by(func.count(Prediction.id).desc()).limit(6).all()
        
        data = []
        for i, (name, count) in enumerate(results):
            lookup_name = name.strip()
            emoji = CROP_EMOJIS.get(lookup_name) or \
                    CROP_EMOJIS.get(lookup_name.replace('_', ' ').title()) or \
                    CROP_EMOJIS.get(lookup_name.lower()) or '🌱'
            
            data.append({
                'name': name.replace('_', ' ').title(),
                'emoji': emoji,
                'count': count,
                'color': colors[i % len(colors)]
            })
        return data

    seasonal_crops_data = {
        'total': get_seasonal_crop_data(None),
        'A': get_seasonal_crop_data(Season.A),
        'B': get_seasonal_crop_data(Season.B),
        'C': get_seasonal_crop_data(Season.C)
    }
    
    top_crops_data = seasonal_crops_data['total']

    # Confidence Score Distribution for this farmer
    high_conf = Prediction.query.join(Recommendation).filter(Recommendation.farmer_id == current_user.id, Prediction.confidence_score >= 60).count()
    med_conf = Prediction.query.join(Recommendation).filter(Recommendation.farmer_id == current_user.id, Prediction.confidence_score >= 40, Prediction.confidence_score < 60).count()
    low_conf = Prediction.query.join(Recommendation).filter(Recommendation.farmer_id == current_user.id, Prediction.confidence_score < 40).count()
    
    confidence_distribution = [
        {'label': 'High (60-100%)', 'val': high_conf, 'color': '#22884F'},
        {'label': 'Moderate (40-59%)', 'val': med_conf, 'color': '#3B82F6'},
        {'label': 'Low (<40%)', 'val': low_conf, 'color': '#F59E0B'}
    ]

    return render_template('Farmer/farmer_dashboard.html', 
                         farmer_name=current_user.name,
                         total_recs=total_recs,
                         avg_farm_size=float(current_user.farm_size_hectares or 0),
                         top_crops_data=top_crops_data,
                         seasonal_crops_data=seasonal_crops_data,
                         confidence_distribution=confidence_distribution,
                         recent_recommendations=recent_recommendations)


@app.route('/planting-calendar')
@login_required
def planting_calendar():
    calendar_data = PlantingCalendar.query.all()
    cooperative_name = current_user.name if isinstance(current_user, Cooperative) else None
    farmer_name = current_user.name if isinstance(current_user, Farmer) else None
    template_folder = 'Farmer' if isinstance(current_user, Farmer) else 'cooperative'
    
    return render_template(f'{template_folder}/planting_calendar.html', 
                         calendar_data=calendar_data,
                         cooperative_name=cooperative_name,
                         farmer_name=farmer_name)

@app.route('/dashboard/analytics')
@login_required
def analytics():
    import json
    cooperative_name = current_user.name if isinstance(current_user, Cooperative) else None
    farmer_name = current_user.name if isinstance(current_user, Farmer) else None
    
    # Load the crop whitelist data
    whitelist_path = os.path.join(app.root_path, 'ml', 'rwanda_crop_whitelist.json')
    whitelist_data = {}
    try:
        with open(whitelist_path, 'r') as f:
            whitelist_data = json.load(f)
    except Exception as e:
        print(f"Error loading whitelist: {e}")
    
    template_folder = 'Farmer' if isinstance(current_user, Farmer) else 'cooperative'
    return render_template(f'{template_folder}/analytics.html', 
                         cooperative_name=cooperative_name,
                         farmer_name=farmer_name,
                         whitelist_data=whitelist_data)

@app.route('/dashboard/farmers', methods=['GET', 'POST'])
@login_required
def dashboard_farmers():
    if not isinstance(current_user, Cooperative):
        flash('Access denied. Only cooperatives can manage farmers.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        farmer_district = request.form.get('farmer_district')
        farm_size_hectares = request.form.get('farm_size_hectares')
        gender_str = request.form.get('gender')
        
        # Convert gender string to enum
        gender = None
        if gender_str == 'Male':
            gender = Gender.Male
        elif gender_str == 'Female':
            gender = Gender.Female
        elif gender_str == 'Other':
            gender = Gender.Other
        
        # Validation
        if not all([name, farmer_district]):
            flash('Name and district are required fields.', 'error')
            return render_template('cooperative/farmers.html', 
                             cooperative_name=current_user.name,
                             rwanda_districts=RWANDA_DISTRICTS)
        
        # Create new farmer linked to this cooperative
        new_farmer = Farmer(
            name=name,
            phone_number=phone_number,
            farmer_district=farmer_district,
            farm_size_hectares=farm_size_hectares if farm_size_hectares else None,
            gender=gender,
            cooperative_id=current_user.id
        )
        
        try:
            db.session.add(new_farmer)
            db.session.commit()
            flash('Farmer added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding the farmer. Please try again.', 'error')
    
    # Get all farmers for THIS cooperative only
    farmers = Farmer.query.filter_by(cooperative_id=current_user.id).all()
    return render_template('cooperative/farmers.html', 
                         cooperative_name=current_user.name,
                         rwanda_districts=RWANDA_DISTRICTS,
                         farmers=farmers)

@app.route('/dashboard/recommendation', methods=['GET', 'POST'])
@login_required
def get_recommendation():
    cooperative_name = current_user.name if isinstance(current_user, Cooperative) else None
    farmer_name = current_user.name if isinstance(current_user, Farmer) else None
    template_folder = 'Farmer' if isinstance(current_user, Farmer) else 'cooperative'

    if request.method == 'POST':
        # ── Collect form data ─────────────────────────────────
        farmer_id   = request.form.get('farmer_id')
        # If it's a farmer, they are their own farmer_id
        if isinstance(current_user, Farmer):
            farmer_id = current_user.id

        farm_district = request.form.get('farm_district')
        season      = request.form.get('season')
        altitude    = request.form.get('altitude')
        soil_ph     = request.form.get('soil_ph')
        nitrogen    = request.form.get('nitrogen')
        phosphorus  = request.form.get('phosphorus')
        potassium   = request.form.get('potassium')
        rainfall    = request.form.get('rainfall')
        temperature = request.form.get('temperature')
        humidity    = request.form.get('humidity')

        # ── Validation ────────────────────────────────────────
        if not all([farm_district, season]):
            flash('Farm district and season are required fields.', 'error')
            if isinstance(current_user, Cooperative):
                farmers = Farmer.query.filter_by(cooperative_id=current_user.id).all()
            else:
                farmers = [current_user]

            recommendations = Recommendation.query.filter_by(farmer_id=current_user.id).order_by(
                Recommendation.created_at.desc()).limit(50).all() if isinstance(current_user, Farmer) else \
                Recommendation.query.join(Farmer).filter(Farmer.cooperative_id == current_user.id).order_by(
                Recommendation.created_at.desc()).limit(50).all()

            return render_template(f'{template_folder}/recommendation.html',
                                   cooperative_name=cooperative_name,
                                   farmer_name=farmer_name,
                                   rwanda_districts=RWANDA_DISTRICTS,
                                   farmers=farmers,
                                   recommendations=recommendations)

        # ── Build ML input (N/P/K in kg/ha — predictor scales internally) ──
        input_data = {
            'soil_ph':     float(soil_ph)     if soil_ph     else 6.5,
            'nitrogen':    float(nitrogen)    if nitrogen    else 50.0,
            'phosphorus':  float(phosphorus)  if phosphorus  else 30.0,
            'potassium':   float(potassium)   if potassium   else 40.0,
            'rainfall':    float(rainfall)    if rainfall    else 1000.0,
            'temperature': float(temperature) if temperature else 22.0,
            'humidity':    float(humidity)    if humidity    else 70.0,
            'altitude':    float(altitude)    if altitude    else 1500.0,
        }

        # ── Run ML model with whitelist validation ────────────
        try:
            predictions = predict_crops(input_data, district=farm_district, season=season)
        except Exception as e:
            print(f"ML Prediction error: {e}")
            predictions = [
                {'crop_name': 'Maize',        'confidence_score': 60.0, 'source': 'fallback'},
                {'crop_name': 'Beans',        'confidence_score': 25.0, 'source': 'fallback'},
                {'crop_name': 'Sweet Potato', 'confidence_score': 15.0, 'source': 'fallback'},
            ]

        # ── Save recommendation record ────────────────────────
        new_recommendation = Recommendation(
            farmer_id=int(farmer_id) if farmer_id else (current_user.id if isinstance(current_user, Farmer) else 1),
            farm_district=farm_district,
            season=season,
            altitude=float(altitude)    if altitude    else None,
            soil_ph=float(soil_ph)      if soil_ph     else None,
            nitrogen=float(nitrogen)    if nitrogen    else None,
            phosphorus=float(phosphorus) if phosphorus else None,
            potassium=float(potassium)  if potassium   else None,
            rainfall=float(rainfall)    if rainfall    else None,
            temperature=float(temperature) if temperature else None,
            humidity=float(humidity)    if humidity    else None,
        )

        try:
            db.session.add(new_recommendation)
            db.session.commit()

            for pred in predictions:
                db.session.add(Prediction(
                    recommendation_id=new_recommendation.id,
                    crop_name=pred['crop_name'],
                    confidence_score=round(pred['confidence_score'], 2),
                ))
            db.session.commit()

            return redirect(url_for('recommendation_results', res_id=new_recommendation.id))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred while saving the recommendation. Please try again.', 'error')
            print(f"Database error: {e}")

    # ── GET — render the form ─────────────────────────────────
    if isinstance(current_user, Cooperative):
        farmers = Farmer.query.filter_by(cooperative_id=current_user.id).all()
        recommendations = Recommendation.query.join(Farmer).filter(Farmer.cooperative_id == current_user.id).order_by(
            Recommendation.created_at.desc()).limit(50).all()
    else:
        farmers = [current_user]
        recommendations = Recommendation.query.filter_by(farmer_id=current_user.id).order_by(
            Recommendation.created_at.desc()).limit(50).all()

    return render_template(f'{template_folder}/recommendation.html',
                           cooperative_name=cooperative_name,
                           farmer_name=farmer_name,
                           rwanda_districts=RWANDA_DISTRICTS,
                           farmers=farmers,
                           recommendations=recommendations)

@app.route('/dashboard/weather-forecast')
@login_required
def weather_forecast():
    cooperative_name = current_user.name if isinstance(current_user, Cooperative) else None
    farmer_name = current_user.name if isinstance(current_user, Farmer) else None
    template_folder = 'Farmer' if isinstance(current_user, Farmer) else 'cooperative'
    return render_template(f'{template_folder}/weather_forecast.html', 
                         cooperative_name=cooperative_name,
                         farmer_name=farmer_name)

@app.route('/history')
@login_required
def history():
    cooperative_name = current_user.name if isinstance(current_user, Cooperative) else None
    farmer_name = current_user.name if isinstance(current_user, Farmer) else None
    template_folder = 'Farmer' if isinstance(current_user, Farmer) else 'cooperative'
    
    if isinstance(current_user, Cooperative):
        recommendations = Recommendation.query.join(Farmer).filter(Farmer.cooperative_id == current_user.id).order_by(Recommendation.created_at.desc()).limit(200).all()
    else:
        recommendations = Recommendation.query.filter_by(farmer_id=current_user.id).order_by(Recommendation.created_at.desc()).limit(200).all()
        
    return render_template(f'{template_folder}/history.html', 
                         cooperative_name=cooperative_name, 
                         farmer_name=farmer_name,
                         recommendations=recommendations)

@app.route('/api/weather/<district_name>')
@login_required
def api_weather(district_name):
    """API endpoint to fetch weather data for a specific district"""
    
    print(f"API called for district: {district_name}")
    
    # Get district coordinates, default to Kigali if not found
    district_info = DISTRICT_COORDINATES.get(district_name, {"lat": -1.9403, "lon": 29.8739, "alt": 1567})
    
    print(f"District info: {district_info}")
    
    # If API key is configured, fetch live data
    if OPENWEATHER_API_KEY:
        try:
            # Fetch current weather using district coordinates
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={district_info['lat']}&lon={district_info['lon']}&appid={OPENWEATHER_API_KEY}&units=metric"
            print(f"Fetching: {weather_url}")
            weather_response = requests.get(weather_url, timeout=5)
            
            print(f"Weather API response status: {weather_response.status_code}")
            
            if weather_response.ok:
                weather_data = weather_response.json()
                print(f"Weather data: {weather_data}")
                
                # Fetch 5-day forecast
                forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={district_info['lat']}&lon={district_info['lon']}&appid={OPENWEATHER_API_KEY}&units=metric"
                forecast_response = requests.get(forecast_url, timeout=5)
                
                forecast_data = None
                if forecast_response.ok:
                    forecast_data = forecast_response.json()
                
                # Parse the data
                result = parse_weather_data(weather_data, forecast_data, district_name, district_info['alt'])
                print(f"Returning weather data: {result}")
                return jsonify(result)
            else:
                # If API fails, return demo data
                print(f"Weather API error: {weather_response.status_code} - {weather_response.text}")
                return jsonify(generate_demo_weather_data(district_name, district_info['alt']))
                
        except Exception as e:
            print(f"Error fetching weather data for {district_name}: {e}")
            # Return demo data on error
            return jsonify(generate_demo_weather_data(district_name, district_info['alt']))
    else:
        # No API key configured, return demo data
        print("No OpenWeatherMap API key configured")
        return jsonify(generate_demo_weather_data(district_name, district_info['alt']))

def parse_weather_data(weather_data, forecast_data, district_name, altitude=1567):
    """Parse OpenWeatherMap API response"""
    
    # Get current weather
    temperature = round(weather_data['main']['temp'])
    humidity = weather_data['main']['humidity']
    rainfall = weather_data.get('rain', {}).get('1h', 0)
    
    # Parse forecast if available
    if forecast_data:
        forecast = parse_forecast(forecast_data)
        weekly_rainfall = generate_weekly_rainfall_from_forecast(forecast_data)
        temp_humidity = parse_temp_humidity(forecast_data)
    else:
        forecast = generate_demo_forecast()
        weekly_rainfall = generate_weekly_rainfall('moderate')
        temp_humidity = generate_temp_humidity_data(temperature)
    
    return {
        'temperature': temperature,
        'rainfall': rainfall,
        'humidity': humidity,
        'altitude': altitude,
        'forecast': forecast,
        'weeklyRainfall': weekly_rainfall,
        'tempHumidity': temp_humidity
    }

def parse_forecast(forecast_data):
    """Parse 5-day forecast from API"""
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    daily_data = {}
    
    for item in forecast_data['list']:
        dt = datetime.fromtimestamp(item['dt'])
        day_index = dt.weekday()
        
        if day_index not in daily_data:
            daily_data[day_index] = {
                'high': -float('inf'),
                'low': float('inf'),
                'rain': 0,
                'icon': get_weather_icon(item['weather'][0]['main'])
            }
        
        daily_data[day_index]['high'] = max(daily_data[day_index]['high'], item['main']['temp_max'])
        daily_data[day_index]['low'] = min(daily_data[day_index]['low'], item['main']['temp_min'])
        daily_data[day_index]['rain'] += item.get('rain', {}).get('3h', 0)
    
    # Convert to list starting from tomorrow
    today_index = datetime.now().weekday()
    forecast = []
    for i in range(1, 8):  # Start from 1 to 7 (tomorrow to next 7 days)
        day_index = (today_index + i) % 7
        if day_index in daily_data:
            d = daily_data[day_index]
            forecast.append({
                'day': days[day_index],
                'icon': d['icon'],
                'high': round(d['high']),
                'low': round(d['low']),
                'rain': round(d['rain'])
            })
        else:
            forecast.append({
                'day': days[day_index],
                'icon': '☀️',
                'high': 25,
                'low': 18,
                'rain': 0
            })
    
    return forecast

def generate_weekly_rainfall_from_forecast(forecast_data):
    """Generate 8-week rainfall trend from forecast data"""
    # Simplified - use forecast data to estimate
    base = 30
    return [round(base + (i % 3) * 10 + (i * 2)) for i in range(8)]

def parse_temp_humidity(forecast_data):
    """Parse temperature and humidity data"""
    temps = []
    humidity = []
    
    for i, item in enumerate(forecast_data['list'][:7]):
        temps.append(round(item['main']['temp']))
        humidity.append(item['main']['humidity'])
    
    return {'temps': temps, 'humidity': humidity}

def get_weather_icon(weather_main):
    """Map weather condition to emoji"""
    icons = {
        'Clear': '☀️',
        'Clouds': '⛅',
        'Rain': '🌧️',
        'Drizzle': '🌦️',
        'Thunderstorm': '⛈️',
        'Mist': '🌫️',
        'Fog': '🌫️'
    }
    return icons.get(weather_main, '☀️')

def generate_demo_weather_data(district_name, altitude=1567):
    """Generate demo weather data when API is not available"""
    
    # Generate data based on altitude
    base_temp = 25 - (altitude / 200)
    
    return {
        'temperature': round(base_temp + 3),
        'rainfall': 25,
        'humidity': 72,
        'altitude': altitude,
        'forecast': generate_demo_forecast(),
        'weeklyRainfall': generate_weekly_rainfall('moderate'),
        'tempHumidity': generate_temp_humidity_data(base_temp)
    }

def generate_demo_forecast():
    """Generate demo 7-day forecast"""
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    icons = ['☀️', '⛅', '🌧️', '☀️', '⛅', '🌧️', '☀️']
    today_index = datetime.now().weekday()
    
    forecast = []
    for i in range(1, 8):
        day_idx = (today_index + i) % 7
        forecast.append({
            'day': days[day_idx], 
            'icon': icons[day_idx], 
            'high': 24 + i % 4, 
            'low': 16 + i % 3, 
            'rain': (i % 3) * 10
        })
    return forecast

def generate_weekly_rainfall(level):
    """Generate 8-week rainfall trend"""
    base = {'low': 10, 'moderate': 30, 'high': 60}.get(level, 30)
    return [round(base + (i % 3) * 10 + (i * 2)) for i in range(8)]

def generate_temp_humidity_data(base_temp):
    """Generate temperature and humidity data"""
    return {
        'temps': [round(base_temp + i) for i in range(7)],
        'humidity': [65 + i % 15 for i in range(7)]
    }

@app.route('/dashboard/recommendation/results/<int:res_id>')
@login_required
def recommendation_results(res_id):
    # Get the recommendation by ID
    recommendation = Recommendation.query.get_or_404(res_id)
    
    # Get all predictions for this recommendation
    predictions = Prediction.query.filter_by(recommendation_id=res_id).order_by(Prediction.confidence_score.desc()).all()
    
    cooperative_name = current_user.name if isinstance(current_user, Cooperative) else None
    farmer_name = current_user.name if isinstance(current_user, Farmer) else None
    template_folder = 'Farmer' if isinstance(current_user, Farmer) else 'cooperative'
    
    return render_template(f'{template_folder}/recommendation_results.html',
                         recommendation=recommendation,
                         predictions=predictions,
                         cooperative_name=cooperative_name,
                         farmer_name=farmer_name)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
