# DAWN — Data Schema

This is the working reference for the database structure — check here while coding rather than the full plan doc. Keep this in sync with the actual SQLAlchemy models as they evolve; if the two drift apart, this file is wrong and needs updating, not the code.

**Design principle:** raw, granular, append-only records over clean aggregates. Aggregates (average accuracy, calibrated difficulty) are always a recomputable cache on top of raw rows — never the only place that information lives. This is what keeps the dataset genuinely usable for statistical/ML work later, not just for the dashboard.

**Normalization principle:** Subject, Topic, and Subtopic are standalone entities, not free-text strings repeated across tables — a full three-level hierarchy (Subject → Topic → Subtopic). Every table that references any of these does so via foreign key, not by re-typing the name — this avoids silent mismatches (typos, inconsistent casing) that would otherwise corrupt joins, accuracy rollups, and any future IRT/ML grouping.

---

### Subjects

| Column | Type | Notes |
|---|---|---|
| subject_id | PK | |
| subject_name | text | e.g. "Physics", "Chemistry", "Maths" |

### Topics

| Column | Type | Notes |
|---|---|---|
| topic_id | PK | |
| topic_name | text | e.g. "Rotational Dynamics" |
| subject_id | FK → Subjects | |
| track | JEE / Board / Both | some topics overlap both syllabi |

### Subtopics

| Column | Type | Notes |
|---|---|---|
| subtopic_id | PK | |
| topic_id | FK → Topics | every subtopic belongs to exactly one topic |
| subtopic_name | text | e.g. "Moment of Inertia" |

### Sources
*One row per Book × Topic — same book gets multiple rows across topics, since calibration is topic-specific.*

| Column | Type | Notes |
|---|---|---|
| source_id | PK | |
| book_name | text | e.g. "HC Verma Part 1" |
| topic_id | FK → Topics | |
| track | JEE / Board | |
| rated_difficulty | Easy/Medium/Hard/Unrated | book's own stated label, if any |
| difficulty_scheme | labeled / exercise-ordinal / unknown | |
| total_problems | int | |
| problems_solved | int | |
| calibrated_difficulty | float | learned, not stated |
| average_accuracy | float | recomputable cache |
| calibration_confidence | uncalibrated / provisional / calibrated | |

### Source_Exercises (child of Sources)
*Exercise-wise calibration — a Source can have many exercises, each independently calibrated.*

| Column | Type | Notes |
|---|---|---|
| exercise_id | PK | |
| source_id | FK → Sources | |
| exercise_number | text | "Exercise 3", etc. |
| problems_in_exercise | int | |
| problems_solved | int | |
| calibrated_difficulty | float | empirical, per exercise |
| average_accuracy | float | |

### Questions
*Every attempt — raw and append-only. Redoing a queued wrong question creates a **new row**, never overwrites the old one.*

| Column | Type | Notes |
|---|---|---|
| question_id | PK | |
| session_id | FK → Sessions | |
| source_id | FK → Sources | |
| exercise_id | FK → Source_Exercises | nullable |
| topic_id | FK → Topics | |
| subtopic_id | FK → Subtopics | |
| track | JEE / Board | |
| question_number | int | auto-increment within session |
| subjective_difficulty | Easy/Med/Hard | logged live, mid-session |
| correctness | Correct/Incorrect/Partial/Pending | logged at batch grading, not live |
| error_type | Nil/Conceptual/Silly/Calculation/Strategic/Time-pressure/Misread | only if incorrect |
| time_taken_seconds | int | auto-computed from timestamps |
| timestamp | datetime | full moment logged — enables day/time/fatigue analysis later |
| position_in_session | int | ordinal position in session/batch — within-session fatigue modeling |
| confidence_rating | Low/Med/High, optional | metacognitive signal — do you know what you know |
| original_question_id | FK → Questions, nullable | points back to the original attempt if this row is a redo |
| photo_path | text | nullable, doubt-solving reference |

### Sessions
*Fixed metadata set once at session start.*

| Column | Type | Notes |
|---|---|---|
| session_id | PK | |
| topic_id | FK → Topics | |
| subtopic_id | FK → Subtopics | |
| source_id | FK → Sources | |
| track | JEE / Board | |
| starting_question_number | int | |
| batch_size | int | default 10 |
| start_time | timestamp | |
| end_time | timestamp | nullable until session ends |

### ErrorQueue

| Column | Type | Notes |
|---|---|---|
| queue_id | PK | |
| question_id | FK → Questions | the original wrong attempt |
| error_type | text | copied from Questions for fast filtering |
| times_reviewed | int | |
| last_reviewed | timestamp | nullable |
| next_review_date | date | graduated interval logic |
| status | pending / diagnosed / resolved | |

### Tests (TWT/MT)

| Column | Type | Notes |
|---|---|---|
| test_id | PK | |
| date | date | |
| type | TWT / MT | |
| track | JEE / Board | |
| subject_scores | JSON | per-subject breakdown |
| overall_percentile | float | nullable |
| paper_pdf_path | text | nullable |
| answer_key_pdf_path | text | nullable |

### Assignments (teacher homework)

| Column | Type | Notes |
|---|---|---|
| assignment_id | PK | |
| source_id | FK → Sources | nullable if not from a tracked book |
| topic_id | FK → Topics | |
| due_date | date | |
| status | assigned / in_progress / done | |

### Board_Syllabus

| Column | Type | Notes |
|---|---|---|
| syllabus_id | PK | |
| subject | text | |
| chapter | text | |
| topic_id | FK → Topics, nullable | link only when this chapter genuinely overlaps JEE content — leave null when Board's framing/depth differs enough that forcing a shared topic would be misleading |
| due_date | date | internal/board exam |
| status | not_started / in_progress / done | |
