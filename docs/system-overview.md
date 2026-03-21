# System Overview (Design Phase)

## Goals
- Single source of truth for supervision data.
- Role-based access with personalized views.
- Standard workflows for intake, assignment, monitoring, programs, and reporting.

## Scope
### In scope
- Accounts and role-based access.
- Offender profile management.
- Case management and officer assignment.
- Risk assessments and risk level tracking.
- Monitoring: check-ins and compliance.
- Programs: categories, program lifecycle, enrollments, sessions, attendance.
- Reporting and dashboards (admin/officer/offender views).

### Planned extensions
- Multi-institution tenancy (scoping data to an institution/office).
- External integrations (SMS/email notifications, court systems, national ID verification).
- Deeper audit trail (immutable event logs).

## Core assumptions
- An offender may have multiple cases; supervision is tied to the **active case**.
- A case may be assigned to **one** officer at a time.
- Program participation is tracked through enrollments, sessions, and attendance records.

## Non-functional requirements (NFRs)
- **Security:** authentication, least privilege, safe defaults, CSRF protection.
- **Auditability:** timestamps and traceability for key records.
- **Performance:** pagination and selective querying for lists/dashboards.
- **Reliability:** predictable operations and backup strategy.
- **Maintainability:** modular Django apps, consistent patterns (forms/views/templates).

## Modules (Django apps)
- `accounts`: custom user model (roles, officer designation), authentication, admin user pages.
- `offenders`: offender profiles, cases, assessments; officer assignment on cases.
- `monitoring`: check-ins, compliance tracking, and supervision events.
- `programs`: program catalog (categories/programs) and participation (enrollment/sessions/attendance).
- `reports`: report generation + scheduling.
- `datasets` / `ml_models`: optional data + ML support.
- `dashboard`: role-specific dashboards and cross-module metrics.

