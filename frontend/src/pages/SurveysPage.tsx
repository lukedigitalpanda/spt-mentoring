import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../utils/api';
import type { Survey, Question, PaginatedResponse } from '../types';

function BrandStar({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <path d="M10 0 L10 20 M0 10 L20 10 M2.93 2.93 L17.07 17.07 M17.07 2.93 L2.93 17.07"
        stroke="#e01e8c" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function fmtDate(d?: string | null) {
  if (!d) return '';
  return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

const statusBadge: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  draft:  'bg-gray-100 text-gray-500',
  closed: 'bg-red-100 text-red-500',
};

// ── Individual question renderer ──────────────────────────────────────────────
function QuestionField({
  question,
  value,
  onChange,
}: {
  question: Question;
  value: string | string[];
  onChange: (v: string | string[]) => void;
}) {
  const baseInput = 'w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors';

  if (question.question_type === 'text') {
    return (
      <textarea
        className={`${baseInput} resize-none`}
        rows={3}
        required={question.is_required}
        value={value as string}
        onChange={e => onChange(e.target.value)}
        placeholder="Your answer…"
      />
    );
  }

  if (question.question_type === 'rating' || question.question_type === 'scale') {
    const max = question.question_type === 'rating' ? 5 : 10;
    return (
      <div className="flex items-center gap-1.5 flex-wrap">
        {Array.from({ length: max }, (_, i) => i + 1).map(n => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(String(n))}
            className={`w-10 h-10 rounded-lg text-sm font-semibold transition-all ${
              value === String(n)
                ? 'bg-pink-500 text-white shadow-brand'
                : 'bg-white border border-purple-200 text-navy-500 hover:border-pink-500 hover:text-pink-500'
            }`}
          >
            {n}
          </button>
        ))}
        {question.question_type === 'scale' && (
          <div className="w-full flex justify-between text-[10px] text-navy-500/40 mt-1">
            <span>Strongly disagree</span>
            <span>Strongly agree</span>
          </div>
        )}
      </div>
    );
  }

  if (question.question_type === 'multiple_choice') {
    return (
      <div className="space-y-2">
        {question.options.map(opt => (
          <label key={opt} className="flex items-center gap-2.5 cursor-pointer group">
            <input
              type="radio"
              name={`q_${question.id}`}
              value={opt}
              checked={value === opt}
              onChange={() => onChange(opt)}
              required={question.is_required}
              className="accent-pink"
            />
            <span className="text-sm text-navy-500/80 group-hover:text-navy-500">{opt}</span>
          </label>
        ))}
      </div>
    );
  }

  if (question.question_type === 'checkbox') {
    const checked = Array.isArray(value) ? value : [];
    const toggle = (opt: string) => {
      if (checked.includes(opt)) onChange(checked.filter(v => v !== opt));
      else onChange([...checked, opt]);
    };
    return (
      <div className="space-y-2">
        {question.options.map(opt => (
          <label key={opt} className="flex items-center gap-2.5 cursor-pointer group">
            <input
              type="checkbox"
              checked={checked.includes(opt)}
              onChange={() => toggle(opt)}
              className="accent-pink"
            />
            <span className="text-sm text-navy-500/80 group-hover:text-navy-500">{opt}</span>
          </label>
        ))}
      </div>
    );
  }

  return null;
}

// ── Survey form ───────────────────────────────────────────────────────────────
function SurveyForm({ survey, onDone }: { survey: Survey; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [answers, setAnswers] = useState<Record<number, string | string[]>>({});
  const [submitted, setSubmitted] = useState(false);

  const submitMutation = useMutation({
    mutationFn: (payload: { answers: { question: number; value: string }[] }) =>
      api.post(`/surveys/surveys/${survey.id}/submit/`, payload),
    onSuccess: () => {
      setSubmitted(true);
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const answersPayload = Object.entries(answers).map(([qId, val]) => ({
      question: Number(qId),
      value: Array.isArray(val) ? val.join(', ') : val,
    }));
    submitMutation.mutate({ answers: answersPayload });
  };

  if (submitted) {
    return (
      <div className="text-center py-16">
        <div className="w-16 h-16 rounded-2xl bg-gradient-brand-soft flex items-center justify-center shadow-brand mx-auto mb-5">
          <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-xl font-extrabold text-navy-500 mb-2">Thank you!</h2>
        <p className="text-sm text-navy-500/50 mb-6">Your response has been recorded.</p>
        <button
          onClick={onDone}
          className="text-xs font-semibold text-pink-500 hover:underline flex items-center gap-1 mx-auto"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
          </svg>
          Back to surveys
        </button>
      </div>
    );
  }

  const sorted = [...survey.questions].sort((a, b) => a.order - b.order);

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={onDone} className="text-xs font-semibold text-pink-500 hover:underline flex items-center gap-1">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
          </svg>
          Surveys
        </button>
        <span className="text-navy-500/30">/</span>
        <span className="text-sm font-bold text-navy-500 truncate">{survey.title}</span>
      </div>

      <div className="bg-white rounded-2xl shadow-card p-6 mb-6">
        <h2 className="text-xl font-extrabold text-navy-500 mb-1">{survey.title}</h2>
        {survey.description && (
          <p className="text-sm text-navy-500/60">{survey.description}</p>
        )}
        {survey.closes_at && (
          <p className="text-xs text-navy-500/40 mt-2">Closes {fmtDate(survey.closes_at)}</p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {sorted.map((q, idx) => (
          <div key={q.id} className="bg-white rounded-2xl shadow-card p-5">
            <p className="text-sm font-semibold text-navy-500 mb-1">
              {idx + 1}. {q.text}
              {q.is_required && <span className="text-pink-500 ml-0.5">*</span>}
            </p>
            <QuestionField
              question={q}
              value={answers[q.id] ?? (q.question_type === 'checkbox' ? [] : '')}
              onChange={v => setAnswers(prev => ({ ...prev, [q.id]: v }))}
            />
          </div>
        ))}

        {submitMutation.isError && (
          <div className="bg-red-50 border border-red-100 rounded-xl px-4 py-3 text-xs text-red-600">
            Failed to submit. You may have already completed this survey.
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitMutation.isPending}
            className="bg-pink-500 text-white text-sm font-semibold px-6 py-2.5 rounded-xl hover:bg-pink-600 transition-colors disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed shadow-brand"
          >
            {submitMutation.isPending ? 'Submitting…' : 'Submit survey'}
          </button>
        </div>
      </form>
    </div>
  );
}

// ── Survey card ───────────────────────────────────────────────────────────────
function SurveyCard({ survey, onSelect }: { survey: Survey; onSelect: () => void }) {
  return (
    <div className="bg-white rounded-2xl shadow-card hover:shadow-brand transition-all p-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full capitalize ${statusBadge[survey.status] ?? ''}`}>
              {survey.status}
            </span>
          </div>
          <h3 className="font-bold text-sm text-navy-500">{survey.title}</h3>
        </div>
        <div className="flex flex-col items-end flex-shrink-0 gap-0.5">
          <span className="text-xs font-bold text-navy-500">{survey.questions.length}</span>
          <span className="text-[10px] text-navy-500/40">questions</span>
        </div>
      </div>

      {survey.description && (
        <p className="text-xs text-navy-500/50 line-clamp-2 mb-4">{survey.description}</p>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-purple-50">
        <div className="text-xs text-navy-500/40">
          {survey.closes_at && <span>Closes {fmtDate(survey.closes_at)}</span>}
        </div>
        {survey.status === 'active' && (
          <button
            onClick={onSelect}
            className="text-sm font-semibold bg-pink-500 text-white px-4 py-2 rounded-lg hover:bg-pink-600 transition-colors shadow-brand"
          >
            Take survey
          </button>
        )}
      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function SurveysPage() {
  const [activeSurvey, setActiveSurvey] = useState<Survey | null>(null);

  const { data, isLoading } = useQuery<PaginatedResponse<Survey>>({
    queryKey: ['surveys'],
    queryFn: () => api.get('/surveys/surveys/').then(r => r.data),
  });

  if (activeSurvey) {
    return (
      <SurveyForm
        survey={activeSurvey}
        onDone={() => setActiveSurvey(null)}
      />
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-brand text-white px-8 py-8 mb-8 shadow-brand">
        <div className="absolute -top-8 -right-8 w-48 h-48 rounded-full bg-white/5" />
        <div className="relative z-10">
          <p className="text-xs font-semibold text-white/60 uppercase tracking-widest mb-1">Progress tracking</p>
          <h1 className="text-2xl font-extrabold">Surveys</h1>
          <p className="mt-1 text-white/60 text-sm">Track your skills development and programme experience.</p>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-4">
        <BrandStar />
        <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Available Surveys</h2>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" />
        </div>
      ) : !data?.results?.length ? (
        <div className="text-center py-16 text-sm text-navy-500/40">
          No surveys available at the moment.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.results.map(survey => (
            <SurveyCard key={survey.id} survey={survey} onSelect={() => setActiveSurvey(survey)} />
          ))}
        </div>
      )}
    </div>
  );
}
