import json
from django import forms
from django.contrib import admin
from .models import Survey, Question, SurveyResponse, Answer


# ── Custom widgets ────────────────────────────────────────────────────────────

class OptionsLineWidget(forms.Textarea):
    """One option per line — converts to/from a JSON list on save."""

    def format_value(self, value):
        if isinstance(value, list):
            return '\n'.join(str(v) for v in value)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return '\n'.join(str(v) for v in parsed)
            except (json.JSONDecodeError, TypeError):
                pass
        return value or ''

    def value_from_datadict(self, data, files, name):
        raw = super().value_from_datadict(data, files, name) or ''
        return [line.strip() for line in raw.splitlines() if line.strip()]


class OptionsField(forms.Field):
    """Form field that accepts one-per-line text and returns a Python list."""
    widget = OptionsLineWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', False)
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        return value

    def to_python(self, value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                result = json.loads(value)
                return result if isinstance(result, list) else []
            except (json.JSONDecodeError, TypeError):
                pass
        return []


_ROLE_CHOICES = [
    ('scholar', 'Scholars'),
    ('mentor', 'Mentors'),
    ('alumni', 'Alumni'),
    ('sponsor', 'Sponsors'),
]


class RoleCheckboxWidget(forms.CheckboxSelectMultiple):
    """Checkbox group for selecting target roles; stored as a JSON list."""

    def format_value(self, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                value = []
        return super().format_value(value or [])

    def value_from_datadict(self, data, files, name):
        selected = super().value_from_datadict(data, files, name) or []
        return json.dumps(selected)


class QuestionInlineForm(forms.ModelForm):
    options = OptionsField(
        widget=OptionsLineWidget(attrs={
            'rows': 4,
            'placeholder': 'Enter each option on a new line…',
            'style': 'width:100%;',
        }),
        help_text='One option per line. Only needed for Multiple choice and Checkbox questions.',
    )

    class Meta:
        model = Question
        fields = '__all__'

    def has_changed(self):
        """SRV-01: treat a row with no question text as empty.

        The custom options (JSON list) and order (default 0) fields can make an
        untouched extra/leftover inline row look 'changed', so Django tries to
        validate it and the survey then refuses to save because the blank row is
        missing required fields. Ignoring rows with no text means a leftover
        blank question never blocks the save and is simply not created.
        """
        text = (self.data.get(self.add_prefix('text')) or '').strip()
        if not text:
            return False
        return super().has_changed()


class SurveyAdminForm(forms.ModelForm):
    target_roles = forms.MultipleChoiceField(
        choices=_ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text='Select the roles this survey targets. Leave blank to show to all users.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance and isinstance(instance.target_roles, list):
            self.initial['target_roles'] = instance.target_roles

    def clean_target_roles(self):
        return list(self.cleaned_data.get('target_roles', []))

    class Meta:
        model = Survey
        fields = '__all__'


# ── Inline / admin classes ────────────────────────────────────────────────────

class QuestionInline(admin.TabularInline):
    model = Question
    form = QuestionInlineForm
    extra = 1
    fields = ['order', 'text', 'question_type', 'options', 'is_required', 'soft_skill_key']


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ['question', 'value']
    can_delete = False


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    form = SurveyAdminForm
    list_display = ['title', 'status', 'programme', 'cohort', 'opens_at', 'closes_at', 'response_count']
    list_filter = ['status', 'programme', 'cohort']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'created_by']
    inlines = [QuestionInline]
    filter_horizontal = ['cohorts']
    fieldsets = (
        (None, {'fields': ('title', 'description', 'status')}),
        ('Audience', {
            'description': (
                'Choose which roles see this survey. '
                'Use "Cohorts" to narrow further to specific cohorts. '
                'Leave roles blank to show to all users.'
            ),
            'fields': ('programme', 'cohorts', 'target_roles'),
        }),
        ('Scheduling', {'fields': ('opens_at', 'closes_at')}),
        ('Metadata', {'fields': ('created_by', 'created_at', 'customer_voice_id')}),
    )

    def response_count(self, obj):
        return obj.responses.count()
    response_count.short_description = 'Responses'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ['respondent', 'survey', 'submitted_at']
    list_filter = ['survey']
    search_fields = ['respondent__email', 'survey__title']
    readonly_fields = ['respondent', 'survey', 'submitted_at']
    inlines = [AnswerInline]
