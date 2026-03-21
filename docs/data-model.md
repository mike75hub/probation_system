# Data Model

This system uses a relational model built around offender supervision and program participation.

## Entity relationship diagram (ERD)

```mermaid
erDiagram
    USER {
        int id PK
        string username
        string role
        string designation
        string email
        string phone
        bool is_active
    }

    OFFENDER {
        int id PK
        int user_id FK
        string offender_id
        string id_number
        date date_of_birth
        string risk_level
        bool is_active
        datetime date_created
    }

    CASE {
        int id PK
        int offender_id FK
        int probation_officer_id FK
        string case_number
        string status
        date sentence_start
        date sentence_end
        datetime date_created
    }

    ASSESSMENT {
        int id PK
        int offender_id FK
        int assessed_by_id FK
        date assessment_date
        float overall_risk_score
    }

    CHECKIN_TYPE {
        int id PK
        string name
        bool is_active
    }

    CHECKIN {
        int id PK
        int case_id FK
        int offender_id FK
        int probation_officer_id FK
        int checkin_type_id FK
        datetime scheduled_date
        string status
        string compliance_level
    }

    PROGRAM_CATEGORY {
        int id PK
        string name
        string slug
        bool is_active
        int display_order
    }

    PROGRAM {
        int id PK
        int category_id FK
        int facilitator_id FK
        string code
        string name
        string program_type
        string status
        string frequency
        string delivery_method
        date start_date
        date end_date
        int max_participants
    }

    ENROLLMENT {
        int id PK
        int program_id FK
        int offender_id FK
        int referred_by_id FK
        string status
        date enrollment_date
        float attendance_rate
        string completion_grade
    }

    SESSION {
        int id PK
        int program_id FK
        int facilitator_id FK
        int session_number
        date date
        time start_time
        time end_time
        bool is_completed
    }

    ATTENDANCE {
        int id PK
        int session_id FK
        int enrollment_id FK
        string status
        int participation_score
    }

    USER ||--|| OFFENDER : "has profile"
    OFFENDER ||--o{ CASE : "has cases"
    USER ||--o{ CASE : "supervises"
    OFFENDER ||--o{ ASSESSMENT : "has assessments"
    USER ||--o{ ASSESSMENT : "assesses"

    PROGRAM_CATEGORY ||--o{ PROGRAM : "contains"
    USER ||--o{ PROGRAM : "facilitates"
    PROGRAM ||--o{ ENROLLMENT : "has enrollments"
    OFFENDER ||--o{ ENROLLMENT : "participates"
    USER ||--o{ ENROLLMENT : "refers"
    PROGRAM ||--o{ SESSION : "has sessions"
    SESSION ||--o{ ATTENDANCE : "records"
    ENROLLMENT ||--o{ ATTENDANCE : "per session"

    CHECKIN_TYPE ||--o{ CHECKIN : "type"
    CASE ||--o{ CHECKIN : "check-ins"
    OFFENDER ||--o{ CHECKIN : "check-ins"
    USER ||--o{ CHECKIN : "officer"
```

## Design notes
- **Officer assignment** is stored on `Case` (`probation_officer_id`), which aligns supervision to the legal context.
- `Enrollment` is unique per `(program, offender)` to prevent duplicate enrollments.
- Program delivery is expressed through `Session` and tracked via `Attendance`.

