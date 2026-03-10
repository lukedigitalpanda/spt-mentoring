from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from .models import Survey, Question, SurveyResponse, Answer
from .serializers import SurveySerializer, QuestionSerializer, SurveyResponseSerializer


class SurveyViewSet(viewsets.ModelViewSet):
    serializer_class = SurveySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'programme', 'cohort']
    search_fields = ['title', 'description']

    def get_queryset(self):
        user = self.request.user
        qs = Survey.objects.all()
        if not (user.is_staff or user.role == 'admin'):
            from django.utils import timezone
            now = timezone.now()
            qs = qs.filter(
                status='active',
                opens_at__lte=now,
            ).filter(closes_at__gte=now) | qs.filter(status='active', closes_at__isnull=True)
        return qs.distinct()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit a survey response."""
        survey = self.get_object()
        user = request.user

        if SurveyResponse.objects.filter(survey=survey, respondent=user).exists():
            return Response({'error': 'Already submitted'}, status=status.HTTP_400_BAD_REQUEST)

        answers_data = request.data.get('answers', [])
        response_obj = SurveyResponse.objects.create(survey=survey, respondent=user)

        for ans in answers_data:
            question_id = ans.get('question')
            value = ans.get('value', '')
            try:
                question = Question.objects.get(pk=question_id, survey=survey)
                Answer.objects.create(response=response_obj, question=question, value=value)
            except Question.DoesNotExist:
                pass

        # Update Scholar soft skills if questions are mapped
        self._update_soft_skills(user, response_obj)

        return Response({'status': 'submitted', 'response_id': response_obj.pk})

    def _update_soft_skills(self, user, response_obj):
        """Update scholar's soft skill scores based on rating questions."""
        if user.role not in ('scholar', 'alumni'):
            return
        profile = getattr(user, 'scholar_profile', None)
        if not profile:
            return
        skills = dict(profile.soft_skills_current)
        for answer in response_obj.answers.select_related('question'):
            key = answer.question.soft_skill_key
            if key and answer.question.question_type in ('rating', 'scale'):
                try:
                    skills[key] = int(answer.value)
                except (ValueError, TypeError):
                    pass
        profile.soft_skills_current = skills
        profile.save(update_fields=['soft_skills_current'])


class SurveyResponseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SurveyResponseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['survey', 'respondent']
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return SurveyResponse.objects.prefetch_related('answers__question').all()
