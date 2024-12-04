# <project>/<app>/management/commands/seed.py
import datetime as dt
import random
import pytz
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.timezone import make_aware

from accounts.models import Company, Customer, CompanyProfile, CustomerProfile
from appointments.models import WeekDay, Service, TimeFrame, Appointment, Location, Professional
import faker

User = get_user_model()


class Command(BaseCommand):
    help = "seed database for testing and development."

    def handle(self, *args, **options):
        self.stdout.write('seeding data...')
        run_seed(self)
        self.stdout.write('done.')


def create_weekdays():
    WeekDay.objects.all().delete()
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekdays = []
    for index, name in enumerate(weekday_names):
        weekday = WeekDay(name=name, id=index)
        weekdays.append(weekday)
    WeekDay.objects.bulk_create(weekdays)


def create_users():
    User.objects.all().delete()
    Company.objects.all().delete()
    Customer.objects.all().delete()
    # Reset index

    # Superuser
    User.objects.create_superuser(
        email='admin@admin.com',
        password='admin',
        role=User.Role.SUPERUSER,
        citizen_id=0
    )
    # Companies
    company1 = Company.objects.create_user(
        email='juan@odontologiasalud.com',
        citizen_id=1,
        first_name='Juan',
        last_name='Perez',
        password='juan',
        phone='3012342654',
    )
    CompanyProfile.objects.create(
        company=company1,
        slug='Odontología Salud',
        name='Clínica Dental Odontología Salud',
        description='Clínica dental especializada en ortodoncia y odontología general.',
        address='Carrera 27 # 45-67',
        phone='301234265',
        profile_picture='profile_pictures/profile_picture1.jpg',
        banner_picture='banner_pictures/banner_picture1.jpg',
        reviews_link='https://maps.app.goo.gl/vT5nr76D5QT2m2Bw8',
        social_facebook_url='https://www.facebook.com/odontologiasalud',
        social_instagram_url='https://www.instagram.com/odontologiasalud',
        social_web_url='https://www.odontologiasalud.com',
    )

    company2 = Company.objects.create_user(
        email='esteban@dentix.com',
        citizen_id=2,
        first_name='Esteban',
        last_name='Gomez',
        password='esteban',
        phone='3012340567',
    )
    CompanyProfile.objects.create(
        company=company2,
        slug='dentix',
        name='Clínica Dental Dentix',
        description='Clínica dental especializada en ortodoncia y odontología general. Contamos con los mejores profesionales y tecnología de punta.',
        address='Calle 45 # 27-67',
        profile_picture='profile_pictures/profile_picture1.jpg',
        banner_picture='banner_pictures/banner_picture1.jpg'
    )
    # Customers
    fake = faker.Faker()
    customers = []
    citizen_ids = []
    password = make_password('password')
    for i in range(300):
        citizen_id = fake.random_int(min=1000000000, max=9999999999)
        while citizen_id in citizen_ids:
            citizen_id = fake.random_int(min=1000000000, max=9999999999)
        citizen_ids.append(citizen_id)
        customer = Customer(
            email=fake.email(),
            citizen_id=citizen_id,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            phone=fake.phone_number(),
            password=password,
            role=User.Role.CUSTOMER
        )
        customers.append(customer)
    Customer.objects.bulk_create(customers)


def create_services():
    Service.objects.all().delete()
    company1, company2 = Company.objects.all()
    services_info = [
        {
            'name': 'Consulta de Ortodoncia',
            'description': 'Consulta de ortodoncia para evaluar el estado de salud bucal y establecer un plan de tratamiento.',
            'duration': dt.timedelta(minutes=30),
            "time_between_appointments": dt.timedelta(minutes=0),
            'company': company1,
            'price': 120_000
        },
        {
            'name': 'Limpieza Dental',
            'description': 'Limpieza dental profesional para eliminar sarro y placa bacteriana.',
            'duration': dt.timedelta(minutes=45),
            "time_between_appointments": dt.timedelta(minutes=15),
            'company': company1,
            'price': 150_000
        },
        {
            'name': 'Blanqueamiento Dental',
            'description': 'Blanqueamiento dental profesional para aclarar el tono de los dientes.',
            'duration': dt.timedelta(minutes=60),
            "time_between_appointments": dt.timedelta(minutes=30),
            'company': company1,
            'price': 250_000
        },
        {
            'name': 'Consulta de Odontología General',
            'description': 'Consulta de odontología general para evaluar el estado de salud bucal y establecer un plan de tratamiento.',
            'duration': dt.timedelta(minutes=30),
            "time_between_appointments": dt.timedelta(minutes=0),
            'company': company1,
            'price': 95_000
        },
        {
            'name': 'Consulta de Ortodoncia',
            'description': 'Consulta de ortodoncia para evaluar el estado de salud bucal y establecer un plan de tratamiento.',
            'duration': dt.timedelta(minutes=30),
            "time_between_appointments": dt.timedelta(minutes=0),
            'company': company2,
            'price': 160_000
        },
        {
            'name': 'Limpieza Dental',
            'description': 'Limpieza dental profesional para eliminar sarro y placa bacteriana.',
            'duration': dt.timedelta(minutes=45),
            "time_between_appointments": dt.timedelta(minutes=15),
            'company': company2,
            'price': 210_000
        },
        {
            'name': 'Blanqueamiento Dental',
            'description': 'Blanqueamiento dental profesional para aclarar el tono de los dientes.',
            'duration': dt.timedelta(minutes=60),
            "time_between_appointments": dt.timedelta(minutes=30),
            'company': company2,
            'price': 350_000
        }
    ]
    for service in services_info:
        service = Service.objects.create(**service)
        for weekday in WeekDay.objects.all():
            start_time = random.randint(7, 8)
            end_time = random.randint(10, 12)
            timeframe1 = TimeFrame.objects.create(
                weekday=weekday,
                start_time=f"{start_time:02d}",
                end_time=f"{end_time:02d}",
                service=service
            )
            start_time = random.randint(13, 15)
            end_time = random.randint(17, 20)
            timeframe2 = TimeFrame.objects.create(
                weekday=weekday,
                start_time=f"{start_time:02d}",
                end_time=f"{end_time:02d}",
                service=service
            )


def create_appointments():
    Appointment.objects.all().delete()
    appointments = []
    for company in Company.objects.all():
        professionals = company.professional_set.all()
        customers = Customer.objects.all()
        for professional in professionals:
            for i in range(300):
                date = timezone.now().date() + dt.timedelta(days=random.randint(-60, 30))
                service = random.choice(professional.services.all())
                start1 = int(service.timeframe_set.first().start_time.hour)
                end1 = int(service.timeframe_set.first().end_time.hour)
                start2 = int(service.timeframe_set.last().start_time.hour)
                end2 = int(service.timeframe_set.last().end_time.hour)
                time = random.choice([1, 2])
                if time == 1:
                    start = start1
                    end = end1
                else:
                    start = start2
                    end = end2
                appointment_datetime = make_aware(
                    dt.datetime.combine(
                        date,
                        dt.time(hour=random.randint(start, end))
                    ),
                    timezone=pytz.timezone('America/Bogota')
                )
                location = professional.location
                appointment = Appointment(
                    customer=random.choice(customers),
                    service=service,
                    start=appointment_datetime,
                    location=location,
                    professional=professional,
                    end=appointment_datetime + service.duration
                )
                appointments.append(appointment)
    Appointment.objects.bulk_create(appointments, ignore_conflicts=True)


def create_locations():
    Location.objects.all().delete()
    company1, company2 = Company.objects.all()
    locations_info = [
        {
            'name': 'Sede Principal',
            'address': 'Carrera 27 # 45-67',
            'phone': '3012342654',
            'company': company1,
            'picture': 'locations/location1.jpg'
        },
        {
            'name': 'Sede Sur',
            'address': 'Carrera 45 # 27-67',
            'phone': '3012340567',
            'company': company1,
            'picture': 'locations/location2.jpg'
        },
        {
            'name': 'Sede Centro',
            'address': 'Carrera 27 # 45-67',
            'phone': '3012342654',
            'company': company1,
            'picture': 'locations/location3.jpg'
        },
        {
            'name': 'Sede Norte',
            'address': 'Calle 45 # 27-67',
            'phone': '3012340567',
            'company': company2,
        },
        {
            'name': 'Sede Occidente',
            'address': 'Calle 45 # 27-67',
            'phone': '3012340567',
            'company': company2
        },
        {
            'name': 'Sede virtual',
            'address': 'Carrera 27 # 45-67',
            'phone': '3012340567',
            'company': company2
        }
    ]
    locations = [Location(**location) for location in locations_info]
    Location.objects.bulk_create(locations)


def create_professionals():
    Professional.objects.all().delete()
    company1, company2 = Company.objects.all()
    locations1 = list(company1.location_set.all())
    locations2 = list(company2.location_set.all())
    professionals_info = [
        {
            'name': 'Dr. Andrés Castro',
            'description': 'Especialista en ortodoncia y odontología general.',
            'company': company1,
            'location': locations1[0],
            'picture': 'professionals/professional1.jpg'
        },
        {
            'name': 'Dr. Juan Carlos Jimenez',
            'description': 'Especialista en ortodoncia y odontología general.',
            'company': company1,
            'location': locations1[1],
            'picture': 'professionals/professional2.jpg'
        },
        {
            'name': 'Dra. Maria Gomez',
            'description': 'Especialista en ortodoncia y odontología general.',
            'company': company1,
            'location': locations1[2],
            'picture': 'professionals/professional3.jpg'
        },
        {
            'name': 'Dr. Esteban Gomez',
            'description': 'Especialista en ortodoncia y odontología general.',
            'company': company2,
            'location': locations2[0],
            'picture': 'professionals/professional4.jpg'
        },
        {
            'name': 'Dra. Laura Perez',
            'description': 'Especialista en ortodoncia y odontología general.',
            'company': company2,
            'location': locations2[1],
            'picture': 'professionals/professional5.jpg'
        },
    ]
    professionals = [Professional(**professional) for professional in professionals_info]
    Professional.objects.bulk_create(professionals)
    for professional in Professional.objects.all():
        services = list(professional.company.service_set.all())
        professional.services.set(random.sample(services, random.randint(1, len(services))))
        professional.save()


def run_seed(self):
    # Clear data from tables
    self.stdout.write("weekdays...")
    create_weekdays()
    self.stdout.write("users...")
    create_users()
    self.stdout.write("locations...")
    create_locations()
    self.stdout.write("services...")
    create_services()
    self.stdout.write("professionals...")
    create_professionals()
    self.stdout.write("appointments...")
    create_appointments()
