"""
Django admin reporting pages.

Registers custom admin views for:
  - Mentoring Contact Report  (scholar/mentor pairs, message counts, last contact dates)
"""
import csv
from datetime import timedelta

from django.contrib import admin
from django.http import HttpResponse
from django.db.models import Count, Max
from django.template.response import TemplateResponse
from django.utils import timezone

from .models import MentoringReport


@admin.register(MentoringReport)
class MentoringReportAdmin(admin.ModelAdmin):
    # This page is a read-only report — no CRUD
    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    def get_urls(self):
        from django.urls import path
        return [
            path(
                '',
                self.admin_site.admin_view(self.report_view),
                name='reports_mentoringreport_changelist',
            ),
            path(
                'export/',
                self.admin_site.admin_view(self.export_csv),
                name='reports_mentoringreport_export',
            ),
        ]

    # ── Main report view ──────────────────────────────────────────────────────

    def report_view(self, request):
        from apps.users.models import MentoringMatch, User
        from apps.cohorts.models import Cohort

        days       = int(request.GET.get('days', 14))
        cohort_id  = request.GET.get('cohort', '')
        inactive   = request.GET.get('inactive', '') == '1'
        threshold  = timezone.now() - timedelta(days=days)

        matches = self._base_qs(inactive, cohort_id)
        rows    = self._build_rows(matches, threshold)

        total        = len(rows)
        needs_chase  = sum(1 for r in rows if r['needs_chase'])
        no_contact   = sum(1 for r in rows if r['scholar_total'] == 0 and r['mentor_total'] == 0)
        active_pairs = sum(1 for r in rows if r['match_active'])

        matched_ids = MentoringMatch.objects.filter(is_active=True).values_list('scholar_id', flat=True)
        unmatched   = list(
            User.objects.filter(role=User.Role.SCHOLAR, is_active=True)
            .exclude(pk__in=matched_ids)
            .select_related('scholar_profile')
            .order_by('last_name', 'first_name')
        )

        cohorts = list(Cohort.objects.filter(is_active=True).select_related('programme').order_by('programme__name', '-year'))

        context = {
            **self.admin_site.each_context(request),
            'title': 'Mentoring Contact Report',
            'rows': rows,
            'total': total,
            'needs_chase': needs_chase,
            'no_contact': no_contact,
            'active_pairs': active_pairs,
            'days': days,
            'cohort_id': cohort_id,
            'inactive': inactive,
            'cohorts': cohorts,
            'unmatched': unmatched,
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/reports/mentoring_report.html', context)

    # ── CSV export ────────────────────────────────────────────────────────────

    def export_csv(self, request):
        days      = int(request.GET.get('days', 14))
        cohort_id = request.GET.get('cohort', '')
        inactive  = request.GET.get('inactive', '') == '1'
        threshold = timezone.now() - timedelta(days=days)

        rows = self._build_rows(self._base_qs(inactive, cohort_id), threshold)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="mentoring_contact_report_{timezone.now().date()}.csv"'
        )

        fields = [
            'scholar_name', 'scholar_email', 'scholar_cohorts',
            'mentor_name', 'mentor_email', 'mentor_company', 'mentor_specialisms',
            'matched_on', 'match_active',
            'scholar_messages_sent', 'scholar_last_message', 'scholar_days_since',
            'mentor_messages_sent', 'mentor_last_message', 'mentor_days_since',
            'needs_chase',
        ]
        writer = csv.DictWriter(response, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            row = dict(row)
            row['scholar_cohorts'] = '; '.join(row['scholar_cohorts'])
            writer.writerow(row)
        return response

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _base_qs(self, include_inactive, cohort_id):
        from apps.users.models import MentoringMatch
        qs = MentoringMatch.objects.select_related(
            'scholar', 'mentor',
            'scholar__scholar_profile',
            'mentor__mentor_profile',
        )
        if not include_inactive:
            qs = qs.filter(is_active=True)
        if cohort_id:
            qs = qs.filter(scholar__cohort_memberships__cohort_id=cohort_id).distinct()
        return qs.order_by('scholar__last_name', 'scholar__first_name')

    def _build_rows(self, qs, threshold):
        from apps.messaging.models import Message
        from apps.cohorts.models import CohortMembership

        now  = timezone.now()
        rows = []

        # Pre-fetch cohort memberships in bulk to avoid N+1
        scholar_ids = [m.scholar_id for m in qs]
        memberships = (
            CohortMembership.objects
            .filter(user_id__in=scholar_ids)
            .select_related('cohort', 'cohort__programme')
        )
        cohort_map = {}
        for cm in memberships:
            cohort_map.setdefault(cm.user_id, []).append(
                f"{cm.cohort.programme.name} – {cm.cohort.name}"
            )

        for match in qs:
            # Messages scholar → mentor (in any shared conversation)
            s_agg = Message.objects.filter(
                sender=match.scholar,
                conversation__participants=match.mentor,
                status=Message.Status.DELIVERED,
            ).aggregate(last=Max('sent_at'), total=Count('id'))

            # Messages mentor → scholar
            m_agg = Message.objects.filter(
                sender=match.mentor,
                conversation__participants=match.scholar,
                status=Message.Status.DELIVERED,
            ).aggregate(last=Max('sent_at'), total=Count('id'))

            s_days = (now - s_agg['last']).days if s_agg['last'] else None
            m_days = (now - m_agg['last']).days if m_agg['last'] else None

            needs_chase = (
                s_agg['last'] is None or s_agg['last'] < threshold or
                m_agg['last'] is None or m_agg['last'] < threshold
            )

            mp = getattr(match.mentor, 'mentor_profile', None)

            rows.append({
                'match_id':              match.pk,
                'match_active':          match.is_active,
                'matched_on':            match.matched_on,
                # Scholar
                'scholar_id':            match.scholar_id,
                'scholar_name':          match.scholar.full_name,
                'scholar_email':         match.scholar.email,
                'scholar_cohorts':       cohort_map.get(match.scholar_id, []),
                # Mentor
                'mentor_id':             match.mentor_id,
                'mentor_name':           match.mentor.full_name,
                'mentor_email':          match.mentor.email,
                'mentor_company':        mp.company if mp else '',
                'mentor_specialisms':    ', '.join(mp.specialisms or []) if mp else '',
                # Messaging — scholar side
                'scholar_total':         s_agg['total'],
                'scholar_messages_sent': s_agg['total'],
                'scholar_last':          s_agg['last'],
                'scholar_last_message':  s_agg['last'],
                'scholar_days_since':    s_days,
                # Messaging — mentor side
                'mentor_total':          m_agg['total'],
                'mentor_messages_sent':  m_agg['total'],
                'mentor_last':           m_agg['last'],
                'mentor_last_message':   m_agg['last'],
                'mentor_days_since':     m_days,
                # Status
                'needs_chase':           needs_chase,
            })

        # Needs-chase rows first, then alphabetically by scholar
        rows.sort(key=lambda r: (not r['needs_chase'], r['scholar_name'].lower()))
        return rows
