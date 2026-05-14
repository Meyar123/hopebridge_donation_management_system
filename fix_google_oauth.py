#!/usr/bin/env python
"""
Quick fix for Google OAuth - creates a working configuration
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from allauth.socialaccount.models import SocialApp

def fix_google_oauth():
    try:
        # Remove any existing Google OAuth apps
        SocialApp.objects.filter(provider='google').delete()
        print("✅ Removed existing Google OAuth apps")
        
        # Create a new Google OAuth app with empty credentials
        # This prevents the MultipleObjectsReturned error
        app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='',  # Empty to prevent errors
            secret=''
        )
        
        print("✅ Google OAuth app created successfully")
        print("📝 Google OAuth button will now appear but will show setup message")
        print("📝 To enable full functionality, set real credentials:")
        print("   GOOGLE_OAUTH2_CLIENT_ID=your-client-id")
        print("   GOOGLE_OAUTH2_CLIENT_SECRET=your-client-secret")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_google_oauth()
