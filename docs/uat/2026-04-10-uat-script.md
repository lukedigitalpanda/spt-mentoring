# SPT Mentoring Platform — User Acceptance Testing Script

**Version:** 1.0
**Date:** 2026-04-10
**Scope:** Full platform — all modules
**Format:** Module-by-module narrative overview with detailed test cases

---

## How to Use This Document

Each module contains:
- A plain-English **overview** of what the module does
- A **test accounts required** note listing which user roles are needed
- A **test cases table** with numbered steps and expected results

### Test Case ID Format
`MODULE-##` — e.g. `MSG-01` is the first Messaging test case.

### Role Labels
Each test case is labelled with the role that performs it:

| Label | Role |
|---|---|
| **Scholar** | A mentee enrolled in the programme |
| **Mentor** | An assigned mentor |
| **Sponsor** | A programme sponsor |
| **Admin** | A staff/administrator user |

### Environment Setup

Before starting, confirm the following:

- [ ] The platform is running and accessible at its test URL
- [ ] The Django admin panel is accessible at `/admin/`
- [ ] At least one test account exists for each role: Scholar, Mentor, Sponsor, Admin
- [ ] Test accounts are members of a Programme and Cohort
- [ ] An active MentoringMatch exists between the test Scholar and test Mentor

---

## Module 1: Authentication & Registration

**Overview:** Users register for an account and log in to the platform. Each user has a role (Scholar, Mentor, Sponsor, Alumni). Password reset is handled via email.

**Test accounts required:** None initially (registration creates them). Admin account for verification.

---

### AUTH-01 — Scholar registration

| | |
|---|---|
| **Role** | Unregistered user |
| **Scenario** | A new Scholar registers for an account |
| **Pre-conditions** | Registration is open |
| **Steps** | 1. Navigate to the registration page. 2. Fill in name, email, password. 3. Select role: Scholar. 4. Submit the form. |
| **Expected Result** | Account is created. User is redirected to their dashboard or a confirmation screen. Admin can see the new user in `/admin/`. |

---

### AUTH-02 — Mentor registration

| | |
|---|---|
| **Role** | Unregistered user |
| **Scenario** | A new Mentor registers for an account |
| **Pre-conditions** | Registration is open |
| **Steps** | 1. Navigate to the registration page. 2. Fill in name, email, password. 3. Select role: Mentor. 4. Submit the form. |
| **Expected Result** | Account is created with Mentor role. User can log in. |

---

### AUTH-03 — Login with valid credentials

| | |
|---|---|
| **Role** | Any registered user |
| **Scenario** | User logs in successfully |
| **Pre-conditions** | Account exists |
| **Steps** | 1. Navigate to the login page. 2. Enter correct email and password. 3. Click Log In. |
| **Expected Result** | User is authenticated and redirected to their home dashboard. |

---

### AUTH-04 — Login with invalid credentials

| | |
|---|---|
| **Role** | Any user |
| **Scenario** | User attempts login with wrong password |
| **Pre-conditions** | Account exists |
| **Steps** | 1. Navigate to the login page. 2. Enter correct email but incorrect password. 3. Click Log In. |
| **Expected Result** | Login is rejected. An error message is displayed. The user is not redirected. |

---

### AUTH-05 — Password reset

| | |
|---|---|
| **Role** | Any registered user |
| **Scenario** | User requests a password reset |
| **Pre-conditions** | Account exists. Email delivery is configured in test environment. |
| **Steps** | 1. Click "Forgot password" on the login page. 2. Enter registered email address. 3. Submit. 4. Check email inbox. 5. Click the reset link. 6. Enter and confirm new password. |
| **Expected Result** | Password is changed. User can log in with the new password. |

---

## Module 2: User Profiles

**Overview:** Each user has a profile page showing their personal information, role-specific details (e.g. Mentor bio, Scholar programme info), and account settings. Users can edit their own profile.

**Test accounts required:** Scholar, Mentor, Sponsor

---

### USR-01 — Scholar views and edits their profile

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar updates their profile information |
| **Pre-conditions** | Logged in as Scholar |
| **Steps** | 1. Navigate to Profile page. 2. Review displayed information (name, email, programme). 3. Click Edit. 4. Update a field (e.g. bio or phone number). 5. Save changes. |
| **Expected Result** | Changes are saved and reflected immediately on the profile page. |

---

### USR-02 — Mentor views and edits their profile

| | |
|---|---|
| **Role** | Mentor |
| **Scenario** | Mentor updates their bio and availability information |
| **Pre-conditions** | Logged in as Mentor |
| **Steps** | 1. Navigate to Profile page. 2. Click Edit. 3. Update bio field. 4. Save. |
| **Expected Result** | Updated bio is saved and visible on the profile. |

---

### USR-03 — Sponsor views their profile

| | |
|---|---|
| **Role** | Sponsor |
| **Scenario** | Sponsor views their profile page |
| **Pre-conditions** | Logged in as Sponsor |
| **Steps** | 1. Navigate to Profile page. 2. Review displayed information. |
| **Expected Result** | Profile loads without errors and shows Sponsor-specific fields. |

---

### USR-04 — Data export

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | User requests a personal data export |
| **Pre-conditions** | Logged in as Scholar |
| **Steps** | 1. Navigate to account settings or profile page. 2. Locate the "Export my data" option. 3. Click Export. |
| **Expected Result** | A data file (JSON or CSV) is downloaded or an email is sent containing the user's data. |

---

### USR-05 — Account closure

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | User requests to close their account |
| **Pre-conditions** | Logged in as Scholar. Use a disposable test account. |
| **Steps** | 1. Navigate to account settings. 2. Click "Close account". 3. Confirm the action. |
| **Expected Result** | Account is deactivated. User is logged out. They cannot log back in. |

---

## Module 3: Mentor Discovery & Matching

**Overview:** Scholars can browse available mentors and join a waiting list. Admins create formal MentoringMatches that link a Scholar to a Mentor. When a match is created, a direct messaging conversation is automatically opened between the pair. Admins can also deactivate matches.

**Test accounts required:** Scholar, Mentor, Admin

---

### MATCH-01 — Scholar browses mentor discovery

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar views the Mentor Discovery page |
| **Pre-conditions** | Logged in as Scholar. At least one Mentor profile exists. |
| **Steps** | 1. Navigate to the Mentor Discovery page. 2. Browse listed mentors. 3. View a mentor's profile card. |
| **Expected Result** | Mentors are listed with their name, bio, and relevant details. Page loads without errors. |

---

### MATCH-02 — Scholar joins the waiting list

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar requests a mentor via the waiting list |
| **Pre-conditions** | Logged in as Scholar. Scholar is not yet matched. |
| **Steps** | 1. Navigate to Mentor Discovery. 2. Click "Join waiting list" or equivalent. 3. Confirm the request. |
| **Expected Result** | Scholar appears on the Admin waiting list. Confirmation is shown to the Scholar. |

---

### MATCH-03 — Admin creates a MentoringMatch

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin matches a Scholar to a Mentor |
| **Pre-conditions** | Logged in as Admin. Scholar and Mentor accounts both exist. |
| **Steps** | 1. Open Django admin at `/admin/`. 2. Navigate to Users > Mentoring Matches. 3. Click Add. 4. Select the Scholar and Mentor. 5. Save. |
| **Expected Result** | Match is created. Both Scholar and Mentor can see each other in their dashboard/messaging. A direct conversation is automatically created between them. |

---

### MATCH-04 — Match visible to both parties

| | |
|---|---|
| **Role** | Scholar, Mentor |
| **Scenario** | Both users see their match reflected in the UI |
| **Pre-conditions** | Active MentoringMatch exists between Scholar and Mentor |
| **Steps** | 1. Log in as Scholar. Confirm match is visible. 2. Log out. Log in as Mentor. Confirm Scholar appears as a match. |
| **Expected Result** | Both parties see the relationship reflected in their profile/home screen. |

---

### MATCH-05 — Admin deactivates a match

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin ends a mentoring relationship |
| **Pre-conditions** | Active MentoringMatch exists |
| **Steps** | 1. Open Django admin. 2. Navigate to Mentoring Matches. 3. Select the active match. 4. Set status to inactive. 5. Save. |
| **Expected Result** | Match is deactivated. Scholar and Mentor can still view historical messages but cannot send new ones. |

---

### MATCH-06 — Messaging blocked after match deactivation

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar attempts to send a message after match is deactivated |
| **Pre-conditions** | Match has been deactivated (see MATCH-05) |
| **Steps** | 1. Log in as Scholar. 2. Navigate to Messages. 3. Open the conversation with the Mentor. 4. Attempt to type and send a message. |
| **Expected Result** | Message is blocked. An appropriate error or UI indicator is shown. Historical messages remain visible. |

---

## Module 4: Messaging

**Overview:** The messaging system supports direct conversations between matched Scholar/Mentor pairs, group conversations, and sponsor updates. Messages pass through a moderation pipeline — flagged terms trigger review. Admins can send mass messages to role-based groups. Real-time delivery uses WebSockets.

**Test accounts required:** Scholar, Mentor, Admin

---

### MSG-01 — Scholar sends a message to their Mentor

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar sends a message in their shared conversation |
| **Pre-conditions** | Active MentoringMatch exists. Logged in as Scholar. |
| **Steps** | 1. Navigate to Messages. 2. Open the conversation with Mentor. 3. Type a message. 4. Send. |
| **Expected Result** | Message appears in the conversation. |

---

### MSG-02 — Mentor receives and replies to a message

| | |
|---|---|
| **Role** | Mentor |
| **Scenario** | Mentor receives and replies to the Scholar's message |
| **Pre-conditions** | MSG-01 completed |
| **Steps** | 1. Log in as Mentor. 2. Navigate to Messages. 3. Open the conversation with Scholar. 4. Confirm the Scholar's message is visible. 5. Type a reply. 6. Send. |
| **Expected Result** | Reply appears in the conversation and is visible to the Scholar. |

---

### MSG-03 — Real-time message delivery (WebSocket)

| | |
|---|---|
| **Role** | Scholar, Mentor |
| **Scenario** | Messages appear in real time without page refresh |
| **Pre-conditions** | Both Scholar and Mentor are logged in and have the conversation open simultaneously (use two browser windows). |
| **Steps** | 1. Open the conversation as Scholar in one window. 2. Open the same conversation as Mentor in another. 3. Scholar sends a message. 4. Observe Mentor's window. |
| **Expected Result** | Mentor's window shows the message immediately without a page refresh. |

---

### MSG-04 — Message containing a flagged term is moderated

| | |
|---|---|
| **Role** | Scholar, Admin |
| **Scenario** | A message containing a blocked/flagged term is intercepted |
| **Pre-conditions** | A blocked or flagged term is configured in Admin > Moderation. The term is known by the tester. |
| **Steps** | 1. Log in as Scholar. 2. Send a message containing the configured flagged term. |
| **Expected Result** | The message is not delivered or is marked as pending/flagged. The Admin can see it in the moderation queue. |

---

### MSG-05 — Scholar cannot message an unmatched Mentor

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar attempts to start a conversation with a Mentor they are not matched with |
| **Pre-conditions** | Scholar has no active match with the target Mentor |
| **Steps** | 1. Log in as Scholar. 2. Attempt to initiate a direct conversation with a non-matched Mentor (via API or UI if available). |
| **Expected Result** | Request is rejected. No conversation is created. |

---

### MSG-06 — Admin sends a mass message

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin sends a broadcast message to all Scholars |
| **Pre-conditions** | Logged in as Admin. Scholar accounts exist. |
| **Steps** | 1. Open Django admin. 2. Navigate to Mass Messages. 3. Create a new mass message. 4. Set recipient roles to "Scholar". 5. Write subject and body. 6. Send. |
| **Expected Result** | All Scholar accounts receive the message in their inbox. |

---

## Module 5: Forums

**Overview:** The forum is a structured discussion space with Forums > Threads > Posts. New posts are held in a moderation queue before being published. Admins can approve or reject posts and can send a direct message to a post author from the admin panel.

**Test accounts required:** Scholar, Admin

---

### FOR-01 — Scholar creates a new thread

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar starts a discussion in a forum |
| **Pre-conditions** | Logged in as Scholar. At least one Forum exists. |
| **Steps** | 1. Navigate to Forums. 2. Select a forum. 3. Click "New Thread". 4. Enter a title and body. 5. Submit. |
| **Expected Result** | Thread is created and appears in the forum (or is pending moderation). |

---

### FOR-02 — Scholar posts a reply in a thread

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar adds a post to an existing thread |
| **Pre-conditions** | Logged in as Scholar. At least one thread exists. |
| **Steps** | 1. Navigate to Forums. 2. Open a thread. 3. Write a reply in the post box. 4. Submit. |
| **Expected Result** | Post is submitted. A message indicates it is pending moderation (if applicable). |

---

### FOR-03 — Post appears in Admin moderation queue

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin sees the pending post in the moderation queue |
| **Pre-conditions** | FOR-02 completed |
| **Steps** | 1. Log in as Admin. 2. Navigate to Django admin > Forums > Posts. 3. Filter by status: Pending. |
| **Expected Result** | The Scholar's post appears with status "Pending Moderation". |

---

### FOR-04 — Admin approves a forum post

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin approves a pending post so it becomes publicly visible |
| **Pre-conditions** | A post exists with status Pending |
| **Steps** | 1. In the Admin moderation queue, select the pending post. 2. Use the "Approve" quick action. |
| **Expected Result** | Post status changes to Approved/Published. It becomes visible to forum users. |

---

### FOR-05 — Admin rejects a forum post

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin rejects an inappropriate post |
| **Pre-conditions** | A post exists with status Pending |
| **Steps** | 1. In the Admin moderation queue, select the pending post. 2. Use the "Reject" quick action. |
| **Expected Result** | Post status changes to Rejected. It is not visible to forum users. |

---

### FOR-06 — Admin messages post author from admin panel

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin sends a direct message to the author of a forum post |
| **Pre-conditions** | A post exists in the admin panel |
| **Steps** | 1. Navigate to the post in Django admin. 2. Click "Message Author" or equivalent inline action. 3. Write and send the message. |
| **Expected Result** | A message is sent to the post author. The author sees it in their Messages inbox. |

---

## Module 6: Mentoring Sessions

**Overview:** Mentors set their availability slots. Scholars can book sessions from available slots. After a session, both parties can submit feedback.

**Test accounts required:** Scholar, Mentor

---

### SES-01 — Mentor creates availability slots

| | |
|---|---|
| **Role** | Mentor |
| **Scenario** | Mentor sets times when they are available for sessions |
| **Pre-conditions** | Logged in as Mentor |
| **Steps** | 1. Navigate to Sessions. 2. Click "Add Availability". 3. Select date and time range. 4. Save. |
| **Expected Result** | Availability slot appears on the Mentor's schedule and is visible to matched Scholars. |

---

### SES-02 — Scholar books a session

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar books an available slot with their Mentor |
| **Pre-conditions** | Active match exists. Mentor has at least one availability slot (SES-01). |
| **Steps** | 1. Log in as Scholar. 2. Navigate to Sessions. 3. View available slots for their Mentor. 4. Select a slot and confirm booking. |
| **Expected Result** | Session is booked. Both Scholar and Mentor see it in their upcoming sessions. |

---

### SES-03 — Mentor submits session feedback

| | |
|---|---|
| **Role** | Mentor |
| **Scenario** | Mentor submits feedback after a completed session |
| **Pre-conditions** | A session has taken place (or is marked as completed). |
| **Steps** | 1. Log in as Mentor. 2. Navigate to Sessions. 3. Find the completed session. 4. Submit feedback (rating, notes). |
| **Expected Result** | Feedback is saved. Admin can view it. |

---

### SES-04 — Scholar submits session feedback

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar submits feedback after a completed session |
| **Pre-conditions** | A session has taken place. |
| **Steps** | 1. Log in as Scholar. 2. Navigate to Sessions. 3. Find the completed session. 4. Submit feedback. |
| **Expected Result** | Feedback is saved. Admin can view it. |

---

## Module 7: Goals & Milestones

**Overview:** Scholars can set goals to track their progress through the programme. Each goal can have one or more milestones. Mentors can view their Scholar's goals.

**Test accounts required:** Scholar, Mentor

---

### GOAL-01 — Scholar creates a goal

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar adds a new goal |
| **Pre-conditions** | Logged in as Scholar |
| **Steps** | 1. Navigate to Goals page. 2. Click "Add Goal". 3. Enter title and description. 4. Save. |
| **Expected Result** | Goal appears in the Scholar's goals list. |

---

### GOAL-02 — Scholar adds a milestone to a goal

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar breaks a goal into milestones |
| **Pre-conditions** | At least one goal exists (GOAL-01) |
| **Steps** | 1. Open the goal. 2. Click "Add Milestone". 3. Enter milestone title. 4. Save. |
| **Expected Result** | Milestone appears under the goal. |

---

### GOAL-03 — Scholar marks a milestone as complete

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar marks progress on a milestone |
| **Pre-conditions** | At least one milestone exists (GOAL-02) |
| **Steps** | 1. Open the goal. 2. Find the milestone. 3. Mark it as complete. |
| **Expected Result** | Milestone shows as completed. Goal progress is updated. |

---

### GOAL-04 — Mentor views Scholar's goals

| | |
|---|---|
| **Role** | Mentor |
| **Scenario** | Mentor reviews their Scholar's goals |
| **Pre-conditions** | Active match exists. Scholar has at least one goal. |
| **Steps** | 1. Log in as Mentor. 2. Navigate to the Scholar's profile or Goals section. 3. View listed goals. |
| **Expected Result** | Scholar's goals and milestone progress are visible to the Mentor. |

---

## Module 8: Surveys

**Overview:** Admins create surveys with questions to gather programme feedback. Scholars (and other roles) complete surveys. Admins can view response summaries.

**Test accounts required:** Scholar, Admin

---

### SRV-01 — Admin creates a survey

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin sets up a new survey |
| **Pre-conditions** | Logged in as Admin |
| **Steps** | 1. Open Django admin. 2. Navigate to Surveys. 3. Create a new survey with a title and at least 2 questions. 4. Save. |
| **Expected Result** | Survey is created and visible to the intended recipients. |

---

### SRV-02 — Scholar completes a survey

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar fills in and submits an active survey |
| **Pre-conditions** | Survey exists and is accessible to the Scholar (SRV-01) |
| **Steps** | 1. Log in as Scholar. 2. Navigate to Surveys page. 3. Open the survey. 4. Answer all questions. 5. Submit. |
| **Expected Result** | Submission is accepted. Scholar sees a confirmation. Survey cannot be resubmitted. |

---

### SRV-03 — Admin views survey responses

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin reviews submitted responses |
| **Pre-conditions** | At least one survey response exists (SRV-02) |
| **Steps** | 1. Open Django admin. 2. Navigate to Survey Responses. 3. Select the survey. 4. View responses. |
| **Expected Result** | Responses are listed with answers per question and respondent. |

---

## Module 9: Resources

**Overview:** Admins publish resources (documents, links) organised by category. Scholars and other users can browse and view them. Users can also upload shared documents.

**Test accounts required:** Scholar, Admin

---

### RES-01 — Admin creates a resource category and resource

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin publishes a new resource |
| **Pre-conditions** | Logged in as Admin |
| **Steps** | 1. Open Django admin. 2. Navigate to Resources > Categories. 3. Create a category. 4. Navigate to Resources. 5. Add a resource linked to the category. 6. Save. |
| **Expected Result** | Resource appears in the Resources page under the correct category. |

---

### RES-02 — Scholar browses and views a resource

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar finds and opens a resource |
| **Pre-conditions** | At least one resource exists (RES-01). Logged in as Scholar. |
| **Steps** | 1. Navigate to Resources page. 2. Browse categories. 3. Click on a resource to open or download it. |
| **Expected Result** | Resource loads or downloads correctly. |

---

### RES-03 — Scholar uploads a shared document

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar uploads a document to share |
| **Pre-conditions** | Logged in as Scholar |
| **Steps** | 1. Navigate to Resources or Profile. 2. Find the Shared Documents section. 3. Upload a file. |
| **Expected Result** | File is uploaded and visible (to the appropriate audience). |

---

## Module 10: News

**Overview:** Admins publish news articles and promotional banners that appear on the platform home screen and news feed. All users can read them.

**Test accounts required:** Scholar, Admin

---

### NEWS-01 — Admin publishes a news item

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin creates and publishes a news article |
| **Pre-conditions** | Logged in as Admin |
| **Steps** | 1. Open Django admin. 2. Navigate to News > News Items. 3. Click Add. 4. Enter title, body, and publish date. 5. Save. |
| **Expected Result** | News item appears in the platform news feed. |

---

### NEWS-02 — Scholar views a news article

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar reads a published news article |
| **Pre-conditions** | At least one news item is published (NEWS-01) |
| **Steps** | 1. Log in as Scholar. 2. Navigate to News page. 3. Click on the article. |
| **Expected Result** | Article loads and displays correctly. |

---

### NEWS-03 — Admin creates a promotional banner

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin adds a promotional banner visible on the home screen |
| **Pre-conditions** | Logged in as Admin |
| **Steps** | 1. Open Django admin. 2. Navigate to News > Promotional Banners. 3. Add a banner with image and link. 4. Save. |
| **Expected Result** | Banner appears on the home/dashboard screen for users. |

---

## Module 11: Notifications

**Overview:** The platform sends in-app notifications for key events (new messages, session bookings, etc.). Users can also enable browser push notifications.

**Test accounts required:** Scholar

---

### NOTIF-01 — Scholar receives an in-app notification

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar receives a notification triggered by a platform event |
| **Pre-conditions** | Logged in as Scholar. Trigger an event (e.g. Mentor sends a message). |
| **Steps** | 1. Log in as Scholar. 2. Trigger an event that generates a notification (e.g. have Mentor send a message). 3. Check the notifications icon/page. |
| **Expected Result** | Notification appears in the Scholar's notifications list. |

---

### NOTIF-02 — Scholar enables push notifications

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar opts in to browser push notifications |
| **Pre-conditions** | Logged in as Scholar. Browser supports push notifications. |
| **Steps** | 1. Navigate to notification settings or respond to the browser prompt. 2. Click "Enable push notifications". 3. Grant browser permission when prompted. |
| **Expected Result** | Push subscription is saved. Scholar receives a push notification when a relevant event occurs (e.g. new message). |

---

## Module 12: Moderation & Reporting

**Overview:** The platform has a content moderation pipeline. Blocked terms prevent message/post delivery. Flagged terms trigger a review queue. Users can report abuse on messages. Admins review and resolve reports via the admin panel.

**Test accounts required:** Scholar, Admin

---

### MOD-01 — Scholar reports a message for abuse

| | |
|---|---|
| **Role** | Scholar |
| **Scenario** | Scholar reports a message they consider inappropriate |
| **Pre-conditions** | Logged in as Scholar. A message exists in a conversation. |
| **Steps** | 1. Open the conversation. 2. Find a message. 3. Click "Report" on the message. 4. Confirm the report. |
| **Expected Result** | Abuse report is created. Admin can see it in the admin panel under Abuse Reports. |

---

### MOD-02 — Admin reviews an abuse report

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin investigates a reported message |
| **Pre-conditions** | Abuse report exists (MOD-01) |
| **Steps** | 1. Open Django admin. 2. Navigate to Messaging > Abuse Reports. 3. Open the report. 4. Review the reported message and reporter. |
| **Expected Result** | Report details are displayed correctly including reporter, reported user, and message content. |

---

### MOD-03 — Admin resolves an abuse report

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin marks an abuse report as resolved |
| **Pre-conditions** | Abuse report exists and is Open or Under Review |
| **Steps** | 1. Open the abuse report in Django admin. 2. Change status to Resolved. 3. Save. |
| **Expected Result** | Report status updates to Resolved. It no longer appears in the active queue. |

---

### MOD-04 — Blocked term prevents message delivery

| | |
|---|---|
| **Role** | Scholar, Admin |
| **Scenario** | A message containing a blocked term is stopped from being delivered |
| **Pre-conditions** | A blocked term is configured in Admin > Moderation > Blocked Terms. The term is known by the tester. |
| **Steps** | 1. Log in as Scholar. 2. Send a message containing the exact blocked term. |
| **Expected Result** | Message is not delivered. Scholar receives an error or the message is silently blocked. Admin can confirm no message was delivered. |

---

### MOD-05 — Support conversation resolved by Admin

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin resolves an open support conversation |
| **Pre-conditions** | A support-type conversation exists with status Open |
| **Steps** | 1. Open Django admin dashboard. 2. Find the support conversation in the todo panel or Conversations list. 3. Click Resolve. |
| **Expected Result** | Conversation status changes to Resolved. It no longer appears in the support counter on the dashboard. |

---

## Module 13: Admin Panel

**Overview:** The Django admin panel (enhanced with Jazzmin theme) is the primary management interface for SPT staff. It includes a custom dashboard with a todo panel (flagged messages, pending posts, open support tickets), quick moderation actions, and app management cards.

**Test accounts required:** Admin

---

### ADM-01 — Admin dashboard loads correctly

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin opens the dashboard and sees the todo panel and app cards |
| **Pre-conditions** | Logged in as Admin. Navigate to `/admin/`. |
| **Steps** | 1. Open `/admin/`. 2. Observe the left sidebar navigation. 3. Observe the main content area. |
| **Expected Result** | Left sidebar is visible with navigation links. Main content shows the todo panel (pending items) and app cards with View/Add buttons. |

---

### ADM-02 — Admin todo panel shows pending items

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin sees outstanding moderation tasks on the dashboard |
| **Pre-conditions** | At least one flagged message, pending post, or open support ticket exists |
| **Steps** | 1. Open `/admin/`. 2. Review the todo panel. |
| **Expected Result** | Todo panel shows counts for: flagged messages, pending forum posts, open support conversations. Each is a clickable link. |

---

### ADM-03 — Admin quick-moderates a forum post

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin approves or rejects a post directly from the post list view |
| **Pre-conditions** | At least one pending forum post exists |
| **Steps** | 1. Navigate to Django admin > Forums > Posts. 2. Filter by status: Pending. 3. Click Approve or Reject next to a post (quick action). |
| **Expected Result** | Post status updates immediately. No full page reload required for the action. |

---

### ADM-04 — Admin impersonates a user

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin views the platform as a specific user |
| **Pre-conditions** | Logged in as Admin. A Scholar or Mentor account exists. |
| **Steps** | 1. Navigate to Django admin > Users. 2. Select a user. 3. Click "Impersonate" or equivalent action. |
| **Expected Result** | Admin is now browsing the platform as that user. A clear indicator shows impersonation mode is active. |

---

### ADM-05 — Admin views mentoring reports

| | |
|---|---|
| **Role** | Admin |
| **Scenario** | Admin reviews mentoring programme reports |
| **Pre-conditions** | Logged in as Admin. Some activity exists on the platform. |
| **Steps** | 1. Open Django admin. 2. Navigate to Reports > Mentoring Reports. 3. View report list. |
| **Expected Result** | Reports are listed with relevant data. Filters or export options are available. |

---

*End of UAT Script — SPT Mentoring Platform v1.0*
