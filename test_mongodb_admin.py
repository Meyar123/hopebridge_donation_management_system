#!/usr/bin/env python
"""
Test script for MongoDB Admin functionality
Run this to verify the admin system works correctly
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from mongo_utils import connect_to_mongodb, get_mongodb_connection
from mongo_models import User as MongoUser, Donor as MongoDonor, Recipient as MongoRecipient, \
    Volunteer as MongoVolunteer, Item as MongoItem, Donation as MongoDonation, \
    Activity as MongoActivity, VolunteerActivity as MongoVolunteerActivity, Address
from datetime import datetime

def test_mongodb_connection():
    """Test MongoDB connection"""
    print("Testing MongoDB connection...")
    try:
        connect_to_mongodb()
        if get_mongodb_connection():
            print("✅ MongoDB connection successful")
            return True
        else:
            print("❌ MongoDB connection failed")
            return False
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
        return False

def test_admin_data_queries():
    """Test admin data queries"""
    print("\nTesting admin data queries...")
    try:
        # Test user queries
        total_users = MongoUser.objects.count()
        active_users = MongoUser.objects(is_active=True).count()
        print(f"✅ Users: {total_users} total, {active_users} active")
        
        # Test donation queries
        total_donations = MongoDonation.objects.count()
        available_donations = MongoDonation.objects(status='available').count()
        print(f"✅ Donations: {total_donations} total, {available_donations} available")
        
        # Test activity queries
        total_activities = MongoActivity.objects.count()
        print(f"✅ Activities: {total_activities} total")
        
        # Test user roles
        donors = MongoDonor.objects.count()
        recipients = MongoRecipient.objects.count()
        volunteers = MongoVolunteer.objects.count()
        print(f"✅ Roles: {donors} donors, {recipients} recipients, {volunteers} volunteers")
        
        return True
    except Exception as e:
        print(f"❌ Admin data query error: {e}")
        return False

def test_admin_relationships():
    """Test admin relationship queries"""
    print("\nTesting admin relationship queries...")
    try:
        # Test donation with relationships
        donations = MongoDonation.objects.limit(5)
        for donation in donations:
            item = MongoItem.objects(id=donation.item_id).first()
            donor = MongoDonor.objects(id=donation.donor_id).first()
            donor_user = MongoUser.objects(id=donor.user_id).first() if donor else None
            
            if item and donor_user:
                print(f"✅ Donation: {item.name} by {donor_user.name}")
            else:
                print(f"⚠️  Donation: Missing relationships")
        
        # Test activity with relationships
        activities = MongoActivity.objects.limit(5)
        for activity in activities:
            volunteer = MongoVolunteer.objects(id=activity.volunteer_id).first()
            volunteer_user = MongoUser.objects(id=volunteer.user_id).first() if volunteer else None
            
            if volunteer_user:
                print(f"✅ Activity: {activity.title} by {volunteer_user.name}")
            else:
                print(f"⚠️  Activity: Missing relationships")
        
        return True
    except Exception as e:
        print(f"❌ Admin relationship query error: {e}")
        return False

def test_admin_statistics():
    """Test admin statistics calculations"""
    print("\nTesting admin statistics calculations...")
    try:
        # Test category statistics
        categories = MongoItem.objects.distinct('category')
        print(f"✅ Categories found: {len(categories)}")
        
        for category in categories:
            items = MongoItem.objects(category=category)
            item_ids = [item.id for item in items]
            donations = MongoDonation.objects(item_id__in=item_ids)
            
            stats = {
                'total': donations.count(),
                'available': donations(status='available').count(),
                'claimed': donations(status='claimed').count(),
                'shipped': donations(status='shipped').count(),
            }
            print(f"✅ {category}: {stats}")
        
        return True
    except Exception as e:
        print(f"❌ Admin statistics error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing MongoDB Admin System")
    print("=" * 50)
    
    tests = [
        test_mongodb_connection,
        test_admin_data_queries,
        test_admin_relationships,
        test_admin_statistics,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! MongoDB Admin system is ready.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
