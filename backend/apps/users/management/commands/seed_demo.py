"""
Management command to seed demo data for development.
Usage: python manage.py seed_demo
"""
from django.core.management.base import BaseCommand
from apps.users.models import User, MentoringMatch
from apps.cohorts.models import Programme, Cohort, CohortMembership
from apps.moderation.models import FlaggedTerm


class Command(BaseCommand):
    help = 'Seed demo data'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo data…')

        # Admin
        admin, _ = User.objects.get_or_create(
            email='admin@spt.org',
            defaults={'username': 'admin', 'first_name': 'Platform', 'last_name': 'Admin',
                      'role': User.Role.ADMIN, 'is_staff': True, 'is_superuser': True}
        )
        admin.set_password('admin123')
        admin.save()

        # Programme & Cohort
        prog, _ = Programme.objects.get_or_create(name='Engineering Scholars Programme', defaults={'is_active': True})
        cohort, _ = Cohort.objects.get_or_create(programme=prog, year=2024, defaults={'name': '2024 Cohort', 'is_active': True})

        # Mentors
        for i in range(1, 4):
            mentor, _ = User.objects.get_or_create(
                email=f'mentor{i}@example.com',
                defaults={
                    'username': f'mentor{i}', 'first_name': f'Mentor', 'last_name': f'{i}',
                    'role': User.Role.MENTOR, 'engineering_discipline': 'Civil Engineering',
                    'is_verified': True,
                }
            )
            mentor.set_password('password123')
            mentor.save()
            CohortMembership.objects.get_or_create(cohort=cohort, user=mentor)

        # Scholars
        for i in range(1, 7):
            scholar, _ = User.objects.get_or_create(
                email=f'scholar{i}@example.com',
                defaults={
                    'username': f'scholar{i}', 'first_name': f'Scholar', 'last_name': f'{i}',
                    'role': User.Role.SCHOLAR, 'engineering_discipline': 'Mechanical Engineering',
                }
            )
            scholar.set_password('password123')
            scholar.save()
            CohortMembership.objects.get_or_create(cohort=cohort, user=scholar)

            # Match scholars to mentors (2 scholars per mentor)
            mentor_num = ((i - 1) // 2) + 1
            mentor = User.objects.filter(email=f'mentor{mentor_num}@example.com').first()
            if mentor:
                MentoringMatch.objects.get_or_create(
                    scholar=scholar, mentor=mentor,
                    defaults={'matched_by': admin, 'is_active': True}
                )

        # Example flagged term
        FlaggedTerm.objects.get_or_create(
            term='contact me outside',
            defaults={'severity': 2, 'notes': 'Safeguarding – off-platform contact attempt'}
        )

        self.stdout.write(self.style.SUCCESS('Demo data created successfully.'))
        self.stdout.write('Admin login: admin@spt.org / admin123')
        self.stdout.write('Mentor login: mentor1@example.com / password123')
        self.stdout.write('Scholar login: scholar1@example.com / password123')
