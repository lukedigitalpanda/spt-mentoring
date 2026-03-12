export type Role = 'scholar' | 'mentor' | 'sponsor' | 'alumni' | 'admin';

export interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: Role;
  phone: string;
  bio: string;
  profile_picture: string | null;
  location: string;
  engineering_discipline: string;
  interests: string[];
  is_verified: boolean;
  crm_id: string;
  is_active: boolean;
  notification_email: boolean;
  mentor_profile?: MentorProfile;
  scholar_profile?: ScholarProfile;
  sponsor_profile?: SponsorProfile;
}

export interface MentorProfile {
  company: string;
  job_title: string;
  years_experience: number;
  max_scholars: number;
  specialisms: string[];
  availability: string;
  current_scholar_count: number;
  has_capacity: boolean;
}

export interface ScholarProfile {
  university: string;
  course: string;
  year_of_study: number | null;
  graduation_year: number | null;
  scholarship_reference: string;
  sponsor: number | null;
  goals: string;
  soft_skills_current: Record<string, number>;
}

export interface SponsorProfile {
  organisation: string;
  contact_name: string;
  update_frequency_days: number;
}

export interface Message {
  id: number;
  conversation: number;
  sender: number;
  sender_name: string;
  body: string;
  sent_at: string;
  status: 'pending' | 'delivered' | 'flagged' | 'blocked' | 'deleted';
  attachment: string | null;
  is_read: boolean;
}

export interface Conversation {
  id: number;
  conversation_type: 'direct' | 'group' | 'sponsor_update';
  participants: number[];
  participant_names: string[];
  subject: string;
  created_at: string;
  last_message: { id: number; body: string; sent_at: string; sender: string } | null;
  unread_count: number;
}

export interface NewsItem {
  id: number;
  title: string;
  slug: string;
  summary: string;
  body: string;
  cover_image: string | null;
  status: 'draft' | 'published' | 'archived';
  audience: 'all' | 'scholar' | 'mentor' | 'sponsor';
  is_featured: boolean;
  published_at: string | null;
  author_name: string;
}

export interface Forum {
  id: number;
  title: string;
  description: string;
  visibility: 'open' | 'programme' | 'private';
  thread_count: number;
}

export interface Thread {
  id: number;
  forum: number;
  title: string;
  created_by_name: string;
  created_at: string;
  is_pinned: boolean;
  is_locked: boolean;
  post_count: number;
  last_post_at: string | null;
}

export interface Post {
  id: number;
  thread: number;
  author: number;
  author_name: string;
  body: string;
  created_at: string;
  status: 'pending' | 'visible' | 'flagged' | 'hidden';
}

export interface Resource {
  id: number;
  title: string;
  description: string;
  resource_type: 'document' | 'link' | 'video';
  category: number | null;
  file: string | null;
  url: string;
  audience: 'all' | 'scholar' | 'mentor' | 'sponsor' | 'admin';
  download_count: number;
}

export interface Survey {
  id: number;
  title: string;
  description: string;
  status: 'draft' | 'active' | 'closed';
  opens_at: string | null;
  closes_at: string | null;
  response_count: number;
  questions: Question[];
}

export interface Question {
  id: number;
  text: string;
  question_type: 'text' | 'rating' | 'multiple_choice' | 'checkbox' | 'scale';
  options: string[];
  order: number;
  is_required: boolean;
}

export interface Cohort {
  id: number;
  name: string;
  year: number;
  programme: number;
  programme_name: string;
  member_count: number;
  is_active: boolean;
}

export interface Programme {
  id: number;
  name: string;
  description: string;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ── Sessions ──────────────────────────────────────────────────────────────────

export interface AvailabilitySlot {
  id: number;
  mentor: number;
  mentor_name: string;
  start_time: string;
  end_time: string;
  is_booked: boolean;
  notes: string;
}

export interface SessionFeedback {
  id: number;
  session: number;
  from_user: number;
  from_user_name: string;
  rating: number;
  highlights: string;
  improvements: string;
  would_recommend: boolean | null;
  created_at: string;
}

export interface MentoringSession {
  id: number;
  mentor: number;
  mentor_name: string;
  scholar: number;
  scholar_name: string;
  slot: number | null;
  title: string;
  start_time: string;
  end_time: string;
  status: 'pending' | 'confirmed' | 'cancelled' | 'completed' | 'no_show';
  meeting_url: string;
  agenda: string;
  mentor_notes: string;
  scholar_notes: string;
  duration_minutes: number;
  feedback: SessionFeedback[];
  created_at: string;
}

// ── Notifications ─────────────────────────────────────────────────────────────

export type NotificationType =
  | 'session_request' | 'session_confirmed' | 'session_cancelled'
  | 'session_reminder' | 'session_feedback' | 'message'
  | 'match' | 'forum_reply' | 'survey' | 'goal' | 'system';

export interface Notification {
  id: number;
  notification_type: NotificationType;
  title: string;
  body: string;
  link: string;
  is_read: boolean;
  created_at: string;
}

// ── Goals ─────────────────────────────────────────────────────────────────────

export interface GoalMilestone {
  id: number;
  goal: number;
  title: string;
  is_completed: boolean;
  completed_at: string | null;
  due_date: string | null;
}

export interface Goal {
  id: number;
  user: number;
  title: string;
  description: string;
  category: 'career' | 'technical' | 'personal' | 'academic' | 'networking' | 'other';
  status: 'active' | 'completed' | 'paused';
  due_date: string | null;
  created_at: string;
  completed_at: string | null;
  milestones: GoalMilestone[];
  milestone_count: number;
  completed_milestone_count: number;
  progress_percent: number;
}

// ── Waiting List ──────────────────────────────────────────────────────────────

export interface WaitingListEntry {
  id: number;
  scholar: number;
  scholar_name: string;
  preferred_mentor: number | null;
  preferred_mentor_name: string;
  engineering_discipline: string;
  notes: string;
  requested_at: string;
  is_matched: boolean;
  matched_at: string | null;
}
