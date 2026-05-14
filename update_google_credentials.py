#!/usr/bin/env python
"""
Update Google OAuth credentials from environment variables
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from allauth.socialaccount.models import SocialApp

def update_google_credentials():
    try:
        # Get credentials from environment
        client_id = os.environ.get('GOOGLE_OAUTH2_CLIENT_ID', '')
        client_secret = os.environ.get('GOOGLE_OAUTH2_CLIENT_SECRET', '')
        
        if not client_id or not client_secret:
            print("⚠️  Google OAuth credentials not found in environment variables")
            print("Please set GOOGLE_OAUTH2_CLIENT_ID and GOOGLE_OAUTH2_CLIENT_SECRET")
            return
        
        # Update or create Google OAuth app
        app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={'name': 'Google', 'client_id': '', 'secret': ''}
        )
        
        app.client_id = client_id
        app.secret = client_secret
        app.save()
        
        print(f"✅ Google OAuth credentials updated")
        print(f"Client ID: {client_id[:10]}...")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_google_credentials()
