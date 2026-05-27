from __init__ import db, login_manager
from flask_login import UserMixin
from datetime import datetime
import enum

class CooperativeStatus(enum.Enum):
    Pending = 'Pending'
    Active = 'Active'
    Disabled = 'Disabled'

class Season(enum.Enum):
    A = 'Season A'
    B = 'Season B'
    C = 'Season C'

class Gender(enum.Enum):
    Male = 'Male'
    Female = 'Female'
    Other = 'Other'


class Admin(UserMixin, db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return f'admin-{self.id}'


class Cooperative(UserMixin, db.Model):
    __tablename__ = 'cooperative'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20))
    district = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return f'coop-{self.id}'


class Farmer(UserMixin, db.Model):
    __tablename__ = 'farmer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=True)  # Nullable for coop-added farmers
    password = db.Column(db.String(255), nullable=True)            # Nullable for coop-added farmers
    farmer_district = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    farm_size_hectares = db.Column(db.Numeric(6, 2))
    gender = db.Column(db.Enum(Gender))
    cooperative_id = db.Column(db.Integer, db.ForeignKey('cooperative.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recommendations = db.relationship('Recommendation', backref='farmer', lazy=True)

    def get_id(self):
        return f'farmer-{self.id}'


class Recommendation(db.Model):
    __tablename__ = 'recommendation'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmer.id'), nullable=False)
    soil_ph = db.Column(db.Numeric(4, 2))
    nitrogen = db.Column(db.Numeric(6, 2))
    phosphorus = db.Column(db.Numeric(6, 2))
    potassium = db.Column(db.Numeric(6, 2))
    rainfall = db.Column(db.Numeric(7, 2))
    temperature = db.Column(db.Numeric(5, 2))
    humidity = db.Column(db.Numeric(5, 2))
    altitude = db.Column(db.Numeric(7, 2))
    farm_district = db.Column(db.String(100))
    farmer_district = db.Column(db.String(100))
    season = db.Column(db.Enum(Season))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    predictions = db.relationship('Prediction', backref='recommendation', lazy=True,
                                  order_by='Prediction.confidence_score.desc()')


class Prediction(db.Model):
    __tablename__ = 'prediction'
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('recommendation.id'), nullable=False)
    crop_name = db.Column(db.String(100))
    confidence_score = db.Column(db.Numeric(5, 2))
    model_version = db.Column(db.String(50), default='1.0')
    is_accepted = db.Column(db.Boolean, default=False)
    predicted_at = db.Column(db.DateTime, default=datetime.utcnow)


class PlantingCalendar(db.Model):
    __tablename__ = 'planting_calendar'
    id = db.Column(db.Integer, primary_key=True)
    crop_name = db.Column(db.String(100))
    season = db.Column(db.Enum(Season))
    district = db.Column(db.String(100))
    planting_start_month = db.Column(db.Integer)
    planting_end_month = db.Column(db.Integer)
    harvest_duration_weeks = db.Column(db.Integer)
    suitable_altitude_min = db.Column(db.Integer)
    suitable_altitude_max = db.Column(db.Integer)
    notes = db.Column(db.Text)
    updated_by = db.Column(db.Integer, db.ForeignKey('admin.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith('admin-'):
        return Admin.query.get(int(user_id.split('-')[1]))
    elif user_id.startswith('coop-'):
        return Cooperative.query.get(int(user_id.split('-')[1]))
    elif user_id.startswith('farmer-'):
        return Farmer.query.get(int(user_id.split('-')[1]))
    return None
