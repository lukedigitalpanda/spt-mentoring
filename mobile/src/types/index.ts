export type UserRole = 'scholar' | 'mentor' | 'sponsor' | 'alumni' | 'admin';

export interface User {
  id: number;
  email: string;
  full_name: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  engineering_discipline: string;
  location: string;
  bio: string;
  is_verified: boolean;
}

export interface Notification {
  id: number;
  notification_type: string;
  title: string;
  body: string;
  link: string;
  is_read: boolean;
  created_at: string;
}

export interface MentoringSession {
  id: number;
  mentor: User;
  scholar: User;
  title: string;
  agenda: string;
  status: 'pending' | 'confirmed' | 'cancelled' | 'completed' | 'no_show';
  start_time: string;
  end_time: string;
  jitsi_room_url: string;
  duration_minutes: number;
  is_upcoming: boolean;
}

export interface Message {
  id: number;
  sender: User;
  content: string;
  sent_at: string;
  status: string;
}

export interface Conversation {
  id: number;
  participants: User[];
  last_message: Message | null;
  unread_count: number;
}

export interface Goal {
  id: number;
  title: string;
  description: string;
  category: string;
  status: 'active' | 'completed' | 'paused';
  due_date: string | null;
  progress_percent: number;
  created_at: string;
}
