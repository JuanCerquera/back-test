import mercadopago
from django.contrib.auth.hashers import make_password
from google.auth.exceptions import RefreshError
from google.auth.transport import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from app import settings
from .models import *


class CompanySerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    class Meta:
        model = Company
        fields = [
            "id", "password", "first_name", "last_name", "phone", "email", "citizen_id"
        ]


class CompanyProfileSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False)
    company = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )
    subscription = serializers.SerializerMethodField()
    has_google_account_linked = serializers.SerializerMethodField()
    google_account_context = serializers.SerializerMethodField()

    def get_subscription(self, obj):
        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
        subscription_id = obj.subscription_id

        if not subscription_id:
            return None
        subscription = sdk.subscription().get(obj.subscription_id)['response']
        print(subscription)
        return {
            "status": subscription['status'],
            "reason": subscription['reason'],
            "date_created": subscription['date_created'],
            "next_payment_date": subscription['next_payment_date'],
        }

    def get_has_google_account_linked(self, obj):
        return obj.google_credentials != None

    def get_google_account_context(self, obj):
        user_credentials = obj.google_credentials
        if user_credentials:
            try:
                creds = Credentials(
                    **user_credentials
                )
                if creds.expired and creds.refresh_token:
                        creds.refresh(Request())

                service = build('people', 'v1', credentials=creds)
                profile = service.people().get(resourceName='people/me', personFields='names,emailAddresses,photos'
                                                ).execute()
                name = profile['names'][0]['displayName']
                photo = profile['photos'][0]['url']
                email = profile['emailAddresses'][0]['value']

                context = {
                    'name': name,
                    'picture': photo,
                    'email': email,
                }
                return context
            except RefreshError as e:
                obj.google_credentials = None
                obj.save()
                return None
        else:
            return None

    class Meta:
        model = CompanyProfile
        fields = "__all__"


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class CustomerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        exclude = ["is_staff", "is_superuser", "is_active", "date_joined",
                   "last_login", "groups", "user_permissions", "password"]

    def create(self, validated_data):
        print("Validating..")
        # Find if existing customer with citizen_id
        customer = Customer.objects.filter(citizen_id=validated_data['citizen_id']).first()
        if not customer:
            # Find if existing customer with email
            customer = Customer.objects.filter(email=validated_data['email']).first()
        #Update fields
        if customer:
            for key, value in validated_data.items():
                setattr(customer, key, value)
            customer.save()
            return customer
        # Create new customer
        return super().create(validated_data)

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data.update({'id': self.user.id})
        return data
