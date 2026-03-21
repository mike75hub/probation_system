import random
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from datasets.models import Dataset, DatasetSource
from monitoring.models import (
    Alert,
    CheckIn,
    CheckInType,
    DrugTest,
    EmploymentVerification,
    GPSLocation,
    GPSMonitoring,
)
from offenders.models import Assessment, Case, Offender
from programs.models import (
    Attendance,
    Enrollment,
    Program,
    ProgramCategory,
    Session,
)

try:
    from faker import Faker
except Exception:  # pragma: no cover
    Faker = None


KENYAN_FIRST_NAMES = [
    "Brian",
    "Kevin",
    "Dennis",
    "James",
    "John",
    "Peter",
    "David",
    "Samuel",
    "Daniel",
    "Joseph",
    "George",
    "Paul",
    "Martin",
    "Anthony",
    "Eric",
    "Vincent",
    "Allan",
    "Stephen",
    "Michael",
    "Charles",
    "Mary",
    "Grace",
    "Jane",
    "Mercy",
    "Faith",
    "Joyce",
    "Alice",
    "Rose",
    "Eunice",
    "Lucy",
    "Esther",
    "Susan",
    "Irene",
    "Caroline",
    "Beatrice",
]

KENYAN_LAST_NAMES = [
    "Wanjiku",
    "Mwangi",
    "Odhiambo",
    "Ochieng",
    "Kamau",
    "Kiptoo",
    "Kariuki",
    "Mutiso",
    "Njoroge",
    "Karanja",
    "Otieno",
    "Achieng",
    "Chebet",
    "Cheruiyot",
    "Wambui",
    "Wafula",
    "Muriithi",
    "Onyango",
    "Kilonzo",
    "Koech",
    "Ngugi",
    "Maina",
    "Wekesa",
    "Musyoka",
    "Mburu",
    "Githinji",
]

KENYAN_COUNTIES = [
    "Nairobi",
    "Mombasa",
    "Kisumu",
    "Nakuru",
    "Kiambu",
    "Machakos",
    "Kajiado",
    "Uasin Gishu",
    "Meru",
    "Nyeri",
    "Kericho",
    "Kakamega",
    "Bungoma",
    "Embu",
    "Laikipia",
    "Murang'a",
    "Kwale",
    "Kilifi",
    "Garissa",
    "Kitui",
    "Narok",
]

KENYAN_SUBCOUNTIES = [
    "Central",
    "East",
    "West",
    "North",
    "South",
    "Kibra",
    "Embakasi",
    "Westlands",
    "Lang'ata",
    "Dagoretti",
]

COURTS = [
    "Milimani Law Courts",
    "Kibera Law Courts",
    "Makadara Law Courts",
    "Nakuru Law Courts",
    "Mombasa Law Courts",
    "Kisumu Law Courts",
]

OFFENSES_BY_CATEGORY = {
    "property": [
        "Burglary",
        "Housebreaking",
        "Theft of motor vehicle",
        "Shoplifting",
        "Handling stolen goods",
    ],
    "violent": [
        "Assault causing actual bodily harm",
        "Robbery with violence",
        "Domestic disturbance",
    ],
    "drug": [
        "Possession of cannabis",
        "Trafficking in narcotic substances",
        "Possession of controlled substances",
    ],
    "traffic": [
        "Dangerous driving",
        "Driving without license",
        "Driving under the influence",
    ],
    "financial": [
        "Obtaining by false pretences",
        "Forgery",
        "Fraudulent accounting",
    ],
    "other": [
        "Disorderly conduct",
        "Breach of peace",
        "Public nuisance",
    ],
}


def _digits(n: int) -> str:
    return "".join(random.choice("0123456789") for _ in range(n))


def _phone_kenya() -> str:
    # Keep it simple: +2547XXXXXXXX
    return f"+2547{_digits(8)}"


def _id_number_kenya() -> str:
    # 8-digit ID-like number (do not use real IDs).
    return _digits(8)


def _safe_username(prefix: str, n: int) -> str:
    return f"{prefix}{n:04d}"


def _random_name(fake: "Faker | None") -> tuple[str, str]:
    if fake is not None:
        # Use faker for variety, but keep it "Kenyan-looking" by mixing with local lists.
        if random.random() < 0.6:
            return (random.choice(KENYAN_FIRST_NAMES), random.choice(KENYAN_LAST_NAMES))
        name = fake.name().split()
        return (name[0], name[-1])
    return (random.choice(KENYAN_FIRST_NAMES), random.choice(KENYAN_LAST_NAMES))


def _pick(seq):
    return random.choice(list(seq))


def _start_index_for_prefix(model_cls, field_name: str, prefix: str) -> int:
    """
    Find next numeric suffix for values like PREFIX0001.
    """
    values = model_cls.objects.filter(**{f"{field_name}__startswith": prefix}).values_list(
        field_name, flat=True
    )
    max_n = 0
    rx = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    for v in values:
        m = rx.match(str(v))
        if m:
            try:
                max_n = max(max_n, int(m.group(1)))
            except ValueError:
                pass
    return max_n + 1


class Command(BaseCommand):
    help = (
        "Seed Kenya-themed sample data (users, offenders, cases, programs, monitoring, and sample datasets). "
        "Use for development/staging only."
    )

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=500, help="Base count for core entities.")
        parser.add_argument("--offenders", type=int, default=None, help="Number of offenders to create.")
        parser.add_argument("--cases", type=int, default=None, help="Number of cases to create.")
        parser.add_argument("--assessments", type=int, default=None, help="Number of assessments to create.")
        parser.add_argument("--programs", type=int, default=50, help="Number of programs to create.")
        parser.add_argument("--enrollments", type=int, default=None, help="Number of enrollments to create.")
        parser.add_argument("--checkins", type=int, default=None, help="Number of check-ins to create.")
        parser.add_argument("--gps", type=int, default=200, help="Number of GPSMonitoring records to create.")
        parser.add_argument("--drug-tests", type=int, default=None, help="Number of drug tests to create.")
        parser.add_argument("--employment", type=int, default=None, help="Number of employment verifications to create.")
        parser.add_argument("--alerts", type=int, default=None, help="Number of alerts to create.")
        parser.add_argument("--datasets", type=int, default=3, help="Number of sample datasets (CSV) to create.")
        parser.add_argument(
            "--prefix",
            type=str,
            default="ke_",
            help="Prefix used for generated usernames and IDs (safe to run multiple times).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducibility.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(options["seed"])
        fake = Faker() if Faker is not None else None
        if fake is not None:
            fake.seed_instance(options["seed"])

        base_count = int(options["count"])
        prefix = str(options["prefix"])

        offenders_n = int(options["offenders"] or base_count)
        cases_n = int(options["cases"] or base_count)
        assessments_n = int(options["assessments"] or base_count)
        enrollments_n = int(options["enrollments"] or base_count)
        checkins_n = int(options["checkins"] or base_count)
        programs_n = int(options["programs"])
        gps_n = int(options["gps"])
        drug_tests_n = int(options["drug_tests"] or base_count)
        employment_n = int(options["employment"] or base_count)
        alerts_n = int(options["alerts"] or base_count)
        datasets_n = int(options["datasets"])

        User = get_user_model()

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding Kenya-themed data"))
        self.stdout.write(f"- prefix={prefix!r} seed={options['seed']}")
        self.stdout.write(
            f"- offenders={offenders_n} cases={cases_n} assessments={assessments_n} programs={programs_n} "
            f"enrollments={enrollments_n} checkins={checkins_n} gps={gps_n} "
            f"drug_tests={drug_tests_n} employment={employment_n} alerts={alerts_n} datasets={datasets_n}"
        )

        officers = self._ensure_staff_users(User, fake, prefix, role="officer", n=25)
        ngos = self._ensure_staff_users(User, fake, prefix, role="ngo", n=10)
        admins = self._ensure_staff_users(User, fake, prefix, role="admin", n=2, is_superuser=True)

        offenders = self._ensure_offenders(User, fake, prefix, offenders_n)
        self._ensure_cases(fake, prefix, offenders, officers, cases_n)
        self._ensure_assessments(fake, offenders, officers, assessments_n)

        categories = self._ensure_program_categories()
        programs = self._ensure_programs(fake, prefix, programs_n, categories, officers, ngos, admins[0])
        enrollments = self._ensure_enrollments(fake, offenders, officers, programs, enrollments_n)
        sessions = self._ensure_sessions(fake, programs)
        self._ensure_attendance(fake, enrollments, sessions)

        checkin_types = self._ensure_checkin_types()
        self._ensure_checkins(fake, offenders, officers, checkin_types, checkins_n)

        self._ensure_gps(fake, offenders, gps_n)
        self._ensure_drug_tests(fake, offenders, officers, ngos, drug_tests_n)
        self._ensure_employment_verifications(fake, offenders, officers, employment_n)
        self._ensure_alerts(fake, offenders, officers, alerts_n)

        self._ensure_sample_datasets(fake, prefix, admins[0], datasets_n)

        self.stdout.write(self.style.SUCCESS("Done."))

    def _ensure_staff_users(self, User, fake, prefix: str, role: str, n: int, is_superuser: bool = False):
        start = _start_index_for_prefix(User, "username", f"{prefix}{role}_")
        users = []
        for i in range(start, start + n):
            username = _safe_username(f"{prefix}{role}_", i)
            if User.objects.filter(username=username).exists():
                continue
            first, last = _random_name(fake)
            email = f"{username}@example.co.ke"
            user = User.objects.create_user(
                username=username,
                email=email,
                password="Pass1234!",
                first_name=first,
                last_name=last,
                role=role,
                is_staff=True,
                is_superuser=is_superuser,
            )
            users.append(user)
        if not users:
            users = list(User.objects.filter(username__startswith=f"{prefix}{role}_")[:n])
        return users

    def _ensure_offenders(self, User, fake, prefix: str, n: int):
        start = _start_index_for_prefix(User, "username", f"{prefix}offender_")
        offenders = []
        for i in range(start, start + n):
            username = _safe_username(f"{prefix}offender_", i)
            if User.objects.filter(username=username).exists():
                continue
            first, last = _random_name(fake)
            user = User.objects.create_user(
                username=username,
                email=f"{username}@example.co.ke",
                password="Pass1234!",
                first_name=first,
                last_name=last,
                role="offender",
                is_staff=False,
            )

            dob_year = random.randint(1965, 2005)
            dob = date(dob_year, random.randint(1, 12), random.randint(1, 28))
            county = _pick(KENYAN_COUNTIES)
            sub_county = _pick(KENYAN_SUBCOUNTIES)
            offender = Offender.objects.create(
                user=user,
                offender_id=f"{prefix.upper()}OFF{i:06d}",
                date_of_birth=dob,
                gender=_pick(["male", "female"]),
                nationality="Kenyan",
                id_number=f"{_id_number_kenya()}{i%10}",
                risk_level=_pick(["low", "medium", "high"]),
                ml_risk_score=round(random.random(), 4),
                address=f"P.O. Box {_digits(5)}-{_digits(5)}, {county}",
                county=county,
                sub_county=sub_county,
                phone_alternative=_phone_kenya() if random.random() < 0.5 else "",
                email=f"{username}@example.co.ke" if random.random() < 0.7 else "",
                emergency_contact_name=f"{_pick(KENYAN_FIRST_NAMES)} {_pick(KENYAN_LAST_NAMES)}",
                emergency_contact_phone=_phone_kenya(),
                emergency_contact_relationship=_pick(
                    ["Parent", "Sibling", "Spouse", "Guardian", "Friend"]
                ),
                is_active=True,
            )
            offenders.append(offender)

        if not offenders:
            offenders = list(Offender.objects.filter(offender_id__startswith=f"{prefix}OFF")[:n])
        return offenders

    def _ensure_cases(self, fake, prefix: str, offenders, officers, n: int):
        start = _start_index_for_prefix(Case, "case_number", f"{prefix}CASE")
        for i in range(start, start + n):
            case_number = f"{prefix}CASE{i:06d}"
            if Case.objects.filter(case_number=case_number).exists():
                continue
            offender = offenders[(i - start) % len(offenders)]
            category = _pick(list(OFFENSES_BY_CATEGORY.keys()))
            offense = _pick(OFFENSES_BY_CATEGORY[category])
            offense_date = timezone.now().date() - timedelta(days=random.randint(30, 1200))
            sentence_start = offense_date + timedelta(days=random.randint(1, 60))
            duration_months = random.randint(3, 36)
            sentence_end = sentence_start + timedelta(days=duration_months * 30)
            court = _pick(COURTS)
            location = _pick(KENYAN_COUNTIES)
            sentence_type = _pick(
                ["probation", "community_service", "parole", "conditional_release"]
            )
            Case.objects.create(
                offender=offender,
                case_number=case_number,
                court_name=court,
                court_location=location,
                offense=offense,
                offense_category=category,
                offense_date=offense_date,
                sentence_start=sentence_start,
                sentence_end=sentence_end,
                sentence_duration=duration_months,
                sentence_type=sentence_type,
                probation_officer=_pick(officers) if officers else None,
                status=_pick(["active", "active", "active", "completed", "violated"]),
                special_conditions=_pick(
                    [
                        "Report weekly to the probation office.",
                        "Attend counseling sessions as scheduled.",
                        "Observe curfew as directed by the supervising officer.",
                        "No contact with complainant / protected persons.",
                        "",
                    ]
                ),
                notes="Case record captured in the system.",
            )

    def _ensure_assessments(self, fake, offenders, officers, n: int):
        existing = Assessment.objects.count()
        needed = max(0, n - existing)
        for _ in range(needed):
            offender = _pick(offenders)
            assessed_by = _pick(officers) if officers else None
            assessment_date = timezone.now().date() - timedelta(days=random.randint(0, 365))
            Assessment.objects.create(
                offender=offender,
                assessment_date=assessment_date,
                assessed_by=assessed_by,
                criminal_history=random.randint(0, 10),
                education_level=_pick([1, 2, 3, 4, 5]),
                employment_status=_pick(
                    ["employed", "self_employed", "unemployed", "student", "casual"]
                ),
                employment_duration=random.randint(0, 120),
                substance_abuse=random.random() < 0.25,
                mental_health_issues=random.random() < 0.15,
                anger_issues=random.random() < 0.2,
                family_support=_pick([1, 2, 3, 4, 5]),
                peer_support=_pick([1, 2, 3, 4, 5]),
                community_ties=_pick([1, 2, 3, 4, 5]),
                financial_stability=_pick([1, 2, 3, 4, 5]),
                housing_stability=_pick([1, 2, 3, 4, 5]),
                recommended_interventions=_pick(
                    [
                        "Life skills training; regular check-ins.",
                        "Substance abuse counseling; vocational program.",
                        "Anger management; community service supervision.",
                        "Employment support; mentorship.",
                    ]
                ),
                notes="Assessment notes recorded by officer.",
            )

    def _ensure_program_categories(self):
        defaults = [
            ("Vocational & Skills", "Skills training and employability support", "fas fa-tools", "primary"),
            ("Counseling & Therapy", "Counseling and psychosocial support", "fas fa-comments", "info"),
            ("Substance Abuse", "Addiction support and relapse prevention", "fas fa-notes-medical", "warning"),
            ("Life Skills", "Financial literacy and life skills", "fas fa-user-check", "success"),
        ]
        cats = []
        for name, desc, icon, color in defaults:
            obj, _ = ProgramCategory.objects.get_or_create(
                name=name,
                defaults={"description": desc, "icon": icon, "color": color},
            )
            cats.append(obj)
        return cats

    def _ensure_programs(self, fake, prefix: str, n: int, categories, officers, ngos, created_by):
        existing = Program.objects.count()
        needed = max(0, n - Program.objects.count())
        programs = list(Program.objects.all()[:n])
        for i in range(1, needed + 1):
            prog_type = _pick(
                [
                    "vocational",
                    "educational",
                    "counseling",
                    "life_skills",
                    "substance_abuse",
                    "anger_management",
                ]
            )
            start_date = timezone.now().date() + timedelta(days=random.randint(-60, 30))
            duration_weeks = random.randint(4, 24)
            end_date = start_date + timedelta(weeks=duration_weeks)
            facilitator_pool = (officers or []) + (ngos or [])
            facilitator = _pick(facilitator_pool) if facilitator_pool else None
            co_facilitator = _pick(facilitator_pool) if facilitator_pool and random.random() < 0.4 else None

            name = f"{_pick(KENYAN_COUNTIES)} {prog_type.replace('_', ' ').title()} Programme {timezone.now().year}-{existing + i:03d}"
            program = Program.objects.create(
                name=name,
                description="Rehabilitation programme offered through the probation office and partners.",
                program_type=prog_type,
                category=_pick(categories) if categories else None,
                objectives="Improve compliance, reduce re-offending risk, and support reintegration.",
                curriculum="Module 1: Orientation; Module 2: Skills; Module 3: Reintegration planning.",
                duration_weeks=duration_weeks,
                hours_per_week=random.randint(2, 10),
                max_participants=random.randint(20, 60),
                eligibility_criteria="Subject to officer assessment; prioritise medium/high risk where appropriate.",
                target_risk_level=_pick(["all", "low_medium", "medium_high", "medium", "high"]),
                facilitator=facilitator,
                co_facilitator=co_facilitator,
                facilitator_notes="",
                location=f"{_pick(KENYAN_COUNTIES)} Probation Office / Partner Center",
                schedule_description=_pick(
                    [
                        "Mondays & Wednesdays, 2-4 PM",
                        "Tuesdays, 10 AM - 12 PM",
                        "Fridays, 9-11 AM",
                    ]
                ),
                start_date=start_date,
                end_date=end_date,
                cost_per_participant=Decimal(str(round(random.uniform(0, 20000), 2))),
                resources_required="Trainer, classroom space, stationery.",
                status=_pick(["active", "active", "draft", "inactive"]),
                is_featured=random.random() < 0.1,
                created_by=created_by,
            )
            programs.append(program)
        return programs[:n]

    def _ensure_enrollments(self, fake, offenders, officers, programs, n: int):
        existing = Enrollment.objects.count()
        needed = max(0, n - existing)
        created = 0
        attempts = 0
        enrollments = list(Enrollment.objects.all()[:n])
        while created < needed and attempts < needed * 5:
            attempts += 1
            program = _pick(programs)
            offender = _pick(offenders)
            if Enrollment.objects.filter(program=program, offender=offender).exists():
                continue
            enrollment_date = timezone.now().date() - timedelta(days=random.randint(0, 365))
            status = _pick(["pending", "active", "completed", "dropped_out", "suspended"])
            actual_start = enrollment_date + timedelta(days=random.randint(0, 14))
            actual_end = None
            completion_grade = ""
            certificate = False
            cert_date = None
            if status in ("completed",):
                actual_end = actual_start + timedelta(days=random.randint(30, 180))
                completion_grade = _pick(
                    ["excellent", "good", "satisfactory", "needs_improvement"]
                )
                certificate = random.random() < 0.7
                cert_date = actual_end if certificate else None

            enrollment = Enrollment.objects.create(
                program=program,
                offender=offender,
                enrollment_date=enrollment_date,
                referred_by=_pick(officers) if officers else None,
                referral_notes="Referred for programme participation.",
                status=status,
                actual_start_date=actual_start if status != "pending" else None,
                actual_end_date=actual_end,
                attendance_rate=round(random.uniform(40, 100), 1),
                participation_score=random.randint(0, 10),
                skill_improvement=_pick(
                    [
                        "Improved communication and planning skills.",
                        "Basic vocational skills acquired.",
                        "Better coping mechanisms reported.",
                        "",
                    ]
                ),
                completion_grade=completion_grade,
                certificate_issued=certificate,
                certificate_issue_date=cert_date,
                progress_notes="",
                facilitator_feedback="",
                officer_feedback="",
            )
            enrollments.append(enrollment)
            created += 1
        return enrollments[:n]

    def _ensure_sessions(self, fake, programs):
        sessions = []
        for program in programs:
            # Create a small, manageable number of sessions per program.
            existing = Session.objects.filter(program=program).count()
            if existing >= 6:
                sessions.extend(list(Session.objects.filter(program=program)[:6]))
                continue
            for sn in range(existing + 1, 7):
                session_date = program.start_date + timedelta(days=sn * 7)
                Session.objects.create(
                    program=program,
                    session_number=sn,
                title=f"Session {sn}: Module {sn}",
                description="Programme session.",
                    learning_objectives="Attendance, skills practice, and reflection.",
                    date=session_date,
                    start_time=time(9, 0),
                    end_time=time(11, 0),
                    location=program.location,
                    facilitator=program.facilitator,
                    materials_required="Notebook, pen.",
                    reference_materials="Handouts.",
                    is_completed=session_date < timezone.now().date(),
                    completion_notes="",
                )
            sessions.extend(list(Session.objects.filter(program=program)[:6]))
        return sessions

    def _ensure_attendance(self, fake, enrollments, sessions):
        # Create limited attendance records (avoid exploding the DB).
        for enrollment in enrollments[: min(500, len(enrollments))]:
            relevant_sessions = [s for s in sessions if s.program_id == enrollment.program_id]
            for sess in relevant_sessions[:3]:
                if Attendance.objects.filter(session=sess, enrollment=enrollment).exists():
                    continue
                Attendance.objects.create(
                    session=sess,
                    enrollment=enrollment,
                    status=_pick(["present", "present", "late", "absent", "excused"]),
                    check_in_time=timezone.now() - timedelta(days=random.randint(1, 60))
                    if random.random() < 0.6
                    else None,
                    check_out_time=None,
                    participation_score=random.randint(0, 10) if random.random() < 0.7 else None,
                    notes="",
                )

    def _ensure_checkin_types(self):
        defaults = [
            ("In Person", "Physical reporting at probation office", "fas fa-user-check", "primary"),
            ("Phone", "Phone call check-in", "fas fa-phone", "info"),
            ("Home Visit", "Home visit supervision", "fas fa-home", "warning"),
            ("Video", "Video check-in", "fas fa-video", "success"),
        ]
        types = []
        for name, desc, icon, color in defaults:
            obj, _ = CheckInType.objects.get_or_create(
                name=name, defaults={"description": desc, "icon": icon, "color": color, "is_active": True}
            )
            types.append(obj)
        return types

    def _ensure_checkins(self, fake, offenders, officers, checkin_types, n: int):
        existing = CheckIn.objects.count()
        needed = max(0, n - existing)
        cases = list(Case.objects.select_related("offender").all())
        if not cases:
            return
        for _ in range(needed):
            case = _pick(cases)
            scheduled = timezone.now() - timedelta(days=random.randint(-10, 60))
            status = _pick(["scheduled", "completed", "missed", "cancelled", "rescheduled"])
            actual = scheduled + timedelta(minutes=random.randint(0, 60)) if status == "completed" else None
            next_date = scheduled + timedelta(days=random.randint(7, 30)) if status in ("completed", "rescheduled") else None
            CheckIn.objects.create(
                case=case,
                offender=case.offender,
                probation_officer=case.probation_officer or (_pick(officers) if officers else None),
                checkin_type=_pick(checkin_types) if checkin_types else None,
                scheduled_date=scheduled,
                actual_date=actual,
                location=f"{case.offender.county} Probation Office",
                purpose=_pick(
                    [
                        "Routine supervision and compliance review.",
                        "Program attendance review and counseling referral.",
                        "Employment verification and support planning.",
                        "Address update and next steps.",
                    ]
                ),
                status=status,
                compliance_level=_pick(["full", "partial", "non"]) if status == "completed" else "",
                risk_assessment="",
                behavior_notes="",
                progress_notes="",
                concerns_issues="",
                recommendations="",
                next_steps="",
                next_checkin_date=next_date,
                officer_signature="",
                offender_signature="",
                witness_name="",
                created_by=case.probation_officer or (_pick(officers) if officers else None),
            )

    def _ensure_gps(self, fake, offenders, n: int):
        existing = GPSMonitoring.objects.count()
        needed = max(0, n - existing)
        cases = list(Case.objects.select_related("offender").all())
        if not cases:
            return
        for i in range(1, needed + 1):
            case = _pick(cases)
            offender = case.offender
            device_id = f"KEGPS-{_digits(6)}-{existing + i:04d}"
            if GPSMonitoring.objects.filter(device_id=device_id).exists():
                continue
            issued = timezone.now().date() - timedelta(days=random.randint(0, 180))
            end = issued + timedelta(days=random.randint(30, 365))
            gps = GPSMonitoring.objects.create(
                offender=offender,
                case=case,
                device_id=device_id,
                device_type=_pick(["Ankle Monitor", "Wrist Monitor"]),
                device_status=_pick(["active", "active", "maintenance", "inactive"]),
                issued_date=issued,
                expected_return_date=end,
                actual_return_date=None,
                monitoring_start_date=issued,
                monitoring_end_date=end if random.random() < 0.6 else None,
                checkin_frequency_hours=_pick([1, 2, 4, 6, 12, 24]),
                restricted_zones="",
                curfew_start=time(20, 0) if random.random() < 0.5 else None,
                curfew_end=time(6, 0) if random.random() < 0.5 else None,
                battery_level=random.randint(10, 100),
                last_sync=timezone.now() - timedelta(hours=random.randint(0, 72)),
                notes="",
            )
            # Add a few locations per device.
            for _ in range(3):
                lat = Decimal(str(round(random.uniform(-4.8, 4.7), 6)))
                lon = Decimal(str(round(random.uniform(33.9, 41.9), 6)))
                ts = timezone.now() - timedelta(hours=random.randint(0, 240))
                GPSLocation.objects.create(
                    gps_monitoring=gps,
                    latitude=lat,
                    longitude=lon,
                    accuracy=round(random.uniform(5, 50), 2),
                    altitude=round(random.uniform(1200, 2200), 2),
                    speed=round(random.uniform(0, 80), 2),
                    timestamp=ts,
                    is_in_restricted_zone=random.random() < 0.05,
                    is_curfew_violation=random.random() < 0.03,
                    battery_level=random.randint(10, 100),
                    address=f"{_pick(KENYAN_SUBCOUNTIES)}, {_pick(KENYAN_COUNTIES)}",
                    provider=_pick(["gps", "network"]),
                    notes="",
                )

    def _ensure_sample_datasets(self, fake, prefix: str, uploaded_by, n: int):
        source, _ = DatasetSource.objects.get_or_create(
            name="Kenya Probation Service",
            defaults={"source_type": "internal", "description": "Operational data source."},
        )

        existing = Dataset.objects.count()
        for idx in range(existing + 1, existing + n + 1):
            name = f"risk_assessment_{idx:02d}"
            if Dataset.objects.filter(name=name).exists():
                continue

            # Generate a small CSV that matches the "risk" style features used elsewhere in the codebase.
            rows = 500
            cols = [
                "criminal_history",
                "education_level",
                "employment_status",
                "substance_abuse",
                "mental_health_issues",
                "family_support",
                "financial_stability",
                "two_year_recid",  # classification target
            ]
            lines = [",".join(cols)]
            for _ in range(rows):
                criminal_history = random.randint(0, 10)
                education_level = random.randint(1, 5)
                employment_status = _pick(["employed", "self_employed", "unemployed", "student", "casual"])
                substance_abuse = 1 if random.random() < 0.25 else 0
                mental_health_issues = 1 if random.random() < 0.15 else 0
                family_support = random.randint(1, 5)
                financial_stability = random.randint(1, 5)

                # Label correlated with risk factors (for training data).
                risk_score = (
                    criminal_history * 0.25
                    + (6 - education_level) * 0.12
                    + (1.2 if employment_status in ("unemployed", "casual") else 0.0)
                    + substance_abuse * 0.8
                    + mental_health_issues * 0.4
                    + (6 - family_support) * 0.12
                    + (6 - financial_stability) * 0.12
                    + random.uniform(-0.5, 0.5)
                )
                two_year_recid = 1 if risk_score >= 2.6 else 0

                lines.append(
                    ",".join(
                        map(
                            str,
                            [
                                criminal_history,
                                education_level,
                                employment_status,
                                substance_abuse,
                                mental_health_issues,
                                family_support,
                                financial_stability,
                                two_year_recid,
                            ],
                        )
                    )
                )

            content = "\n".join(lines).encode("utf-8")

            ds = Dataset(
                name=name,
                description="Risk assessment training dataset.",
                dataset_type="risk_assessment",
                source=source,
                status=Dataset.Status.UPLOADED,
                uploaded_by=uploaded_by,
            )
            ds.original_file.save(f"{name}.csv", ContentFile(content), save=False)
            ds.file_size = ds.original_file.size
            ds.file_format = "csv"
            ds.save()

    def _ensure_drug_tests(self, fake, offenders, officers, ngos, n: int):
        existing = DrugTest.objects.count()
        needed = max(0, n - existing)
        cases = list(Case.objects.select_related("offender").all())
        if not cases:
            return
        conducted_by_pool = (officers or []) + (ngos or [])
        for _ in range(needed):
            case = _pick(cases)
            offender = case.offender
            dt = timezone.now() - timedelta(days=random.randint(0, 365), hours=random.randint(0, 23))
            result = _pick(["negative", "negative", "negative", "positive", "inconclusive", "refused"])
            substances = ["Alcohol", "Cannabis", "Cocaine", "Opiates", "Amphetamines"]
            detected = []
            if result == "positive":
                detected = random.sample(substances[1:], k=random.randint(1, 2))
            DrugTest.objects.create(
                offender=offender,
                case=case,
                conducted_by=_pick(conducted_by_pool) if conducted_by_pool else None,
                test_type=_pick(["urine", "breath", "saliva"]),
                test_date=dt,
                location=f"{offender.county} Probation Office / Partner Clinic",
                result=result,
                substances_tested=", ".join(substances),
                substances_detected=", ".join(detected),
                concentration_levels="",
                observations="",
                offender_comments="",
                follow_up_required=result in ("positive", "inconclusive"),
                follow_up_date=dt + timedelta(days=random.randint(7, 21))
                if result in ("positive", "inconclusive")
                else None,
                recommendations="Counseling referral and repeat test."
                if result in ("positive", "inconclusive")
                else "",
                witness_name="",
                lab_reference=f"LAB-{_digits(8)}" if random.random() < 0.6 else "",
            )

    def _ensure_employment_verifications(self, fake, offenders, officers, n: int):
        existing = EmploymentVerification.objects.count()
        needed = max(0, n - existing)
        cases = list(Case.objects.select_related("offender").all())
        if not cases:
            return
        for _ in range(needed):
            case = _pick(cases)
            offender = case.offender
            start = timezone.now().date() - timedelta(days=random.randint(0, 900))
            status = _pick(["verified", "verified", "pending", "unverified", "terminated"])
            end = None
            if status == "terminated":
                end = start + timedelta(days=random.randint(30, 365))
            verified_by = _pick(officers) if officers and status in ("verified", "terminated") else None
            verif_date = start + timedelta(days=random.randint(7, 60)) if verified_by else None
            employer = _pick(
                [
                    "Jua Kali Workshop",
                    "Matatu SACCO",
                    "Supermarket",
                    "Construction Site",
                    "Agribusiness Farm",
                    "Small Retail Shop",
                    "Private Security Firm",
                ]
            )
            EmploymentVerification.objects.create(
                offender=offender,
                case=case,
                employer_name=f"{employer} - {_pick(KENYAN_COUNTIES)}",
                employer_address=f"P.O. Box {_digits(5)}-{_digits(5)}, {_pick(KENYAN_COUNTIES)}",
                employer_phone=_phone_kenya() if random.random() < 0.8 else "",
                employer_email="" if random.random() < 0.7 else f"{_digits(3)}@example.co.ke",
                position=_pick(["Driver", "Mason", "Cashier", "Shop Attendant", "Welder", "Farmhand", "Guard"]),
                employment_type=_pick(["full_time", "part_time", "contract", "temporary", "self_employed"]),
                start_date=start,
                end_date=end,
                verification_status=status,
                verified_by=verified_by,
                verification_date=verif_date,
                verification_method=_pick(["Phone call", "Site visit", "Letter", "Email"]) if verified_by else "",
                hours_per_week=random.randint(10, 60) if random.random() < 0.8 else None,
                salary=Decimal(str(round(random.uniform(5000, 80000), 2))) if random.random() < 0.7 else None,
                pay_frequency=_pick(["weekly", "biweekly", "monthly", "daily"]) if random.random() < 0.7 else "",
                supervisor_name=f"{_pick(KENYAN_FIRST_NAMES)} {_pick(KENYAN_LAST_NAMES)}"
                if random.random() < 0.6
                else "",
                supervisor_phone=_phone_kenya() if random.random() < 0.6 else "",
                notes="Employment verification record.",
                created_by=verified_by,
            )

    def _ensure_alerts(self, fake, offenders, officers, n: int):
        existing = Alert.objects.count()
        needed = max(0, n - existing)
        cases = list(Case.objects.select_related("offender").all())
        checkins = list(CheckIn.objects.select_related("case", "offender").all())
        gps_list = list(GPSMonitoring.objects.select_related("case", "offender").all())
        if not cases:
            return
        for _ in range(needed):
            case = _pick(cases)
            offender = case.offender
            alert_type = _pick(
                [
                    "checkin_missed",
                    "gps_violation",
                    "drug_test_positive",
                    "employment_terminated",
                    "curfew_violation",
                    "battery_low",
                    "system",
                    "other",
                ]
            )
            priority = _pick(["low", "medium", "high", "critical"])
            status = _pick(["new", "acknowledged", "in_progress", "resolved", "closed"])
            acknowledged_by = _pick(officers) if officers and status != "new" else None
            resolved_by = _pick(officers) if officers and status in ("resolved", "closed") else None

            related_checkin = _pick(checkins) if checkins and alert_type == "checkin_missed" else None
            related_gps = _pick(gps_list) if gps_list and alert_type in ("gps_violation", "battery_low", "curfew_violation") else None

            title = {
                "checkin_missed": "Missed check-in detected",
                "gps_violation": "GPS monitoring violation",
                "drug_test_positive": "Positive drug test result",
                "employment_terminated": "Employment terminated",
                "curfew_violation": "Curfew violation",
                "battery_low": "GPS device battery low",
                "system": "System alert",
                "other": "General alert",
            }.get(alert_type, "Alert")

            Alert.objects.create(
                alert_type=alert_type,
                priority=priority,
                status=status,
                offender=offender,
                case=case,
                related_checkin=related_checkin,
                related_gps=related_gps,
                title=title,
                description="Alert generated by monitoring rules.",
                location=f"{offender.sub_county}, {offender.county}" if random.random() < 0.8 else "",
                acknowledged_time=timezone.now() - timedelta(hours=random.randint(1, 72)) if acknowledged_by else None,
                resolved_time=timezone.now() - timedelta(hours=random.randint(1, 24)) if resolved_by else None,
                acknowledged_by=acknowledged_by,
                resolved_by=resolved_by,
                resolution_notes="Reviewed and actioned." if resolved_by else "",
                action_taken="Called offender and scheduled follow-up." if resolved_by else "",
            )
