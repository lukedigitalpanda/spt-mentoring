"""
Attachment validator tests (Task 8: P2-2 backend).

validate_message_attachment is the single validator shared by chat message
attachments and forum post attachments — these tests exercise it directly so
both call sites stay in lockstep.
"""
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.users.validators import validate_message_attachment, MAX_ATTACHMENT_BYTES


def zip_upload(name='archive.zip', content_type='application/zip', size=None):
    content = b'PK\x03\x04 fake zip content'
    if size is not None:
        content = b'0' * size
    return SimpleUploadedFile(name, content, content_type=content_type)


class ValidateMessageAttachmentTests(TestCase):
    def test_zip_under_20mb_is_accepted(self):
        """A small ZIP with the standard application/zip content type passes."""
        upload = zip_upload()
        validate_message_attachment(upload)  # should not raise

    def test_zip_x_zip_compressed_mime_is_accepted(self):
        """The alternate application/x-zip-compressed MIME (common on Windows) also passes."""
        upload = zip_upload(content_type='application/x-zip-compressed')
        validate_message_attachment(upload)  # should not raise

    def test_exe_is_rejected(self):
        upload = SimpleUploadedFile(
            'virus.exe', b'MZ fake exe content', content_type='application/x-msdownload'
        )
        with self.assertRaises(ValidationError):
            validate_message_attachment(upload)

    def test_js_is_rejected(self):
        upload = SimpleUploadedFile(
            'script.js', b'alert(1)', content_type='application/javascript'
        )
        with self.assertRaises(ValidationError):
            validate_message_attachment(upload)

    def test_oversize_zip_is_rejected(self):
        upload = zip_upload(size=MAX_ATTACHMENT_BYTES + 1)
        with self.assertRaises(ValidationError):
            validate_message_attachment(upload)
