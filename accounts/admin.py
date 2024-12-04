from django.contrib import admin

# Register your models here.
from .models import Company, Customer, CompanyProfile

admin.site.register(Customer)


class CompanyProfileInline(admin.StackedInline):
    model = CompanyProfile
    can_delete = False
    verbose_name_plural = 'Company Profile'


# Custom Company admin page
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    # Include company default fields
    inlines = [
        CompanyProfileInline,
    ]
