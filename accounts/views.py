import json

import google_auth_oauthlib
import requests
from django.contrib import messages
from django.contrib.auth import authenticate, logout, login
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from oauthlib.oauth2 import AccessDeniedError
from rest_framework import status, viewsets, permissions
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from app.settings import CLIENT_CONFIG, GOOGLE_SCOPES, BACKEND_SITE_URL, FRONTEND_SITE_URL
from .models import *
from .serializers import *


class GoogleAuthCallback(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            CLIENT_CONFIG,
            scopes=GOOGLE_SCOPES
        )
        flow.redirect_uri = f"{FRONTEND_SITE_URL}/citas/"
        authorization_response = request.build_absolute_uri().replace('http://', 'https://')

        try:
            flow.fetch_token(authorization_response=authorization_response)
        except AccessDeniedError as e:
            messages.error(request, 'Ha ocurrido un error al intentar conectar con Google')
            return redirect(reverse_lazy("appointments:appointment-list"))

        credentials = {'token': flow.credentials.token,
                       'refresh_token': flow.credentials.refresh_token,
                       'token_uri': flow.credentials.token_uri,
                       'client_id': flow.credentials.client_id,
                       'client_secret': flow.credentials.client_secret,
                       'scopes': flow.credentials.scopes}
        company_id = request.user.id
        company = Company.objects.get(pk=company_id)
        company.companyprofile.google_credentials = credentials
        try:
            service = build('calendar', 'v3', credentials=flow.credentials)
            # Create a new calendar
            calendar = {
                'summary': 'Citas de Agenda Ya',
                'timeZone': 'America/Bogota'
            }
            created_calendar = service.calendars().insert(body=calendar).execute()
            company.companyprofile.calendar_id = created_calendar['id']
            company.companyprofile.save()
            messages.success(request, 'Conexión con Google exitosa')
        except Exception as e:
            messages.error(request,
                           'Ha ocurrido un error al intentar conectar con Google Calendar, recuerda autorizar todos los permisos solicitados')
        return redirect(FRONTEND_SITE_URL)


class GoogleAuthRevoke(APIView):
    def post(self, request):
        company = Company.objects.get(pk=request.user.id)
        credentials = Credentials(
            **company.companyprofile.google_credentials
        )
        revoke = requests.post('https://oauth2.googleapis.com/revoke',
                               params={'token': credentials.token},
                               headers={'content-type': 'application/x-www-form-urlencoded'})

        company.companyprofile.google_credentials = None
        company.companyprofile.calendar_id = None
        company.companyprofile.save()
        return Response(status=status.HTTP_200_OK)


class GoogleAuthLogin(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Save user in session
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            CLIENT_CONFIG,
            scopes=GOOGLE_SCOPES,
        )
        flow.redirect_uri = f"{FRONTEND_SITE_URL}/citas/"
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
        )
        return redirect(authorization_url)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(data={"error": e.args[0]}, status=status.HTTP_400_BAD_REQUEST)
            return Response(status=status.HTTP_400_BAD_REQUEST)


class CompanyViewSet(ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]


class CompanyProfileViewSet(ModelViewSet):
    queryset = CompanyProfile.objects.all()
    serializer_class = CompanyProfileSerializer
    permission_classes = [permissions.AllowAny] #todo: change to IsAuthenticated and use SimpleCompanyProfileView instead
    filterset_fields = ['company', "slug"]

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChangePasswordView(APIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        user = request.user
        if user.check_password(old_password):
            user.set_password(new_password)
            user.save()
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "Contraseña incorrecta"})


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        user = authenticate(request, username=request.data['email'], password=request.data['password'])
        request.session['user_id'] = user.id
        return super().post(request, *args, **kwargs)


class CompanyRegisterView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        data = request.data
        company_serializer = CompanySerializer(data=data)
        company_profile_serializer = CompanyProfileSerializer(data=data)
        valid_company = company_serializer.is_valid()
        valid_company_profile = company_profile_serializer.is_valid()
        if valid_company and valid_company_profile:
            first_name = data['first_name']
            last_name = data['last_name']
            valid_slug = False
            i = 0
            slug = None
            while not valid_slug:
                i += 1
                try:
                    slug = f"{first_name}-{last_name}-{i}"
                    CompanyProfile.objects.get(slug=slug)
                except CompanyProfile.DoesNotExist:
                    valid_slug = True
            company = company_serializer.save()
            company_profile = company_profile_serializer.save(company=company, slug=slug)
            return Response(status=status.HTTP_201_CREATED)
        errors = {}
        errors.update(company_serializer.errors)
        errors.update(company_profile_serializer.errors)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

class SimpleCompanyProfileView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, company_id):
        company = Company.objects.get(pk=company_id)
        company_profile = CompanyProfile.objects.get(company=company)
        return Response(CompanyProfileSerializer(company_profile).data, status=status.HTTP_200_OK)