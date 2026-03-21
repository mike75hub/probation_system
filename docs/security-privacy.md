# Security & Privacy (Design Phase)

## Authentication
- All protected pages require authenticated access.
- Roles are stored on the custom `User` model and used to gate views/templates.

## Authorization (least privilege)
- Admin: global access.
- Officer: scoped access to assigned cases/offenders where applicable.
- Offender: access limited to own profile/case information (as configured).
- Judiciary/NGO: scoped access for reporting and facilitation (as configured).

## Sensitive data (PII)
Examples:
- national ID / passport numbers,
- date of birth,
- addresses and contact details,
- risk scores and assessments.

Design practices:
- minimize display of sensitive fields by default,
- restrict list views and exports by role,
- prefer server-side authorization checks (not only template conditions).

## Web security controls
- CSRF protection enabled via Django middleware.
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` are environment-driven in production.
- Use HTTPS/TLS in production.

## Operational security
- Keep `.env` out of version control.
- Restrict database and media file access.
- Backups: scheduled snapshots of the database; secure key management.

## Auditability (recommended)
Current state uses timestamps and status fields on primary models.
For higher-compliance deployments, add:
- append-only audit events per critical action (create/update/delete/assign),
- report generation logs (who generated what, when).

