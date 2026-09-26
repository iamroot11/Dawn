# DAWN — Decisions Log

Running record of real design choices and the reasoning behind them, in the order they were made. New entries go at the bottom, dated. This is not a changelog of code — it's the "why," kept in the moment rather than reconstructed later.

---

**Core premise.** DAWN isn't a tracker, it's a proactive learning system — it should actively decide what to practice next, not just report on what already happened.

**Zone of Tension.** Hypothesis: maximum learning happens around 85% accuracy — above that, no real challenge; below that, fundamentals aren't there yet. This mirrors real research (Wilson, Shenhav, Straccia & Cohen, 2019, "The Eighty Five Percent Rule for Optimal Learning"), though that study was on algorithms/simple tasks, not directly on JEE-style multi-step problems — treated as a strong design principle to steer toward, not a hard law, and the real number may end up being personally calibrated over time.

**Outcomes over hours.** Success is measured by shrinking weak-topic count, rising mastery trend, and test performance — not hours logged. Hours are a background stat, never the headline metric.

**Rote memorization → Anki, not rebuilt.** Formulas, reactions, and pure recall don't need a custom spaced-repetition engine — Anki's FSRS algorithm already does this well. DAWN's job is generation (auto-create cards from diagnosed rote gaps) and routing, not scheduling.

**Language/architecture: Python, not React/web-hosted.** User is more comfortable in Python and wants to understand every line of code (AI builds to spec, doesn't design independently). Chose FastAPI + SQLite running locally on the laptop, reachable from iPad/phone over home wifi via local IP — no cloud hosting, no cost, no deployment pipeline to maintain.

**Zone of Tension is batch-scoped, not real-time.** Originally assumed live per-question adaptive selection was possible. Corrected: DAWN never digitizes actual question content (books stay physical), and correctness is only known after a grading pass anyway — so real-time item-level steering isn't feasible without a fully digitized, pre-tagged question bank (out of scope). Redesigned around batches of ~10 questions: log difficulty live, grade the whole batch at once against the answer key, and let that batch's accuracy inform the *next* batch/session's difficulty and source recommendation.

**Session-scoped logging.** Topic, subtopic, and source are fixed once at session start — per-question logging during a session only requires the difficulty tap, keeping entry under ~15 seconds to avoid the friction that kills adherence.

**Source calibration solves "where do I actually practice this from."** Difficulty isn't one absolute scale across books — each source keeps its own stated difficulty plus a learned calibration multiplier from actual results. Recommendations always resolve to a concrete instruction (book + calibrated difficulty band), never a bare topic name.

**Cold-start problem.** Calibration only exists after attempts are logged from a source, so brand-new sources have no calibration data yet — this is the exact circularity the user caught. Fix: every source carries a confidence level (uncalibrated/provisional/calibrated); uncalibrated sources fall back to the book's stated difficulty as a prior, and DAWN explicitly frames early questions from a new source as calibration probes, not just practice.

**Exercise-ordinal difficulty handling.** Some books only label "Exercise 1, 2, 3..." with no guaranteed difficulty progression. DAWN does not assume later exercises are harder — it empirically calibrates accuracy per exercise number from real results and only treats exercise order as a difficulty proxy once the data actually supports it for that specific book.

**Error queue has its own decay logic, competing with new practice.** Hypothesis: an error diagnosed once and never revisited will be forgotten again, making the diagnosis useless. Fix: queued wrong problems get graduated review intervals (correct redo → interval extends, e.g. 3→7→16 days; wrong again → resets short), and when queue urgency crosses a threshold, the scheduler can override planned new-practice time entirely rather than treating review as a background task.

**AnkiConnect integration.** DAWN was blind to whether outsourced memorization was actually being retained. Fix: poll Anki's local HTTP API (AnkiConnect, requires Anki desktop running) for per-deck retention rate, cards due, and mature/young ratio, feeding this into the scheduler as a real input rather than assuming Anki decks are being handled fine on their own.

**Concept AI must be rigorous, not just convenient.** Explicit goal: genuine teacher-independence, not just supplementary help. Design choices: JEE Advanced-level rigor by default, deliberate cross-chapter connections, real PYQ patterns pulled in, inline diagrams, and a two-phase Learn/Re-explain structure where the AI withholds correction until the user has fully explained a concept from memory, then interrogates like a strict examiner. Explicit caveat logged: an LLM can be confidently wrong on subtle edge cases, so a verification habit (cross-checking anything load-bearing) is treated as necessary, not optional, given the stated goal of reduced teacher dependency.

**Homework as a third, fixed-deadline stream.** Unlike JEE (flexible, decay-driven) and Board (deadline-driven but DAWN-visible), teacher-assigned homework is an external hard constraint DAWN doesn't choose. Modeled as its own stream with due dates the scheduler treats as non-negotiable, while completed homework still logs through the same question-tracking mechanics for full analytics benefit.

**Board terminology, not HSC.** User hasn't decided between HSC and ISC — all schema fields and module names use generic "Board" language instead of assuming HSC specifically.

**Schema normalization: Topics/Subtopics as standalone tables.** Originally free-text columns repeated across Sources, Sessions, Questions, and Assignments — risked silent mismatches (typos, inconsistent casing) that would corrupt joins and analytics. Fixed by making Topics and Subtopics their own tables, referenced everywhere by foreign key. Board_Syllabus gets an optional nullable link to Topics, used only when a Board chapter genuinely overlaps JEE content closely enough that sharing decay/mastery data wouldn't be misleading.

**Schema built for future statistical/ML work, not just the dashboard.** User will be learning statistics/ML (IRT, survival analysis, regression, classification) alongside JEE prep and wants this dataset usable for that later. Design principle adopted: raw, granular, append-only records always take priority over clean aggregates — aggregates are a recomputable cache, never the only surviving record. Concretely: full timestamps (not just duration) for time-of-day/fatigue analysis, `position_in_session` for within-session fatigue modeling, optional `confidence_rating` for metacognitive calibration data, and `original_question_id` so a redo creates a new row rather than overwriting history — preserving the full attempt sequence needed for future forgetting-curve/survival-analysis modeling. This statistical/ML layer itself is scoped as Phase 7 — a stretch goal built after the core system works and real data exists, not part of the MVP.

**Docs structure.** Split into `PLAN.md` (vision/modules, evolves with scope), `SCHEMA.md` (working reference, kept in sync with actual code), and `DECISIONS.md` (this file — dated reasoning trail, append-only by nature). README stays at repo root as the entry point.

**Subject normalized as its own table, above Topics.** Same reasoning as the Topic/Subtopic fix — "Physics"/"Chemistry"/"Maths" as free text on Topics carried the same typo/mismatch risk already fixed one level down. Corrected to a full three-level hierarchy (Subject → Topic → Subtopic), with Topics referencing Subjects by foreign key instead of a string.

**Sessions need live state to auto-compute question numbers and timing.** Building the actual question-logging endpoints exposed a gap: server-side auto-increment of `question_number` and auto-computed `time_taken_seconds` require knowing which question is currently active and when it started. Added `current_question_number` and `current_question_started_at` to Sessions — advanced on every question logged, read on the next one to compute elapsed time. Without this, the client would need to track and send timing itself, defeating the point of server-side computation.

**Naming collision: SQLAlchemy's `Session` model vs. `sqlalchemy.orm.Session`.** The DAWN table representing a study session is named `Session`, which collides with the standard import name for a database session object. Resolved by aliasing on import (`from app.models import Session as DBSession`) rather than renaming the table — the table name `Session` matches the domain language used everywhere else in the docs.

**Session pause/resume, without touching timer math at read time.** Real study sessions get interrupted (calls, breaks) — logging a question after a long unlogged gap would corrupt `time_taken_seconds` unless pause time is accounted for. Added `is_paused`, `paused_at`, `total_paused_seconds` to Sessions. Resolved by shifting `current_question_started_at` forward by the pause duration on resume, rather than subtracting pause time wherever timing is calculated — the existing `time_taken = now − current_question_started_at` formula in `/questions` needed zero changes as a result. `/questions` also rejects logging while `is_paused` is true, forcing an explicit resume first.

**Subtopic made optional on Sessions and Questions.** Not every topic subdivides cleanly into subtopics — forcing one on every session/question would push toward fake placeholder subtopics just to satisfy the schema, corrupting the same data the Topic/Subtopic normalization was meant to protect. `subtopic_id` is now nullable wherever it's used as a foreign key (Sessions, Questions). The Subtopics table itself, and its link to Topics, stays mandatory — that governs what a subtopic *is*, not where it's *used*.

25/9/2026
**Deleted all Pydantic and FastAPI Models**: All of the Pydantic schemas, FastAPI Models are getting confusing, so removing them temporarily to focus purely on the schema.

25/9/2026
**Decision to use simple HTTP Requests:** Considering the complexity of Pydantic and FastAPI, and the needs of the project, will be using HTTP Requests in JSON for simpler methods. 