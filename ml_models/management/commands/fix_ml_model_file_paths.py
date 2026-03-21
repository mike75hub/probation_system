from __future__ import annotations

from django.core.management.base import BaseCommand

from ml_models.models import MLModel


class Command(BaseCommand):
    help = "Fix MLModel FileField names accidentally stored with a leading 'media/' prefix."

    def handle(self, *args, **options):
        fixed = 0
        checked = 0

        for model in MLModel.objects.exclude(model_file="").exclude(model_file__isnull=True):
            checked += 1
            changed = False

            for field_name in ("model_file", "scaler_file", "encoder_file"):
                f = getattr(model, field_name)
                if not f:
                    continue

                name = f.name or ""
                if not name.startswith("media/"):
                    continue

                # If current stored name doesn't exist, but a stripped name does, fix it.
                stripped = name[len("media/") :]
                try:
                    exists_current = f.storage.exists(name)
                    exists_stripped = f.storage.exists(stripped)
                except Exception:
                    continue

                if (not exists_current) and exists_stripped:
                    f.name = stripped
                    changed = True

            if changed:
                model.save(update_fields=["model_file", "scaler_file", "encoder_file"])
                fixed += 1

        self.stdout.write(self.style.SUCCESS(f"Checked {checked} model(s); fixed {fixed}"))

