import json

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, status, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import CustomerSerializer
from .filters import AppointmentFilterBackend
from .serializers import *
import mercadopago
from datetime import datetime
from .tasks import *
from .templatetags.custom_tags import duration


class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if request.query_params.get('get_all', False) == 'true':
            return None
        return super().paginate_queryset(queryset, request, view=view)


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all().order_by('id')
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, AppointmentFilterBackend]
    search_fields = ['customer__first_name', 'location__name', 'service__name', 'professional__name']
    ordering_fields = ['id', 'location__name', 'service__name', 'professional__name', 'date']


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['company']

    def create_or_update(self, request, update=False):
        if update:
            instance = self.get_object()
            service_serializer = ServiceSerializer(instance, data=request.data)
        else:
            service_serializer = ServiceSerializer(data=request.data)
        valid_service = service_serializer.is_valid()
        service_serializer_errors = service_serializer.errors
        additional_questions_data = json.loads(request.data['additional_questions'])
        additional_questions_serializers = []
        additional_questions_errors = {}
        valid_additional_questions = True
        for question in additional_questions_data:
            serializer = AdditionalQuestionSerializer(data=question)
            additional_questions_serializers.append(serializer)
            if not serializer.is_valid(raise_exception=False):
                additional_questions_errors[question['id']] = serializer.errors
                valid_additional_questions = False
        timeframes_data = json.loads(request.data['timeframes'])
        timeframes_serializers = []
        timeframes_errors = {}
        valid_timeframes = True
        for timeframe in timeframes_data:
            serializer = TimeFrameSerializer(data=timeframe)
            timeframes_serializers.append(serializer)
            if not serializer.is_valid(raise_exception=False):
                timeframes_errors[timeframe['id']] = serializer.errors
                valid_timeframes = False
        if all([valid_service, valid_additional_questions, valid_timeframes]):
            service = service_serializer.save()
            if update:
                service.additionalquestion_set.all().delete()
                for question in additional_questions_serializers:
                    question.save(service=service)
                service.timeframe_set.all().delete()
                for timeframe in timeframes_serializers:
                    timeframe.save(service=service)
            data = {
                'service': service_serializer.data,
                'additional_questions': [question.data for question in additional_questions_serializers],
                'timeframes': [timeframe.data for timeframe in timeframes_serializers]
            }
            if update:
                return Response(data, status=status.HTTP_200_OK)
            else:
                return Response(data, status=status.HTTP_201_CREATED)
        # Relate each additional_question with its errors
        errors = service_serializer_errors
        errors.update({
            'additional_questions': additional_questions_errors,
            'timeframes': timeframes_errors
        })
        print("7")
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        return self.create_or_update(request)

    def update(self, request, *args, **kwargs):
        return self.create_or_update(request, update=True)


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['company']

    def partial_update(self, request, *args, **kwargs):
        location = self.get_object()
        data = request.data.copy()
        if not request.data['picture']:
            data.pop('picture')
        location_serializer = LocationSerializer(location, data=data, partial=True)
        valid_location = location_serializer.is_valid()
        if valid_location:
            location_serializer.save()
            return Response(location_serializer.data, status=status.HTTP_200_OK)
        return Response(location_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    #Overwrite get endpoint
    def list(self, request, *args, **kwargs):
        if request.query_params.get('service', None):
            service = request.query_params.get('service')
            professionals = Professional.objects.filter(services=service)
            locations = Location.objects.filter(professional__in=professionals)
            self.queryset = locations
        return super().list(request, *args, **kwargs)


class ProfessionalViewSet(viewsets.ModelViewSet):
    queryset = Professional.objects.all()
    serializer_class = ProfessionalSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['company', 'services', 'location']

    def create(self, request, *args, **kwargs):
        request.data._mutable = True
        services = request.data.pop('services')
        services = json.loads(services[0])
        professional_serializer = ProfessionalSerializer(data=request.data)
        valid_professional = professional_serializer.is_valid()
        if valid_professional:
            professional = professional_serializer.save()
            professional.services.set(services)
            return Response(professional_serializer.data, status=status.HTTP_201_CREATED)
        return Response(professional_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdditionalQuestionViewSet(viewsets.ModelViewSet):
    queryset = AdditionalQuestion.objects.all()
    serializer_class = AdditionalQuestionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['service']


class NewAppointmentView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Make sure all the required fields are present
        print(request.data)
        required_fields = ['date', 'time', 'service','location','professional','citizen_id', 'email','name', 'last_name', 'email','phone']
        errors = {}
        for field in required_fields:
            if field not in request.data or not request.data[field]:
                errors[field] = ['Este campo es requerido.']

        try:
            start_date = datetime.strptime(request.data['date'], '%Y-%m-%d')
        except ValueError:
            errors['date'] = ['La fecha seleccionada es inválida.']
        except KeyError:
            pass

        try:
            start_time = datetime.strptime(request.data['time'], '%H:%M:%S')
        except ValueError:
            errors['time'] = ['La hora seleccionada es inválida.']
        except KeyError:
            pass

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)


        start = datetime.combine(start_date, start_time.time())
        end = start + Service.objects.get(pk=request.data['service']).duration
        appointment_data = request.data.copy()
        appointment_data['start'] = start
        appointment_data['end'] = end
        appointment_serializer = AppointmentSerializer(data=appointment_data)
        try:
            customer = Customer.objects.get(citizen_id=request.data['citizen_id'])
            customer_serializer = CustomerSerializer(customer, data=request.data)
        except Customer.DoesNotExist:
            try:
                customer = Customer.objects.get(email=request.data['email'])
                customer_serializer = CustomerSerializer(customer, data=request.data)
            except Customer.DoesNotExist:
                customer_serializer = CustomerSerializer(data=request.data)
        except ValueError:
            errors['citizen_id'] = ['El número de cédula debe ser numérico.']
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        valid_appointment = appointment_serializer.is_valid()
        valid_customer = customer_serializer.is_valid()
        if valid_appointment and valid_customer:
            customer = customer_serializer.save()
            appointment = appointment_serializer.save(customer=customer)
            data = {
                'customer': customer_serializer.data,
                'appointment': appointment_serializer.data,
            }
            appointment_data = {
                'customer_email': customer.email,
                "customer_full_name": customer.full_name,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "company_email": appointment.service.company.email,
                "company_phone": appointment.service.company.phone,
                "company_address": appointment.service.company.companyprofile.address,
                "company_name": appointment.service.company.companyprofile.name,
                "customer_phone": appointment.customer.phone,
                "service_duration": duration(appointment.service.duration),
                "service_description": appointment.service.description,
                "service_name": appointment.service.name,
                "date": appointment.start.date().isoformat(),
                "time": appointment.start.time().isoformat(),
                "professional_name": appointment.professional.name,
                "calendar_id": appointment.service.company.companyprofile.calendar_id,
                "start_isoformat": start.isoformat(),
                "end_isoformat": end.isoformat(),
                "google_credentials": appointment.service.company.companyprofile.google_credentials,
                "location_is_virtual": appointment.location.is_virtual,
                "reviews_link": appointment.service.company.companyprofile.reviews_link
            }

            transaction.on_commit(lambda: new_appointment_notify_customer.delay(appointment_data))
            transaction.on_commit(lambda: new_appointment_notify_company.delay(appointment_data))
            transaction.on_commit(lambda: new_appointment_add_to_calendar.delay(appointment_data))

            in_1_minute = timezone.now() + timezone.timedelta(minutes=1)
            in_2_minutes = timezone.now() + timezone.timedelta(minutes=2)
            send_reminder_email.apply_async((appointment_data,), eta=in_1_minute)
            send_review_email.apply_async((appointment_data,), eta=in_2_minutes)

            return Response(data, status=status.HTTP_201_CREATED)
        errors = {}

        errors.update(appointment_serializer.errors)
        errors.update(customer_serializer.errors)

        try:
            Company.objects.get(email=request.data['email'])
            errors['email'] = ['Ya existe una empresa con este correo electrónico.']
        except Company.DoesNotExist:
            pass
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)


class GetPlansInfo(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
        plans = sdk.plan().search({"q":"Denti"})['response']['results']
        plans_data = [
            {
                "id": 0,
                "name": "Denti - Plan emprendedor (Gratis)",
                "price": 0,
            }
        ]
        for plan in plans:
            _id = plan['id']
            price = plan['auto_recurring']['transaction_amount']
            name = f"{plan['reason']} (${price:,.0f})"

            plan_data = {
                "id": _id,
                "name": name,
                "price": price,
            }
            plans_data.append(plan_data)

        return Response(status=status.HTTP_200_OK, data=plans_data)


class ProcessPaymentView(APIView):
    permission_classes = [permissions.AllowAny]
    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

    def post(self, request):
        subscription_data = {
            "card_token_id": request.data['token'],
            "payer_email": request.data['payer']["email"],
            "preapproval_plan_id": request.data["plan_id"]
        }
        subscription = self.sdk.subscription().create(subscription_data)

        return Response(data=subscription, status=subscription['status'])


class StatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, company_id):
        start = timezone.now()
        company = Company.objects.get(pk=company_id)
        stats = {}

        appointments = Appointment.objects.filter(service__company=company)
        services = Service.objects.filter(company=company).values_list('name', flat=True)
        professionals = Professional.objects.filter(company=company).values_list('name', flat=True)
        dates = appointments.values_list('start__date', flat=True).distinct().order_by('start__date')

        # Precompute counts and sums
        appointments_per_service_per_date = appointments.values('start__date', 'service__name').annotate(
            count=Count('id'))
        revenue_per_service_per_date = appointments.values('start__date', 'service__name').annotate(
            revenue=Sum('service__price'))
        appointments_per_professional_per_date = appointments.values('start__date', 'professional__name').annotate(
            count=Count('id'))

        # Appointments by service by date
        stats['appointments_per_service_per_date'] = [["Date"] + list(services)]
        for date in dates:
            row = [date]
            for service in services:
                count = next((item['count'] for item in appointments_per_service_per_date if
                              item['start__date'] == date and item['service__name'] == service), 0)
                row.append(count)
            stats['appointments_per_service_per_date'].append(row)

        # Appointments by service
        stats['appointments_per_service'] = [["Service", "Count"]]
        for service in services:
            count = appointments.filter(service__name=service).count()
            stats['appointments_per_service'].append([service, count])

        # Revenue by service
        stats['revenue_per_service_per_date'] = [["Date"] + list(services)]
        for date in dates:
            row = [date]
            for service in services:
                revenue = next((item['revenue'] for item in revenue_per_service_per_date if
                                item['start__date'] == date and item['service__name'] == service), 1_000_000)
                row.append(revenue)
            stats['revenue_per_service_per_date'].append(row)

        # Appointments by professional
        stats['appointments_per_professional_per_date'] = [["Date"] + list(professionals)]
        for date in dates:
            row = [date]
            for professional in professionals:
                count = next((item['count'] for item in appointments_per_professional_per_date if
                              item['start__date'] == date and item['professional__name'] == professional), 0)
                row.append(count)
            stats['appointments_per_professional_per_date'].append(row)

        # Revenue this month
        stats['revenue_this_month'] = (
                appointments.filter(start__month=timezone.now().month)
                .aggregate(Sum('service__price'))['service__price__sum'] or 1_000_000
        )

        # Appointments this month
        appointments_this_month = appointments.filter(start__month=timezone.now().month)
        stats['appointments_this_month'] = appointments_this_month.count()

        # Customers this month
        # Get appointments from before this month
        appointments_before_this_month = appointments.filter(start__lt=timezone.now().replace(day=1))
        old_customers = []
        for appointment in appointments_before_this_month:
            if appointment.customer not in old_customers:
                old_customers.append(appointment.customer)
        new_customers = []
        for appointment in appointments_this_month:
            if appointment.customer not in old_customers and appointment.customer not in new_customers:
                new_customers.append(appointment.customer)

        stats['new_customers_this_month'] = len(new_customers)
        customers = old_customers + new_customers
        # Totals
        stats['total_revenue'] = appointments.aggregate(Sum('service__price'))['service__price__sum'] or 0
        stats['total_appointments'] = appointments.count()
        stats['total_customers'] = len(customers)

        end = timezone.now()
        delta_ms = (end - start).total_seconds() * 1000
        print(f"Execution time: {delta_ms}")
        return Response(stats)


class AvailableTimesView(APIView):
    def get(self, request, professional_id, service_id, date):
        professional = Professional.objects.get(pk=professional_id)
        service = Service.objects.get(pk=service_id)
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        busy_times = professional.get_busy_times(date_obj)
        weekday = date_obj.weekday()
        timeframes = service.timeframe_set.filter(weekday__id=weekday)
        available_times = []
        # If date is today or less, return empty list
        if date_obj <= timezone.now().date():
            return Response(available_times)
        print(f"Finding available times for {professional} on {date} with {service}")
        print(f"Busy times: {busy_times}")
        for timeframe in timeframes:
            print(f"Checking timeframe: {timeframe}")
            current_time = timeframe.start_time
            while current_time < timeframe.end_time:
                print(f"Current time: {current_time}")
                valid_time = True
                for busy_time_start, busy_time_end in busy_times:
                    if busy_time_start <= current_time < busy_time_end:
                        valid_time = False
                        current_time = (dt.datetime.combine(dt.date(1, 1, 1), current_time) + service.duration + service.time_between_appointments).time()
                        print(f"Busy time: {busy_time_start} - {busy_time_end}")
                        break
                if valid_time:
                    print(f"Valid time, appending...")
                    available_times.append(current_time)
                    current_time = (dt.datetime.combine(dt.date(1, 1, 1), current_time) + service.duration + service.time_between_appointments).time()
        output = [{"id": name, "name": name} for idx,name in enumerate(available_times)]
        return Response(output)
