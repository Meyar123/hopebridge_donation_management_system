# users/social_adapter.py
import re
import logging
import requests
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from datetime import datetime
from django.contrib.auth.hashers import make_password
from mongo_utils import connect_to_mongodb, get_mongodb_connection, ensure_mongodb_connection
from mongo_models import User as MongoUser, Address as MongoAddress

def _ensure_mongo():
    try:
        ensure_mongodb_connection()
    except Exception as e:
        logger.error(f"Failed to ensure MongoDB connection: {e}")
        # Try to connect anyway
        connect_to_mongodb()

logger = logging.getLogger(__name__)

PEOPLE_URL = "https://people.googleapis.com/v1/people/me"


def _normalize_phone(value: str) -> str:
    """
    מחזירה רק ספרות; אם יש יותר מ-10 ספרות – שומרת את 10 האחרונות.
    (מתאים למספרים בינ"ל עם +972 וכד' ומנרמל ל-050XXXXXXX)
    """
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    - מאכלסת name מהפרופיל של Google (או מ-local part של המייל אם חסר)
    - לאחר השמירה מושכת טלפון מ-Google People API אם המשתמשת אישרה scope מתאים
    """

    def populate_user(self, request, sociallogin, data):
        # קודם ברירת מחדל של allauth
        user = super().populate_user(request, sociallogin, data)

        # מקור בטוח לשמות: extra_data (לפעמים data חסר שדות)
        extra = {}
        try:
            extra = (sociallogin.account.extra_data or {})
        except Exception:
            extra = {}

        # ננסה לפי סדר עדיפויות: given+family → name → data → fallback מהאימייל
        given = (extra.get("given_name") or data.get("given_name") or "").strip()
        family = (extra.get("family_name") or data.get("family_name") or "").strip()
        display = (extra.get("name") or data.get("name") or "").strip()

        candidate = (f"{given} {family}".strip()) or display or ""
        if not candidate and user.email:
            candidate = (
                user.email.split("@")[0]
                .replace(".", " ")
                .replace("_", " ")
                .strip()
            )

        # אם קיים – נשבץ לשדה המודל שלך
        if candidate:
            user.name = candidate

        return user

    # עוזרת: שליפת access_token בתואמות גרסאות שונות של allauth
    def _get_access_token(self, sociallogin):
        token_obj = getattr(sociallogin, "token", None)
        access_token = getattr(token_obj, "token", None) if token_obj else None
        if not access_token and hasattr(sociallogin.account, "get_tokens"):
            try:
                tok = sociallogin.account.get_tokens().first()
                if tok:
                    access_token = tok.token
            except Exception as e:
                logger.debug("get_tokens() failed: %s", e)
        return access_token

    def save_user(self, request, sociallogin, form=None):
        """
        שומרת את המשתמש/ת ואז מנסה להביא טלפון מתוך Google People API.
        אם אין הרשאה/טוקן/שגיאה – נשאיר את הטלפון ריק (ניתן להשלים ידנית).
        """
        user = super().save_user(request, sociallogin, form)

        # --------- סנכרון ל-Mongo ---------
        try:
            # Try to ensure MongoDB connection first
            if not ensure_mongodb_connection():
                logger.warning("MongoDB not available, using fallback user system")
                # Set session data from Django user as fallback
                request.session['mongo_user_id'] = str(user.id)
                request.session['mongo_user_email'] = user.email
                request.session['mongo_user_name'] = getattr(user, "name", "") or user.email.split("@")[0]
                request.session['mongo_user_is_staff'] = False
                request.session['mongo_user_is_superuser'] = False
                logger.info(f"Set fallback session data for user: {user.email}")
                return user
            
            # Try to perform a simple MongoDB operation to test if we can actually use it
            # This will catch authentication errors that happen during operations
            try:
                logger.info(f"Testing MongoDB operations for email: {user.email}")
                # Try a simple query to test if we can actually use MongoDB
                MongoUser.objects.limit(1).first()
                logger.info(f"MongoDB operations test successful, proceeding with user creation")
            except Exception as test_error:
                logger.warning(f"MongoDB operations test failed: {test_error}, using fallback system")
                # Set session data from Django user as fallback
                request.session['mongo_user_id'] = str(user.id)
                request.session['mongo_user_email'] = user.email
                request.session['mongo_user_name'] = getattr(user, "name", "") or user.email.split("@")[0]
                request.session['mongo_user_is_staff'] = False
                request.session['mongo_user_is_superuser'] = False
                logger.info(f"Set fallback session data for user: {user.email}")
                return user
            
            logger.info(f"Attempting to find/create MongoUser for email: {user.email}")
            m_user = MongoUser.objects(email=user.email).first()
            if not m_user:
                # יוצרים משתמש Mongo ראשוני
                m_user = MongoUser(
                    email=user.email,
                    name=getattr(user, "name", "") or (user.email.split("@")[0]),
                    phone=getattr(user, "phone", ""),
                    address=MongoAddress(  # כתובת ריקה בשלב זה
                        street="", city="", postal_code="", country="", apartment="", instructions=""
                    ),
                    password_hash=make_password(None),  # סיסמה "לא שמישה" כי זה סושיאל
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                    date_joined=datetime.utcnow(),
                )
                m_user.save()
            else:
                # מעדכנים שם/טלפון אם חסר
                changed = False
                if not getattr(m_user, "name", "") and getattr(user, "name", ""):
                    m_user.name = user.name
                    changed = True
                if not getattr(m_user, "phone", "") and getattr(user, "phone", ""):
                    m_user.phone = user.phone
                    changed = True
                if changed:
                    m_user.save()

            # כותבים session keys כמו בלוגין Mongo ידני
            request.session['mongo_user_id'] = str(m_user.id)
            request.session['mongo_user_email'] = m_user.email
            request.session['mongo_user_name'] = getattr(m_user, "name", "") or user.email
            request.session['mongo_user_is_staff'] = bool(getattr(m_user, "is_staff", False))
            request.session['mongo_user_is_superuser'] = bool(getattr(m_user, "is_superuser", False))
        except Exception as e:
            logger.exception("Mongo sync after social login failed: %s", e)
            # Don't fail the entire login process if MongoDB sync fails
            # Set session data from Django user as fallback
            try:
                request.session['mongo_user_id'] = str(user.id)
                request.session['mongo_user_email'] = user.email
                request.session['mongo_user_name'] = getattr(user, "name", "") or user.email.split("@")[0]
                request.session['mongo_user_is_staff'] = False
                request.session['mongo_user_is_superuser'] = False
                logger.info(f"Set fallback session data for user: {user.email}")
            except Exception as session_error:
                logger.error(f"Failed to set fallback session data: {session_error}")
            pass

        # --------- (לא שינינו) משיכת טלפון מ-Google People API ---------
        if getattr(user, "phone", "").strip():
            return user

        access_token = self._get_access_token(sociallogin)
        if not access_token:
            logger.debug("No Google access token available; skipping phone fetch.")
            return user

        try:
            resp = requests.get(
                PEOPLE_URL,
                params={"personFields": "phoneNumbers"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=8,
            )
            if resp.status_code == 200:
                payload = resp.json()
                numbers = payload.get("phoneNumbers") or []
                if numbers:
                    primary = next(
                        (n for n in numbers if (n.get("metadata") or {}).get("primary")),
                        numbers[0],
                    )
                    raw = primary.get("value", "")
                    norm = _normalize_phone(raw)
                    if norm:
                        user.phone = norm
                        user.save(update_fields=["phone"])
                        # נסה להשלים גם ב-Mongo אם חסר
                        try:
                            if ensure_mongodb_connection():
                                m = MongoUser.objects(email=user.email).first()
                                if m and not getattr(m, "phone", ""):
                                    m.phone = norm
                                    m.save()
                        except Exception:
                            pass
            else:
                logger.warning("Google People API error %s: %s", resp.status_code, resp.text)
        except Exception as e:
            logger.exception("Failed fetching phone via Google People API: %s", e)

        return user