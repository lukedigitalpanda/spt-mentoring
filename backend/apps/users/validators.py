import os
from django.core.exceptions import ValidationError

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
ALLOWED_ATTACHMENT_TYPES = ALLOWED_IMAGE_TYPES | {'application/pdf'}
MAX_PROFILE_PICTURE_BYTES = 5 * 1024 * 1024   # 5 MB
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024        # 10 MB

# Map common extensions to MIME types for the magic-byte-free fallback
_EXT_TO_MIME = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.png': 'image/png', '.webp': 'image/webp',
    '.gif': 'image/gif', '.pdf': 'application/pdf',
}


def _get_content_type(file):
    """Return content_type from the upload, falling back to extension sniffing."""
    ct = getattr(file, 'content_type', None)
    if ct:
        return ct.split(';')[0].strip().lower()
    ext = os.path.splitext(file.name)[1].lower()
    return _EXT_TO_MIME.get(ext, '')


def validate_profile_picture(file):
    ct = _get_content_type(file)
    if ct not in ALLOWED_IMAGE_TYPES:
        raise ValidationError('Profile pictures must be JPEG, PNG, WebP, or GIF.')
    if file.size > MAX_PROFILE_PICTURE_BYTES:
        raise ValidationError('Profile picture must be 5 MB or smaller.')


def validate_message_attachment(file):
    ct = _get_content_type(file)
    if ct not in ALLOWED_ATTACHMENT_TYPES:
        raise ValidationError('Attachments must be an image or PDF.')
    if file.size > MAX_ATTACHMENT_BYTES:
        raise ValidationError('Attachment must be 10 MB or smaller.')
