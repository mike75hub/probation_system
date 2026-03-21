# Architecture

## Architectural style
- **Server-rendered Django** with a modular “app per domain” structure.
- Business rules are primarily expressed through:
  - models (relationships + constraints),
  - forms (validation),
  - services/commands where automation is needed (e.g., officer auto-assignment).

## Key boundaries
- **Identity & access** (`accounts`): authentication, roles, officer designation.
- **Supervision** (`offenders`, `monitoring`): offender profiles, cases, officer assignment, check-ins.
- **Rehabilitation** (`programs`): program catalog, enrollment, session delivery, attendance.
- **Insights** (`dashboard`, `reports`, `ml_models`): monitoring KPIs, report outputs, optional predictions.

## Assignment strategy (case → officer)
Cases are assigned to officers via:
- an admin bulk action on cases, and
- a management command for batch assignment.

Strategy: **least-loaded** officer based on current active caseload, tie-break by officer id.

## Request flow (typical)
1. User authenticates via `accounts`.
2. Dashboard renders a role-specific view with relevant metrics.
3. The user performs workflow actions (create offender/case, schedule check-in, enroll in program).
4. The system records events with timestamps and status fields.

## Extensibility points
- Add an `Institution` model to scope all major entities for multi-tenant deployments.
- Swap SQLite → PostgreSQL and add proper backups/monitoring in production.
- Add a structured audit log (append-only) for high-compliance environments.

