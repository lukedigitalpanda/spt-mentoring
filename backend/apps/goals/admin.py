from django.contrib import admin
from .models import Goal, GoalMilestone


class GoalMilestoneInline(admin.TabularInline):
    model = GoalMilestone
    extra = 0


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'category', 'status', 'due_date', 'progress_percent']
    list_filter = ['status', 'category']
    search_fields = ['user__email', 'title']
    inlines = [GoalMilestoneInline]
