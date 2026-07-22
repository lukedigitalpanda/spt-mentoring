# Jazzmin Admin Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stock Django admin shell with Jazzmin to get a persistent sidebar navigator, SPT-branded colour scheme, and icon-annotated model links — eliminating the main navigational friction in the current admin.

**Architecture:** Install `jazzmin` before `django.contrib.admin` in INSTALLED_APPS; configure it entirely through `JAZZMIN_SETTINGS` and `JAZZMIN_UI_TWEAKS` in settings.py; retire the hand-rolled `base_site.html` (Jazzmin handles branding via settings); keep the custom `index.html` todo panel and all custom admin views untouched; provide a new `jazzmin.css` to paint AdminLTE with SPT navy/purple/pink tokens.

**Tech Stack:** Django 4.2, django-jazzmin 2.x, AdminLTE 3, Bootstrap 4, Font Awesome 5 Free

---

## File map

| Action | File | Purpose |
|--------|------|---------|
| Modify | `backend/requirements.txt` | Add `jazzmin` package |
| Modify | `backend/config/settings.py` | Add jazzmin to INSTALLED_APPS; add JAZZMIN_SETTINGS + JAZZMIN_UI_TWEAKS |
| Delete | `backend/templates/admin/base_site.html` | Jazzmin takes over branding/layout; config moves to settings |
| Modify | `backend/templates/admin/index.html` | No template change needed — works as-is once base_site.html is removed |
| Create | `backend/static/admin/css/jazzmin.css` | SPT colour overrides on AdminLTE/Bootstrap classes |
| Keep   | `backend/static/admin/css/form_fix.css` | Unchanged — still loaded via FormFixMixin |
| Keep   | `backend/templates/admin/todo_panel.html` | Unchanged — still rendered via template tag |
| Keep   | All `apps/*/admin.py` custom views | Untouched — custom URLs/views survive Jazzmin |

---

## Task 1 — Install jazzmin

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add jazzmin to requirements.txt**

Open `backend/requirements.txt` and add this line after the existing packages:

```
jazzmin==2.6.0
```

- [ ] **Step 2: Install into the running container**

```bash
docker compose exec backend pip install jazzmin==2.6.0
```

Expected output ends with: `Successfully installed jazzmin-2.6.0`

- [ ] **Step 3: Verify import works**

```bash
docker compose exec backend python -c "import jazzmin; print(jazzmin.__version__)"
```

Expected: `2.6.0`

---

## Task 2 — Wire Jazzmin into Django settings

**Files:**
- Modify: `backend/config/settings.py`

- [ ] **Step 1: Add jazzmin to INSTALLED_APPS before django.contrib.admin**

In `backend/config/settings.py`, change:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
```

to:

```python
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
```

**Critical:** `jazzmin` must come *before* `django.contrib.admin` so its templates take precedence.

- [ ] **Step 2: Add JAZZMIN_SETTINGS block at end of settings.py**

Append to the bottom of `backend/config/settings.py`:

```python
# ── Jazzmin admin theme ───────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    # ── Branding ──────────────────────────────────────────────────────────────
    "site_title": "SPT Mentoring Admin",
    "site_header": "SPT Mentoring",
    "site_brand": "Mentoring",
    "site_logo": "admin/img/sptlogo.webp",
    "login_logo": "admin/img/sptlogo.webp",
    "login_logo_dark": "admin/img/sptlogo.webp",
    "site_logo_classes": None,
    "site_icon": None,
    "welcome_sign": "Helping young people become future engineers",
    "copyright": "Smallpeice Trust",

    # ── Search ────────────────────────────────────────────────────────────────
    "search_model": ["users.User"],
    "user_avatar": None,

    # ── Top menu ──────────────────────────────────────────────────────────────
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "View Site", "url": "https://mentoring.smallpeice.online", "new_window": True},
        {"app": "users"},
    ],

    # ── User dropdown ─────────────────────────────────────────────────────────
    "usermenu_links": [
        {"name": "View Site", "url": "https://mentoring.smallpeice.online", "new_window": True},
        {"model": "users.User"},
    ],

    # ── Sidebar nav ───────────────────────────────────────────────────────────
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": ["auth", "guardian"],
    "hide_models": [],

    # Order sidebar sections
    "order_with_respect_to": [
        "users",
        "messaging",
        "forums",
        "cohorts",
        "resources",
        "news",
        "surveys",
        "sessions",
        "goals",
        "moderation",
        "notifications",
        "reports",
    ],

    # Custom sidebar links (Matching Wizard, Reports)
    "custom_links": {
        "users": [
            {
                "name": "Matching Wizard",
                "url": "admin:users_mentoringmatch_wizard",
                "icon": "fas fa-magic",
                "permissions": ["users.add_mentoringmatch"],
            }
        ],
        "reports": [
            {
                "name": "Mentoring Report",
                "url": "/admin/reports/mentoring/",
                "icon": "fas fa-chart-bar",
            }
        ],
    },

    # ── Model icons ───────────────────────────────────────────────────────────
    "icons": {
        "users.User":               "fas fa-user",
        "users.MentoringMatch":     "fas fa-handshake",
        "users.ScholarProfile":     "fas fa-graduation-cap",
        "users.MentorProfile":      "fas fa-chalkboard-teacher",
        "users.SponsorProfile":     "fas fa-building",
        "users.MentorWaitingList":  "fas fa-clock",
        "messaging.Conversation":   "fas fa-comments",
        "messaging.Message":        "fas fa-envelope",
        "messaging.AbuseReport":    "fas fa-flag",
        "messaging.MassMessage":    "fas fa-bullhorn",
        "forums.Forum":             "fas fa-layer-group",
        "forums.Thread":            "fas fa-list-ul",
        "forums.Post":              "fas fa-comment-alt",
        "cohorts.Programme":        "fas fa-project-diagram",
        "cohorts.Cohort":           "fas fa-users",
        "cohorts.CohortMembership": "fas fa-user-check",
        "cohorts.SiteSettings":     "fas fa-cog",
        "resources.ResourceCategory": "fas fa-folder",
        "resources.Resource":       "fas fa-file-alt",
        "resources.SharedDocument": "fas fa-file-upload",
        "news.NewsItem":            "fas fa-newspaper",
        "news.PromotionalBanner":   "fas fa-ad",
        "surveys.Survey":           "fas fa-poll",
        "surveys.Question":         "fas fa-question-circle",
        "surveys.SurveyResponse":   "fas fa-check-square",
        "sessions.AvailabilitySlot": "fas fa-calendar",
        "sessions.MentoringSession": "fas fa-calendar-check",
        "sessions.SessionFeedback": "fas fa-star",
        "goals.Goal":               "fas fa-bullseye",
        "goals.GoalMilestone":      "fas fa-flag-checkered",
        "moderation.BlockedTerm":   "fas fa-ban",
        "moderation.FlaggedTerm":   "fas fa-exclamation-triangle",
        "moderation.ModerationLog": "fas fa-clipboard-list",
        "notifications.Notification": "fas fa-bell",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    # ── Related modal ─────────────────────────────────────────────────────────
    "related_modal_active": False,

    # ── Custom assets ─────────────────────────────────────────────────────────
    "custom_css": "admin/css/jazzmin.css",
    "custom_js": None,
    "use_google_fonts_cdn": True,

    # ── Change form layout ────────────────────────────────────────────────────
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "users.user": "collapsible",
        "users.scholarprofile": "collapsible",
        "users.mentorprofile": "collapsible",
    },
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,        # Overridden in jazzmin.css
    "accent": "accent-purple",
    "navbar": "navbar-dark",      # Dark top bar; colour set in jazzmin.css
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",  # Primary overridden to SPT purple in jazzmin.css
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
    "actions_sticky_top": True,
}
```

- [ ] **Step 3: Verify Django can read settings without error**

```bash
docker compose exec backend python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

If you see `ModuleNotFoundError: No module named 'jazzmin'`, re-run Task 1 Step 2.

---

## Task 3 — Create the SPT colour override stylesheet

**Files:**
- Create: `backend/static/admin/css/jazzmin.css`

Jazzmin uses AdminLTE 3 + Bootstrap 4. The existing `brand.css` targets Django admin's own CSS variables — those no longer apply. This new file maps SPT tokens onto AdminLTE/Bootstrap selectors.

- [ ] **Step 1: Create `backend/static/admin/css/jazzmin.css`**

```css
/*
 * SPT Mentoring — Jazzmin colour overrides
 * Paints AdminLTE 3 / Bootstrap 4 with SPT brand tokens.
 *
 * Tokens:
 *   navy   #1d1464
 *   purple #4527a0
 *   pink   #e01e8c
 *   orange #f5821e
 */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Typography ─────────────────────────────────────────────────────────── */
body,
.nav-sidebar .nav-link,
.brand-text,
.content-header h1 {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* ── Top navbar (navy) ──────────────────────────────────────────────────── */
.main-header.navbar {
  background-color: #1d1464 !important;
  border-bottom: 2px solid #4527a0 !important;
}
.main-header .navbar-nav .nav-link,
.main-header .navbar-nav .nav-link:hover,
.main-header .nav-item .nav-link {
  color: rgba(255, 255, 255, 0.9) !important;
}
.main-header .navbar-nav .nav-link:hover {
  color: #e01e8c !important;
}

/* ── Sidebar (navy → purple gradient) ──────────────────────────────────── */
.main-sidebar,
.main-sidebar::before {
  background: linear-gradient(180deg, #1d1464 0%, #2d1e8a 100%) !important;
}
.brand-link {
  background: #1d1464 !important;
  border-bottom: 1px solid rgba(255,255,255,0.12) !important;
}
.brand-link:hover {
  background: #4527a0 !important;
}
.brand-text {
  color: #fff !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em;
}

/* Sidebar nav items */
.nav-sidebar .nav-item > .nav-link {
  color: rgba(255, 255, 255, 0.75) !important;
  border-radius: 8px !important;
  margin: 1px 6px !important;
  transition: background 0.15s, color 0.15s;
}
.nav-sidebar .nav-item > .nav-link:hover {
  background: rgba(255, 255, 255, 0.10) !important;
  color: #fff !important;
}
.nav-sidebar .nav-item > .nav-link.active,
.nav-sidebar .nav-item.menu-open > .nav-link {
  background: #4527a0 !important;
  color: #fff !important;
  font-weight: 600;
}
.nav-sidebar .nav-treeview .nav-link {
  color: rgba(255, 255, 255, 0.65) !important;
}
.nav-sidebar .nav-treeview .nav-link:hover,
.nav-sidebar .nav-treeview .nav-link.active {
  background: rgba(229, 30, 140, 0.18) !important;
  color: #f9c5e2 !important;
}

/* Sidebar header labels */
.nav-header {
  color: rgba(255, 255, 255, 0.45) !important;
  font-size: 10px !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  padding: 10px 14px 4px !important;
}

/* Sidebar search box */
.sidebar-form .input-group .form-control {
  background: rgba(255,255,255,0.10) !important;
  border-color: rgba(255,255,255,0.15) !important;
  color: #fff !important;
}
.sidebar-form .input-group .form-control::placeholder { color: rgba(255,255,255,0.45) !important; }

/* ── Brand / logo area ──────────────────────────────────────────────────── */
.brand-link .brand-image { max-height: 32px; margin-top: 0; }

/* ── Content area ───────────────────────────────────────────────────────── */
.content-wrapper { background: #f8f7fc !important; }
.card { border-radius: 12px !important; border: 1px solid #e8e4f5 !important; }
.card-header {
  background: linear-gradient(90deg, #4527a0 0%, #6a3fc8 100%) !important;
  color: #fff !important;
  border-radius: 11px 11px 0 0 !important;
  font-weight: 600;
}
.card-header a { color: rgba(255,255,255,0.85) !important; }

/* ── Buttons ────────────────────────────────────────────────────────────── */
.btn-primary,
input[type="submit"],
.submit-row input[type="submit"] {
  background-color: #4527a0 !important;
  border-color: #4527a0 !important;
  color: #fff !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
}
.btn-primary:hover,
input[type="submit"]:hover {
  background-color: #e01e8c !important;
  border-color: #e01e8c !important;
}
.btn-secondary {
  border-radius: 8px !important;
}
.btn-danger {
  border-radius: 8px !important;
}

/* ── Links ──────────────────────────────────────────────────────────────── */
a:not(.btn):not(.nav-link):not(.brand-link) { color: #4527a0; }
a:not(.btn):not(.nav-link):not(.brand-link):hover { color: #e01e8c; }

/* ── Breadcrumbs ────────────────────────────────────────────────────────── */
.content-header .breadcrumb { background: transparent !important; }
.content-header .breadcrumb-item a { color: #4527a0; }
.content-header .breadcrumb-item.active { color: #6b6b8a; }

/* ── Data tables / changelists ──────────────────────────────────────────── */
.table thead th {
  background: #f0edf8 !important;
  color: #1d1464 !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #cdc6e8 !important;
}
.table tbody tr:hover td { background: #fdf0f8 !important; }
#result_list tbody tr:hover { background: #fdf0f8; }

/* Selected row checkbox */
#result_list tbody tr.selected { background: #ede9f8 !important; }

/* ── Changelist filters ─────────────────────────────────────────────────── */
#changelist-filter h2 {
  background: #4527a0 !important;
  color: #fff !important;
}
#changelist-filter h3 { color: #4527a0 !important; }
#changelist-filter li.selected a { color: #e01e8c !important; font-weight: 700; }

/* ── Form fields ────────────────────────────────────────────────────────── */
.form-control:focus,
input:focus,
select:focus,
textarea:focus {
  border-color: #4527a0 !important;
  box-shadow: 0 0 0 3px rgba(69, 39, 160, 0.12) !important;
}

/* ── Dashboard grid (from custom index.html) ────────────────────────────── */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  margin-top: 8px;
}
.app-card {
  background: #fff;
  border: 1px solid #e8e4f5;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 6px rgba(69,39,160,0.07);
  transition: box-shadow 0.15s;
}
.app-card:hover { box-shadow: 0 4px 16px rgba(69,39,160,0.13); }
.app-card-header {
  background: linear-gradient(90deg,#4527a0 0%,#6a3fc8 100%);
  padding: 10px 16px;
}
.app-card-title {
  color: #fff !important;
  font-weight: 700;
  font-size: 0.85rem;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.app-card-body { padding: 8px 0; }
.model-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 16px;
  border-bottom: 1px solid #f3f0fb;
}
.model-row:last-child { border-bottom: none; }
.model-name a { color: #4527a0; font-weight: 500; }
.model-actions { display: flex; gap: 6px; }
.model-action-btn {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 6px;
  border: 1px solid;
  text-decoration: none !important;
  font-weight: 600;
  transition: all 0.12s;
}
.view-btn { color: #4527a0 !important; border-color: #cdc6e8 !important; }
.view-btn:hover { background: #4527a0 !important; color: #fff !important; border-color: #4527a0 !important; }
.add-btn { color: #e01e8c !important; border-color: #f0b8d8 !important; }
.add-btn:hover { background: #e01e8c !important; color: #fff !important; border-color: #e01e8c !important; }

/* ── Footer ─────────────────────────────────────────────────────────────── */
.main-footer {
  background: #fff !important;
  border-top: 1px solid #e8e4f5 !important;
  color: #6b6b8a !important;
  font-size: 12px !important;
}
.main-footer a { color: #4527a0; }

/* ── Form layout fixes (carried over from form_fix.css logic) ───────────── */
.aligned .form-row {
  display: flex !important;
  align-items: flex-start !important;
  gap: 12px !important;
  overflow: visible !important;
  flex-wrap: wrap !important;
}
.aligned label:not(.vCheckboxLabel) {
  float: none !important;
  width: 160px !important;
  flex-shrink: 0 !important;
  padding-top: 10px !important;
  box-sizing: border-box !important;
}
.aligned .form-row > div,
.aligned .form-row .related-widget-wrapper,
.aligned .form-row p.readonly {
  flex: 1 1 auto !important;
  min-width: 200px !important;
}
.aligned .form-row select,
.aligned .form-row .vSelect {
  width: 100% !important;
  max-width: 500px !important;
  height: auto !important;
  box-sizing: border-box !important;
}
.submit-row {
  overflow: visible !important;
  display: flex !important;
  align-items: center !important;
  flex-wrap: wrap !important;
  gap: 10px !important;
}
.inline-group .tabular { overflow-x: auto !important; display: block !important; }
.module, .inline-group { overflow: visible !important; }
```

---

## Task 4 — Remove base_site.html

**Files:**
- Delete: `backend/templates/admin/base_site.html`

All the functionality it provided is now handled by Jazzmin settings:
- Title → `JAZZMIN_SETTINGS["site_title"]`
- Logo → `JAZZMIN_SETTINGS["site_logo"]`
- Brand CSS → `JAZZMIN_SETTINGS["custom_css"]` pointing at `jazzmin.css`
- Announcement text → `JAZZMIN_SETTINGS["welcome_sign"]`
- Footer text → `JAZZMIN_SETTINGS["copyright"]`
- Form-fix CSS → duplicated at the bottom of `jazzmin.css`

- [ ] **Step 1: Delete base_site.html**

```bash
rm /opt/spt-mentoring/backend/templates/admin/base_site.html
```

- [ ] **Step 2: Confirm the file is gone**

```bash
ls /opt/spt-mentoring/backend/templates/admin/
```

Expected: `base_site.html` is NOT in the listing. `index.html`, `login.html`, `todo_panel.html` remain.

---

## Task 5 — Restart and smoke-test

- [ ] **Step 1: Restart the backend**

```bash
docker compose restart backend
```

Wait ~10 seconds for Daphne to come up.

- [ ] **Step 2: Run Django system check**

```bash
docker compose exec backend python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Visit the admin and verify**

Open `http://localhost/admin/` (or the production URL).

Check:
- [ ] Sidebar appears on the left with app sections
- [ ] SPT logo visible in top-left brand area
- [ ] Top navbar is navy (#1d1464)
- [ ] Sidebar background is navy-to-purple gradient
- [ ] Active nav item highlights in purple (#4527a0)
- [ ] Dashboard shows the todo_panel and app cards
- [ ] Clicking a model link navigates without page errors
- [ ] Matching Wizard link appears under Users section in sidebar
- [ ] Font is Inter

- [ ] **Step 4: Check the moderation queue workflow still works**

Navigate to Forums → Posts → filter by Flagged.
- [ ] ✅ Approve and ❌ Reject buttons visible on list rows
- [ ] Clicking Approve redirects to next flagged post (or filtered list)

- [ ] **Step 5: Check a change form**

Open any User record. Verify:
- [ ] Form renders in horizontal/collapsible tab layout (not one giant page)
- [ ] Save button is SPT purple, hover goes pink

---

## Task 6 — Bake jazzmin into the Docker image

Once you're happy with the result in the running container, rebuild to make it permanent.

- [ ] **Step 1: Rebuild the backend image**

```bash
docker compose build backend
```

This re-runs `pip install -r requirements.txt` which now includes `jazzmin==2.6.0`.

- [ ] **Step 2: Restart with the new image**

```bash
docker compose up -d backend
```

- [ ] **Step 3: Final system check**

```bash
docker compose exec backend python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

---

## Known edge cases

**Login page** — Jazzmin provides its own login template. Our existing `templates/admin/login.html` will override it. Check that the login page still works after Task 5 Step 3. If it looks broken, either delete it (let Jazzmin handle it with `login_logo` setting) or update it to extend `jazzmin/login.html`.

**FormFixMixin** — Several admin classes use `FormFixMixin` which injects `form_fix.css`. That CSS is now redundant (the same rules are in `jazzmin.css`). It won't cause errors — just a small amount of duplicate CSS. You can remove `FormFixMixin` and the `form_fix.css` file as a follow-up cleanup if desired.

**`brand.css`** — This file still exists in `static/admin/css/` but is no longer referenced by any template (since `base_site.html` is deleted). It is harmless to leave it; delete it in a follow-up cleanup if preferred.

**`jazzmin` version** — If `2.6.0` is not on PyPI at install time, try `pip install jazzmin` (latest) and pin the version that installs.
