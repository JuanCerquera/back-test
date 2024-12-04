import datetime as dt

import pytz
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from accounts.models import Company, Customer


class NonDeletableManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class NonDeletableModel(models.Model):
    active = models.BooleanField(default=True)
    objects = NonDeletableManager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        # Search for active relationships
        self.active = False
        self.save()

    def save(self, *args, **kwargs):
        if not self.id:
            self.active = True
        super().save(*args, **kwargs)


class WeekDay(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self) -> str:
        return self.name


class Service(NonDeletableModel):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    duration = models.DurationField(validators=[MinValueValidator(dt.timedelta(minutes=15))])
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    time_between_appointments = models.DurationField()
    description = models.TextField(blank=True)
    professional_is_selectable = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name

    def get_timeframes(self) -> dict:
        timeframes = {}
        weekdays = WeekDay.objects.order_by('index')
        for weekday in weekdays:
            specific_timeframes = self.timeframe_set.filter(weekday=weekday, is_enabled=True)
            if len(specific_timeframes) > 0:
                timeframes[weekday.name] = specific_timeframes

        return timeframes

    def get_appointments(self, date: dt.date) -> list:
        return self.appointment_set.filter(start__date=date)


class Appointment(NonDeletableModel):
    location = models.ForeignKey('Location', on_delete=models.RESTRICT)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    professional = models.ForeignKey('Professional', on_delete=models.RESTRICT)
    start = models.DateTimeField()
    end = models.DateTimeField()
    is_complete = models.BooleanField(default=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    observations = models.TextField(blank=True)
    reminder_sent = models.BooleanField(default=False)
    review_email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('service', 'start')

    def __str__(self) -> str:
        return f'{self.customer}: {self.service} From {self.start} to {self.end}'


"""
def schedule_reminder_email(instance: Appointment):
    desired_time = dt.datetime.combine(instance.date, instance.time) - dt.timedelta(days=1)
    clocked, _ = ClockedSchedule.objects.get_or_create(clocked_time=desired_time)
    PeriodicTask.objects.create(
        clocked=clocked,
        name=f"reminder_{instance.id}",
        task="appointments.tasks.send_reminder_email",
        one_off=True,
        args=json.dumps([instance.id]),
    )
"""
"""
def schedule_review_email(instance: Appointment):
    if not instance.service.company.companyprofile.reviews_link:
        return

    desired_time = instance.end_datetime() + dt.timedelta(hours=1)
    clocked, _ = ClockedSchedule.objects.get_or_create(clocked_time=desired_time)
    PeriodicTask.objects.create(
        clocked=clocked,
        name=f"review_{instance.id}",
        task="appointments.tasks.send_review_email",
        one_off=True,
        args=json.dumps([instance.id]),
    )
"""


class TimeFrame(models.Model):
    start_time = models.TimeField(default="07:00")
    end_time = models.TimeField(default="17:00")
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    weekday = models.ForeignKey(WeekDay, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.weekday}: {self.start_time} - {self.end_time}'

    def get_times(self) -> list:
        times: list = []

        current_time = self.start_time
        while current_time < self.end_time:
            times.append(current_time)
            duration = self.service.duration
            gap_time = self.service.time_between_appointments
            # Add duration to current time
            current_time = dt.datetime.combine(dt.date(1, 1, 1), current_time) + duration + gap_time
            current_time = current_time.time()
        return times


class Location(NonDeletableModel):
    name = models.CharField(max_length=100)
    is_virtual = models.BooleanField(default=False)
    address = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    picture = models.ImageField(upload_to='locations', blank=True, null=True)

    def __str__(self) -> str:
        return self.name


class Professional(NonDeletableModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    picture = models.ImageField(upload_to='professionals', blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.RESTRICT)
    services = models.ManyToManyField(Service, blank=True, related_name="professionals")

    def __str__(self) -> str:
        return self.name

    def get_busy_times(self, date: dt.date) -> list:
        appointments = self.appointment_set.filter(start__date=date)
        print(date)
        print(appointments)
        #Get times in current timezone
        timezone = pytz.timezone(settings.TIME_ZONE)
        busy_times = [
            (appointment.start.astimezone(timezone).time(), appointment.end.astimezone(timezone).time())
            for appointment in appointments
        ]
        return busy_times


class AdditionalQuestion(NonDeletableModel):
    text = models.CharField(max_length=100)
    # type = models.CharField(max_length=20, choices=[
    #     ('text', 'Text'),
    #     ('number', 'Number'),
    #     ("select", "Select"),
    #     ("checkbox", "Checkbox")
    # ])
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.question


class Answer(models.Model):
    question = models.ForeignKey(AdditionalQuestion, on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    answer = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.answer

class AdditionalQuestionResponse(models.Model):
    appointment = models.ForeignKey(Appointment, related_name="responses", on_delete=models.CASCADE)
    question = models.ForeignKey(AdditionalQuestion, on_delete=models.CASCADE)
    response = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.response
