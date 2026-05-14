#!/usr/bin/env python3
"""
Script to diagnose and fix MongoDB connection issues in Railway deployment
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings_production')
django.setup()

from django.conf import settings
from mongo_utils import connect_to_mongodb, get_mongodb_connection

def diagnose_mongodb():
    """Diagnose MongoDB connection issues"""
    print("=== MongoDB Connection Diagnosis ===")
    print(f"MONGODB_URI: {getattr(settings, 'MONGODB_URI', 'Not set')}")
    print(f"MONGODB_HOST: {getattr(settings, 'MONGODB_HOST', 'Not set')}")
    print(f"MONGODB_PORT: {getattr(settings, 'MONGODB_PORT', 'Not set')}")
    print(f"MONGODB_DATABASE: {getattr(settings, 'MONGODB_DATABASE', 'Not set')}")
    print(f"MONGODB_USER: {getattr(settings, 'MONGODB_USER', 'Not set')}")
    print(f"MONGODB_PASSWORD: {'***' if getattr(settings, 'MONGODB_PASSWORD', '') else 'Not set'}")
    
    print("\n=== Environment Variables ===")
    mongodb_vars = ['MONGODB_URI', 'MONGOHOST', 'MONGOPORT', 'MONGODB_DATABASE', 'MONGOUSER', 'MONGOPASSWORD']
    for var in mongodb_vars:
        value = os.environ.get(var, 'Not set')
        if 'PASSWORD' in var and value != 'Not set':
            value = '***'
        print(f"{var}: {value}")
    
    print("\n=== Connection Test ===")
    try:
        if connect_to_mongodb():
            print("✅ MongoDB connection successful!")
            if get_mongodb_connection():
                print("✅ MongoDB connection verified!")
            else:
                print("❌ MongoDB connection verification failed")
        else:
            print("❌ MongoDB connection failed")
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
    
    print("\n=== Recommendations ===")
    if 'railway.internal' in getattr(settings, 'MONGODB_URI', ''):
        print("⚠️  Railway internal hostname detected. This might not be accessible.")
        print("   Consider using MongoDB Atlas or external MongoDB service.")
    
    if not getattr(settings, 'MONGODB_URI', ''):
        print("⚠️  No MONGODB_URI set. Check Railway environment variables.")
    
    print("\n=== Fallback Solution ===")
    print("The application has been updated to work without MongoDB.")
    print("User roles will be stored in Django sessions as a fallback.")

if __name__ == "__main__":
    diagnose_mongodb()
