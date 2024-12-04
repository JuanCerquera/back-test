from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpRequest
from app.settings import MEDIA_URL


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **kwargs):
        user = self.model(email=email, **kwargs)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **kwargs):
        user = self.model(email=email, is_staff=True, is_superuser=True, **kwargs)
        user.set_password(password)
        user.save()
        return user


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        COMPANY = 'COMPANY', 'Company'
        SUPERUSER = 'SUPERUSER', 'Superuser'

    role = models.CharField(max_length=10, choices=Role.choices, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)

    BASE_ROLE = None
    email = models.EmailField(
        verbose_name="email address",
        max_length=255,
        unique=True,
        blank=True,
        null=True,
    )
    citizen_id = models.IntegerField(unique=True, blank=True, null=True)

    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def save(self, *args, **kwargs):
        if not self.role:
            self.role = self.BASE_ROLE
        super().save(*args, **kwargs)

    def profile_picture_url(self):
        if self.companyprofile.profile_picture:
            return self.companyprofile.profile_picture.url
        else:
            return MEDIA_URL + 'profile_pictures/default.jpg'

    def banner_picture_url(self):
        if self.companyprofile.banner_picture:
            return self.companyprofile.banner_picture.url
        else:
            return MEDIA_URL + 'banner_pictures/default.png'

    def has_google_account_linked(self):
        return self.companyprofile.google_credentials is not None


class CompanyManager(UserManager):
    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(role=User.Role.COMPANY)


class Company(User):
    BASE_ROLE = User.Role.COMPANY
    objects = CompanyManager()
    class Meta:
        proxy = True
    @staticmethod
    def from_request(request: HttpRequest) -> 'Company':
        return Company.objects.get(pk=request.user.pk)
    
    def get_next_step(self):
        possible_steps = [
            ('Crear sede', 'location'),
            ('Crear profesional', 'professional'),
            ('Crear servicio', 'service'),
        ]

        for step_name, model_name in possible_steps:
            queryset = model_name + "_set"
            content = getattr(self, queryset).all()
            if len(content) == 0:
                return {'name': step_name, 'urlname': f'appointments:{model_name}-create'}
            
        return {}


class CompanyProfile(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    profile_picture = models.ImageField(upload_to='profile_pictures/',
                                        null=True, blank=True)
    banner_picture = models.ImageField(upload_to='banner_pictures/',
                                       null=True, blank=True)
    slug = models.CharField(max_length=30, unique=True)
    reviews_link = models.CharField(max_length=200, blank=True, null=True)
    color_1 = models.CharField(max_length=7, default='#F3F4F6')
    color_2 = models.CharField(max_length=7, default='#4F46E5')
    google_credentials = models.JSONField(null=True, blank=True)
    calendar_id = models.CharField(max_length=100, null=True, blank=True)
    social_facebook_url = models.CharField(max_length=200, null=True, blank=True)
    social_instagram_url = models.CharField(max_length=200, null=True, blank=True)
    social_web_url = models.CharField(max_length=200, null=True, blank=True)

    should_input_email = models.BooleanField(default=True)
    should_input_citizen_id = models.BooleanField(default=True)
    should_input_phone = models.BooleanField(default=True)
    subscription_id = models.CharField(max_length=100,null=True, blank=True)
    def get_fields(self):
        fields = {
            'Nombre': self.name,
            'Descripción': self.description,
            'Dirección': self.address,
            'Teléfono': self.phone,
            'Foto de perfil': self.profile_picture,
            'Foto de banner': self.banner_picture,
            'Slug': self.slug,
            'Enlace para reseñas': self.reviews_link,
            'Facebook': self.social_facebook_url,
            'Instagram': self.social_instagram_url,
            'Sitio web': self.social_web_url,
        }

        fields = dict(sorted(fields.items(), key=lambda x:1 if x[1] else 0, reverse=True))
        return fields
    
    def get_complete_fields(self):
        fields = self.get_fields()
        complete_fields = [field for field in fields.values() if field]
        return complete_fields

    def get_completeness(self):
        fields = self.get_fields()

        complete_fields = self.get_complete_fields()

        completeness = int(len(complete_fields) / len(fields) * 100)
        return completeness
    
    def get_input_avoidance_flags(self):
        return {
            'email': not self.should_input_email,
            'citizen_id': not self.should_input_citizen_id,
            'phone': not self.should_input_phone,
        }


class CustomerManager(UserManager):
    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(role=User.Role.CUSTOMER)


class Customer(User):
    BASE_ROLE = User.Role.CUSTOMER
    objects = CustomerManager()
    class Meta:
        proxy = True

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name


class CustomerProfile(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    # profile_picture = models.ImageField(upload_to='profile_pictures/')


# Create company when google auth
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not instance.role:
        instance.role = User.Role.COMPANY
        profile = CompanyProfile(company=instance, slug=instance.email.split('@')[0])
        profile.save()
        instance.save()
