"""
Bulk import / CRM integration for User data.
Supports CSV and XLSX uploads.
"""
import io
import logging
import pandas as pd
from django.contrib.auth.hashers import make_password
from .models import User

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {'email', 'first_name', 'last_name', 'role'}

ROLE_MAP = {
    'scholar': User.Role.SCHOLAR,
    'mentor': User.Role.MENTOR,
    'sponsor': User.Role.SPONSOR,
    'alumni': User.Role.ALUMNI,
    'admin': User.Role.ADMIN,
}


class UserBulkImport:
    @classmethod
    def process(cls, file_obj, imported_by=None):
        filename = getattr(file_obj, 'name', '')
        try:
            if filename.endswith('.xlsx') or filename.endswith('.xls'):
                df = pd.read_excel(io.BytesIO(file_obj.read()))
            else:
                df = pd.read_csv(io.BytesIO(file_obj.read()))
        except Exception as e:
            return {'success': False, 'error': f'Could not parse file: {e}'}

        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            return {'success': False, 'error': f'Missing required columns: {missing}'}

        created, updated, errors = 0, 0, []

        for idx, row in df.iterrows():
            try:
                role = ROLE_MAP.get(str(row.get('role', '')).lower().strip())
                if not role:
                    errors.append({'row': idx + 2, 'error': f'Unknown role: {row.get("role")}'})
                    continue

                email = str(row['email']).strip().lower()
                defaults = {
                    'first_name': str(row['first_name']).strip(),
                    'last_name': str(row['last_name']).strip(),
                    'role': role,
                    'username': email,
                }
                # Optional fields
                for field in ('phone', 'location', 'engineering_discipline', 'crm_id'):
                    if field in row and pd.notna(row[field]):
                        defaults[field] = str(row[field]).strip()

                user, was_created = User.objects.update_or_create(email=email, defaults=defaults)

                if was_created:
                    # Set a temporary password; user must reset on first login
                    user.set_password(User.objects.make_random_password())
                    user.save(update_fields=['password'])
                    created += 1
                else:
                    updated += 1

            except Exception as e:
                errors.append({'row': idx + 2, 'error': str(e)})
                logger.exception('Error importing row %d', idx + 2)

        return {
            'success': True,
            'created': created,
            'updated': updated,
            'errors': errors,
            'total_rows': len(df),
        }
