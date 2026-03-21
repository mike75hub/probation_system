from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .forms import DatasetUploadForm
from .models import DatasetSource
from .validators import DatasetValidator


class DatasetValidatorTests(TestCase):
    def test_validate_csv_structure_accepts_in_memory_upload(self):
        uploaded = SimpleUploadedFile(
            "ok.csv",
            b"col1,col2\n1,2\n3,4\n",
            content_type="text/csv",
        )
        self.assertTrue(DatasetValidator.validate_csv_structure(uploaded))

    def test_validate_csv_structure_rejects_header_only(self):
        uploaded = SimpleUploadedFile(
            "empty.csv",
            b"col1,col2\n",
            content_type="text/csv",
        )
        with self.assertRaises(ValidationError):
            DatasetValidator.validate_csv_structure(uploaded)


class DatasetUploadFormTests(TestCase):
    def test_upload_form_does_not_require_temporary_file_path(self):
        User = get_user_model()
        user = User.objects.create_user(username="u1", password="pass1234")
        source = DatasetSource.objects.create(name="S1", source_type="internal")
        uploaded = SimpleUploadedFile(
            "data.csv",
            b"col1,col2\n1,2\n",
            content_type="text/csv",
        )
        form = DatasetUploadForm(
            data={
                "name": "D1",
                "description": "",
                "dataset_type": "custom",
                "source": source.pk,
            },
            files={"original_file": uploaded},
            user=user,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())
