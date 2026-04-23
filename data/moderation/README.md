# Moderation Terms

## What is this?

`moderation_terms.txt` is a plain-text list of terms (one per line) that the
platform screens for in every message sent between users.  It covers:

- Literal profanity and slurs
- Obfuscated variants (e.g. `sh1t`, `a$$hole`, `f.u.c.k`)
- Multi-word safeguarding phrases (e.g. `how to kill`, `how to murder`)
- Drug and alcohol references
- Contact-detail leak patterns (email addresses, URLs, Microsoft Teams handles)

The list is maintained externally and loaded into the database via a Django
management command.  It does **not** live in the database directly — this file
is the single source of truth.

## Where does the list come from?

The file is provided by the SPT platform team and should be stored at:

```
data/moderation/moderation_terms.txt
```

It is excluded from version control via `.gitignore` because it contains
distressing content.  To obtain a fresh copy, contact the platform lead.

## How to import (or re-import) the list

Place the updated `moderation_terms.txt` file in `data/moderation/`, then run
inside the backend container:

```bash
docker exec spt-mentoring-backend-1 python manage.py import_moderation_terms
```

The command is **idempotent** — safe to run multiple times.  On each run it:

1. Creates new rows for terms not yet in the database.
2. Updates classification fields (`category`, `severity`) on existing rows that
   came from the same source tag (`bulk_import_v1`).
3. Re-activates any rows that were previously deactivated.
4. Skips rows whose `source` field is anything other than `bulk_import_v1`
   (see the safety rule below).

### Useful flags

| Flag | Effect |
|---|---|
| `--dry-run` | Print what would change without writing to the database |
| `--deactivate-missing` | Deactivate `bulk_import_v1` rows absent from the current file |
| `--file <path>` | Use a different input file |
| `--source <tag>` | Override the source tag (default: `bulk_import_v1`) |

Example dry-run before a real import:

```bash
docker exec spt-mentoring-backend-1 python manage.py import_moderation_terms --dry-run
```

## Safety rule — admin-added terms are never touched

Admins can add custom moderation terms directly through the Django admin panel
(`/admin/moderation/moderationterm/add/`).  When doing so, set the `source`
field to `admin` (or leave it at its default).

**The importer will never update, deactivate, or delete rows whose `source`
differs from `bulk_import_v1`.**  This means:

- Admin-curated terms survive every re-import.
- The `--deactivate-missing` flag only deactivates bulk-imported rows.
- If you need to remove an admin-added term, do so manually via the admin panel.
