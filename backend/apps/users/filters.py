import django_filters
from .models import User


class UserFilter(django_filters.FilterSet):
    role = django_filters.MultipleChoiceFilter(choices=User.Role.choices)
    is_active = django_filters.BooleanFilter()
    is_verified = django_filters.BooleanFilter()
    cohort = django_filters.NumberFilter(field_name='cohort_memberships__cohort')
    programme = django_filters.NumberFilter(field_name='cohort_memberships__cohort__programme')

    class Meta:
        model = User
        fields = ['role', 'is_active', 'is_verified', 'cohort', 'programme']
