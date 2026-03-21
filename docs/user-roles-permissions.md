# User Roles, Permissions, and Personalized Views

## Roles
- **Admin (`admin`)**
- **Probation Officer (`officer`)**
- **Offender (`offender`)**
- **Judiciary (`judiciary`)**
- **NGO (`ngo`)**

## Role capabilities (design intent)

| Area | Admin | Officer | Offender | Judiciary | NGO |
|---|---|---|---|---|---|
| User management | full | view self | view self | view self | view self |
| Officer directory + designation | full | view self | - | - | - |
| Offenders | full | create/update | view self | view (scoped) | view (scoped) |
| Cases | full | manage assigned | view own | view (scoped) | - |
| Assessments | full | create/manage | view own (optional) | view | - |
| Check-ins / monitoring | full | manage assigned | view own | view | - |
| Programs catalog | full | view/enroll | view | view | create/facilitate (as allowed) |
| Reports | full | generate (scoped) | view (optional) | view | view |

## Personalized views
- **Officer pages:** officer list + officer detail/caseload view for admins (and self-view for the officer).
- **Offender pages:** offender detail shows active case information and assigned officer (derived from active case).
- **Dashboards:** different dashboard cards and KPIs by role.

## Officer designation
Officers include a `designation` field (e.g., “Senior Probation Officer”, “Case Manager”, “Programs Liaison”).
This improves:
- filtering/search in officer lists,
- presentation clarity (who does what),
- reporting (grouping by designation in future iterations).

