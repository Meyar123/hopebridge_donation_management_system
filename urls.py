from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from mongodb_only_views import about_view as mongo_about_view

# Health check endpoint for Railway
def health_check(request):
    from django.http import HttpResponse
    # Railway expects a simple 200 OK response with plain text
    return HttpResponse("OK", status=200)

# MongoDB connection test endpoint
def mongodb_test(request):
    from django.http import JsonResponse
    from mongo_utils import get_mongodb_connection, ensure_mongodb_connection
    from django.conf import settings
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Try to ensure MongoDB connection
        connected = ensure_mongodb_connection()
        
        # Get connection status
        connection_status = get_mongodb_connection()
        
        # Get MongoDB settings
        mongodb_info = {
            'connected': connected,
            'connection_status': connection_status,
            'uri_set': bool(getattr(settings, 'MONGODB_URI', None)),
            'host': getattr(settings, 'MONGODB_HOST', 'Not set'),
            'port': getattr(settings, 'MONGODB_PORT', 'Not set'),
            'database': getattr(settings, 'MONGODB_DATABASE', 'Not set'),
            'uri_contains_railway_internal': 'railway.internal' in getattr(settings, 'MONGODB_URI', ''),
        }
        
        return JsonResponse({
            'status': 'success',
            'mongodb': mongodb_info,
            'message': 'MongoDB connection test completed'
        })
        
    except Exception as e:
        logger.error(f"MongoDB test error: {e}")
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'message': 'MongoDB connection test failed'
        }, status=500)

# Welcome view for root path
def welcome_view(request):
    from django.shortcuts import render
    return render(request, 'welcome.html')

# ---- יבוא עקבי של כל ה-views שלנו ----
from mongodb_only_views import (
    # Auth & Profile
    mongo_login_view, mongo_register_view, mongo_logout_view,
    mongo_dashboard_view, mongo_profile_view, mongo_profile_update_view,
    password_reset_start, password_reset_confirm,

    # Onboarding / compat
    onboarding, dashboard_selection_view, profile_redirect_view,
    blocked_user_view, contact_admin, register_volunteer, about_view,

    # Roles
    mongo_become_recipient_view, mongo_become_volunteer_view, mongo_become_donor_view,

    # Donations/Items
    mongo_item_list_view, mongo_item_create_view, mongo_claim_donation_view,
    mongo_update_donation_status_view, mongo_delete_donation_view, mongo_update_donation_view,

    # Activities
    mongo_activity_list_view, mongo_activity_create_view,
    mongo_join_activity_view, mongo_leave_activity_view,
    mongo_update_activity_status_view, mongo_delete_activity_view,
    # Email verification
    mongo_verify_email_view, mongo_resend_code_view,
)

from mongodb_admin import (
    mongo_admin_dashboard, mongo_admin_user_management,
    mongo_admin_donation_management, mongo_admin_activity_management,
    mongo_admin_activity_logs,
    mongo_admin_delete_donation, mongo_admin_ship_donation,

    # חדשים
    mongo_admin_user_detail, mongo_admin_toggle_user_status,
    mongo_admin_delete_user, mongo_admin_delete_activity,
    mongo_admin_export_data,
)

# ---- אופציה A: להפנות /admin לדשבורד מנוהל שלנו ----
urlpatterns = [
    path('admin/', lambda request: redirect('admin_dashboard')),
    path('health/', health_check, name='health_check'),
    path('mongodb-test/', mongodb_test, name='mongodb_test'),
]

# ---- עמודים כלליים ----
urlpatterns += [
    path('about/', mongo_about_view, name='about'),
    path('contact-admin/', contact_admin, name='contact_admin'),
]

# ---- allauth ----
urlpatterns += [
    path('accounts/', include('allauth.urls')),
]

# ---- Onboarding + No-roles ----
urlpatterns += [
    path('onboarding/', onboarding, name='onboarding'),
    path('dashboard/no-roles/', TemplateView.as_view(template_name='dashboard/no_roles.html'), name='no_roles'),
]

# ---- Main & Auth ----
urlpatterns += [
    path('', welcome_view, name='welcome'),
    path('login/',    mongo_login_view,    name='login'),
    path('logout/',   mongo_logout_view,   name='logout'),
    path('register/', mongo_register_view, name='register'),
]

# ---- Password reset ----
urlpatterns += [
    path('password-reset/', password_reset_start, name='password_reset'),
    path('reset/<uidb64>/<token>/', password_reset_confirm, name='password_reset_confirm'),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"),
        name='password_reset_complete'
    ),
]

# ---- אימות מייל ----
urlpatterns += [
    path('verify-email/', mongo_verify_email_view, name='verify_email'),
    path('resend-code/',  mongo_resend_code_view,  name='resend_code'),
]

# ---- Profile & Roles ----
urlpatterns += [
    path('accounts/profile/', profile_redirect_view, name='profile_redirect'),
    path('dashboard/selection/', dashboard_selection_view, name='dashboard_selection'),

    path('become-donor/',     mongo_become_donor_view,     name='become_donor'),
    path('become-recipient/', mongo_become_recipient_view, name='become_recipient'),
    path('become-volunteer/', mongo_become_volunteer_view, name='become_volunteer'),

    path('profile/',      mongo_profile_view,        name='profile'),
    path('profile/edit/', mongo_profile_update_view, name='edit_profile'),
    path('blocked/',      blocked_user_view,         name='blocked_user'),
]

# ---- Dashboards לפי תפקיד ----
urlpatterns += [
    path('dashboard/donor/',     mongo_dashboard_view, name='donor_dashboard'),
    path('dashboard/recipient/', mongo_dashboard_view, name='recipient_dashboard'),
    path('dashboard/volunteer/', mongo_dashboard_view, name='volunteer_dashboard'),
]

# ---- MongoDB Admin ----
urlpatterns += [
    path('admin-dashboard/', mongo_admin_dashboard, name='admin_dashboard'),
    path('admin-users/', mongo_admin_user_management, name='admin_user_management'),
    path('admin-users/<str:user_id>/', mongo_admin_user_detail, name='admin_user_detail'),
    path('admin-users/<str:user_id>/toggle-status/', mongo_admin_toggle_user_status, name='admin_toggle_user_status'),
    path('admin-users/<str:user_id>/delete/', mongo_admin_delete_user, name='admin_delete_user'),

    path('admin-donations/', mongo_admin_donation_management, name='admin_donation_management'),
    path('admin-donations/<str:donation_id>/ship/', mongo_admin_ship_donation, name='admin_ship_donation'),
    path('admin-donations/<str:donation_id>/delete/', mongo_admin_delete_donation, name='admin_delete_donation'),

    path('admin-activities/', mongo_admin_activity_management, name='admin_activity_management'),
    path('admin-activities/<str:activity_id>/delete/', mongo_admin_delete_activity, name='admin_delete_activity'),

    path('admin-logs/', mongo_admin_activity_logs, name='admin_activity_logs'),
    path('admin-export/', mongo_admin_export_data, name='admin_export_data'),
]

# ---- Volunteer Registration ----
urlpatterns += [
    path('register/volunteer/', register_volunteer, name='register_volunteer'),
]

# ---- Donations ----
urlpatterns += [
    path('donations/',        mongo_item_list_view,   name='donation_list'),
    path('donations/create/', mongo_item_create_view, name='create_donation'),

    path('donations/<str:donation_id>/claim/',         mongo_claim_donation_view,         name='claim_donation'),
    path('donations/<str:donation_id>/update-status/', mongo_update_donation_status_view, name='update_donation_status'),
    path('donations/<str:donation_id>/update/',        mongo_update_donation_view,        name='update_donation'),
    path('donations/<str:donation_id>/delete/',        mongo_delete_donation_view,        name='delete_donation'),
]

# ---- Items ----
urlpatterns += [
    path('items/',        mongo_item_list_view,   name='item_list'),
    path('items/create/', mongo_item_create_view, name='create_item'),
]

# ---- Activities ----
urlpatterns += [
    path('activities/',                 mongo_activity_list_view,   name='activity_list'),
    path('activities/create/',          mongo_activity_create_view, name='create_activity'),
    path('activities/<str:activity_id>/join/', mongo_join_activity_view, name='join_activity'),
    path('activities/<str:activity_id>/leave/', mongo_leave_activity_view, name='leave_activity'),
    path('activities/<str:activity_id>/update-status/', mongo_update_activity_status_view, name='update_activity_status'),
    path('activities/<str:activity_id>/delete/', mongo_delete_activity_view, name='delete_activity'),
]

# ---- סטטי/מדיה בפיתוח ----
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# In production, WhiteNoise handles static files

urlpatterns += [
    path('dashboard/', profile_redirect_view, name='dashboard'),
]