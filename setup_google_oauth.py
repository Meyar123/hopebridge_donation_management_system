#!/usr/bin/env python
"""
Setup Google OAuth with proper configuration
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from allauth.socialaccount.models import SocialApp

def setup_google_oauth():
    try:
        # Remove any existing Google OAuth apps
        SocialApp.objects.filter(provider='google').delete()
        print("✅ Cleared existing Google OAuth apps")
        
        # Create a new Google OAuth app
        # For development, we'll use placeholder values that won't cause errors
        app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='',  # Empty client_id prevents the error
            secret=''
        )
        
        print("✅ Google OAuth app created (placeholder mode)")
        print("📝 To enable Google OAuth:")
        print("1. Get Google OAuth credentials from Google Cloud Console")
        print("2. Set environment variables:")
        print("   GOOGLE_OAUTH2_CLIENT_ID=your-client-id")
        print("   GOOGLE_OAUTH2_CLIENT_SECRET=your-client-secret")
        print("3. Run: python update_google_credentials.py")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    setup_google_oauth()
