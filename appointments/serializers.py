import datetime

from rest_framework import serializers

from accounts.serializers import CustomerSerializer
from appointments.models import *


class AppointmentSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )
    customer = CustomerSerializer(read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    professional_name = serializers.CharField(source='professional.name', read_only=True)
    title = serializers.SerializerMethodField()
    company = serializers.IntegerField(source='service.company.id', read_only=True)

    def get_title(self, obj):
        return f"{obj.service.name} - {obj.customer.full_name}"

    class Meta:
        model = Appointment
        fields = '__all__'
        # extra fields


class ServiceSerializer(serializers.ModelSerializer):
    timeframes = serializers.SerializerMethodField()
    additional_questions = serializers.SerializerMethodField()

    def get_additional_questions(self, obj):
        return AdditionalQuestionSerializer(obj.additionalquestion_set.all(), many=True).data
    def get_timeframes(self, obj):
        return TimeFrameSerializer(obj.timeframe_set.all(), many=True).data

    class Meta:
        model = Service
        fields = [
            "id", "name", "description", "duration", "price",
            "company", "timeframes", "time_between_appointments",
            "additional_questions"
        ]


class AdditionalQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionalQuestion
        exclude = ['service']


class AdditionalQuestionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionalQuestionResponse
        exclude = ['appointment']


class TimeFrameSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeFrame
        exclude = ['service']

    def validate(self, data):
        if data['end_time'] < data['start_time']:
            raise serializers.ValidationError('La hora de finalización debe ser mayor a la hora de inicio')
        return data


class LocationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Location
        fields = '__all__'

    def validate(self, data):
        if 'is_virtual' not in data and not data['address']:
            raise serializers.ValidationError({
                'address': 'La dirección es requerida para una ubicación no virtual',
            })
        return data

class ProfessionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Professional
        fields = "__all__"
