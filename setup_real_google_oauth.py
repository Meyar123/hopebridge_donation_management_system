#!/usr/bin/env python
"""
Setup Google OAuth with real credentials
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from allauth.socialaccount.models import SocialApp

def setup_real_google_oauth():
    try:
        # Get Google OAuth credentials from environment variables
        client_id = os.environ.get('GOOGLE_OAUTH2_CLIENT_ID', '')
        client_secret = os.environ.get('GOOGLE_OAUTH2_CLIENT_SECRET', '')
        
        if not client_id or not client_secret:
            print("⚠️  Google OAuth credentials not found in environment variables")
            print("Please set GOOGLE_OAUTH2_CLIENT_ID and GOOGLE_OAUTH2_CLIENT_SECRET")
            return
        
        # Remove any existing Google OAuth apps
        SocialApp.objects.filter(provider='google').delete()
        print("✅ Cleared existing Google OAuth apps")
        
        # Create a new Google OAuth app with real credentials
        app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id=client_id,
            secret=client_secret
        )
        
        print("✅ Google OAuth app created with real credentials")
        print(f"Client ID: {client_id[:20]}...")
        print("🎉 Google OAuth should now work properly!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    setup_real_google_oauth()
