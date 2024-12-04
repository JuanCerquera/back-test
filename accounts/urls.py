from django.urls import path
from rest_framework import routers

from .views import *

app_name = "accounts"

from rest_framework_simplejwt import views as jwt_views

router = routers.SimpleRouter()
router.register(r'companies', CompanyViewSet)
router.register(r'customers', CustomerViewSet)
router.register(r'company-profiles', CompanyProfileViewSet)


urlpatterns = [
    path('google_auth_callback/', GoogleAuthCallback.as_view(), name='google-auth-callback'),
    path('google_auth_login/', GoogleAuthLogin.as_view(), name='google-auth-login'),
    path('google_auth_revoke/', GoogleAuthRevoke.as_view(), name='google-auth-revoke'),
    path('change_password/', ChangePasswordView.as_view(), name='change-password'),
    path('register_company/', CompanyRegisterView.as_view(), name='register-company'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('simple_company_profile/<int:company_id>', SimpleCompanyProfileView.as_view(), name='simple-company-profile'),
]
