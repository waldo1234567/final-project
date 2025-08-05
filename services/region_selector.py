import math
from geoip2.database import Reader
from flask import request
from config import AWS_REGION_COORDS

def haversine(lat1,lon1, lat2, lon2):
    R = 6371
    theta1, theta2 = math.radians(lat1), math.radians(lat2)
    delta1 = math.radians(lat2 - lat1)
    delta2 = math.radians(lon2 - lon1)
    a = math.sin(delta1/2)**2 + math.cos(theta1)*math.cos(theta2)*math.sin(delta2/2)**2
    return 2 * R * math.asin(math.sqrt(a))

_geoip_reader = Reader('geoip/GeoLite2-City.mmdb')

def detect_user_region(default ='ap-southeast-1'):
    
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    try:
        city = _geoip_reader.city(ip)
        user_lat = city.location.latitude
        user_lon = city.location.longitude
        if user_lat is None or user_lon is None:
            raise ValueError("No location for IP")
        
    except Exception:
        return default

    best_region = default
    best_dist = float('inf')
    for region, (lat, lon) in AWS_REGION_COORDS.items():
        d = haversine(user_lat, user_lon, lat, lon)
        if d < best_dist:
            best_dist = d
            best_region = region
    
    return best_region