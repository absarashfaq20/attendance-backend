import django_filters
from .models import Attendance


class AttendanceFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='date')
    student = django_filters.NumberFilter(field_name='student')
    month = django_filters.NumberFilter(field_name='date', lookup_expr='month')
    year = django_filters.NumberFilter(field_name='date', lookup_expr='year')

    class Meta:
        model = Attendance
        fields = ['date', 'student', 'month', 'year']
