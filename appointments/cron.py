def setup():
    import django
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    django.setup()


def append_y_to_company():
    # import django
    # import os
    # from accounts.models import Company

    # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    # django.setup()
    # print("Yes")
    # company = Company.objects.get(pk=2)
    # company.first_name += "y"
    # company.save()
    print("Hola")
    

    # return send_email(
    #     subject='Prueba',
    #     template='appointments/emails/appointment_reminder.html',
    #     context={'appointment': Appointment()},
    #     recipient="me.lm2207@gmail.com",
    # )

    # print("Hola mundo")