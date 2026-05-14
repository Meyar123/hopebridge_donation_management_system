from mongoengine import Document, EmbeddedDocument, fields
from datetime import datetime
import uuid
from mongoengine import BooleanField, StringField, DateTimeField


class Address(EmbeddedDocument):
    street = fields.StringField(max_length=255, required=True)
    city = fields.StringField(max_length=100, required=True)
    postal_code = fields.StringField(max_length=20, required=True)
    country = fields.StringField(max_length=100, required=True)
    apartment = fields.StringField(max_length=50, required=True)
    instructions = fields.StringField()
    latitude = fields.FloatField()
    longitude = fields.FloatField()

class User(Document):
    email = fields.EmailField(unique=True, required=True)
    name = fields.StringField(max_length=100, required=True)
    phone = fields.StringField(max_length=20, required=True)
    address = fields.EmbeddedDocumentField(Address)
    is_active = fields.BooleanField(default=True)
    is_staff = fields.BooleanField(default=False)
    is_superuser = fields.BooleanField(default=False)
    date_joined = fields.DateTimeField(default=datetime.utcnow)
    last_login = fields.DateTimeField()
    password_hash = fields.StringField(required=True)
    
    meta = {
        'collection': 'users',
        'indexes': ['email', 'name']
    }

    email_verified = BooleanField(default=False)
    verification_code = StringField()
    verification_code_created_at = DateTimeField()

    def generate_verification_code(self):
        import random
        from datetime import datetime
        code = str(random.randint(100000, 999999))
        self.verification_code = code
        self.verification_code_created_at = datetime.utcnow()
        self.save()
        return code

    def is_verification_code_valid(self, code, expiry_minutes=10):
        if self.verification_code != code:
            return False
        if not self.verification_code_created_at:
            return False
        from datetime import datetime, timedelta
        return datetime.utcnow() - self.verification_code_created_at < timedelta(minutes=expiry_minutes)

class Donor(Document):
    user_id = fields.ObjectIdField(required=True)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'donors',
        'indexes': ['user_id']
    }

class Recipient(Document):
    user_id = fields.ObjectIdField(required=True)
    shipping_address = fields.StringField(required=True)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'recipients',
        'indexes': ['user_id']
    }

class Volunteer(Document):
    user_id = fields.ObjectIdField(required=True)
    preferences = fields.StringField()
    limitations = fields.StringField()
    created_at = fields.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'volunteers',
        'indexes': ['user_id']
    }

class Item(Document):
    name = fields.StringField(max_length=100, required=True)
    description = fields.StringField(required=True)
    category = fields.StringField(max_length=50, required=True)
    condition = fields.StringField(max_length=50, required=True)
    image_url = fields.StringField()  # Store image path/URL
    donor_id = fields.ObjectIdField(required=True)
    latitude = fields.FloatField()
    longitude = fields.FloatField()
    item_location = fields.StringField(max_length=255)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'items',
        'indexes': ['donor_id', 'category', 'name']
    }

class Donation(Document):
    item_id = fields.ObjectIdField(required=True)
    donor_id = fields.ObjectIdField(required=True)
    recipient_id = fields.ObjectIdField()
    created_at = fields.DateTimeField(default=datetime.utcnow)
    status = fields.StringField(max_length=20, default='available')
    
    meta = {
        'collection': 'donations',
        'indexes': ['item_id', 'donor_id', 'recipient_id', 'status']
    }

class Activity(Document):
    title = fields.StringField(max_length=200, required=True)
    description = fields.StringField(required=True)
    category = fields.StringField(max_length=50, required=True)
    location = fields.StringField(max_length=255, required=True)
    latitude = fields.FloatField()
    longitude = fields.FloatField()
    image_url = fields.StringField()
    volunteer_id = fields.ObjectIdField(required=True)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    activity_date = fields.DateTimeField(required=True)
    duration_hours = fields.IntField(default=1)
    max_participants = fields.IntField(default=1)
    requirements = fields.StringField()
    contact_info = fields.StringField(max_length=255)
    status = fields.StringField(max_length=20, default='available')
    
    meta = {
        'collection': 'activities',
        'indexes': ['volunteer_id', 'category', 'activity_date']
    }

class VolunteerActivity(Document):
    activity_id = fields.ObjectIdField(required=True)
    volunteer_id = fields.ObjectIdField(required=True)
    participant_id = fields.ObjectIdField()
    created_at = fields.DateTimeField(default=datetime.utcnow)
    status = fields.StringField(max_length=20, default='available')
    notes = fields.StringField()
    
    meta = {
        'collection': 'volunteer_activities',
        'indexes': ['activity_id', 'volunteer_id', 'participant_id', 'status']
    }

