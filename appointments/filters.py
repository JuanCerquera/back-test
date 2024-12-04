from rest_framework import filters

class AppointmentFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        date_gt = request.query_params.get("date_gt", None)
        date_lt = request.query_params.get("date_lt", None)
        company = request.query_params.get("company", None)
        if date_gt:
            queryset = queryset.filter(start__gt=date_gt)
        if date_lt:
            queryset = queryset.filter(end__lt=date_lt)
        if company:
            queryset = queryset.filter(service__company=company)
        return queryset