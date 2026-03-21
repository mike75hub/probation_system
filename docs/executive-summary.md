# Executive Summary

## What the system is
The Probation Management System is a role-based case supervision platform designed to:
- register offenders and their legal cases,
- assign probation officers to supervise cases,
- schedule and record check-ins and compliance,
- manage rehabilitation programs (catalog, enrollment, sessions, attendance),
- support reporting and dashboards,
- optionally use ML-driven risk scoring as decision support.

## Who it serves
- **Administrators:** user + configuration management, system-wide analytics, caseload oversight.
- **Probation Officers:** manage assigned cases, monitoring tasks, assessments, and program referrals.
- **Offenders:** view their supervision details (as configured) and assigned officer.
- **Judiciary / NGO staff:** participate in facilitation and reporting (as configured).

## Key outcomes
- Standardized intake and supervision workflow.
- Clear ownership of cases (assigned officer).
- Improved compliance visibility (scheduled vs completed/missed check-ins).
- Structured program participation tracking and measurable outcomes.

## Technology summary
- Django (server-rendered), SQLite for local/dev, optional PostgreSQL for production.
- Bootstrap UI + Crispy Forms.
- WhiteNoise for production static files.

