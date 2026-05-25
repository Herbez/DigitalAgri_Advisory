import os
import json
import random

BASE_DIR  = os.path.dirname(__file__)
WHITELIST_PATH = os.path.join(BASE_DIR, 'rwanda_crop_whitelist.json')

_whitelist = None
_district_lookup = None

# ── Display name mapping ──────────────────────────────────────
# Keep for backward compatibility or if needed by other parts of the app
CROP_DISPLAY_NAMES = {
    'irish_potato': 'Irish Potato',
    'sweet_potato': 'Sweet Potato',
    'banana':       'Banana',
    'beans':        'Beans',
    'cassava':      'Cassava',
    'maize':        'Maize',
    'rice':         'Rice',
    'tomato':       'Tomato',
    'wheat':        'Wheat',
    'sorghum':      'Sorghum',
    'sunflower':    'Sunflower',
    'vegetables':   'Vegetables',
    'coffee':       'Coffee',
}

def _load():
    global _whitelist, _district_lookup
    if _whitelist is None:
        try:
            with open(WHITELIST_PATH, 'r') as f:
                _whitelist = json.load(f)
            
            # Build a case-insensitive district lookup
            _district_lookup = {k.strip().lower(): k for k in _whitelist.get('districts', {}).keys()}
        except Exception as e:
            print(f"Error loading whitelist: {e}")
            _whitelist = {"districts": {}}
            _district_lookup = {}

def _normalise_season(season: str) -> str:
    s = season.strip()
    if s in ('A', 'B', 'C'):
        return f'Season_{s}'
    if s in ('Season_A', 'Season_B', 'Season_C'):
        return s
    return 'Season_A'

def _get_whitelist_crops(district: str, season: str) -> list:
    """Return valid crop display names for a district+season."""
    _load()
    if not district:
        return []
    
    season_key = _normalise_season(season)
    key = district.strip().lower()
    
    actual_district_name = _district_lookup.get(key)
    if not actual_district_name:
        return []
        
    district_data = _whitelist['districts'].get(actual_district_name, {})
    season_data = district_data.get(season_key, {})
    return season_data.get('crops', [])

def predict_crops(input_dict: dict, district: str = None, season: str = None) -> list:
    """
    Returns suitable crops based on the Rwanda district/season crop whitelist.
    Soil data in input_dict is currently ignored for crop selection but 
    retained in the system for generating agricultural advice.
    """
    _load()

    if not district or not season:
        # Fallback if no district/season provided
        return [
            {'crop_name': 'Maize', 'confidence_score': round(random.uniform(60, 75), 2), 'source': 'fallback'},
            {'crop_name': 'Beans', 'confidence_score': round(random.uniform(45, 55), 2), 'source': 'fallback'}
        ]

    valid_crops = _get_whitelist_crops(district, season)
    
    if not valid_crops:
        return [
            {'crop_name': 'Maize', 'confidence_score': round(random.uniform(60, 75), 2), 'source': 'district_fallback'},
            {'crop_name': 'Beans', 'confidence_score': round(random.uniform(45, 55), 2), 'source': 'district_fallback'}
        ]

    # Map whitelist crops to the required output format
    # Assign random confidence scores based on rank to maintain UI consistency
    predictions = []
    
    # Random ranges:
    # 1st: 60 - 75
    # 2nd: 45 - 55
    # 3rd: 5 - 35
    ranges = [(60, 75), (45, 55), (5, 35)]
    
    for i, crop in enumerate(valid_crops):
        # Limit to top 3 crops to match the specified ranges
        if i >= 3:
            break
            
        low, high = ranges[i]
        confidence = round(random.uniform(low, high), 2)
            
        predictions.append({
            'crop_name': crop,
            'confidence_score': confidence,
            'source': 'whitelist'
        })
        
    return predictions
