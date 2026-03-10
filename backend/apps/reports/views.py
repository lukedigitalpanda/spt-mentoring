"""
Reporting module – provides mass reporting on all scholar/mentor data,
messaging activity, contact frequency, and cohort progress.
All reports are admin-only and support CSV export.
"""
import csv
from django.http import HttpResponse
from django.db.models import Count, Max, Min, Q, F
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from datetime import timedelta


class ScholarMentorContactReport(APIView):
    """
    Report showing last contact dates between Scholar/Mentor pairs.
    Flags pairs with no contact beyond the configured threshold.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.users.models import MentoringMatch
        from apps.messaging.models import Message

        days_threshold = int(request.query_params.get('days', 14))
        threshold = timezone.now() - timedelta(days=days_threshold)
        export_csv = request.query_params.get('format') == 'csv'

        matches = MentoringMatch.objects.filter(is_active=True).select_related(
            'scholar', 'mentor'
        )

        rows = []
        for match in matches:
            pair_ids = [match.scholar_id, match.mentor_id]

            # Messages from scholar to mentor
            scholar_last = Message.objects.filter(
                sender=match.scholar,
                conversation__participants=match.mentor,
                status=Message.Status.DELIVERED,
            ).aggregate(last=Max('sent_at'), total=Count('id'))

            # Messages from mentor to scholar
            mentor_last = Message.objects.filter(
                sender=match.mentor,
                conversation__participants=match.scholar,
                status=Message.Status.DELIVERED,
            ).aggregate(last=Max('sent_at'), total=Count('id'))

            needs_chase = (
                scholar_last['last'] is None or scholar_last['last'] < threshold or
                mentor_last['last'] is None or mentor_last['last'] < threshold
            )

            rows.append({
                'scholar_id': match.scholar_id,
                'scholar_name': match.scholar.full_name,
                'scholar_email': match.scholar.email,
                'mentor_id': match.mentor_id,
                'mentor_name': match.mentor.full_name,
                'mentor_email': match.mentor.email,
                'scholar_last_message': scholar_last['last'],
                'scholar_total_messages': scholar_last['total'],
                'mentor_last_message': mentor_last['last'],
                'mentor_total_messages': mentor_last['total'],
                'needs_chase': needs_chase,
                'matched_on': match.matched_on,
            })

        if export_csv:
            return self._csv_response(rows)
        return Response({'count': len(rows), 'threshold_days': days_threshold, 'results': rows})

    def _csv_response(self, rows):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="scholar_mentor_contact_report.csv"'
        if not rows:
            return response
        writer = csv.DictWriter(response, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        return response


class SponsorUpdateReport(APIView):
    """Report on how often scholars are sending updates to their sponsors."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.users.models import User
        from apps.messaging.models import Message

        export_csv = request.query_params.get('format') == 'csv'
        rows = []

        scholars = User.objects.filter(
            role=User.Role.SCHOLAR, is_active=True
        ).select_related('scholar_profile__sponsor', 'scholar_profile__sponsor__sponsor_profile')

        for scholar in scholars:
            profile = getattr(scholar, 'scholar_profile', None)
            sponsor = getattr(profile, 'sponsor', None) if profile else None
            sponsor_profile = getattr(sponsor, 'sponsor_profile', None) if sponsor else None
            freq = getattr(sponsor_profile, 'update_frequency_days', 90) if sponsor_profile else 90

            last_update = Message.objects.filter(
                sender=scholar,
                conversation__conversation_type='sponsor_update',
                status=Message.Status.DELIVERED,
            ).aggregate(last=Max('sent_at'), total=Count('id'))

            days_since = None
            overdue = False
            if last_update['last']:
                days_since = (timezone.now() - last_update['last']).days
                overdue = days_since > freq
            else:
                overdue = True

            rows.append({
                'scholar_id': scholar.pk,
                'scholar_name': scholar.full_name,
                'scholar_email': scholar.email,
                'sponsor_name': sponsor.full_name if sponsor else '',
                'sponsor_email': sponsor.email if sponsor else '',
                'expected_frequency_days': freq,
                'last_update_sent': last_update['last'],
                'days_since_update': days_since,
                'total_updates_sent': last_update['total'],
                'is_overdue': overdue,
            })

        if export_csv:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="sponsor_update_report.csv"'
            if rows:
                writer = csv.DictWriter(response, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            return response

        return Response({'count': len(rows), 'results': rows})


class UserDataReport(APIView):
    """Mass report of all scholar/mentor data."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.users.models import User
        from apps.users.exports import UserCSVExport

        role = request.query_params.get('role')
        cohort_id = request.query_params.get('cohort')
        programme_id = request.query_params.get('programme')

        qs = User.objects.filter(is_active=True).select_related(
            'mentor_profile', 'scholar_profile', 'sponsor_profile'
        )
        if role:
            qs = qs.filter(role=role)
        if cohort_id:
            qs = qs.filter(cohort_memberships__cohort_id=cohort_id)
        if programme_id:
            qs = qs.filter(cohort_memberships__cohort__programme_id=programme_id)

        if request.query_params.get('format') == 'csv':
            return UserCSVExport.export(qs)

        from apps.users.serializers import UserListSerializer
        return Response({
            'count': qs.count(),
            'results': UserListSerializer(qs, many=True).data,
        })


class CohortProgressReport(APIView):
    """Overview of a cohort's engagement metrics."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.cohorts.models import Cohort, CohortMembership
        from apps.messaging.models import Message

        cohort_id = request.query_params.get('cohort')
        if not cohort_id:
            from apps.cohorts.serializers import CohortSerializer
            cohorts = Cohort.objects.filter(is_active=True)
            return Response({'cohorts': CohortSerializer(cohorts, many=True).data})

        try:
            cohort = Cohort.objects.get(pk=cohort_id)
        except Cohort.DoesNotExist:
            return Response({'error': 'Cohort not found'}, status=404)

        memberships = CohortMembership.objects.filter(cohort=cohort).select_related('user')
        members = [m.user for m in memberships]
        member_ids = [u.pk for u in members]

        total_messages = Message.objects.filter(
            sender__in=member_ids, status=Message.Status.DELIVERED
        ).count()

        return Response({
            'cohort': cohort.name,
            'programme': cohort.programme.name,
            'year': cohort.year,
            'total_members': len(members),
            'total_messages_sent': total_messages,
            'members': [
                {'id': u.pk, 'name': u.full_name, 'role': u.role, 'email': u.email}
                for u in members
            ],
        })


class ModerationReport(APIView):
    """Report on moderation activity."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.moderation.models import ModerationLog
        from django.db.models import Count

        summary = ModerationLog.objects.values('action').annotate(count=Count('id')).order_by()
        pending_flagged = 0
        try:
            from apps.messaging.models import Message
            pending_flagged = Message.objects.filter(status=Message.Status.FLAGGED).count()
        except Exception:
            pass

        return Response({
            'summary_by_action': list(summary),
            'pending_flagged_messages': pending_flagged,
        })
