from __future__ import absolute_import, unicode_literals
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from celery import shared_task
from appointments.models import Appointment
from app.settings import EMAIL_ADMIN
from django.conf import settings
from django.template.loader import get_template
from django.core.mail import EmailMessage


def send_email(subject, template, context, recipient,
               reply_to=[EMAIL_ADMIN], from_email=EMAIL_ADMIN):
    context['SITE_URL'] = settings.BACKEND_SITE_URL
    message = get_template(template).render(context)
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=from_email,
        to=recipient,
        reply_to=reply_to,
    )
    email.content_subtype = "html"
    return email.send(fail_silently=True)


@shared_task
def new_appointment_notify_customer(instance):
    print("Sending email")
    if not instance["customer_email"]:
        return
    send_email(
        subject=f"¡Nueva reserva confirmada! - {instance['customer_full_name']} | {instance['start']}",
        template="appointments/new_appointment_customer.html",
        context={'appointment': instance},
        recipient=[instance["customer_email"]],
    )


@shared_task
def new_appointment_notify_company(instance):
    print("Sending email")
    send_email(
        subject=f"¡Nueva reserva confirmada! - {instance['customer_full_name']} |  {instance['start']}",
        template="appointments/new_appointment_company.html",
        context={'appointment': instance},
        recipient=[instance["company_email"]],
    )


@shared_task
def new_appointment_add_to_calendar(instance):
    user_credentials = instance["google_credentials"]
    if not user_credentials or not instance["customer_email"]:
        return
    creds = Credentials(
        **user_credentials
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    service = build('calendar', 'v3', credentials=creds)
    event = {
        'summary': f'{instance["customer_full_name"]} - {instance["service_name"]} - {instance["company_name"]}',
        "sendNotifications": True,
        'location': instance["company_address"],
        'description': f'{instance["service_description"]}',
        'start': {
            'dateTime': instance["start_isoformat"],
            'timeZone': 'America/Bogota',
        },
        'end': {
            'dateTime': instance["end_isoformat"],
            'timeZone': 'America/Bogota',
        },
        'attendees': [
            {'email': instance["customer_email"]},
        ],
    }

    if instance["location_is_virtual"]:
        event['conferenceData'] = {
            'createRequest': {
                'requestId': "7qxalsvy0e",
                'conferenceSolutionKey': {
                    'type': 'hangoutsMeet',
                },
            },
        }
    event = service.events().insert(
        calendarId=instance["calendar_id"],
        body=event, conferenceDataVersion=1).execute()

@shared_task
def send_reminder_email(instance):
    send_email(
        subject=f"¡Recuerda tu cita! - {instance['customer_full_name']} | {instance['start']}",
        template="appointments/appointment_reminder.html",
        context={'appointment': instance},
        recipient=[instance["customer_email"]],
    )

@shared_task
def send_review_email(instance):
    send_email(
        subject="¡Calificanos!",
        template="appointments/service_review.html",
        context={'appointment': instance},
        recipient=[instance["customer_email"]],
    )
