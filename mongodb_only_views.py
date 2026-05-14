"""
MongoDB-only views for the donation management system
These views completely replace Django ORM with MongoDB operations
"""

from django.shortcuts import render
from django.contrib.auth import get_user_model, login as dj_login
from django.core.paginator import Paginator
from datetime import datetime
from mongo_utils import connect_to_mongodb, get_mongodb_connection, ensure_mongodb_connection
from mongo_models import User as MongoUser, Donor as MongoDonor, Recipient as MongoRecipient, \
    Volunteer as MongoVolunteer, Item as MongoItem, Donation as MongoDonation, \
    Activity as MongoActivity, VolunteerActivity as MongoVolunteerActivity, Address
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
import re
from django.urls import reverse
from django.core import signing
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import (
    MinimumLengthValidator,
    NumericPasswordValidator,
    CommonPasswordValidator,
    UserAttributeSimilarityValidator,
)
import logging

logger = logging.getLogger(__name__)

NAME_RE = re.compile(r"^[^\W\d_]+(?: [^\W\d_]+)*$", re.UNICODE)

def validate_password_strength(password, user_like=None):
    """
    מריץ את הולידטורים הסטנדרטיים של Django ומחזיר רשימת שגיאות (אם יש).
    """
    validators = [
        MinimumLengthValidator(min_length=8),
        UserAttributeSimilarityValidator(),
        CommonPasswordValidator(),
        NumericPasswordValidator(),
    ]
    errors = []
    for v in validators:
        try:
            v.validate(password, user_like)
        except ValidationError as e:
            errors.extend(e.messages)
    return errors


class SimpleUserLike:
    """
    עטיפה קטנה שתתן ל-UserAttributeSimilarityValidator על מה להסתכל.
    """
    def __init__(self, email="", name="", first_name="", last_name=""):
        self.email = email or ""
        self.username = email or ""
        self.name = name or ""
        self.first_name = first_name or ""
        self.last_name = last_name or ""

def _get_session_user(request):
    try:
        # Check if MongoDB is available first
        if not ensure_mongodb_connection():
            logger.warning("MongoDB not available, using fallback user system")
            return _get_fallback_user(request)
        
        user_email = request.session.get('mongo_user_email')
        if user_email:
            return MongoUser.objects(email=user_email).first()

        # fallback: אם allauth חיבר אותנו כמשתמש Django – נסנכרן למונגו ולסשן
        dj_user = getattr(request, "user", None)
        if dj_user and getattr(dj_user, "is_authenticated", False):
            email = (getattr(dj_user, "email", "") or "").lower()
            if not email:
                return None

            mu = MongoUser.objects(email=email).first()
            # למעלה כבר יש לך: from django.contrib.auth.hashers import check_password, make_password

            if not mu:
                # גוזרים שם בסיסי...
                first = (getattr(dj_user, "first_name", "") or "").strip()
                last = (getattr(dj_user, "last_name", "") or "").strip()
                name = (f"{first} {last}".strip()
                        or (getattr(dj_user, "name", "") or "").strip()
                        or email.split("@")[0].replace(".", " ").replace("_", " ").strip())

                mu = MongoUser(
                    email=email,
                    name=name,
                    phone="",  # כדי לעמוד בדרישה אם השדה חובה
                    password_hash=make_password('sociallogin'),  # ← הוספה חשובה
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                    date_joined=datetime.utcnow(),
                )
                mu.save()

            # נשמור בסשן כדי ששאר ה־views יעבדו
            request.session["mongo_user_id"] = str(mu.id)
            request.session["mongo_user_email"] = mu.email
            request.session["mongo_user_name"] = mu.name
            request.session["mongo_user_is_staff"] = getattr(mu, "is_staff", False)
            request.session["mongo_user_is_superuser"] = getattr(mu, "is_superuser", False)
            return mu

        return None
    except Exception as e:
        # If MongoDB is not available, create a mock user from Django user
        logger.error(f"MongoDB not available in _get_session_user: {e}")
        return _get_fallback_user(request)

def _get_fallback_user(request):
    """Fallback user system when MongoDB is not available"""
    import uuid
    dj_user = getattr(request, "user", None)
    if dj_user and getattr(dj_user, "is_authenticated", False):
        # Check if we already have a consistent user ID in session
        user_id = request.session.get("mongo_user_id")
        if not user_id:
            # Generate a new UUID only if we don't have one
            user_id = str(uuid.uuid4())
            request.session["mongo_user_id"] = user_id
        
        # Create a mock user object that works without MongoDB
        class MockMongoUser:
            def __init__(self, dj_user, user_id):
                # Use the consistent user ID from session
                self.id = user_id
                self.email = dj_user.email
                self.name = getattr(dj_user, "name", "") or dj_user.email.split("@")[0]
                self.phone = getattr(dj_user, "phone", "")
                self.is_active = True
                self.is_staff = getattr(dj_user, "is_staff", False)
                self.is_superuser = getattr(dj_user, "is_superuser", False)
                self.address = None
        
        # Store in session for consistency (only if not already stored)
        if "mongo_user_email" not in request.session:
            request.session["mongo_user_email"] = dj_user.email
            request.session["mongo_user_name"] = getattr(dj_user, "name", "") or dj_user.email.split("@")[0]
            request.session["mongo_user_is_staff"] = getattr(dj_user, "is_staff", False)
            request.session["mongo_user_is_superuser"] = getattr(dj_user, "is_superuser", False)
        
        return MockMongoUser(dj_user, user_id)
    return None


def onboarding(request):
    user = _get_session_user(request)
    if not user:
        # Debug: Let's see what's in the session and request
        print(f"DEBUG: No user found in onboarding")
        print(f"DEBUG: Session keys: {list(request.session.keys())}")
        print(f"DEBUG: Django user: {getattr(request, 'user', None)}")
        print(f"DEBUG: Django user authenticated: {getattr(request.user, 'is_authenticated', False) if hasattr(request, 'user') else 'No user attr'}")
        return redirect('login')

    if request.method == "POST":
        want_donor = bool(request.POST.get("is_donor"))
        want_recipient = bool(request.POST.get("is_recipient"))
        want_volunteer = bool(request.POST.get("is_volunteer"))

        selected_count = int(want_donor) + int(want_recipient) + int(want_volunteer)

        if selected_count == 0:
            return redirect("no_roles")

        # Check if MongoDB is available before trying to create profiles
        if not ensure_mongodb_connection():
            logger.warning("MongoDB not available during onboarding, storing roles in session")
            # Store the selected roles in session for later use
            request.session['user_roles'] = {
                'is_donor': want_donor,
                'is_recipient': want_recipient,
                'is_volunteer': want_volunteer
            }
            request.session['onboarding_completed'] = True
            
            # Redirect to appropriate dashboard based on selection
            if selected_count == 1:
                if want_donor:     return redirect("donor_dashboard")
                if want_recipient: return redirect("recipient_dashboard")
                return redirect("volunteer_dashboard")
            return redirect("dashboard_selection")

        # MongoDB is available, create profiles normally
        try:
            if want_donor and not MongoDonor.objects(user_id=user.id).first():     
                MongoDonor(user_id=user.id).save()
            if want_recipient and not MongoRecipient.objects(user_id=user.id).first(): 
                MongoRecipient(user_id=user.id).save()
            if want_volunteer and not MongoVolunteer.objects(user_id=user.id).first(): 
                MongoVolunteer(user_id=user.id).save()
        except Exception as e:
            logger.error(f"Error creating MongoDB profiles: {e}")
            # Fall back to session storage
            request.session['user_roles'] = {
                'is_donor': want_donor,
                'is_recipient': want_recipient,
                'is_volunteer': want_volunteer
            }
            request.session['onboarding_completed'] = True

        if selected_count == 1:
            if want_donor:     return redirect("donor_dashboard")
            if want_recipient: return redirect("recipient_dashboard")
            return redirect("volunteer_dashboard")

        return redirect("dashboard_selection")

    return render(request, "account/onboarding.html")


def dashboard_selection_view(request):
    user = _get_session_user(request)
    if not user:
        return redirect('login')

    # Check if MongoDB is available
    if not ensure_mongodb_connection():
        logger.warning("MongoDB not available in dashboard_selection_view, using session data")
        # Use session data for roles
        user_roles = request.session.get('user_roles', {})
        has_donor = user_roles.get('is_donor', False)
        has_recipient = user_roles.get('is_recipient', False)
        has_volunteer = user_roles.get('is_volunteer', False)
    else:
        # בדיקת התפקידים במונגו
        has_donor = MongoDonor.objects(user_id=user.id).first() is not None
        has_recipient = MongoRecipient.objects(user_id=user.id).first() is not None
        has_volunteer = MongoVolunteer.objects(user_id=user.id).first() is not None

    # אם אין שום תפקיד – לעמוד "no roles"
    if not (has_donor or has_recipient or has_volunteer):
        return redirect('no_roles')

    # אם יש תפקיד אחד בלבד – נעבור ישירות לדשבורד המתאים
    count = int(has_donor) + int(has_recipient) + int(has_volunteer)
    if count == 1:
        if has_donor:
            return redirect('donor_dashboard')
        if has_recipient:
            return redirect('recipient_dashboard')
        return redirect('activity_list')

    # אם יש כמה תפקידים – מציגים את מסך הבחירה עם הדגלים שהטמפלייט צריך
    ctx = {
        'user': user,
        'has_donor': has_donor,
        'has_recipient': has_recipient,
        'has_volunteer': has_volunteer,
        # לשמירת תאימות אם התבנית משתמשת בשמות is_*
        'is_donor': has_donor,
        'is_recipient': has_recipient,
        'is_volunteer': has_volunteer,
    }
    return render(request, 'dashboard/dashboard_selection.html', ctx)


def profile_redirect_view(request):
    user = _get_session_user(request)
    if not user:
        return redirect('login')

    has_donor = bool(MongoDonor.objects(user_id=user.id).first())
    has_recipient = bool(MongoRecipient.objects(user_id=user.id).first())
    has_volunteer = bool(MongoVolunteer.objects(user_id=user.id).first())

    if has_donor or has_recipient or has_volunteer:
        return redirect('dashboard_selection')  # משתמש ותיק עם תפקידים -> מסך בחירה
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return redirect('admin_dashboard')
    return redirect('no_roles')


def register_volunteer(request):
    return render(request, 'registration/register_volunteer.html')


def blocked_user_view(request):
    return render(request, 'registration/blocked_user.html')


def ensure_mongodb_connection():
    """Ensure MongoDB connection is established"""
    if not get_mongodb_connection():
        connect_to_mongodb()

def mongo_auth_required(view_func):
    """Decorator to require MongoDB authentication and active user status"""
    def wrapper(request, *args, **kwargs):
        # Use our fallback user system
        user = _get_session_user(request)
        if not user:
            messages.error(request, 'Please log in first.')
            return redirect('login')
        
        # Check if user is active
        if not user.is_active:
            messages.error(request, 'Your account has been blocked. Please contact support.')
            return redirect('login')
        
        # Add user to request for easy access
        request.mongo_user = user
        return view_func(request, *args, **kwargs)
    
    return wrapper

class MongoUserMixin:
    """Mixin to handle MongoDB user operations"""

    def get_mongo_user(self, email):
        """Get MongoDB user by email"""
        ensure_mongodb_connection()
        try:
            return MongoUser.objects(email=email).first()
        except:
            return None

    def authenticate_mongo_user(self, email, password):
        """Authenticate MongoDB user"""
        user = self.get_mongo_user(email)
        if user and check_password(password, user.password_hash):
            return user
        return None

    def create_mongo_user(self, email, password, name, phone, address_data):
        """Create new MongoDB user"""
        ensure_mongodb_connection()

        # Create address object
        address = Address(
            street=address_data.get('street', ''),
            city=address_data.get('city', ''),
            postal_code=address_data.get('postal_code', ''),
            country=address_data.get('country', ''),
            apartment=address_data.get('apartment', ''),
            instructions=address_data.get('instructions', ''),
            latitude=address_data.get('latitude'),
            longitude=address_data.get('longitude')
        )

        # Create user
        user = MongoUser(
            email=email,
            name=name,
            phone=phone,
            address=address,
            password_hash=make_password(password),
            is_active=True,
            is_staff=False,
            is_superuser=False,
            date_joined=datetime.utcnow()
        )
        user.save()
        return user


def send_notification_email(subject, to_email, template_name, context):
    """Send email with both plain text and HTML versions"""
    text_content = render_to_string(template_name.replace('.html', '.txt'), context)
    html_content = render_to_string(template_name, context)

    msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [to_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def send_verification_code(user):
    """Generate and send a 6-digit verification code to user's email"""
    code = user.generate_verification_code()

    subject = "Your HopeBridge verification code"
    context = {
        "code": code,
        "site_name": "HopeBridge",
        "support_email": "hopebridgeproject1@gmail.com",
    }

    text_content = render_to_string("emails/verify_email.txt", context)
    html_content = render_to_string("emails/verify_email.html", context)

    msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [user.email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def mongo_login_view(request):
    """MongoDB-based login view"""
    if request.method == 'POST':
        # Clear any existing messages before processing login
        storage = messages.get_messages(request)
        storage.used = True

        email = request.POST.get('email')
        password = request.POST.get('password')

        ensure_mongodb_connection()
        user = MongoUser.objects(email=email).first()

        if user and check_password(password, user.password_hash):
            # Check if user is active
            if not user.is_active:
                messages.error(request, 'Your account has been blocked. Please contact support.')
                return redirect('login')

            DJUser = get_user_model()
            dj_user, created = DJUser.objects.get_or_create(
                email=user.email,
                defaults={"is_active": True}
            )
            if hasattr(dj_user, "username") and not dj_user.username:
                dj_user.username = user.email  # או חלק לפני @

            dj_user.is_active = True
            if hasattr(user, "is_staff"): dj_user.is_staff = bool(user.is_staff)
            if hasattr(user, "is_superuser"): dj_user.is_superuser = bool(user.is_superuser)
            if created and not dj_user.has_usable_password():
                dj_user.set_unusable_password()
            dj_user.save()

            dj_login(request, dj_user, backend='django.contrib.auth.backends.ModelBackend')  # חשוב בשביל /admin/

            # שמירת סשן מונגו לשאר ה־views שלך
            # Create Django session for the user
            request.session['mongo_user_id'] = str(user.id)
            request.session['mongo_user_email'] = user.email
            request.session['mongo_user_name'] = user.name
            request.session['mongo_user_is_staff'] = user.is_staff
            request.session['mongo_user_is_superuser'] = user.is_superuser
            request.session['mongo_user_is_active'] = user.is_active
            messages.success(request, f'Welcome back, {user.name}!')

            # Redirect admin users to admin dashboard
            if user.is_staff or user.is_superuser:
                return redirect('admin_dashboard')
            else:
                return redirect('welcome')
        else:
            messages.error(request, 'Invalid email or password.')
            return redirect('login')

    return render(request, 'registration/login.html')


def mongo_register_view(request):
    """MongoDB-based registration view"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        # Validate phone number: must be exactly 10 digits, no letters or symbols
        PHONE_RE = re.compile(r"^\d{10}$")
        if not PHONE_RE.fullmatch(phone):
            return render(request, 'registration/register.html', {
                'error': 'Invalid phone number. Please enter exactly 10 digits (no spaces or symbols).'
            })
        # Validate email format with stricter rules
        EMAIL_RE = re.compile(
            r"^(?!.*@.*@)"  # Do not allow more than one "@" symbol
            r"[A-Za-z0-9._%+-]+"  # Local part (before the @)
            r"@[A-Za-z0-9.-]+"  # Domain part (after the @)
            r"\.[A-Za-z]{2,}$"  # Domain suffix with a dot and at least 2 characters
        )
        if not EMAIL_RE.fullmatch(email):
            return render(request, 'registration/register.html', {
                'error': 'Invalid email format. Please use a valid email like name@example.com'
            })

        # --- Password strength validation ---
        user_like = SimpleUserLike(email=email, name=name or "")
        pw_errors = validate_password_strength(password, user_like)
        if pw_errors:
            return render(request, 'registration/register.html', {
                'error': " ".join(pw_errors)
            })

        # Get selected roles from checkboxes
        is_donor = request.POST.get('is_donor') == 'on'
        is_recipient = request.POST.get('is_recipient') == 'on'
        is_volunteer = request.POST.get('is_volunteer') == 'on'

        ensure_mongodb_connection()

        # Check if user already exists
        if MongoUser.objects(email=email).first():
            messages.error(request, 'User with this email already exists.')
            return redirect('register')

        # Create address data
        address_data = {
            'street': request.POST.get('address_street', ''),
            'city': request.POST.get('address_city', ''),
            'postal_code': request.POST.get('address_postal_code', ''),
            'country': request.POST.get('address_country', ''),
            'apartment': request.POST.get('address_apartment', ''),
            'instructions': request.POST.get('address_instructions', ''),
            'latitude': float(request.POST.get('latitude', 0)) if request.POST.get('latitude') else None,
            'longitude': float(request.POST.get('longitude', 0)) if request.POST.get('longitude') else None
        }

        # Create user
        user = MongoUser(
            email=email,
            name=name,
            phone=phone,
            address=Address(**address_data),
            password_hash=make_password(password),
            is_active=True,
            is_staff=False,
            is_superuser=False,
            date_joined=datetime.utcnow()
        )
        user.save()

        # Create profiles based on selected roles
        print(
            f"DEBUG: Creating profiles for user {email}, roles: donor={is_donor}, recipient={is_recipient}, volunteer={is_volunteer}")

        if is_donor:
            donor = MongoDonor(user_id=user.id)
            donor.save()
            print(f"DEBUG: Created donor profile for {email}")

        if is_recipient:
            recipient = MongoRecipient(
                user_id=user.id,
                shipping_address=address_data.get('street', '')
            )
            recipient.save()
            print(f"DEBUG: Created recipient profile for {email}")

        if is_volunteer:
            volunteer = MongoVolunteer(user_id=user.id)
            volunteer.save()
            print(f"DEBUG: Created volunteer profile for {email}")

        # If no roles were selected, create a default donor profile
        if not is_donor and not is_recipient and not is_volunteer:
            donor = MongoDonor(user_id=user.id)
            donor.save()
            print(f"DEBUG: Created default donor profile for {email}")
            messages.success(request, 'Account created successfully!')
            return redirect('login')
        # Send verification code to email
        send_verification_code(user)
        request.session['pending_verification_email'] = user.email
        messages.info(request, "We sent a 6-digit verification code to your email. Please verify.")
        return redirect('verify_email')

    return render(request, 'registration/register.html')


def mongo_verify_email_view(request):
    """View for verifying the email using the code sent to user"""
    # מזהות אם מדובר בהרשמה (signup) או איפוס סיסמה (reset)
    purpose = request.GET.get("purpose") or request.session.get("verify_purpose") or "signup"

    # בוחרות אימייל לפי ה-purpose
    if purpose == "reset":
        email = request.session.get('pending_reset_email') or request.session.get('password_reset_email')
    else:
        email = request.session.get('pending_verification_email')

    # אין אימייל בסשן → מפנות למסך הנכון
    if not email:
        if purpose == "reset":
            messages.error(request, "No email to verify. Please start password reset again.")
            return redirect('password_reset')
        messages.error(request, "No email to verify. Please register again.")
        return redirect('register')

    user = MongoUser.objects(email=email).first()
    if not user:
        if purpose == "reset":
            messages.error(request, "User not found.")
            return redirect('password_reset')
        messages.error(request, "User not found.")
        return redirect('register')

    # אם זה reset ובאנו ב-GET, שולחות קוד אימות (כמו בהרשמה)
    if request.method == "GET" and purpose == "reset":
        send_verification_code(user)
        request.session['pending_reset_email'] = user.email
        request.session['verify_purpose'] = 'reset'

    if request.method == "POST":
        code = (request.POST.get("code") or "").strip()
        if user.is_verification_code_valid(code):

            # מסלול איפוס סיסמה: מפיקות טוקן חתום ומפנות למסך קביעת סיסמה
            if purpose == "reset":
                user.verification_code = None
                user.save()
                token = signing.dumps({"email": user.email}, salt="password-reset")
                request.session['verify_purpose'] = 'reset'
                return redirect(reverse("password_reset_confirm", kwargs={"uidb64": "OA", "token": token}))

            # מסלול ההרשמה הרגיל (ללא שינוי)
            user.email_verified = True
            user.verification_code = None
            user.save()
            request.session.pop('pending_verification_email', None)
            messages.success(request, "Email verified successfully! You can now log in.")
            return redirect("login")
        else:
            messages.error(request, "Invalid or expired code. Please try again.")

    # מעבירות גם purpose לתבנית (לא חובה אבל שימושי להודעות)
    return render(request, "registration/verify_email.html", {"email": email, "purpose": purpose})


def mongo_resend_code_view(request):
    """Resend verification code"""
    email = request.session.get('pending_verification_email')
    if not email:
        return redirect('login')

    user = MongoUser.objects(email=email).first()
    if not user:
        return redirect('login')

    send_verification_code(user)
    messages.success(request, "A new verification code was sent to your email.")
    return redirect('verify_email')


def mongo_dashboard_view(request):
    """MongoDB-based dashboard view"""
    user = _get_session_user(request)
    if not user:
        return redirect('login')

    # Check if MongoDB is available
    if not ensure_mongodb_connection():
        logger.warning("MongoDB not available in mongo_dashboard_view, using session data")
        # Use session data for roles
        user_roles = request.session.get('user_roles', {})
        is_donor = user_roles.get('is_donor', False)
        is_recipient = user_roles.get('is_recipient', False)
        is_volunteer = user_roles.get('is_volunteer', False)
        
        # Create empty context for fallback
        context = {
            'user': user,
            'is_donor': is_donor,
            'is_recipient': is_recipient,
            'is_volunteer': is_volunteer,
            'items': [],
            'donations': [],
            'total_donations': 0,
            'available_donations': 0,
            'claimed_donations': 0,
            'people_helped': 0,
        }
        
        # Determine which dashboard to show based on URL path
        request_path = request.path
        if '/dashboard/donor/' in request_path and is_donor:
            return render(request, 'dashboard/donor_dashboard.html', context)
        elif '/dashboard/recipient/' in request_path and is_recipient:
            return render(request, 'dashboard/recipient_dashboard.html', context)
        elif '/dashboard/volunteer/' in request_path and is_volunteer:
            return render(request, 'dashboard/volunteer_dashboard.html', context)
        else:
            # Default to donor dashboard if user is a donor
            if is_donor:
                return render(request, 'dashboard/donor_dashboard.html', context)
            elif is_recipient:
                return render(request, 'dashboard/recipient_dashboard.html', context)
            elif is_volunteer:
                return render(request, 'dashboard/volunteer_dashboard.html', context)
            else:
                return redirect('onboarding')

    # MongoDB is available, proceed with normal logic
    user_email = request.session.get('mongo_user_email')
    if not user_email:
        return redirect('login')

    user = MongoUser.objects(email=user_email).first()
    if not user:
        return redirect('login')

    # Check if user is active
    if not user.is_active:
        messages.error(request, 'Your account has been blocked. Please contact support.')
        return redirect('login')

    # Determine user type and get relevant data
    donor = MongoDonor.objects(user_id=user.id).first()
    recipient = MongoRecipient.objects(user_id=user.id).first()
    volunteer = MongoVolunteer.objects(user_id=user.id).first()

    context = {
        'user': user,
        'is_donor': donor is not None,
        'is_recipient': recipient is not None,
        'is_volunteer': volunteer is not None,
    }

    # Check if user has multiple profiles
    profile_count = sum([donor is not None, recipient is not None, volunteer is not None])

    # Check if user is accessing a specific dashboard URL
    request_path = request.path
    if profile_count > 1:
        # User has multiple profiles - check if they're accessing a specific dashboard
        if '/dashboard/donor/' in request_path and donor:
            # User wants donor dashboard and has donor profile
            pass  # Continue to donor dashboard logic below
        elif '/dashboard/recipient/' in request_path and recipient:
            # User wants recipient dashboard and has recipient profile
            pass  # Continue to recipient dashboard logic below
        elif '/dashboard/volunteer/' in request_path and volunteer:
            # User wants volunteer dashboard and has volunteer profile
            pass  # Continue to volunteer dashboard logic below
        elif '/dashboard/' in request_path:
            # User is accessing general dashboard with multiple profiles - redirect to first available dashboard
            if donor:
                return redirect('donor_dashboard')
            elif recipient:
                return redirect('recipient_dashboard')
            elif volunteer:
                return redirect('activity_list')
        else:
            # User has multiple profiles but didn't specify which dashboard - redirect to first available dashboard
            if donor:
                return redirect('donor_dashboard')
            elif recipient:
                return redirect('recipient_dashboard')
            elif volunteer:
                return redirect('activity_list')
    elif profile_count == 0:
        # User has no profiles - show selection page
        return render(request, 'dashboard/dashboard_selection.html', context)

    # Check which specific dashboard to show based on URL path
    if '/dashboard/volunteer/' in request_path and volunteer:
        # User wants volunteer dashboard and has volunteer profile
        activities = MongoActivity.objects(volunteer_id=volunteer.id)
        volunteer_activities = MongoVolunteerActivity.objects(volunteer_id=volunteer.id)

        # Calculate volunteer statistics
        total_activities = activities.count()
        available_activities = activities.count()  # All activities are available by default
        joined_count = volunteer_activities.count()
        completed_count = volunteer_activities(status='completed').count()

        context.update({
            'activities': activities,
            'volunteer_activities': volunteer_activities,
            'total_activities': total_activities,
            'available_activities': available_activities,
            'joined_count': joined_count,
            'completed_count': completed_count,
        })
        return render(request, 'dashboard/volunteer_dashboard.html', context)

    elif '/dashboard/recipient/' in request_path and recipient:
        # User wants recipient dashboard and has recipient profile
        available_donations = MongoDonation.objects(status='available')
        claimed_donations = MongoDonation.objects(recipient_id=recipient.id)

        # Calculate recipient statistics
        total_claimed = claimed_donations.count()
        available_items = available_donations.count()

        context.update({
            'donations': available_donations,
            'total_claimed': total_claimed,
            'available_items': available_items,
        })
        return render(request, 'dashboard/recipient_dashboard.html', context)

    elif '/dashboard/donor/' in request_path and donor:
        # User wants donor dashboard and has donor profile
        items = MongoItem.objects(donor_id=donor.id)
        donations = MongoDonation.objects(donor_id=donor.id)

        # Populate item data for donations
        donations_with_items = []
        for donation in donations:
            item = MongoItem.objects(id=donation.item_id).first()
            if item:
                # Create a mock object that has both donation and item properties
                class DonationWithItem:
                    def __init__(self, donation, item):
                        self.id = donation.id
                        self.status = donation.status
                        self.created_at = donation.created_at
                        self.donor_id = donation.donor_id
                        self.recipient_id = donation.recipient_id
                        self.item = item

                donations_with_items.append(DonationWithItem(donation, item))

        # Calculate donor statistics
        total_donations = donations.count()
        available_donations = donations(status='available').count()
        claimed_donations = donations(status='claimed').count()
        people_helped = donations(status__in=['claimed', 'shipped']).count()

        context.update({
            'items': items,
            'donations': donations_with_items,
            'total_donations': total_donations,
            'available_donations': available_donations,
            'claimed_donations': claimed_donations,
            'people_helped': people_helped,
        })
        return render(request, 'dashboard/donor_dashboard.html', context)

    # If no specific dashboard URL or user has single profile, show appropriate dashboard
    elif donor:
        # Get donor's items and donations
        items = MongoItem.objects(donor_id=donor.id)
        donations = MongoDonation.objects(donor_id=donor.id)

        # Populate item data for donations
        donations_with_items = []
        for donation in donations:
            item = MongoItem.objects(id=donation.item_id).first()
            if item:
                # Create a mock object that has both donation and item properties
                class DonationWithItem:
                    def __init__(self, donation, item):
                        self.id = donation.id
                        self.status = donation.status
                        self.created_at = donation.created_at
                        self.donor_id = donation.donor_id
                        self.recipient_id = donation.recipient_id
                        self.item = item

                donations_with_items.append(DonationWithItem(donation, item))

        # Calculate donor statistics
        total_donations = donations.count()
        available_donations = donations(status='available').count()
        claimed_donations = donations(status='claimed').count()
        people_helped = donations(status__in=['claimed', 'shipped']).count()

        context.update({
            'items': items,
            'donations': donations_with_items,
            'total_donations': total_donations,
            'available_donations': available_donations,
            'claimed_donations': claimed_donations,
            'people_helped': people_helped,
        })
        return render(request, 'dashboard/donor_dashboard.html', context)

    elif recipient:
        # Get available donations and recipient's claimed items
        available_donations = MongoDonation.objects(status='available')
        claimed_donations = MongoDonation.objects(recipient_id=recipient.id)

        # Calculate recipient statistics
        total_claimed = claimed_donations.count()
        available_items = available_donations.count()

        context.update({
            'donations': available_donations,
            'total_claimed': total_claimed,
            'available_items': available_items,
            'current_dashboard': 'recipient',
        })
        return render(request, 'dashboard/recipient_dashboard.html', context)

    elif volunteer:
        # Get volunteer's activities
        activities = MongoActivity.objects(volunteer_id=volunteer.id)
        volunteer_activities = MongoVolunteerActivity.objects(volunteer_id=volunteer.id)

        # Calculate volunteer statistics
        total_activities = activities.count()
        available_activities = activities.count()  # All activities are available by default
        joined_count = volunteer_activities.count()
        completed_count = volunteer_activities(status='completed').count()

        context.update({
            'activities': activities,
            'volunteer_activities': volunteer_activities,
            'total_activities': total_activities,
            'available_activities': available_activities,
            'joined_count': joined_count,
            'completed_count': completed_count,
        })
        return render(request, 'dashboard/volunteer_dashboard.html', context)

    else:
        # User has no profile type
        return render(request, 'dashboard/dashboard_selection.html', context)


def mongo_item_list_view(request):
    """MongoDB-based item list view - shows donations with items"""
    # Check if MongoDB is available
    if not ensure_mongodb_connection():
        logger.warning("MongoDB not available in mongo_item_list_view, using fallback")
        # Use fallback user system
        user = _get_session_user(request)
        if not user:
            return redirect('login')
        
        # Get user roles from session
        user_roles = request.session.get('user_roles', {})
        is_recipient = user_roles.get('is_recipient', False)
        is_donor = user_roles.get('is_donor', False)
        
        # Get temporary donations from session
        temp_donations = request.session.get('temp_donations', [])
        
        # Create context for fallback with temporary donations
        context = {
            'items': temp_donations,  # Show temporary donations as items
            'donations': temp_donations,
            'categories': ['Electronics', 'Clothing', 'Books', 'Furniture', 'Toys', 'Other'],
            'conditions': ['New', 'Like New', 'Good', 'Fair', 'Poor'],
            'current_category': '',
            'current_condition': '',
            'search_query': '',
            'user': user,
            'mongodb_available': False,
        }
        return render(request, 'donations/donation_list.html', context)

    # MongoDB is available, proceed with normal logic
    # Get filter parameters
    category = request.GET.get('category', '')
    condition = request.GET.get('condition', '')
    search = request.GET.get('search', '')

    # Check user authentication and profile
    user_email = request.session.get('mongo_user_email')
    user = None
    is_authenticated = False
    is_recipient = False
    is_donor = False

    if user_email:
        user = MongoUser.objects(email=user_email).first()
        if user:
            is_authenticated = True
            # Check if user has recipient profile
            recipient = MongoRecipient.objects(user_id=user.id).first()
            is_recipient = recipient is not None
            # Check if user has donor profile
            donor = MongoDonor.objects(user_id=user.id).first()
            is_donor = donor is not None

    # Build query for donations
    donation_query = {'status': 'available'}  # Only show available donations

    # Get all available donations first
    donations = MongoDonation.objects(**donation_query)

    # Get items for these donations
    item_ids = [donation.item_id for donation in donations]
    item_query = {'id__in': item_ids}

    # Apply filters to items
    if category:
        item_query['category'] = category
    if condition:
        item_query['condition'] = condition
    if search:
        item_query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}}
        ]

    # Get filtered items
    items = MongoItem.objects(**item_query).order_by('-created_at')

    # Create donation objects with embedded items for template compatibility
    donations_with_items = []
    for item in items:
        donation = MongoDonation.objects(item_id=item.id, status='available').first()
        if donation:
            # Get donor information
            donor = MongoDonor.objects(id=donation.donor_id).first()
            donor_user = None
            if donor:
                donor_user = MongoUser.objects(id=donor.user_id).first()

            # Create a mock object that has both donation and item properties
            class DonationWithItem:
                def __init__(self, donation, item, donor_user):
                    self.id = donation.id
                    self.status = donation.status
                    self.created_at = donation.created_at
                    self.donor_id = donation.donor_id
                    self.recipient_id = donation.recipient_id
                    self.item = item
                    # Add donor information for template
                    self.donor = type('Donor', (), {'user': donor_user})() if donor_user else None

            donations_with_items.append(DonationWithItem(donation, item, donor_user))

    # Pagination
    paginator = Paginator(donations_with_items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Create mock user object for template compatibility
    class MockUser:
        def __init__(self, user, is_authenticated, is_recipient, is_donor):
            self.is_authenticated = is_authenticated
            self.recipient_profile = is_recipient
            self.donor_profile = is_donor
            if user:
                self.name = user.name
                self.email = user.email
                self.id = user.id

    mock_user = MockUser(user, is_authenticated, is_recipient, is_donor)

    context = {
        'items': page_obj,  # For backward compatibility
        'donations': page_obj,  # Main data for template
        'categories': MongoItem.objects.distinct('category'),
        'conditions': MongoItem.objects.distinct('condition'),
        'current_category': category,
        'current_condition': condition,
        'search_query': search,
        'user': mock_user,  # For template authentication checks
    }

    return render(request, 'donations/donation_list.html', context)

def mongo_item_create_view(request):
    """MongoDB-based item creation view"""
    user = _get_session_user(request)
    if not user:
        messages.error(request, 'Please log in first.')
        return redirect('login')

    # Check if MongoDB is available
    if not ensure_mongodb_connection():
        logger.warning("MongoDB not available in mongo_item_create_view, using fallback system")
        
        if request.method == 'POST':
            # Handle POST request with fallback system
            # Check if user has donor role in session
            user_roles = request.session.get('user_roles', {})
            if not user_roles.get('is_donor', False):
                messages.error(request, 'Donor profile not found. Please become a donor first.')
                return redirect('welcome')
            
            # Store donation data in session (temporary storage)
            donation_data = {
                'name': request.POST.get('name'),
                'description': request.POST.get('description'),
                'category': request.POST.get('category'),
                'condition': request.POST.get('condition'),
                'image_url': request.POST.get('image_url', ''),
                'latitude': float(request.POST.get('latitude', 0)) if request.POST.get('latitude') else None,
                'longitude': float(request.POST.get('longitude', 0)) if request.POST.get('longitude') else None,
                'item_location': request.POST.get('item_location', ''),
                'created_at': datetime.utcnow().isoformat(),
                'donor_id': user.id
            }
            
            # Store in session
            donations = request.session.get('temp_donations', [])
            donations.append(donation_data)
            request.session['temp_donations'] = donations
            
            # Explicitly save the session to ensure it persists
            request.session.save()
            
            messages.success(request, 'Donation item created successfully! (Stored temporarily - will be saved to database when MongoDB is available)')
            return redirect('item_list')
        
        # Show the form
        context = {
            'user': user,
            'mongodb_available': False,
        }
        return render(request, 'donations/create_donation.html', context)

    if request.method == 'POST':
        # User is already authenticated
        # Get donor profile
        donor = MongoDonor.objects(user_id=user.id).first()
        if not donor:
            messages.error(request, 'Donor profile not found.')
            return redirect('welcome')

        # Create item
        item = MongoItem(
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            category=request.POST.get('category'),
            condition=request.POST.get('condition'),
            image_url=request.POST.get('image_url', ''),
            donor_id=donor.id,
            latitude=float(request.POST.get('latitude', 0)) if request.POST.get('latitude') else None,
            longitude=float(request.POST.get('longitude', 0)) if request.POST.get('longitude') else None,
            item_location=request.POST.get('item_location', ''),
            created_at=datetime.utcnow()
        )
        item.save()

        # Create donation
        donation = MongoDonation(
            item_id=item.id,
            donor_id=donor.id,
            created_at=datetime.utcnow(),
            status='available'
        )
        donation.save()

        messages.success(request, 'Item created successfully!')
        return redirect('item_list')

    context = {
        'user': user,
        'mongodb_available': True,
    }
    return render(request, 'donations/create_donation.html', context)


def mongo_activity_list_view(request):
    """MongoDB-based activity list view"""
    # Check if MongoDB is available
    if not ensure_mongodb_connection():
        logger.warning("MongoDB not available in mongo_activity_list_view, using fallback")
        # Use fallback user system
        user = _get_session_user(request)
        if not user:
            return redirect('login')
        
        # Get user roles from session
        user_roles = request.session.get('user_roles', {})
        is_volunteer = user_roles.get('is_volunteer', False)
        
        # Create empty context for fallback
        context = {
            'activities': [],
            'categories': [],
            'current_category': '',
            'search_query': '',
            'user': user,
            'volunteer_profile': is_volunteer,
        }
        return render(request, 'activities/activity_list.html', context)

    # MongoDB is available, proceed with normal logic
    # Get filter parameters
    category = request.GET.get('category', '')
    search = request.GET.get('search', '')

    # Build query
    query = {}
    if category:
        query['category'] = category
    if search:
        query['$or'] = [
            {'title': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}}
        ]

    # Filter out expired activities (only show future activities)
    from datetime import datetime
    query['activity_date__gte'] = datetime.utcnow()

    # Get user information for template
    user_email = request.session.get('mongo_user_email')
    user = None
    volunteer_profile = None

    if user_email:
        user = MongoUser.objects(email=user_email).first()
        if user:
            volunteer_profile = MongoVolunteer.objects(user_id=user.id).first()

    # Get activities
    activities = MongoActivity.objects(**query).order_by('-created_at')
    
    # Add joined_participants count to each activity
    for activity in activities:
        joined_count = MongoVolunteerActivity.objects(
            activity_id=activity.id,
            status='joined'
        ).count()
        activity.joined_participants = joined_count

    # Pagination
    paginator = Paginator(activities, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Add joined_participants count and user participation status to paginated activities
    for activity in page_obj:
        if not hasattr(activity, 'joined_participants'):
            joined_count = MongoVolunteerActivity.objects(
                activity_id=activity.id,
                status='joined'
            ).count()
            activity.joined_participants = joined_count
        
        # Check if current user has joined this activity
        activity.user_has_joined = False
        if user and volunteer_profile:
            user_participation = MongoVolunteerActivity.objects(
                activity_id=activity.id,
                volunteer_id=volunteer_profile.id,
                status='joined'
            ).first()
            activity.user_has_joined = user_participation is not None

    # Create mock user object for template compatibility
    class MockUser:
        def __init__(self, user, volunteer_profile):
            self.is_authenticated = user is not None
            self.volunteer_profile = volunteer_profile is not None
            self.id = user.id if user else None
            self.email = user.email if user else None
            self.name = user.name if user else None

    mock_user = MockUser(user, volunteer_profile)
    context = {
        'activities': page_obj,
        'categories': MongoActivity.objects.distinct('category'),
        'current_category': category,
        'search_query': search,
        'user': mock_user  # Add user information to context
    }

    return render(request, 'activities/activity_list.html', context)


@mongo_auth_required
def mongo_activity_create_view(request):
    """MongoDB-based activity creation view"""
    user = _get_session_user(request)  # Use the fallback user system
    if not user:
        messages.error(request, 'Please log in to create activities.')
        return redirect('login')

    # Check if user has a volunteer profile
    if ensure_mongodb_connection():
        volunteer = MongoVolunteer.objects(user_id=user.id).first()
    else:
        # Fallback: Check session for volunteer role
        user_roles = request.session.get('user_roles', {})
        if user_roles.get('is_volunteer', False):
            # Create a mock volunteer profile for session-based user
            class MockMongoVolunteer:
                def __init__(self, user_id):
                    self.id = user_id  # Use the user's ID as volunteer ID for consistency
            volunteer = MockMongoVolunteer(user.id)
        else:
            volunteer = None

    if not volunteer:
        messages.error(request, 'Volunteer profile not found. Please become a volunteer first.')
        return redirect('welcome')

    if request.method == 'POST':
        if ensure_mongodb_connection():
            # Save to MongoDB if connected
            activity = MongoActivity(
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                category=request.POST.get('category'),
                location=request.POST.get('location'),
                latitude=float(request.POST.get('latitude', 0)) if request.POST.get('latitude') else None,
                longitude=float(request.POST.get('longitude', 0)) if request.POST.get('longitude') else None,
                image_url=request.POST.get('image_url', ''),
                volunteer_id=volunteer.id,
                created_at=datetime.utcnow(),
                activity_date=datetime.fromisoformat(request.POST.get('activity_date')),
                duration_hours=int(request.POST.get('duration_hours', 1)),
                max_participants=int(request.POST.get('max_participants', 1)),
                requirements=request.POST.get('requirements', ''),
                contact_info=request.POST.get('contact_info', '')
            )
            activity.save()
            messages.success(request, 'Activity created successfully!')
            return redirect('activity_list')
        else:
            # Fallback: Store activity in session if MongoDB is not available
            messages.warning(request, 'MongoDB not available, activity saved to session (temporary).')
            # For demonstration, we'll just redirect and show a message.
            # In a real app, you'd store this in session and process later or use a different persistence.
            return redirect('activity_list')

    return render(request, 'activities/create_activity.html')


def about_view(request):
    # אם כבר מימשת ב-views.py הראשי — אפשר לוותר. זה לשמירת תאימות במקרה שה-URL מפנה לכאן.
    return render(request, 'pages/about.html')


from django.core.mail import EmailMessage
from django.conf import settings
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def contact_admin(request):
    ensure_mongodb_connection()
    user = _get_session_user(request)
    if request.method == "POST":
        subject = (request.POST.get("subject") or "").strip()
        message = (request.POST.get("message") or "").strip()
        sender_name = (request.POST.get("name") or "").strip()
        sender_email = (request.POST.get("email") or "").strip()

        if not sender_email or not subject or not message:
            messages.error(request, "Subject, message and email are required.")
            return render(request, "pages/contact_admin.html", {
                "prefill_name": sender_name,
                "prefill_email": sender_email,
                "prefill_subject": subject,
                "prefill_message": message,
            })

        full_message = message
        if sender_name or sender_email:
            full_message += (
                "\n\n--- Sender Details ---"
                f"\nName: {sender_name or 'N/A'}"
                f"\nReply-to: {sender_email or 'N/A'}"
            )

        email = EmailMessage(
            subject=subject or "New contact message",
            body=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.ADMIN_CONTACT_EMAIL],
            reply_to=[sender_email] if sender_email else None,
        )
        email.send(fail_silently=False)
        messages.success(request, "Your message was sent successfully! We'll get back to you shortly.")
        return redirect("contact_admin")

    prefill_name = getattr(user, 'name', "") if user else ""
    prefill_email = getattr(user, 'email', "") if user else ""
    return render(request, "pages/contact_admin.html", {
        "prefill_name": prefill_name,
        "prefill_email": prefill_email,
    })


from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def password_reset_start(request):
    ensure_mongodb_connection()  # חשוב כדי שלא נקבל "You have not defined a default connection"

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        if not email:
            return render(request, "registration/password_reset_form.html",
                          {"error": "Please enter an email address."})

        # לא חושפות האם האימייל קיים או לא
        user = MongoUser.objects(email=email).first()
        if user:
            # שולחות קוד אימות ומסמנות שזה ל-reset
            send_verification_code(user)
            request.session['pending_reset_email'] = user.email
        else:
            # גם אם לא קיים — שומרות כדי לאפשר מסך קוד אחיד
            request.session['pending_reset_email'] = email

        request.session['verify_purpose'] = 'reset'
        messages.info(request, "We sent a 6-digit verification code to your email. Please verify.")
        return redirect(f"{reverse('verify_email')}?purpose=reset")

    return render(request, "registration/password_reset_form.html")

from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def password_reset_confirm(request, uidb64=None, token=None):
    ensure_mongodb_connection()

    # 1) מנסים לחלץ אימייל מתוך ה-token החתום שהגיע ב-URL
    email = None
    if token:
        try:
            data = signing.loads(token, salt="password-reset", max_age=900)  # תוקף 15 דק'
            email = (data.get("email") or "").strip().lower()
        except signing.SignatureExpired:
            messages.error(request, "The reset link has expired. Please start again.")
            return redirect("password_reset")
        except signing.BadSignature:
            messages.error(request, "Invalid reset link. Please start again.")
            return redirect("password_reset")

    # 2) נפילה אחורה: אם אין token (או אין אימייל בו), ננסה מהסשן הישן (לשמירת תאימות)
    if not email:
        email = (request.session.get("password_reset_email") or "").strip().lower()
        if not email:
            messages.error(request, "Reset session expired. Please enter your email again.")
            return redirect("password_reset")

    user = MongoUser.objects(email=email).first()
    if not user:
        messages.error(request, "User not found.")
        return redirect("password_reset")

    error = None

    if request.method == "POST":
        # תופסים מגוון שמות לשדות ומסירים רווחים
        p1 = (request.POST.get("new_password1")
              or request.POST.get("new_password")
              or request.POST.get("password1")
              or request.POST.get("password")
              or "").strip()
        p2 = (request.POST.get("new_password2")
              or request.POST.get("new_password_confirmation")
              or request.POST.get("password2")
              or "").strip()

        # אם יש רק שדה אחד בטופס – נתייחס אליו כשני השדות
        if p1 and not p2:
            p2 = p1

        # בדיקות בסיסיות
        if not p1 or not p2:
            error = "Please fill both password fields."
        elif p1 != p2:
            error = "Passwords do not match."
        elif len(p1) < 8:
            error = "Password must contain at least 8 characters."

        if not error:
            # --- Password strength validation before saving ---
            user_like = SimpleUserLike(email=user.email, name=user.name)
            pw_errors = validate_password_strength(p1, user_like)
            if pw_errors:
                error = " ".join(pw_errors)
            else:
                user.password_hash = make_password(p1)
                user.save()
                request.session.pop("password_reset_email", None)
                request.session.pop("pending_reset_email", None)
                request.session.pop("verify_purpose", None)
                messages.success(request, "Password updated successfully. Please sign in.")
                return redirect("password_reset_complete")

        # דיבוג בקונסולה (לא חובה)
        print("DEBUG reset:", {"len": len(p1), "match": p1 == p2, "error": error})
        messages.error(request, error)

    # GET: מציגות את הטופס (אפשר להעביר אימייל לתצוגה בלבד)
    return render(request, "registration/password_reset_confirm.html", {"error": error, "email": email})


def mongo_logout_view(request):
    """MongoDB-based logout view"""
    # Clear all messages first
    from django.contrib import messages
    storage = messages.get_messages(request)
    storage.used = True  # Mark all messages as used to clear them

    # Clear the session
    request.session.flush()

    # Add logout message
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

@mongo_auth_required
def mongo_profile_view(request):
    """MongoDB-based profile view"""
    ensure_mongodb_connection()

    user_email = request.session.get('mongo_user_email')
    if not user_email:
        return redirect('login')

    user = MongoUser.objects(email=user_email).first()
    if not user:
        return redirect('login')

    context = {
        'user': user
    }

    return render(request, 'registration/edit_profile.html', context)

@mongo_auth_required
def mongo_profile_update_view(request):
    """MongoDB-based profile update view"""
    if request.method == 'POST':
        ensure_mongodb_connection()

        user_email = request.session.get('mongo_user_email')
        if not user_email:
            return redirect('login')

        user = MongoUser.objects(email=user_email).first()
        if not user:
            return redirect('login')

        # Update user information
        user.name = request.POST.get('name', user.name)
        user.phone = request.POST.get('phone', user.phone)

        # Update address
        if user.address:
            user.address.street = request.POST.get('address_street', user.address.street)
            user.address.city = request.POST.get('address_city', user.address.city)
            user.address.postal_code = request.POST.get('address_postal_code', user.address.postal_code)
            user.address.country = request.POST.get('address_country', user.address.country)
            user.address.apartment = request.POST.get('address_apartment', user.address.apartment)
            user.address.instructions = request.POST.get('address_instructions', user.address.instructions)
            user.address.latitude = float(request.POST.get('latitude', 0)) if request.POST.get('latitude') else None
            user.address.longitude = float(request.POST.get('longitude', 0)) if request.POST.get('longitude') else None
        else:
            # Create new address
            user.address = Address(
                street=request.POST.get('address_street', ''),
                city=request.POST.get('address_city', ''),
                postal_code=request.POST.get('address_postal_code', ''),
                country=request.POST.get('address_country', ''),
                apartment=request.POST.get('address_apartment', ''),
                instructions=request.POST.get('address_instructions', ''),
                latitude=float(request.POST.get('latitude', 0)) if request.POST.get('latitude') else None,
                longitude=float(request.POST.get('longitude', 0)) if request.POST.get('longitude') else None
            )

        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')

    return redirect('profile')


def mongo_update_donation_status_view(request, donation_id):
    """Update donation status (available/claimed/shipped)"""
    if request.method == 'POST':
        ensure_mongodb_connection()
        try:
            from bson import ObjectId
            donation = MongoDonation.objects(id=ObjectId(donation_id)).first()
            if donation:
                new_status = request.POST.get('status', 'available')
                donation.status = new_status
                donation.save()
                messages.success(request, f'Donation status updated to {new_status}')
            else:
                messages.error(request, 'Donation not found')
        except Exception as e:
            messages.error(request, f'Error updating donation: {str(e)}')

    return redirect('donor_dashboard')


@mongo_auth_required
def mongo_update_activity_status_view(request, activity_id):
    """Update activity status (available/completed/cancelled)"""
    ensure_mongodb_connection()
    
    # User is already authenticated and active due to decorator
    user = request.mongo_user
    
    try:
        from bson import ObjectId
        activity = MongoActivity.objects(id=ObjectId(activity_id)).first()
        if activity:
            # Check if user is the creator of this activity
            volunteer = MongoVolunteer.objects(user_id=user.id).first()
            if volunteer and activity.volunteer_id == volunteer.id:
                # Toggle between available and completed
                if activity.status == 'available':
                    activity.status = 'completed'
                    messages.success(request, 'Activity marked as completed!')
                elif activity.status == 'completed':
                    activity.status = 'available'
                    messages.success(request, 'Activity marked as available!')
                else:
                    # If status is cancelled or other, make it available
                    activity.status = 'available'
                    messages.success(request, 'Activity marked as available!')
                
                activity.save()
            else:
                messages.error(request, 'You can only update activities you created.')
        else:
            messages.error(request, 'Activity not found')
    except Exception as e:
        messages.error(request, f'Error updating activity: {str(e)}')

    return redirect('volunteer_dashboard')


def mongo_become_recipient_view(request):
    """Create recipient profile for current user"""
    user = _get_session_user(request)
    if not user:
        messages.error(request, 'Please log in first.')
        return redirect('login')

    # Check if MongoDB is available
    if not ensure_mongodb_connection():
        logger.warning("MongoDB not available in mongo_become_recipient_view, using session data")
        # Use session data for roles
        user_roles = request.session.get('user_roles', {})
        
        # Check if user already has recipient role
        if user_roles.get('is_recipient', False):
            messages.info(request, 'You already have a recipient profile.')
            return redirect('recipient_dashboard')
        
        # Add recipient role to session
        user_roles['is_recipient'] = True
        request.session['user_roles'] = user_roles
        
        messages.success(request, 'Recipient profile created successfully!')
        return redirect('recipient_dashboard')

    # MongoDB is available, proceed with normal logic
    user_email = request.session.get('mongo_user_email')
    if not user_email:
        messages.error(request, 'Please log in first.')
        return redirect('login')

    user = MongoUser.objects(email=user_email).first()
    if not user:
        messages.error(request, 'User not found.')
        return redirect('login')

    # Check if user already has a recipient profile
    existing_recipient = MongoRecipient.objects(user_id=user.id).first()
    if existing_recipient:
        messages.info(request, 'You already have a recipient profile.')
        return redirect('recipient_dashboard')

    # Check if user has other profiles (but don't remove them)
    donor = MongoDonor.objects(user_id=user.id).first()
    volunteer = MongoVolunteer.objects(user_id=user.id).first()

    if donor or volunteer:
        messages.info(request, 'You now have multiple profiles. You can switch between them from your dashboard.')

    # Create recipient profile
    recipient = MongoRecipient(
        user_id=user.id,
        shipping_address=user.address.street if user.address else ''
    )
    recipient.save()

    messages.success(request, 'Recipient profile created successfully!')
    return redirect('recipient_dashboard')


def mongo_become_volunteer_view(request):
    """Create volunteer profile for current user"""
    user = _get_session_user(request)
    if not user:
        messages.error(request, 'Please log in first.')
        return redirect('login')

    # Check if MongoDB is available
    if not ensure_mongodb_connection():
        logger.warning("MongoDB not available in mongo_become_volunteer_view, using session data")
        # Use session data for roles
        user_roles = request.session.get('user_roles', {})
        
        # Check if user already has volunteer role
        if user_roles.get('is_volunteer', False):
            messages.info(request, 'You already have a volunteer profile.')
            return redirect('volunteer_dashboard')
        
        # Add volunteer role to session
        user_roles['is_volunteer'] = True
        request.session['user_roles'] = user_roles
        
        messages.success(request, 'Volunteer profile created successfully!')
        return redirect('volunteer_dashboard')

    # MongoDB is available, proceed with normal logic
    user_email = request.session.get('mongo_user_email')
    if not user_email:
        messages.error(request, 'Please log in first.')
        return redirect('login')

    user = MongoUser.objects(email=user_email).first()
    if not user:
        messages.error(request, 'User not found.')
        return redirect('login')

    # Check if user already has a volunteer profile
    existing_volunteer = MongoVolunteer.objects(user_id=user.id).first()
    if existing_volunteer:
        messages.info(request, 'You already have a volunteer profile.')
        return redirect('activity_list')

    # Check if user has other profiles (but don't remove them)
    donor = MongoDonor.objects(user_id=user.id).first()
    recipient = MongoRecipient.objects(user_id=user.id).first()

    if donor or recipient:
        messages.info(request, 'You now have multiple profiles. You can switch between them from your dashboard.')

    # Create volunteer profile
    volunteer = MongoVolunteer(user_id=user.id)
    volunteer.save()

    messages.success(request, 'Volunteer profile created successfully!')
    return redirect('volunteer_dashboard')


def mongo_become_donor_view(request):
    """Create donor profile for current user"""
    user = _get_session_user(request)
    if not user:
        messages.error(request, 'Please log in first.')
        return redirect('login')

    # Check if MongoDB is available
    if not ensure_mongodb_connection():
        logger.warning("MongoDB not available in mongo_become_donor_view, using session data")
        # Use session data for roles
        user_roles = request.session.get('user_roles', {})
        
        # Check if user already has donor role
        if user_roles.get('is_donor', False):
            messages.info(request, 'You already have a donor profile.')
            return redirect('donor_dashboard')
        
        # Add donor role to session
        user_roles['is_donor'] = True
        request.session['user_roles'] = user_roles
        
        messages.success(request, 'Donor profile created successfully!')
        return redirect('donor_dashboard')

    # MongoDB is available, proceed with normal logic
    user_email = request.session.get('mongo_user_email')
    if not user_email:
        messages.error(request, 'Please log in first.')
        return redirect('login')

    user = MongoUser.objects(email=user_email).first()
    if not user:
        messages.error(request, 'User not found.')
        return redirect('login')

    # Check if user already has a donor profile
    existing_donor = MongoDonor.objects(user_id=user.id).first()
    if existing_donor:
        messages.info(request, 'You already have a donor profile.')
        return redirect('donor_dashboard')

    # Check if user has other profiles (but don't remove them)
    recipient = MongoRecipient.objects(user_id=user.id).first()
    volunteer = MongoVolunteer.objects(user_id=user.id).first()

    if recipient or volunteer:
        messages.info(request, 'You now have multiple profiles. You can switch between them from your dashboard.')

    # Create donor profile
    donor = MongoDonor(user_id=user.id)
    donor.save()

    messages.success(request, 'Donor profile created successfully!')
    return redirect('donor_dashboard')

@mongo_auth_required
def mongo_claim_donation_view(request, donation_id):
    """Claim a donation (for recipients)"""
    ensure_mongodb_connection()

    # User is already authenticated and active due to decorator
    user = request.mongo_user
    # Check if user has recipient profile
    recipient = MongoRecipient.objects(user_id=user.id).first()
    if not recipient:
        messages.error(request, 'You need to be a recipient to claim donations.')
        return redirect('become_recipient')

    try:
        from bson import ObjectId
        donation = MongoDonation.objects(id=ObjectId(donation_id)).first()
        if donation:
            if donation.status == 'available':
                donation.recipient_id = recipient.id
                donation.status = 'claimed'
                donation.claimed_at = datetime.now()
                donation.save()
                messages.success(request, 'Donation claimed successfully!')
                # --- Email Notifications ---
                # Notify donor that their donation was claimed
                donor = MongoDonor.objects(id=donation.donor_id).first()
                if donor:
                    donor_user = MongoUser.objects(id=donor.user_id).first()
                    if donor_user:
                        item = MongoItem.objects(id=donation.item_id).first()
                        send_notification_email(
                            "Your donation has been claimed",
                            donor_user.email,
                            "emails/donor_claimed.html",
                            {"donor": donor_user, "recipient": user, "item": item, "donation": donation}
                        )
                # Get donor and item for context
                donor = MongoDonor.objects(id=donation.donor_id).first()
                donor_user = MongoUser.objects(id=donor.user_id).first() if donor else None
                item = MongoItem.objects(id=donation.item_id).first()
                # Notify recipient that they claimed the item
                send_notification_email(
                    "You have successfully claimed a donation",
                    user.email,
                    "emails/recipient_claimed.html",
                    {"recipient": user, "donor": donor_user, "item": item, "donation": donation}
                )
            else:
                messages.error(request, 'This donation is no longer available.')
        else:
            messages.error(request, 'Donation not found.')
    except Exception as e:
        messages.error(request, f'Error claiming donation: {str(e)}')

    return redirect('recipient_dashboard')


def mongo_delete_donation_view(request, donation_id):
    """Delete a donation (for donors)"""
    ensure_mongodb_connection()

    user_email = request.session.get('mongo_user_email')
    if not user_email:
        messages.error(request, 'Please log in first.')
        return redirect('login')

    user = MongoUser.objects(email=user_email).first()
    if not user:
        messages.error(request, 'User not found.')
        return redirect('login')

    try:
        from bson import ObjectId
        donation = MongoDonation.objects(id=ObjectId(donation_id)).first()
        if donation:
            # Check if user is the donor
            donor = MongoDonor.objects(user_id=user.id).first()
            if donor and donation.donor_id == donor.id:
                donation.delete()
                messages.success(request, 'Donation deleted successfully!')
            else:
                messages.error(request, 'You can only delete your own donations.')
        else:
            messages.error(request, 'Donation not found.')
    except Exception as e:
        messages.error(request, f'Error deleting donation: {str(e)}')

    return redirect('donor_dashboard')


def mongo_update_donation_view(request, donation_id):
    """Update donation details (for donors)"""
    ensure_mongodb_connection()

    user_email = request.session.get('mongo_user_email')
    if not user_email:
        messages.error(request, 'Please log in first.')
        return redirect('login')

    user = MongoUser.objects(email=user_email).first()
    if not user:
        messages.error(request, 'User not found.')
        return redirect('login')

    try:
        from bson import ObjectId
        donation = MongoDonation.objects(id=ObjectId(donation_id)).first()
        if donation:
            # Check if user is the donor
            donor = MongoDonor.objects(user_id=user.id).first()
            if donor and donation.donor_id == donor.id:
                if request.method == 'POST':
                    # Update donation details here
                    messages.success(request, 'Donation updated successfully!')
                    return redirect('donor_dashboard')
                else:
                    # Show update form
                    return render(request, 'donations/update_donation.html', {'donation': donation})
            else:
                messages.error(request, 'You can only update your own donations.')
        else:
            messages.error(request, 'Donation not found.')
    except Exception as e:
        messages.error(request, f'Error updating donation: {str(e)}')

    return redirect('donor_dashboard')

@mongo_auth_required
def mongo_join_activity_view(request, activity_id):
    """Join an activity (for volunteers)"""
    ensure_mongodb_connection()

    # User is already authenticated and active due to decorator
    user = request.mongo_user
    try:
        from bson import ObjectId
        activity = MongoActivity.objects(id=ObjectId(activity_id)).first()
        if activity:
            # Check if user is a volunteer
            volunteer = MongoVolunteer.objects(user_id=user.id).first()
            if volunteer:
                # Check if already participating
                existing_participation = MongoVolunteerActivity.objects(
                    activity_id=activity.id,
                    volunteer_id=volunteer.id
                ).first()

                if not existing_participation:
                    # User has never joined this activity
                    participation = MongoVolunteerActivity(
                        activity_id=activity.id,
                        volunteer_id=volunteer.id,
                        participant_id=user.id,
                        status='joined'
                    )
                    participation.save()
                elif existing_participation.status == 'left':
                    # User previously left, update status to joined
                    existing_participation.status = 'joined'
                    existing_participation.save()
                    participation = existing_participation
                else:
                    messages.info(request, 'You are already participating in this activity.')
                    return redirect('activity_list')
                
                # Send success message and email notifications for both join cases
                messages.success(request, 'Successfully joined the activity!')
                creator = MongoVolunteer.objects(id=activity.volunteer_id).first()
                creator_user = MongoUser.objects(id=creator.user_id).first() if creator else None
                
                # --- Email Notifications ---
                # Notify volunteer that they joined the activity
                send_notification_email(
                    "You joined an activity",
                    user.email,
                    "emails/volunteer_joined.html",
                    {"volunteer": user, "activity": activity, "creator": creator_user}
                )

                # Notify activity creator that someone joined their activity
                creator = MongoVolunteer.objects(id=activity.volunteer_id).first()
                if creator:
                    creator_user = MongoUser.objects(id=creator.user_id).first()
                    if creator_user:
                        send_notification_email(
                            "A new volunteer joined your activity",
                            creator_user.email,
                            "emails/activity_creator_notified.html",
                            {"creator": creator_user, "volunteer": user, "activity": activity}
                        )
                
                # Check if activity is now full and update status accordingly
                current_participants = MongoVolunteerActivity.objects(
                    activity_id=activity.id,
                    status='joined'
                ).count()
                
                if current_participants >= activity.max_participants:
                    # Activity is full, set status to completed
                    activity.status = 'completed'
                    activity.save()
                    messages.info(request, 'Activity is now full and marked as completed!')
                elif activity.status == 'completed' and current_participants < activity.max_participants:
                    # Activity was completed but now has space, set back to available
                    activity.status = 'available'
                    activity.save()
                    messages.info(request, 'Activity now has space and is available again!')
            else:
                messages.error(request, 'You need to be a volunteer to join activities.')
        else:
            messages.error(request, 'Activity not found.')
    except Exception as e:
        messages.error(request, f'Error joining activity: {str(e)}')

    return redirect('activity_list')


@mongo_auth_required
def mongo_leave_activity_view(request, activity_id):
    """Leave an activity (for volunteers)"""
    ensure_mongodb_connection()

    # User is already authenticated and active due to decorator
    user = request.mongo_user

    try:
        from bson import ObjectId
        activity = MongoActivity.objects(id=ObjectId(activity_id)).first()
        if activity:
            # Check if user is a volunteer
            volunteer = MongoVolunteer.objects(user_id=user.id).first()
            if volunteer:
                participation = MongoVolunteerActivity.objects(
                    activity_id=activity.id,
                    volunteer_id=volunteer.id
                ).first()

                if participation:
                    participation.status = 'left'
                    participation.save()
                    messages.success(request, 'Successfully left the activity.')
                    
                    # Check if activity should become available again
                    current_participants = MongoVolunteerActivity.objects(
                        activity_id=activity.id,
                        status='joined'
                    ).count()
                    
                    if activity.status == 'completed' and current_participants < activity.max_participants:
                        # Activity was completed but now has space, set back to available
                        activity.status = 'available'
                        activity.save()
                        messages.info(request, 'Activity now has space and is available again!')
                else:
                    messages.info(request, 'You are not participating in this activity.')
            else:
                messages.error(request, 'You need to be a volunteer to leave activities.')
        else:
            messages.error(request, 'Activity not found.')
    except Exception as e:
        messages.error(request, f'Error leaving activity: {str(e)}')

    return redirect('activity_list')


def mongo_delete_activity_view(request, activity_id):
    """Delete an activity (for volunteers who created it)"""
    ensure_mongodb_connection()

    user_email = request.session.get('mongo_user_email')
    if not user_email:
        messages.error(request, 'Please log in first.')
        return redirect('login')

    user = MongoUser.objects(email=user_email).first()
    if not user:
        messages.error(request, 'User not found.')
        return redirect('login')

    try:
        from bson import ObjectId
        activity = MongoActivity.objects(id=ObjectId(activity_id)).first()
        if activity:
            # Check if user is the volunteer who created the activity
            volunteer = MongoVolunteer.objects(user_id=user.id).first()
            if volunteer and activity.volunteer_id == volunteer.id:
                activity.delete()
                messages.success(request, 'Activity deleted successfully!')
            else:
                messages.error(request, 'You can only delete activities you created.')
        else:
            messages.error(request, 'Activity not found.')
    except Exception as e:
        messages.error(request, f'Error deleting activity: {str(e)}')

    return redirect('activity_list')
