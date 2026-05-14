"""
MongoDB-based Admin System for Donation Management
This replaces the Django ORM admin with MongoDB operations
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.hashers import check_password, make_password
from datetime import datetime, timedelta
from bson import ObjectId
import json

from mongo_utils import connect_to_mongodb, get_mongodb_connection
from mongo_models import User as MongoUser, Donor as MongoDonor, Recipient as MongoRecipient, \
    Volunteer as MongoVolunteer, Item as MongoItem, Donation as MongoDonation, \
    Activity as MongoActivity, VolunteerActivity as MongoVolunteerActivity, Address

def ensure_mongo_connection():
    """Ensure MongoDB connection is established"""
    if not get_mongodb_connection():
        connect_to_mongodb()

def mongo_admin_login_required(view_func):
    """Decorator to check if user is logged in and has admin privileges"""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('mongo_user_email'):
            messages.error(request, 'Please log in to access admin panel.')
            return redirect('login')
        
        ensure_mongo_connection()
        user_email = request.session.get('mongo_user_email')
        user = MongoUser.objects(email=user_email).first()
        
        if not user or not (user.is_staff or user.is_superuser):
            messages.error(request, 'You do not have permission to access admin panel.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper

@mongo_admin_login_required
def mongo_admin_dashboard(request):
    """MongoDB-based admin dashboard"""
    ensure_mongo_connection()
    
    # Get time period filter
    days = int(request.GET.get('days', 30))
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # User Statistics
    total_users = MongoUser.objects.count()
    active_users = MongoUser.objects(is_active=True).count()
    blocked_users = MongoUser.objects(is_active=False).count()
    new_users_period = MongoUser.objects(date_joined__gte=start_date).count()
    
    # Donation Statistics
    total_donations = MongoDonation.objects.count()
    available_donations = MongoDonation.objects(status='available').count()
    claimed_donations = MongoDonation.objects(status='claimed').count()
    shipped_donations = MongoDonation.objects(status='shipped').count()
    unavailable_donations = MongoDonation.objects(status='unavailable').count()
    new_donations_period = MongoDonation.objects(created_at__gte=start_date).count()
    
    # Activity Statistics
    total_activities = MongoActivity.objects.count()
    available_activities = MongoActivity.objects.count()  # All activities are available by default
    joined_activities = MongoVolunteerActivity.objects(status='joined').count()
    completed_activities = MongoVolunteerActivity.objects(status='completed').count()
    cancelled_activities = MongoVolunteerActivity.objects(status='cancelled').count()
    
    # Recent Data with proper relationships
    recent_donations_data = []
    recent_donations = MongoDonation.objects.order_by('-created_at')[:10]
    for donation in recent_donations:
        item = MongoItem.objects(id=donation.item_id).first()
        donor = MongoDonor.objects(id=donation.donor_id).first()
        donor_user = MongoUser.objects(id=donor.user_id).first() if donor else None
        recipient = MongoRecipient.objects(id=donation.recipient_id).first() if donation.recipient_id else None
        recipient_user = MongoUser.objects(id=recipient.user_id).first() if recipient else None
        
        donation_data = {
            'id': donation.id,
            'status': donation.status,
            'created_at': donation.created_at,
            'item': item,
            'donor_name': donor_user.name if donor_user else 'Unknown',
            'donor_email': donor_user.email if donor_user else 'Unknown',
            'recipient_name': recipient_user.name if recipient_user else None,
            'recipient_email': recipient_user.email if recipient_user else None,
        }
        recent_donations_data.append(donation_data)
    
    recent_users = MongoUser.objects.order_by('-date_joined')[:10]
    
    # Top Donors
    top_donors_data = []
    donors = MongoDonor.objects.all()
    for donor in donors:
        donation_count = MongoDonation.objects(donor_id=donor.id).count()
        if donation_count > 0:
            user = MongoUser.objects(id=donor.user_id).first()
            if user:
                top_donors_data.append({
                    'user': user,
                    'donation_count': donation_count
                })
    
    top_donors = sorted(top_donors_data, key=lambda x: x['donation_count'], reverse=True)[:10]
    
    # Top Recipients
    top_recipients_data = []
    recipients = MongoRecipient.objects.all()
    for recipient in recipients:
        claimed_count = MongoDonation.objects(recipient_id=recipient.id).count()
        if claimed_count > 0:
            user = MongoUser.objects(id=recipient.user_id).first()
            if user:
                top_recipients_data.append({
                    'user': user,
                    'claimed_count': claimed_count
                })
    
    top_recipients = sorted(top_recipients_data, key=lambda x: x['claimed_count'], reverse=True)[:10]
    
    # All Donations for table with proper relationships
    all_donations_data = []
    all_donations = MongoDonation.objects.order_by('-created_at')
    for donation in all_donations:
        item = MongoItem.objects(id=donation.item_id).first()
        donor = MongoDonor.objects(id=donation.donor_id).first()
        donor_user = MongoUser.objects(id=donor.user_id).first() if donor else None
        recipient = MongoRecipient.objects(id=donation.recipient_id).first() if donation.recipient_id else None
        recipient_user = MongoUser.objects(id=recipient.user_id).first() if recipient else None
        
        donation_data = {
            'id': donation.id,
            'status': donation.status,
            'created_at': donation.created_at,
            'item': item,
            'donor_name': donor_user.name if donor_user else 'Unknown',
            'donor_email': donor_user.email if donor_user else 'Unknown',
            'recipient_name': recipient_user.name if recipient_user else None,
            'recipient_email': recipient_user.email if recipient_user else None,
        }
        all_donations_data.append(donation_data)
    
    # Donation Category Statistics
    donation_category_stats = []
    categories = MongoItem.objects.distinct('category')
    for category in categories:
        items = MongoItem.objects(category=category)
        item_ids = [item.id for item in items]
        donations = MongoDonation.objects(item_id__in=item_ids)
        
        stats = {
            'item__category': category,
            'total_count': donations.count(),
            'available_count': donations(status='available').count(),
            'claimed_count': donations(status='claimed').count(),
            'shipped_count': donations(status='shipped').count(),
        }
        donation_category_stats.append(stats)
    
    # Volunteer Activity Trends (last 30 days)
    volunteer_activity_trends = []
    for i in range(30):
        date = datetime.utcnow() - timedelta(days=i)
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        activities_created = MongoActivity.objects(
            created_at__gte=start_of_day,
            created_at__lte=end_of_day
        ).count()
        
        activities_completed = MongoVolunteerActivity.objects(
            status='completed',
            created_at__gte=start_of_day,
            created_at__lte=end_of_day
        ).count()
        
        volunteer_activity_trends.append({
            'date': date.strftime('%Y-%m-%d'),
            'activities_created': activities_created,
            'activities_completed': activities_completed
        })
    
    # Reverse to show oldest to newest (so today is at the end)
    volunteer_activity_trends.reverse()
    
    
    # Volunteer Activity Status
    volunteer_activity_status = {
        'available': MongoVolunteerActivity.objects(status='joined').count(),
        'completed': MongoVolunteerActivity.objects(status='completed').count(),
        'cancelled': MongoVolunteerActivity.objects(status='cancelled').count(),
    }
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'blocked_users': blocked_users,
        'new_users_period': new_users_period,
        'total_donations': total_donations,
        'available_donations': available_donations,
        'claimed_donations': claimed_donations,
        'shipped_donations': shipped_donations,
        'unavailable_donations': unavailable_donations,
        'new_donations_period': new_donations_period,
        'total_activities': total_activities,
        'available_activities': available_activities,
        'joined_activities': joined_activities,
        'completed_activities': completed_activities,
        'cancelled_activities': cancelled_activities,
        'recent_donations': recent_donations_data,
        'recent_users': recent_users,
        'top_donors': top_donors,
        'top_recipients': top_recipients,
        'all_donations': all_donations_data,
        'donation_category_stats': donation_category_stats,
        'volunteer_activity_trends': volunteer_activity_trends,
        'volunteer_activity_status': volunteer_activity_status,
        'days': days,
    }
    
    return render(request, 'admin/admin_dashboard.html', context)

@mongo_admin_login_required
def mongo_admin_user_management(request):
    """MongoDB-based user management"""
    ensure_mongo_connection()
    
    # Get filter parameters
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    role_filter = request.GET.get('role', '')
    
    # Build query
    query = {}
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}}
        ]
    if status_filter:
        query['is_active'] = status_filter == 'active'
    
    users = MongoUser.objects(**query).order_by('-date_joined')
    
    # Add role information to users
    users_with_roles = []
    for user in users:
        donor = MongoDonor.objects(user_id=user.id).first()
        recipient = MongoRecipient.objects(user_id=user.id).first()
        volunteer = MongoVolunteer.objects(user_id=user.id).first()
        
        user_data = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'is_active': user.is_active,
            'date_joined': user.date_joined,
            'is_donor': donor is not None,
            'is_recipient': recipient is not None,
            'is_volunteer': volunteer is not None,
        }
        users_with_roles.append(user_data)
    
    # Apply role filter
    if role_filter:
        filtered_users = []
        for user in users_with_roles:
            if role_filter == 'donor' and user['is_donor']:
                filtered_users.append(user)
            elif role_filter == 'recipient' and user['is_recipient']:
                filtered_users.append(user)
            elif role_filter == 'volunteer' and user['is_volunteer']:
                filtered_users.append(user)
        users_with_roles = filtered_users
    
    # Pagination
    paginator = Paginator(users_with_roles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'search_query': search,
        'status_filter': status_filter,
        'role_filter': role_filter,
    }
    
    return render(request, 'admin/user_management.html', context)

@mongo_admin_login_required
def mongo_admin_donation_management(request):
    """MongoDB-based donation management"""
    ensure_mongo_connection()
    
    # Get filter parameters
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    
    # Build query
    query = {}
    if status_filter:
        query['status'] = status_filter
    
    donations = MongoDonation.objects(**query).order_by('-created_at')
    
    # Add relationship data to donations
    donations_with_data = []
    for donation in donations:
        item = MongoItem.objects(id=donation.item_id).first()
        donor = MongoDonor.objects(id=donation.donor_id).first()
        donor_user = MongoUser.objects(id=donor.user_id).first() if donor else None
        recipient = MongoRecipient.objects(id=donation.recipient_id).first() if donation.recipient_id else None
        recipient_user = MongoUser.objects(id=recipient.user_id).first() if recipient else None
        
        donation_data = {
            'id': donation.id,
            'status': donation.status,
            'created_at': donation.created_at,
            'item': item,
            'donor_name': donor_user.name if donor_user else 'Unknown',
            'donor_email': donor_user.email if donor_user else 'Unknown',
            'recipient_name': recipient_user.name if recipient_user else None,
            'recipient_email': recipient_user.email if recipient_user else None,
        }
        donations_with_data.append(donation_data)
    
    # Apply search filter
    if search:
        filtered_donations = []
        for donation in donations_with_data:
            if donation['item'] and (search.lower() in donation['item'].name.lower() or search.lower() in donation['item'].description.lower()):
                filtered_donations.append(donation)
        donations_with_data = filtered_donations
    
    # Apply category filter
    if category_filter:
        filtered_donations = []
        for donation in donations_with_data:
            if donation['item'] and donation['item'].category == category_filter:
                filtered_donations.append(donation)
        donations_with_data = filtered_donations
    
    # Pagination
    paginator = Paginator(donations_with_data, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter
    categories = MongoItem.objects.distinct('category')
    
    context = {
        'donations': page_obj,
        'search_query': search,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'categories': categories,
    }
    
    return render(request, 'admin/donation_management.html', context)

@mongo_admin_login_required
def mongo_admin_activity_management(request):
    """MongoDB-based activity management"""
    ensure_mongo_connection()
    
    # Get filter parameters
    search = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    
    # Build query
    query = {}
    if search:
        query['$or'] = [
            {'title': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}}
        ]
    if category_filter:
        query['category'] = category_filter
    
    activities = MongoActivity.objects(**query).order_by('-created_at')
    
    # Add organizer information to activities
    activities_with_data = []
    for activity in activities:
        volunteer = MongoVolunteer.objects(id=activity.volunteer_id).first()
        volunteer_user = MongoUser.objects(id=volunteer.user_id).first() if volunteer else None
        
        activity_data = {
            'id': activity.id,
            'title': activity.title,
            'description': activity.description,
            'category': activity.category,
            'location': activity.location,
            'activity_date': activity.activity_date,
            'duration_hours': activity.duration_hours,
            'max_participants': activity.max_participants,
            'image_url': activity.image_url,
            'organizer_name': volunteer_user.name if volunteer_user else 'Unknown',
            'organizer_email': volunteer_user.email if volunteer_user else 'Unknown',
        }
        activities_with_data.append(activity_data)
    
    # Pagination
    paginator = Paginator(activities_with_data, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter
    categories = MongoActivity.objects.distinct('category')
    
    context = {
        'activities': page_obj,
        'search_query': search,
        'category_filter': category_filter,
        'categories': categories,
    }
    
    return render(request, 'admin/activity_management.html', context)

@mongo_admin_login_required
def mongo_admin_activity_logs(request):
    """MongoDB-based activity logs"""
    ensure_mongo_connection()
    
    # Get recent activities (this is a simplified version)
    recent_activities = []
    
    # Recent donations
    recent_donations = MongoDonation.objects.order_by('-created_at')[:20]
    for donation in recent_donations:
        item = MongoItem.objects(id=donation.item_id).first()
        donor = MongoDonor.objects(id=donation.donor_id).first()
        donor_user = MongoUser.objects(id=donor.user_id).first() if donor else None
        
        recent_activities.append({
            'type': 'donation',
            'action': f'Donation {donation.status}',
            'description': f'{item.name if item else "Unknown item"} by {donor_user.name if donor_user else "Unknown donor"}',
            'timestamp': donation.created_at,
            'user': donor_user.name if donor_user else 'Unknown',
        })
    
    # Recent activities
    recent_volunteer_activities = MongoActivity.objects.order_by('-created_at')[:20]
    for activity in recent_volunteer_activities:
        volunteer = MongoVolunteer.objects(id=activity.volunteer_id).first()
        volunteer_user = MongoUser.objects(id=volunteer.user_id).first() if volunteer else None
        
        recent_activities.append({
            'type': 'activity',
            'action': 'Activity created',
            'description': f'{activity.title} at {activity.location}',
            'timestamp': activity.created_at,
            'user': volunteer_user.name if volunteer_user else 'Unknown',
        })
    
    # Sort by timestamp
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Pagination
    paginator = Paginator(recent_activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'activities': page_obj,
    }
    
    return render(request, 'admin/activity_logs.html', context)

@mongo_admin_login_required
def mongo_admin_user_detail(request, user_id):
    """MongoDB-based user detail view"""
    ensure_mongo_connection()
    
    try:
        user = MongoUser.objects(id=ObjectId(user_id)).first()
        if not user:
            messages.error(request, 'User not found.')
            return redirect('admin_user_management')
        
        # Get user profiles
        donor = MongoDonor.objects(user_id=user.id).first()
        recipient = MongoRecipient.objects(user_id=user.id).first()
        volunteer = MongoVolunteer.objects(user_id=user.id).first()
        
        # Get user's donations
        user_donations = []
        if donor:
            donations = MongoDonation.objects(donor_id=donor.id)
            for donation in donations:
                item = MongoItem.objects(id=donation.item_id).first()
                user_donations.append({
                    'donation': donation,
                    'item': item
                })
        
        # Get user's claimed donations
        claimed_donations = []
        if recipient:
            donations = MongoDonation.objects(recipient_id=recipient.id)
            for donation in donations:
                item = MongoItem.objects(id=donation.item_id).first()
                claimed_donations.append({
                    'donation': donation,
                    'item': item
                })
        
        # Get user's activities
        user_activities = []
        if volunteer:
            activities = MongoActivity.objects(volunteer_id=volunteer.id)
            user_activities = list(activities)
        
        context = {
            'user': user,
            'donor': donor,
            'recipient': recipient,
            'volunteer': volunteer,
            'user_donations': user_donations,
            'claimed_donations': claimed_donations,
            'user_activities': user_activities,
        }
        
        return render(request, 'admin/user_detail.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading user: {str(e)}')
        return redirect('admin_user_management')

@mongo_admin_login_required
def mongo_admin_toggle_user_status(request, user_id):
    """Toggle user active status"""
    if request.method == 'POST':
        ensure_mongo_connection()
        try:
            user = MongoUser.objects(id=ObjectId(user_id)).first()
            if user:
                user.is_active = not user.is_active
                user.save()
                status = 'activated' if user.is_active else 'blocked'
                messages.success(request, f'User {status} successfully.')
            else:
                messages.error(request, 'User not found.')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    return redirect('admin_user_detail', user_id=user_id)

@mongo_admin_login_required
def mongo_admin_delete_user(request, user_id):
    """Delete user and all related data"""
    if request.method == 'POST':
        ensure_mongo_connection()
        try:
            user = MongoUser.objects(id=ObjectId(user_id)).first()
            if user:
                # Delete related data
                donor = MongoDonor.objects(user_id=user.id).first()
                if donor:
                    # Delete donor's items and donations
                    items = MongoItem.objects(donor_id=donor.id)
                    for item in items:
                        MongoDonation.objects(item_id=item.id).delete()
                        item.delete()
                    donor.delete()
                
                recipient = MongoRecipient.objects(user_id=user.id).first()
                if recipient:
                    # Update donations to remove recipient
                    MongoDonation.objects(recipient_id=recipient.id).update(set__recipient_id=None)
                    recipient.delete()
                
                volunteer = MongoVolunteer.objects(user_id=user.id).first()
                if volunteer:
                    # Delete volunteer's activities
                    activities = MongoActivity.objects(volunteer_id=volunteer.id)
                    for activity in activities:
                        MongoVolunteerActivity.objects(activity_id=activity.id).delete()
                        activity.delete()
                    volunteer.delete()
                
                # Delete user
                user.delete()
                messages.success(request, 'User and all related data deleted successfully.')
            else:
                messages.error(request, 'User not found.')
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
    else:
        # Handle GET request by redirecting to user management
        return redirect('admin_user_management')
    
    return redirect('admin_user_management')

@mongo_admin_login_required
def mongo_admin_ship_donation(request, donation_id):
    """Mark donation as shipped"""
    if request.method == 'POST':
        ensure_mongo_connection()
        try:
            donation = MongoDonation.objects(id=ObjectId(donation_id)).first()
            if donation:
                donation.status = 'shipped'
                donation.save()
                messages.success(request, 'Donation marked as shipped.')
            else:
                messages.error(request, 'Donation not found.')
        except Exception as e:
            messages.error(request, f'Error updating donation: {str(e)}')
    else:
        # Handle GET request by redirecting to donation management
        return redirect('admin_donation_management')
    
    return redirect('admin_donation_management')

@mongo_admin_login_required
def mongo_admin_delete_donation(request, donation_id):
    """Delete donation"""
    if request.method == 'POST':
        ensure_mongo_connection()
        try:
            donation = MongoDonation.objects(id=ObjectId(donation_id)).first()
            if donation:
                # Also delete the associated item
                item = MongoItem.objects(id=donation.item_id).first()
                if item:
                    item.delete()
                donation.delete()
                messages.success(request, 'Donation deleted successfully.')
            else:
                messages.error(request, 'Donation not found.')
        except Exception as e:
            messages.error(request, f'Error deleting donation: {str(e)}')
    else:
        # Handle GET request by redirecting to donation management
        return redirect('admin_donation_management')
    
    return redirect('admin_donation_management')

@mongo_admin_login_required
def mongo_admin_delete_activity(request, activity_id):
    """Delete activity"""
    if request.method == 'POST':
        ensure_mongo_connection()
        try:
            activity = MongoActivity.objects(id=ObjectId(activity_id)).first()
            if activity:
                # Delete related volunteer activities
                MongoVolunteerActivity.objects(activity_id=activity.id).delete()
                activity.delete()
                messages.success(request, 'Activity deleted successfully.')
            else:
                messages.error(request, 'Activity not found.')
        except Exception as e:
            messages.error(request, f'Error deleting activity: {str(e)}')
    
    return redirect('admin_activity_management')

@mongo_admin_login_required
def mongo_admin_export_data(request):
    """Export data to JSON"""
    ensure_mongo_connection()
    
    export_type = request.GET.get('type', 'all')
    
    data = {}
    
    if export_type in ['all', 'users']:
        users = MongoUser.objects.all()
        data['users'] = [user.to_mongo() for user in users]
    
    if export_type in ['all', 'donations']:
        donations = MongoDonation.objects.all()
        data['donations'] = [donation.to_mongo() for donation in donations]
    
    if export_type in ['all', 'activities']:
        activities = MongoActivity.objects.all()
        data['activities'] = [activity.to_mongo() for activity in activities]
    
    response = JsonResponse(data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="admin_export_{export_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
    
    return response