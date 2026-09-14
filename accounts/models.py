from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        # Use email as username if not provided
        if 'username' not in extra_fields or not extra_fields['username']:
            extra_fields['username'] = email.split('@')[0]
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('merchant_owner', 'Merchant Owner'),
        ('kitchen_staff', 'Kitchen Staff'),
        ('delivery_rider', 'Delivery Rider'),
    )
    objects = UserManager()
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='customer')

    AUTH_PROVIDER_CHOICES = (
        ('email', 'Email'),
        ('google', 'Google'),
        ('apple', 'Apple'),
    )
    auth_provider = models.CharField(max_length=50, choices=AUTH_PROVIDER_CHOICES, default='email')
    social_id = models.CharField(max_length=255, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    # Fix related_name clashes with auth.User during migration
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='custom_user_set',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='user',
    )
