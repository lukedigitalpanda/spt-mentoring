# SPT Mentoring Platform

A full-featured mentoring platform for the SPT Scholar Mentoring Programme, supporting Scholars, Mentors, Sponsors, and Admins.

---

## Architecture

```
spt-mentoring/
├── backend/          # Django REST API (Python 3.12)
│   ├── config/       # Settings, URLs, ASGI/WSGI, Celery
│   └── apps/
│       ├── users/        # Users, profiles, matching
│       ├── messaging/    # Moderated messaging + WebSocket + mass messaging
│       ├── cohorts/      # Programmes & cohort management
│       ├── forums/       # Community forums + group mentoring
│       ├── resources/    # Resource bank + document sharing
│       ├── news/         # News items + home page banners
│       ├── surveys/      # Surveys + soft-skill tracking
│       ├── reports/      # Reporting (CSV + JSON)
│       └── moderation/   # Content moderation & safeguarding
├── frontend/         # React + TypeScript + Tailwind CSS
│   └── src/
│       ├── pages/        # HomePage, MessagesPage, AdminPage, LoginPage
│       ├── components/   # Layout, shared UI
│       ├── hooks/        # useAuth (Zustand)
│       ├── utils/        # Axios API client (JWT auto-refresh)
│       └── types/        # TypeScript types
├── docker-compose.yml
└── .env.example
```

---

## Must-Have Requirements Implemented

| Requirement | Implementation |
|---|---|
| CRM integration | `crm_id` field on User; bulk CSV/XLSX import via `/api/users/bulk_upload/`; export via `/api/users/export/` |
| Safeguarding | Moderation pipeline on all messages & forum posts; `is_verified` + DBS fields on Mentor; safeguarding notes on `FlaggedTerm` |
| Moderated messaging | Every message screened by `ModerationService` before delivery; WebSocket real-time chat |
| Filtered/flagged terms | `BlockedTerm` (blocks immediately) and `FlaggedTerm` (holds for admin review) models + admin UI queue |
| Data upload/management | `UserBulkImport` supports CSV + XLSX; Django import-export on admin |
| Searchability | Full-text search across all key models via DRF `SearchFilter`; filterable by role, cohort, programme |
| Cohorts | `Programme → Cohort → CohortMembership`; bulk-assign users via `/api/cohorts/cohorts/{id}/bulk_assign/` |
| Reporting | Contact frequency report, sponsor update report, user data report, cohort progress report – all with CSV export |
| Sponsor contact chase | Automated Celery task sends reminders when scholars haven't updated sponsors within expected frequency |
| No-contact reminders | Celery beat task sends reminders when Scholar/Mentor pair hasn't messaged within `NO_CONTACT_REMINDER_DAYS` |
| Forum | `Forum → Thread → Post` with Open/Programme/Private visibility; same moderation pipeline |
| Mass messaging | `MassMessage` model; send from `mentoring@` or `scholarships@`; target by role/cohort |
| News & home page | `NewsItem` + `PromotionalBanner`; featured items shown on home page |
| Resource bank | Documents, links, videos; audience targeting; download tracking |
| Group mentoring (private) | Private `Forum` + `Conversation` with `type=group` |
| Branding | `branding_colour` + `branding_logo` on `Programme` |
| Document sharing | `SharedDocument` model for peer file sharing |
| Multiple matches | `MentoringMatch` allows one Mentor to have multiple Scholars (`max_scholars` on `MentorProfile`) |
| Report abuse button | `AbuseReport` model + `/api/messaging/abuse-reports/` endpoint + hover-reveal in UI |
| Survey functionality | `Survey → Question → SurveyResponse → Answer`; soft-skill score updates |
| Automated emails | Celery tasks for: no-contact reminders, sponsor update reminders, mass messages |

## Nice-to-Have Requirements Implemented

| Requirement | Implementation |
|---|---|
| Alumni access | `alumni` role – treated like Scholar but can access peer-mentoring content |
| Separate Sponsor area | `sponsor_update` conversation type; separate sponsor report tab in admin |
| Ability to send from specific addresses | `MassMessage.send_from_email` configurable; dropdown in UI |
| Goals / soft skill tracking | `soft_skills_baseline` & `soft_skills_current` on `ScholarProfile`; survey answers auto-update |
| Admin notifications control | Mass messaging + Celery automated reminders controlled by admins |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose, **or** Python 3.12 + Node 20 + PostgreSQL + Redis

### With Docker
```bash
cp .env.example .env          # edit as needed
docker-compose up --build

# In another terminal:
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py seed_demo
```

Open: http://localhost:3000

### Without Docker
```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

# In separate terminals:
celery -A config worker -l info
celery -A config beat -l info

# Frontend
cd frontend
npm install
npm run dev
```

---

## Demo Credentials (after seed_demo)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@spt.org | admin123 |
| Mentor | mentor1@example.com | password123 |
| Scholar | scholar1@example.com | password123 |

---

## API Documentation

Interactive Swagger UI: http://localhost:8000/api/docs/

### Key endpoints

| Endpoint | Description |
|---|---|
| `POST /api/auth/token/` | Login (returns JWT) |
| `GET/POST /api/users/` | List / create users (search, filter by role/cohort) |
| `POST /api/users/bulk_upload/` | Bulk import CSV/XLSX |
| `GET /api/users/export/` | Export all users as CSV |
| `GET /api/users/{id}/activity_summary/` | Last message sent/received |
| `GET /api/users/matches/unmatched_scholars/` | Scholars with no mentor |
| `GET /api/cohorts/cohorts/` | List cohorts |
| `POST /api/cohorts/cohorts/{id}/bulk_assign/` | Bulk-assign users to cohort |
| `GET /api/messaging/conversations/` | User's conversations |
| `POST /api/messaging/messages/` | Send a message (auto-moderated) |
| `POST /api/messaging/mass-messages/{id}/send/` | Trigger mass message send |
| `POST /api/messaging/abuse-reports/` | Report abuse |
| `GET /api/reports/contact/` | Scholar/Mentor contact report |
| `GET /api/reports/contact/?format=csv` | CSV export of contact report |
| `GET /api/reports/sponsor-updates/` | Sponsor update report |
| `GET /api/reports/users/` | Full user data report |
| `GET /api/moderation/flagged-messages/` | Moderation review queue |
| `POST /api/moderation/flagged-messages/{id}/approve/` | Approve flagged message |
| `POST /api/surveys/surveys/{id}/submit/` | Submit survey response |

---

## Safeguarding Notes

- All messages pass through `ModerationService` before delivery
- `BlockedTerm` entries immediately block messages; `FlaggedTerm` entries hold them for admin review
- Admins manage the terms list at `/api/moderation/blocked-terms/` and `/api/moderation/flagged-terms/`
- All moderation decisions are logged in `ModerationLog` (immutable audit trail)
- Mentors have `is_verified` + `dbs_check_date` + `dbs_certificate_number` fields
- Users can report any message via the abuse reporting system
- WebSocket connections require authenticated JWT tokens
