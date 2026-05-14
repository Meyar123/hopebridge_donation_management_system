from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator
import re

# Create your models here.

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        validators=[
            MinLengthValidator(2),  # at least 2 characters
            RegexValidator(
                regex=r'^[^\W\d_]+(?: [^\W\d_]+)*$',
                message='Full Name must contain only letters and spaces (no digits or symbols).',
                flags=re.UNICODE
            )
        ]
    )
    phone = models.CharField(max_length=20)
    # Structured address fields
    address_street = models.CharField(max_length=255, blank=True, default='')
    address_city = models.CharField(max_length=100, blank=True, default='')
    address_postal_code = models.CharField(max_length=20, blank=True, default='')
    address_country = models.CharField(max_length=100, blank=True, default='')
    address_apartment = models.CharField(max_length=50, blank=True, default='')
    address_instructions = models.TextField(blank=True, default='')
    # Optionally keep the old address field for backward compatibility
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    objects = CustomUserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'phone']
    def __str__(self):
        return self.email

    is_donor = models.BooleanField(default=False)
    is_recipient = models.BooleanField(default=False)
    is_volunteer = models.BooleanField(default=False)

