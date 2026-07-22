"""
Survey builder tests (SRV-01).

A leftover blank question row in the admin inline must not block saving the
survey. We exercise the inline formset the admin uses with one real question and
one blank trailing row, and assert it validates and saves only the real row.
"""
from django.forms.models import inlineformset_factory
from django.test import TestCase

from apps.users.models import User
from .models import Survey, Question
from .admin import QuestionInlineForm


def _formset_class():
    return inlineformset_factory(
        Survey, Question, form=QuestionInlineForm, extra=1, can_delete=True,
    )


class SurveyBuilderBlankRowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create(
            username='survey-admin', email='survey-admin@example.com',
            first_name='Survey', last_name='Admin', role=User.Role.ADMIN,
            is_active=True, is_staff=True,
        )
        self.survey = Survey.objects.create(title='Feedback', created_by=self.admin)

    def _data(self, total_forms):
        return {
            'questions-TOTAL_FORMS': str(total_forms),
            'questions-INITIAL_FORMS': '0',
            'questions-MIN_NUM_FORMS': '0',
            'questions-MAX_NUM_FORMS': '1000',
        }

    def test_blank_trailing_row_does_not_block_save(self):
        FormSet = _formset_class()
        data = self._data(2)
        # Row 0: a real question
        data.update({
            'questions-0-text': 'How was your session?',
            'questions-0-question_type': Question.QuestionType.TEXT,
            'questions-0-options': '',
            'questions-0-order': '0',
            'questions-0-is_required': 'on',
            'questions-0-soft_skill_key': '',
        })
        # Row 1: a completely blank leftover row (e.g. left after a Remove)
        data.update({
            'questions-1-text': '',
            'questions-1-question_type': '',
            'questions-1-options': '',
            'questions-1-order': '0',
            'questions-1-soft_skill_key': '',
        })
        formset = FormSet(data, instance=self.survey)
        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        self.assertEqual(self.survey.questions.count(), 1)
        self.assertEqual(self.survey.questions.get().text, 'How was your session?')

    def test_blank_row_has_not_changed(self):
        FormSet = _formset_class()
        data = self._data(1)
        data.update({
            'questions-0-text': '   ',
            'questions-0-question_type': '',
            'questions-0-options': '',
            'questions-0-order': '0',
        })
        formset = FormSet(data, instance=self.survey)
        self.assertTrue(formset.is_valid(), formset.errors)
        self.assertFalse(formset.forms[0].has_changed())
