from rest_framework import routers
from django.urls import path

from .views import *

app_name = "appointments"
router = routers.SimpleRouter()
router.register(r'appointments', AppointmentViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'locations', LocationViewSet)
router.register(r'professionals', ProfessionalViewSet)
router.register(r'additional_questions', AdditionalQuestionViewSet)
urlpatterns = [
    path('new_appointment/', NewAppointmentView.as_view(), name='new_appointment'),
    path('process_payment/', ProcessPaymentView.as_view(), name='process_payment'),
    path('plans_info/', GetPlansInfo.as_view(), name='process_payment'),
    path('stats/<int:company_id>/', StatsView.as_view(), name='process_payment'),
    path("get_available_times/<int:professional_id>/<int:service_id>/<str:date>", AvailableTimesView.as_view(), name='available-times'),
]
