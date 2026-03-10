from rest_framework import serializers
from .models import Survey, Question, SurveyResponse, Answer


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class SurveySerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    response_count = serializers.SerializerMethodField()

    class Meta:
        model = Survey
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']

    def get_response_count(self, obj):
        return obj.responses.count()


class AnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)

    class Meta:
        model = Answer
        fields = ['id', 'question', 'question_text', 'value']


class SurveyResponseSerializer(serializers.ModelSerializer):
    respondent_name = serializers.CharField(source='respondent.full_name', read_only=True)
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = SurveyResponse
        fields = '__all__'
