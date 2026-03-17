from django.contrib import admin
from .models import Survey, Question, SurveyResponse, Answer


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['order', 'text', 'question_type', 'options', 'is_required', 'soft_skill_key']


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ['question', 'value']
    can_delete = False


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'programme', 'cohort', 'opens_at', 'closes_at', 'response_count']
    list_filter = ['status', 'programme', 'cohort']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'created_by']
    inlines = [QuestionInline]
    fieldsets = (
        (None, {'fields': ('title', 'description', 'status')}),
        ('Audience', {'fields': ('programme', 'cohort', 'target_roles')}),
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
