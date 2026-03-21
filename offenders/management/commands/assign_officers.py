"""
Assign probation officers to unassigned cases.
"""

from django.core.management.base import BaseCommand, CommandError

from offenders.models import Case
from offenders.services import assign_cases_to_officers


class Command(BaseCommand):
    help = "Assign probation officers to cases (least-loaded strategy)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--status",
            default=Case.Status.ACTIVE,
            help="Case status to assign (default: active). Use 'all' to ignore status.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reassign even if a case already has an officer.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of cases to process.",
        )

    def handle(self, *args, **options):
        status = options["status"]
        force = options["force"]
        dry_run = options["dry_run"]
        limit = options["limit"]

        only_status = None if str(status).lower() == "all" else status

        qs = Case.objects.all()
        if only_status:
            qs = qs.filter(status=only_status)
        if not force:
            qs = qs.filter(probation_officer__isnull=True)
        qs = qs.order_by("id")
        if limit:
            qs = qs[:limit]

        if not qs.exists():
            self.stdout.write(self.style.WARNING("No matching cases to assign."))
            return

        result = assign_cases_to_officers(
            cases=qs,
            only_status=only_status,
            force=force,
            dry_run=dry_run,
        )

        if result.skipped_no_officers:
            raise CommandError("No active officers found (role='officer').")

        msg = f"Assigned {result.assigned} case(s)"
        if dry_run:
            msg += " (dry-run)"
        self.stdout.write(self.style.SUCCESS(msg))

