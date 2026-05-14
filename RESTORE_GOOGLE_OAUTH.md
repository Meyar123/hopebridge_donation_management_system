# Restore Google OAuth Functionality

## Quick Fix Commands

Run these commands in your terminal to restore Google OAuth:

```bash
# 1. Clear existing Google OAuth apps
python manage.py shell -c "from allauth.socialaccount.models import SocialApp; SocialApp.objects.filter(provider='google').delete(); print('Cleared Google OAuth apps')"

# 2. Create a new Google OAuth app
python manage.py shell -c "from allauth.socialaccount.models import SocialApp; SocialApp.objects.create(provider='google', name='Google', client_id='', secret=''); print('Google OAuth app created')"

# 3. Start the server
python manage.py runserver
```

## Alternative: Use the Setup Scripts

```bash
# Run the fix script
python fix_google_oauth.py

# Start the server
python manage.py runserver
```

## What This Does

1. **Removes duplicate Google OAuth apps** that were causing the `MultipleObjectsReturned` error
2. **Creates a single Google OAuth app** with empty credentials
3. **Enables the Google OAuth button** to appear without errors
4. **Shows setup message** when clicked (since no real credentials are set)

## For Full Google OAuth Functionality

1. Get Google OAuth credentials from Google Cloud Console
2. Set environment variables:
   ```bash
   GOOGLE_OAUTH2_CLIENT_ID=your-client-id
   GOOGLE_OAUTH2_CLIENT_SECRET=your-client-secret
   ```
3. Run: `python update_google_credentials.py`

## Current Status
- ✅ Python 3.13.3 working perfectly
- ✅ Django server running smoothly
- ✅ Google OAuth button will appear
- ⚠️ Google OAuth needs real credentials for full functionality
