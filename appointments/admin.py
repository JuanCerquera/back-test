from django.contrib import admin

# Register your models here.
from .models import Appointment, TimeFrame, Service, WeekDay, AdditionalQuestion

admin.site.register(Appointment)
admin.site.register(TimeFrame)
admin.site.register(Service)
admin.site.register(WeekDay)
admin.site.register(AdditionalQuestion)

