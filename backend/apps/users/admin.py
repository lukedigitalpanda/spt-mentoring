from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from .models import User, MentorProfile, ScholarProfile, SponsorProfile, MentoringMatch, MentorWaitingList


class _SponsorRoleRelatedWrapper(RelatedFieldWidgetWrapper):
    """RelatedFieldWidgetWrapper that pre-fills role=sponsor in the add-user popup.

    Django's add_view reads GET params into the initial form data, so appending
    &role=sponsor to url_params is enough to default the role selector.
    """
    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        if 'url_params' in ctx:
            ctx['url_params'] += '&role=sponsor'
        return ctx

ROLE_CHOICES = [
    ('scholar', 'Scholar'),
    ('mentor', 'Mentor'),
    ('sponsor', 'Sponsor'),
    ('alumni', 'Alumni'),
    ('admin', 'Admin'),
]

# TC-13: Standard engineering disciplines list for multi-select
ENGINEERING_DISCIPLINE_CHOICES = [
    ('Aerospace', 'Aerospace'),
    ('Biomedical', 'Biomedical'),
    ('Chemical', 'Chemical'),
    ('Civil', 'Civil'),
    ('Electrical', 'Electrical'),
    ('Environmental', 'Environmental'),
    ('Materials', 'Materials'),
    ('Mechanical', 'Mechanical'),
    ('Software', 'Software'),
    ('Structural', 'Structural'),
    ('Other', 'Other'),
]


class SafeguardingInline(admin.StackedInline):
    """Shows mentor DBS/PVG dates directly on the User admin page for easy access."""
    model = MentorProfile
    fields = ('dbs_check_date', 'pvg_check_date')
    verbose_name = 'DBS / PVG Check Dates'
    verbose_name_plural = 'DBS / PVG Check Dates'
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False  # added automatically via signal


class UserAdminForm(UserChangeForm):
    # Inherit from UserChangeForm (not a plain ModelForm) so the `password`
    # field stays a read-only ReadOnlyPasswordHashField. A plain ModelForm
    # renders password as an editable text box whose contents are saved
    # UNHASHED, silently breaking login — see the Jun 2026 Claire Thorpe /
    # Hayleigh McAleese incident and tests/test_admin_password_field.py.
    # Password resets must go through the dedicated set-password form.
    secondary_roles = forms.MultipleChoiceField(
        choices=ROLE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Additional roles this user holds (e.g. a Sponsor who is also a Mentor).',
    )
    engineering_disciplines = forms.MultipleChoiceField(
        choices=ENGINEERING_DISCIPLINE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Select the engineering disciplines this user is associated with (used for matching and CRM).',
    )

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['secondary_roles'] = self.instance.secondary_roles or []
            self.initial['engineering_disciplines'] = self.instance.engineering_disciplines or []

    def clean_secondary_roles(self):
        return list(self.cleaned_data.get('secondary_roles') or [])

    def clean_engineering_disciplines(self):
        return list(self.cleaned_data.get('engineering_disciplines') or [])


@admin.register(User)
class UserAdmin(ImportExportModelAdmin, BaseUserAdmin):
    form = UserAdminForm
    list_display = ['email', 'full_name', 'role', 'secondary_roles_display', 'is_active', 'is_verified', 'date_joined']
    list_filter = ['role', 'is_active', 'is_verified']
    search_fields = ['email', 'first_name', 'last_name', 'crm_id']
    ordering = ['last_name', 'first_name']
    readonly_fields = ['impersonate_button']
    inlines = [SafeguardingInline]
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Profile', {'fields': ('role', 'secondary_roles', 'phone', 'bio', 'profile_picture', 'date_of_birth', 'location', 'engineering_discipline', 'engineering_disciplines', 'interests')}),
        ('Safeguarding', {
            'description': (
                'DBS checks apply for England/Wales users. PVG scheme applies for Scottish users only. '
                'DBS certificate numbers are not stored on this platform per data minimisation policy. '
                'Tracking is recorded in Dynamics 365 CRM where possible.'
            ),
            'fields': ('is_verified', 'safeguarding_training_date'),
        }),
        ('CRM', {'fields': ('crm_id',)}),
        ('Notifications', {'fields': ('notification_email', 'notification_sms')}),
        ('Impersonation', {'fields': ('impersonate_button',)}),
    )

    def secondary_roles_display(self, obj):
        """TC-17: Show secondary roles in the user list so multi-role users are immediately visible."""
        roles = obj.secondary_roles or []
        if not roles:
            return '—'
        return format_html(
            '<span style="color:#6b4fa3;font-size:11px;">{}</span>',
            ', '.join(roles),
        )
    secondary_roles_display.short_description = 'Also'

    def impersonate_button(self, obj):
        if not obj.pk:
            return '—'
        return format_html(
            '<a href="{}" class="button" '
            'style="background:#e01e8c;color:#fff;padding:6px 18px;border-radius:6px;'
            'font-weight:700;text-decoration:none;display:inline-block;">'
            'View frontend as this user</a>',
            f'/admin/users/user/{obj.pk}/impersonate/',
        )
    impersonate_button.short_description = 'Impersonate'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        return [
            path(
                '<int:pk>/impersonate/',
                self.admin_site.admin_view(self.impersonate_view),
                name='users_user_impersonate',
            ),
        ] + urls

    def impersonate_view(self, request, pk):
        from django.shortcuts import redirect
        from rest_framework_simplejwt.tokens import RefreshToken
        import logging
        logger = logging.getLogger(__name__)

        target = User.objects.get(pk=pk)
        refresh = RefreshToken.for_user(target)
        logger.warning(
            'Admin impersonation: %s is impersonating %s (pk=%s)',
            request.user.email, target.email, pk,
        )
        url = (
            f'/impersonate'
            f'?access={refresh.access_token}'
            f'&refresh={refresh}'
            f'&uid={pk}'
        )
        return redirect(url)


@admin.register(MentoringMatch)
class MentoringMatchAdmin(admin.ModelAdmin):
    list_display = ['scholar', 'mentor', 'is_active', 'matched_on', 'wizard_link']
    list_filter = ['is_active']
    search_fields = ['scholar__email', 'mentor__email']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """ISS-H: Include users whose mentor/alumni role is primary OR secondary."""
        from django.db.models import Q
        if db_field.name == 'mentor':
            kwargs['queryset'] = User.objects.filter(
                Q(role__in=[User.Role.MENTOR, User.Role.ALUMNI])
                | Q(secondary_roles__contains='mentor')
                | Q(secondary_roles__contains='alumni'),
                is_active=True,
            ).distinct().order_by('last_name', 'first_name')
        elif db_field.name == 'scholar':
            kwargs['queryset'] = User.objects.filter(
                Q(role=User.Role.SCHOLAR)
                | Q(secondary_roles__contains='scholar'),
                is_active=True,
            ).distinct().order_by('last_name', 'first_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def wizard_link(self, obj):
        return format_html(
            '<a href="../wizard/" style="font-size:11px;color:#3b1fa3;">Matching Wizard</a>'
        )
    wizard_link.short_description = ''

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        return [
            path('wizard/', self.admin_site.admin_view(self.wizard_view), name='users_mentoringmatch_wizard'),
        ] + urls

    def wizard_view(self, request):
        from django.contrib import messages as msg
        from django.shortcuts import redirect
        from django.template.response import TemplateResponse
        from .models import User

        DISCIPLINES = [
            'Aerospace', 'Biomedical', 'Chemical', 'Civil', 'Electrical',
            'Environmental', 'Materials', 'Mechanical', 'Software', 'Structural', 'Other',
        ]

        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'create_match':
                scholar_id = request.POST.get('scholar_id')
                mentor_id = request.POST.get('mentor_id')
                try:
                    scholar = User.objects.get(pk=scholar_id)
                    mentor = User.objects.get(pk=mentor_id)
                    match, created = MentoringMatch.objects.get_or_create(
                        scholar=scholar,
                        mentor=mentor,
                        defaults={'matched_by': request.user, 'is_active': True},
                    )
                    if not created:
                        match.is_active = True
                        match.matched_by = request.user
                        match.save(update_fields=['is_active', 'matched_by'])
                    msg.success(
                        request,
                        f'Match {"created" if created else "reinstated"}: {scholar.full_name} ↔ {mentor.full_name}',
                    )
                except Exception as e:
                    msg.error(request, f'Could not create match: {e}')
                return redirect('.')

            if action == 'deactivate_match':
                match_id = request.POST.get('match_id')
                try:
                    match = MentoringMatch.objects.get(pk=match_id)
                    match.is_active = False
                    match.save(update_fields=['is_active'])
                    msg.success(request, f'Match deactivated: {match.scholar.full_name} ↔ {match.mentor.full_name}')
                except Exception as e:
                    msg.error(request, f'Could not deactivate match: {e}')
                return redirect('.')

        # All scholars with active match annotation
        from django.db.models import Count, Q, Prefetch
        active_matches = MentoringMatch.objects.filter(is_active=True).select_related('mentor')
        scholars = (
            User.objects
            .filter(is_active=True, role=User.Role.SCHOLAR)
            .prefetch_related(Prefetch('scholar_matches', queryset=active_matches, to_attr='active_matches'))
            .order_by('last_name', 'first_name')
        )

        # Mentors/alumni with capacity — include secondary-role users
        mentors = (
            User.objects
            .filter(
                Q(role__in=[User.Role.MENTOR, User.Role.ALUMNI])
                | Q(secondary_roles__contains='mentor')
                | Q(secondary_roles__contains='alumni'),
                is_active=True,
            )
            .distinct()
            .select_related('mentor_profile')
            .annotate(active_match_count=Count('mentor_matches', filter=Q(mentor_matches__is_active=True)))
            .order_by('last_name', 'first_name')
        )

        context = {
            **self.admin_site.each_context(request),
            'title': 'Matching Wizard',
            'scholars': scholars,
            'mentors': mentors,
            'disciplines': DISCIPLINES,
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/users/match_wizard.html', context)


class MentorProfileForm(forms.ModelForm):
    # TC-13/TC-20: Use the same structured discipline list as the frontend so
    # admin-entered data is standardised and usable for matching queries.
    specialisms = forms.MultipleChoiceField(
        choices=[(d, d) for d in [
            'Aerospace', 'Biomedical', 'Chemical', 'Civil', 'Electrical',
            'Environmental', 'Materials', 'Mechanical', 'Software', 'Structural', 'Other',
        ]],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=(
            'Select the engineering disciplines this mentor specialises in. '
            'Used for scholar matching — must use the standard list to be queryable.'
        ),
    )

    class Meta:
        model = MentorProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['specialisms'] = self.instance.specialisms or []

    def clean_specialisms(self):
        return list(self.cleaned_data.get('specialisms') or [])


@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    form = MentorProfileForm
    list_display  = ['user', 'company', 'job_title', 'specialism_summary', 'has_capacity', 'matched_scholar_list']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'company', 'job_title']
    readonly_fields = ['matched_scholars_display', 'cohort_display']
    fieldsets = (
        ('Mentor', {
            'fields': ('user', 'company', 'job_title', 'years_experience', 'max_scholars'),
        }),
        ('Matched Scholars & Cohort', {
            'description': 'Current active scholar matches and cohort assignments for this mentor.',
            'fields': ('matched_scholars_display', 'cohort_display'),
        }),
        ('Specialisms', {
            'fields': ('specialisms',),
        }),
        ('Availability', {
            'fields': ('availability', 'linkedin_url'),
        }),
        ('Safeguarding', {
            'description': (
                'Record the date checks were completed. No certificate numbers are stored. '
                'DBS = England/Wales. PVG = Scotland only.'
            ),
            'fields': ('dbs_check_date', 'pvg_check_date'),
        }),
    )

    def specialism_summary(self, obj):
        items = obj.specialisms or []
        if not items:
            return '—'
        summary = ', '.join(items[:3])
        return summary + (f' +{len(items) - 3} more' if len(items) > 3 else '')
    specialism_summary.short_description = 'Specialisms'

    def matched_scholar_list(self, obj):
        matches = obj.user.mentor_matches.filter(is_active=True).select_related('scholar')
        if not matches:
            return '—'
        return ', '.join(m.scholar.full_name for m in matches)
    matched_scholar_list.short_description = 'Matched Scholars'

    def matched_scholars_display(self, obj):
        from django.utils.html import format_html
        matches = obj.user.mentor_matches.filter(is_active=True).select_related('scholar')
        if not matches:
            return 'No active scholar matches.'
        items = ''.join(
            f'<li><a href="/admin/users/scholarprofile/?user__in={m.scholar_id}">'
            f'{m.scholar.full_name}</a> — matched {m.matched_on.strftime("%d %b %Y")}</li>'
            for m in matches
        )
        return format_html('<ul style="margin:0;padding-left:16px;">{}</ul>', format_html(items))
    matched_scholars_display.short_description = 'Active Matches'

    def cohort_display(self, obj):
        from apps.cohorts.models import CohortMembership
        from django.utils.html import format_html
        memberships = (
            CohortMembership.objects
            .filter(user=obj.user)
            .select_related('cohort', 'cohort__programme')
            .order_by('-cohort__year')
        )
        if not memberships:
            return 'Not assigned to any cohort.'
        items = ''.join(
            f'<li>{m.cohort.programme.name} — {m.cohort.name} ({m.cohort.year})</li>'
            for m in memberships
        )
        return format_html('<ul style="margin:0;padding-left:16px;">{}</ul>', format_html(items))
    cohort_display.short_description = 'Cohort Memberships'


class SponsorLinkedFilter(admin.SimpleListFilter):
    title = 'sponsor linked'
    parameter_name = 'has_sponsor'

    def lookups(self, request, model_admin):
        return [('yes', 'Has sponsor'), ('no', 'No sponsor')]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(sponsor__isnull=False)
        if self.value() == 'no':
            return queryset.filter(sponsor__isnull=True)
        return queryset


@admin.register(ScholarProfile)
class ScholarProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'scholarship_reference', 'current_mentor', 'sponsor', 'university', 'course']
    list_filter = [SponsorLinkedFilter, 'user__is_active']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'scholarship_reference']
    readonly_fields = ['matched_mentor_display', 'cohort_display']

    def current_mentor(self, obj):
        match = MentoringMatch.objects.filter(scholar=obj.user, is_active=True).select_related('mentor').first()
        if match:
            return format_html(
                '<span style="color:#2e7d32;font-weight:600;">&#10003; {}</span>',
                match.mentor.full_name,
            )
        return format_html(
            '<a href="/admin/users/mentoringmatch/wizard/" style="color:#e01e8c;font-weight:600;">+ Assign mentor</a>'
        )
    current_mentor.short_description = 'Matched Mentor'

    def matched_mentor_display(self, obj):
        match = MentoringMatch.objects.filter(scholar=obj.user, is_active=True).select_related('mentor').first()
        if not match:
            return format_html(
                'No active mentor match. <a href="/admin/users/mentoringmatch/wizard/">Assign via Matching Wizard →</a>'
            )
        return format_html(
            '<a href="/admin/users/mentorprofile/?user__id__exact={}">'
            '<strong style="color:#2e7d32;">&#10003; {}</strong></a>'
            ' — matched {}',
            match.mentor.pk,
            match.mentor.full_name,
            match.matched_on.strftime('%d %b %Y'),
        )
    matched_mentor_display.short_description = 'Current Mentor'

    def cohort_display(self, obj):
        from apps.cohorts.models import CohortMembership
        memberships = (
            CohortMembership.objects
            .filter(user=obj.user)
            .select_related('cohort', 'cohort__programme')
            .order_by('-cohort__year')
        )
        if not memberships:
            return 'Not assigned to any cohort.'
        items = ''.join(
            f'<li><a href="/admin/cohorts/cohort/{m.cohort.pk}/change/">'
            f'{m.cohort.programme.name} — {m.cohort.name} ({m.cohort.year})</a></li>'
            for m in memberships
        )
        return format_html('<ul style="margin:0;padding-left:16px;">{}</ul>', format_html(items))
    cohort_display.short_description = 'Cohort Memberships'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """ISS-H: Include users whose sponsor role is primary OR secondary."""
        if db_field.name == 'sponsor':
            from django.db.models import Q
            kwargs['queryset'] = User.objects.filter(
                Q(role=User.Role.SPONSOR)
                | Q(secondary_roles__contains='sponsor'),
                is_active=True,
            ).distinct().order_by('last_name', 'first_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    fieldsets = (
        ('Scholar', {
            'fields': ('user', 'scholarship_reference'),
        }),
        ('Matched Mentor & Cohort', {
            'description': 'Current active mentor match and cohort assignments for this scholar.',
            'fields': ('matched_mentor_display', 'cohort_display'),
        }),
        ('Sponsor Link', {
            'description': 'Link this scholar to their sponsor. The sponsor will be able to receive update messages.',
            'fields': ('sponsor',),
        }),
        ('Goals & Skills', {
            'fields': ('goals', 'soft_skills_baseline', 'soft_skills_current'),
        }),
        ('University', {
            'description': 'University details — filled in by the scholar once they have started higher education.',
            'fields': ('university', 'course', 'year_of_study', 'graduation_year'),
        }),
    )


@admin.register(SponsorProfile)
class SponsorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'organisation', 'contact_name', 'linked_scholars_count', 'update_frequency_days']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'organisation']

    def linked_scholars_count(self, obj):
        return obj.user.sponsored_scholars.count()
    linked_scholars_count.short_description = 'Linked Scholars'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'user' and isinstance(formfield.widget, RelatedFieldWidgetWrapper):
            w = formfield.widget
            formfield.widget = _SponsorRoleRelatedWrapper(
                w.widget, w.rel, w.admin_site,
                can_add_related=True,
                can_change_related=w.can_change_related,
                can_delete_related=w.can_delete_related,
                can_view_related=getattr(w, 'can_view_related', False),
            )
        return formfield

    def get_readonly_fields(self, request, obj=None):
        return ['linked_scholars_display'] if obj else []

    def linked_scholars_display(self, obj):
        scholars = obj.user.sponsored_scholars.select_related('user').all()
        if not scholars:
            return 'No scholars linked to this sponsor.'
        items = ''.join(
            f'<li><a href="/admin/users/scholarprofile/{sp.pk}/change/">{sp.user.full_name}</a>'
            f' ({sp.scholarship_reference or "no ref"})</li>'
            for sp in scholars
        )
        return format_html('<ul style="margin:0;padding-left:16px;">{}</ul>', format_html(items))
    linked_scholars_display.short_description = 'Linked Scholars'

    def get_fieldsets(self, request, obj=None):
        base = [('Sponsor', {'fields': ('user', 'organisation', 'contact_name', 'update_frequency_days')})]
        if obj:
            base.append(('Linked Scholars', {'fields': ('linked_scholars_display',)}))
        return base


@admin.register(MentorWaitingList)
class MentorWaitingListAdmin(admin.ModelAdmin):
    list_display = ['scholar', 'preferred_mentor', 'engineering_discipline', 'is_matched', 'requested_at']
    list_filter = ['is_matched']
    search_fields = ['scholar__first_name', 'scholar__last_name', 'scholar__email']
