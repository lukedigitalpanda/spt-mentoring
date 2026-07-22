# SPT Mentoring Platform — System Overview

*Prepared for executive review · June 2026*

---

## 1. What it is

The SPT Mentoring Platform is a secure, web-based system that runs the SPT Scholar
Mentoring Programme end to end. It connects four groups of people — **Scholars**
(the young people we support), **Mentors**, **Sponsors** (funders), and **SPT
staff/Admins** — in one safeguarded environment, and gives staff the tools to
manage matches, monitor contact, and report on the programme.

In short: it replaces a patchwork of spreadsheets, email threads, and manual
chasing with a single, auditable system built around safeguarding.

---

## 2. What it does (functionality)

**For Scholars and Mentors**
- **Profiles** for everyone, with mentor specialisms, capacity, and verification status.
- **Moderated messaging** — real-time 1:1 chat. Every message is automatically
  screened before it is delivered (more in *Safeguarding* below).
- **Mentoring sessions** — schedule 1:1 sessions, join by video call, and capture
  post-session feedback and ratings.
- **Goals & soft-skill tracking** — Scholars set goals with milestones across
  categories; progress feeds into soft-skill scores over time.
- **Forums** — community and group discussion spaces (open, programme-wide, or private).
- **Resource bank** — curated documents, links, and videos, targeted to the right audience.
- **News & home page** — announcements and promotional banners.
- **Surveys** — feedback collection that automatically updates soft-skill measures.
- **Notifications** — in-app and browser push notifications.
- **Report-abuse button** — anyone can flag concerning content for staff review.

**For Sponsors**
- A dedicated update channel and reporting so funders receive regular progress
  on the Scholars they support.

**For SPT staff / Admins**
- **Matching** — assign Mentors to Scholars (a Mentor can support several Scholars),
  and see which Scholars are still unmatched.
- **Cohorts & programmes** — organise users into programmes and cohorts, with
  bulk assignment and per-programme branding (colours/logo).
- **Bulk data management** — import users from CSV/Excel and export data back out;
  CRM-friendly with a CRM ID on every user.
- **Mass messaging** — send targeted announcements by role or cohort, from a
  chosen sending address (e.g. mentoring@ or scholarships@).
- **Automated chasing** — the system automatically reminds Scholars to update
  Sponsors and nudges mentor/scholar pairs who haven't been in contact.
- **Reporting** — contact-frequency, sponsor-update, cohort-progress, and full
  user reports, all exportable to CSV.
- **Moderation queue** — review flagged messages, manage blocked/flagged terms,
  and rely on a full, immutable audit trail of every decision.

---

## 3. Safeguarding (a core design principle, not an add-on)

Because the platform serves young people, safeguarding is built into the foundations:

- **Every** message and forum post is screened by a moderation service *before* delivery.
- Two-tier term control: some terms **block** content immediately; others **hold**
  it for staff review.
- All moderation actions are recorded in an **immutable audit log**.
- Mentors carry **verification and DBS-check** fields.
- All real-time connections require an authenticated, secure login.

---

## 4. How it's built (technology)

The platform follows a modern, industry-standard architecture that is reliable,
secure, and straightforward to maintain.

| Layer | Technology | Why it matters |
|---|---|---|
| **Web app (what users see)** | React + TypeScript | Fast, modern, mobile-friendly interface |
| **Backend / API** | Python (Django + Django REST Framework) | Mature, secure, widely supported — easy to hire for |
| **Real-time chat & notifications** | WebSockets (Django Channels) | Instant messaging without page refreshes |
| **Database** | PostgreSQL | Robust, proven, enterprise-grade data storage |
| **Background jobs** | Celery + Redis | Runs automated reminders and bulk emails reliably |
| **Hosting / deployment** | Docker containers behind Nginx | Consistent, portable, repeatable deployments |
| **Security** | JWT login with automatic session refresh | Secure, standards-based authentication |

**Quality & maintainability**
- Comprehensive automated test suite covering core safeguarding and messaging logic.
- Full, interactive API documentation (Swagger).
- Version-controlled, containerised setup — the whole system can be stood up with a
  single command, which de-risks onboarding new developers and disaster recovery.

---

## 5. Status & maturity

The platform is **live in production** and has completed **two rounds of User
Acceptance Testing (UAT)** with the SPT team, with fixes verified and deployed.
All "must-have" requirements from the original specification are implemented, along
with several "nice-to-have" items (alumni access, dedicated sponsor area,
configurable sending addresses, and goal/soft-skill tracking).

---

## 6. The bottom line

The SPT Mentoring Platform gives SPT a single, safeguarded home for its mentoring
programme. It automates the manual, time-consuming parts (chasing contact, sending
reminders, compiling reports) while keeping young people's safety at the centre of
every interaction. It is built on mainstream, well-supported technology, which keeps
long-term running costs and key-person risk low.
