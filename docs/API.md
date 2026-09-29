# DAWN — API Reference

Every route in `app/main.py`, what it expects in the request, and what it
returns. Kept in sync with `main.py` the same way `SCHEMA.md` is kept in sync
with `models.py` — if they drift, this file is wrong and needs updating.

**Conventions across all routes:**
- Request bodies are JSON. `GET`/`DELETE` take no body; filters go in the query string.
- Any error from the service layer (bad ID, invalid state transition, etc.) comes back as `{"error": "..."}` with HTTP 400.
- Enum fields (`track`, `correctness`, etc.) are sent and returned as their plain string value — e.g. `"JEE"`, not `"Track.JEE"`.
- Datetimes are ISO 8601 strings (e.g. `"2026-09-29T11:21:59.201373"`); `null` where not yet set.
- A field marked **optional** can be omitted from the request body entirely — omitting it is treated as `null`/default, not an error.

---

## Subjects

### `GET /subjects`
Lists all active subjects. No query params.

### `POST /subjects`
| Field | Type | Required |
|---|---|---|
| `subject_name` | string | yes |

### `PATCH /subjects/<subject_id>`
| Field | Type | Required |
|---|---|---|
| `new_name` | string | yes |

### `DELETE /subjects/<subject_id>`
No body. Soft-deletes (sets `is_active = false`).

---

## Topics

### `GET /topics?subject_id=<int>`
Lists active topics. `subject_id` query param is **optional** — omit to list all.

### `POST /topics`
| Field | Type | Required |
|---|---|---|
| `topic_name` | string | yes |
| `subject_id` | int | yes |
| `track` | `"JEE"` \| `"Board"` \| `"Both"` | yes |

### `PATCH /topics/<topic_id>`
| Field | Type | Required |
|---|---|---|
| `new_name` | string | optional |
| `new_subject_id` | int | optional |
| `new_track` | `"JEE"` \| `"Board"` \| `"Both"` | optional |

### `DELETE /topics/<topic_id>`
No body. Soft-deletes.

### `POST /topics/merge`
Merges `source_topic_id` into `target_topic_id` — re-parents its subtopics, hard-deletes the source topic.

| Field | Type | Required |
|---|---|---|
| `source_topic_id` | int | yes |
| `target_topic_id` | int | yes |

---

## Subtopics

### `GET /subtopics?topic_id=<int>`
Lists active subtopics. `topic_id` query param is **optional**.

### `POST /subtopics`
| Field | Type | Required |
|---|---|---|
| `subtopic_name` | string | yes |
| `topic_id` | int | yes |

### `PATCH /subtopics/<subtopic_id>`
| Field | Type | Required |
|---|---|---|
| `new_name` | string | optional |
| `new_topic_id` | int | optional |

### `DELETE /subtopics/<subtopic_id>`
No body. Soft-deletes.

---

## Sources

### `GET /sources?topic_id=<int>`
Lists active sources. `topic_id` query param is **optional**.

### `POST /sources`
| Field | Type | Required |
|---|---|---|
| `book_name` | string | yes |
| `topic_id` | int | yes |
| `track` | `"JEE"` \| `"Board"` \| `"Both"` | yes |
| `rated_difficulty` | `"Easy"` \| `"Medium"` \| `"Hard"` \| `"Unrated"` | optional — defaults to `"Unrated"` |
| `difficulty_scheme` | `"labeled"` \| `"exercise-ordinal"` \| `"unknown"` | optional — defaults to `"unknown"` |
| `total_problems` | int | optional — defaults to `0` |
| `problems_solved` | int | optional — defaults to `0` |

### `PATCH /sources/<source_id>`
| Field | Type | Required |
|---|---|---|
| `new_name` | string | optional |
| `new_topic_id` | int | optional |
| `new_track` | `"JEE"` \| `"Board"` \| `"Both"` | optional |
| `new_rated_difficulty` | `"Easy"` \| `"Medium"` \| `"Hard"` \| `"Unrated"` | optional |
| `new_difficulty_scheme` | `"labeled"` \| `"exercise-ordinal"` \| `"unknown"` | optional |
| `new_total_problems` | int | optional |
| `new_problems_solved` | int | optional |

### `DELETE /sources/<source_id>`
No body. Soft-deletes.

---

## Source Exercises

### `GET /sources/<source_id>/exercises`
Lists active exercises for that source. `source_id` from the URL, no query params.

### `POST /sources/<source_id>/exercises`
`source_id` comes from the URL, not the body.

| Field | Type | Required |
|---|---|---|
| `exercise_number` | string (e.g. `"Exercise 3"`) | yes |
| `problems_in_exercise` | int | optional — defaults to `0` |
| `problems_solved` | int | optional — defaults to `0` |

### `PATCH /exercises/<exercise_id>`
| Field | Type | Required |
|---|---|---|
| `new_source_id` | int | optional |
| `new_exercise_number` | string | optional |
| `new_problems_in_exercise` | int | optional |
| `new_problems_solved` | int | optional |

### `DELETE /exercises/<exercise_id>`
No body. Soft-deletes.

---

## Sessions

### `GET /sessions/<session_id>`
Status snapshot. No body.

**Returns:**
```json
{
  "session": { ... },
  "current_question": { ... } | null,
  "questions": [ { ... }, ... ]
}
```
`current_question` is the row still awaiting completion (`timestamp` is `null`), or `null` if none is open (e.g. after `end_session`, or mid-batch waiting on `grade_batch`). `questions` lists every question logged in the session so far, in order.

### `POST /sessions`
Starts a session — creates the `Session` row and opens its first question row.

| Field | Type | Required |
|---|---|---|
| `topic_id` | int | yes |
| `source_id` | int | yes |
| `track` | `"JEE"` \| `"Board"` \| `"Both"` | yes |
| `starting_question_number` | int | optional — defaults to `1` |
| `subtopic_id` | int | optional |
| `exercise_id` | int | optional — omit for sources with no exercises (e.g. DPPs) |
| `batch_size` | int | optional — defaults to `10` |

**Returns:** `{"session": { ... }, "current_question": { ... }}`

### `POST /sessions/<session_id>/pause`
No body. Fails with 400 if already paused or the session has ended.

### `POST /sessions/<session_id>/resume`
No body. Fails with 400 if not currently paused.

### `POST /sessions/<session_id>/questions/complete`
Fills in the currently-open question (timing is auto-computed) and, if this doesn't close the batch, opens the next one.

| Field | Type | Required |
|---|---|---|
| `subjective_difficulty` | `"Easy"` \| `"Medium"` \| `"Hard"` | yes |
| `confidence_rating` | `"Low"` \| `"Medium"` \| `"High"` | optional |
| `photo_path` | string | optional |

**Returns:**
```json
{
  "completed_question": { ... },
  "batch_complete": true | false,
  "current_question": { ... } | null
}
```
`current_question` is the newly-opened next question, or `null` if `batch_complete` is `true` (nothing opens until `grade_batch` runs).

### `POST /sessions/<session_id>/grade`
Writes correctness/error type onto a batch of already-completed questions. Does **not** pause the session. If the source/exercise still has problems left and the session hasn't ended, opens the next question row.

| Field | Type | Required |
|---|---|---|
| `results` | array of `{"question_id": int, "correctness": string, "error_type": string}` | yes |

`correctness` is one of `"Correct"` \| `"Incorrect"` \| `"Partial"` \| `"Pending"`.
`error_type` is one of `"Nil"` \| `"Conceptual"` \| `"Silly"` \| `"Calculation"` \| `"Strategic"` \| `"Time-pressure"` \| `"Misread"`.

**Returns:**
```json
{
  "graded_questions": [ { ... }, ... ],
  "current_question": { ... } | null
}
```

### `POST /sessions/<session_id>/end`
Finishes the currently-open question (if any) using the same fields as `.../complete`, then ends the session without opening a new question row. Does not force grading.

| Field | Type | Required |
|---|---|---|
| `subjective_difficulty` | `"Easy"` \| `"Medium"` \| `"Hard"` | required **only if** a question is currently open |
| `confidence_rating` | `"Low"` \| `"Medium"` \| `"High"` | optional |
| `photo_path` | string | optional |

**Returns:**
```json
{
  "session": { ... },
  "ungraded_questions": [ { ... }, ... ]
}
```
`ungraded_questions` lists every completed-but-`Pending` question in the session (not just from the last batch) — the frontend should prompt to grade these before treating the session as fully closed out.
