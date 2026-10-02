/// DAWN — Dart models.
///
/// Mirrors app/models.py (and docs/SCHEMA.md). Plain Dart, no code generation:
/// every class has `fromJson` / `toJson` matching the snake_case keys the
/// Flask API returns. Enums serialize to their plain string value
/// ("JEE", not "Track.jee"). Requires Dart 2.17+ (enhanced enums).
library;

// ============================================================
// Helpers
// ============================================================

DateTime? _dt(dynamic v) => v == null ? null : DateTime.parse(v as String);
String? _iso(DateTime? d) => d?.toIso8601String();
double? _dbl(dynamic v) => (v as num?)?.toDouble();

/// Date-only (no time) — for columns that are `Date` rather than `DateTime`.
String? _dateOnly(DateTime? d) => d?.toIso8601String().substring(0, 10);

T? _opt<T>(dynamic v, T Function(String) parse) =>
    v == null ? null : parse(v as String);

// ============================================================
// Enums
// ============================================================

enum Track {
  jee('JEE'),
  board('Board'),
  both('Both');

  final String value;
  const Track(this.value);
  static Track fromJson(String v) => values.firstWhere((e) => e.value == v);
}

enum RatedDifficulty {
  easy('Easy'),
  medium('Medium'),
  hard('Hard'),
  unrated('Unrated');

  final String value;
  const RatedDifficulty(this.value);
  static RatedDifficulty fromJson(String v) =>
      values.firstWhere((e) => e.value == v);
}

enum DifficultyScheme {
  labeled('labeled'),
  exerciseOrdinal('exercise-ordinal'),
  unknown('unknown');

  final String value;
  const DifficultyScheme(this.value);
  static DifficultyScheme fromJson(String v) =>
      values.firstWhere((e) => e.value == v);
}

enum CalibrationConfidence {
  uncalibrated('uncalibrated'),
  provisional('provisional'),
  calibrated('calibrated');

  final String value;
  const CalibrationConfidence(this.value);
  static CalibrationConfidence fromJson(String v) =>
      values.firstWhere((e) => e.value == v);
}

enum SubjectiveDifficulty {
  easy('Easy'),
  medium('Medium'),
  hard('Hard');

  final String value;
  const SubjectiveDifficulty(this.value);
  static SubjectiveDifficulty fromJson(String v) =>
      values.firstWhere((e) => e.value == v);
}

enum Correctness {
  correct('Correct'),
  incorrect('Incorrect'),
  partial('Partial'),
  pending('Pending');

  final String value;
  const Correctness(this.value);
  static Correctness fromJson(String v) =>
      values.firstWhere((e) => e.value == v);
}

enum ErrorType {
  nil('Nil'),
  conceptual('Conceptual'),
  silly('Silly'),
  calculation('Calculation'),
  strategic('Strategic'),
  timePressure('Time-pressure'),
  misread('Misread');

  final String value;
  const ErrorType(this.value);
  static ErrorType fromJson(String v) => values.firstWhere((e) => e.value == v);
}

enum ConfidenceRating {
  low('Low'),
  medium('Medium'),
  high('High');

  final String value;
  const ConfidenceRating(this.value);
  static ConfidenceRating fromJson(String v) =>
      values.firstWhere((e) => e.value == v);
}

enum QueueStatus {
  pending('pending'),
  diagnosed('diagnosed'),
  resolved('resolved');

  final String value;
  const QueueStatus(this.value);
  static QueueStatus fromJson(String v) =>
      values.firstWhere((e) => e.value == v);
}

enum TestType {
  twt('TWT'),
  mt('MT');

  final String value;
  const TestType(this.value);
  static TestType fromJson(String v) => values.firstWhere((e) => e.value == v);
}

enum AssignmentStatus {
  assigned('assigned'),
  inProgress('in_progress'),
  done('done');

  final String value;
  const AssignmentStatus(this.value);
  static AssignmentStatus fromJson(String v) =>
      values.firstWhere((e) => e.value == v);
}

enum SyllabusStatus {
  notStarted('not_started'),
  inProgress('in_progress'),
  done('done');

  final String value;
  const SyllabusStatus(this.value);
  static SyllabusStatus fromJson(String v) =>
      values.firstWhere((e) => e.value == v);
}

// ============================================================
// Subjects / Topics / Subtopics
// ============================================================

class Subject {
  final int subjectId;
  final String subjectName;
  final bool isActive;

  const Subject({
    required this.subjectId,
    required this.subjectName,
    this.isActive = true,
  });

  factory Subject.fromJson(Map<String, dynamic> j) => Subject(
    subjectId: j['subject_id'] as int,
    subjectName: j['subject_name'] as String,
    isActive: j['is_active'] as bool? ?? true,
  );

  Map<String, dynamic> toJson() => {
    'subject_id': subjectId,
    'subject_name': subjectName,
    'is_active': isActive,
  };
}

class Topic {
  final int topicId;
  final String topicName;
  final int subjectId;
  final Track track;
  final bool isActive;

  const Topic({
    required this.topicId,
    required this.topicName,
    required this.subjectId,
    this.track = Track.jee,
    this.isActive = true,
  });

  factory Topic.fromJson(Map<String, dynamic> j) => Topic(
    topicId: j['topic_id'] as int,
    topicName: j['topic_name'] as String,
    subjectId: j['subject_id'] as int,
    track: Track.fromJson(j['track'] as String),
    isActive: j['is_active'] as bool? ?? true,
  );

  Map<String, dynamic> toJson() => {
    'topic_id': topicId,
    'topic_name': topicName,
    'subject_id': subjectId,
    'track': track.value,
    'is_active': isActive,
  };
}

class Subtopic {
  final int subtopicId;
  final int topicId;
  final String subtopicName;
  final bool isActive;

  const Subtopic({
    required this.subtopicId,
    required this.topicId,
    required this.subtopicName,
    this.isActive = true,
  });

  factory Subtopic.fromJson(Map<String, dynamic> j) => Subtopic(
    subtopicId: j['subtopic_id'] as int,
    topicId: j['topic_id'] as int,
    subtopicName: j['subtopic_name'] as String,
    isActive: j['is_active'] as bool? ?? true,
  );

  Map<String, dynamic> toJson() => {
    'subtopic_id': subtopicId,
    'topic_id': topicId,
    'subtopic_name': subtopicName,
    'is_active': isActive,
  };
}

// ============================================================
// Sources / Source exercises
// ============================================================

class Source {
  final int sourceId;
  final String bookName;
  final int topicId;
  final Track track;
  final RatedDifficulty ratedDifficulty;
  final DifficultyScheme difficultyScheme;
  final int totalProblems;
  final int problemsSolved;
  final double? calibratedDifficulty;
  final double? averageAccuracy;
  final CalibrationConfidence calibrationConfidence;
  final bool isActive;

  const Source({
    required this.sourceId,
    required this.bookName,
    required this.topicId,
    this.track = Track.jee,
    this.ratedDifficulty = RatedDifficulty.unrated,
    this.difficultyScheme = DifficultyScheme.unknown,
    this.totalProblems = 0,
    this.problemsSolved = 0,
    this.calibratedDifficulty,
    this.averageAccuracy,
    this.calibrationConfidence = CalibrationConfidence.uncalibrated,
    this.isActive = true,
  });

  factory Source.fromJson(Map<String, dynamic> j) => Source(
    sourceId: j['source_id'] as int,
    bookName: j['book_name'] as String,
    topicId: j['topic_id'] as int,
    track: Track.fromJson(j['track'] as String),
    ratedDifficulty: RatedDifficulty.fromJson(j['rated_difficulty'] as String),
    difficultyScheme: DifficultyScheme.fromJson(
      j['difficulty_scheme'] as String,
    ),
    totalProblems: j['total_problems'] as int? ?? 0,
    problemsSolved: j['problems_solved'] as int? ?? 0,
    calibratedDifficulty: _dbl(j['calibrated_difficulty']),
    averageAccuracy: _dbl(j['average_accuracy']),
    calibrationConfidence: CalibrationConfidence.fromJson(
      j['calibration_confidence'] as String,
    ),
    isActive: j['is_active'] as bool? ?? true,
  );

  Map<String, dynamic> toJson() => {
    'source_id': sourceId,
    'book_name': bookName,
    'topic_id': topicId,
    'track': track.value,
    'rated_difficulty': ratedDifficulty.value,
    'difficulty_scheme': difficultyScheme.value,
    'total_problems': totalProblems,
    'problems_solved': problemsSolved,
    'calibrated_difficulty': calibratedDifficulty,
    'average_accuracy': averageAccuracy,
    'calibration_confidence': calibrationConfidence.value,
    'is_active': isActive,
  };
}

class SourceExercise {
  final int exerciseId;
  final int sourceId;
  final String exerciseNumber; // e.g. "Exercise 3"
  final int problemsInExercise;
  final int problemsSolved;
  final double? calibratedDifficulty;
  final double? averageAccuracy;
  final bool isActive;

  const SourceExercise({
    required this.exerciseId,
    required this.sourceId,
    required this.exerciseNumber,
    this.problemsInExercise = 0,
    this.problemsSolved = 0,
    this.calibratedDifficulty,
    this.averageAccuracy,
    this.isActive = true,
  });

  factory SourceExercise.fromJson(Map<String, dynamic> j) => SourceExercise(
    exerciseId: j['exercise_id'] as int,
    sourceId: j['source_id'] as int,
    exerciseNumber: j['exercise_number'] as String,
    problemsInExercise: j['problems_in_exercise'] as int? ?? 0,
    problemsSolved: j['problems_solved'] as int? ?? 0,
    calibratedDifficulty: _dbl(j['calibrated_difficulty']),
    averageAccuracy: _dbl(j['average_accuracy']),
    isActive: j['is_active'] as bool? ?? true,
  );

  Map<String, dynamic> toJson() => {
    'exercise_id': exerciseId,
    'source_id': sourceId,
    'exercise_number': exerciseNumber,
    'problems_in_exercise': problemsInExercise,
    'problems_solved': problemsSolved,
    'calibrated_difficulty': calibratedDifficulty,
    'average_accuracy': averageAccuracy,
    'is_active': isActive,
  };
}

// ============================================================
// Sessions
// ============================================================

class Session {
  final int sessionId;
  final int topicId;
  final int? subtopicId;
  final int sourceId;
  final int? exerciseId;
  final Track track;
  final int startingQuestionNumber;
  final int batchSize;
  final bool isPaused;
  final DateTime? pausedAt;
  final int totalPausedSeconds;
  final DateTime startTime;
  final DateTime? endTime;

  const Session({
    required this.sessionId,
    required this.topicId,
    this.subtopicId,
    required this.sourceId,
    this.exerciseId,
    this.track = Track.jee,
    this.startingQuestionNumber = 1,
    this.batchSize = 10,
    this.isPaused = false,
    this.pausedAt,
    this.totalPausedSeconds = 0,
    required this.startTime,
    this.endTime,
  });

  bool get hasEnded => endTime != null;

  factory Session.fromJson(Map<String, dynamic> j) => Session(
    sessionId: j['session_id'] as int,
    topicId: j['topic_id'] as int,
    subtopicId: j['subtopic_id'] as int?,
    sourceId: j['source_id'] as int,
    exerciseId: j['exercise_id'] as int?,
    track: Track.fromJson(j['track'] as String),
    startingQuestionNumber: j['starting_question_number'] as int? ?? 1,
    batchSize: j['batch_size'] as int? ?? 10,
    isPaused: j['is_paused'] as bool? ?? false,
    pausedAt: _dt(j['paused_at']),
    totalPausedSeconds: j['total_paused_seconds'] as int? ?? 0,
    startTime: _dt(j['start_time'])!,
    endTime: _dt(j['end_time']),
  );

  Map<String, dynamic> toJson() => {
    'session_id': sessionId,
    'topic_id': topicId,
    'subtopic_id': subtopicId,
    'source_id': sourceId,
    'exercise_id': exerciseId,
    'track': track.value,
    'starting_question_number': startingQuestionNumber,
    'batch_size': batchSize,
    'is_paused': isPaused,
    'paused_at': _iso(pausedAt),
    'total_paused_seconds': totalPausedSeconds,
    'start_time': _iso(startTime),
    'end_time': _iso(endTime),
  };
}

// ============================================================
// Questions
// ============================================================

class Question {
  final int questionId;
  final int sessionId;
  final int sourceId;
  final int? exerciseId;
  final int topicId;
  final int? subtopicId;
  final Track track;
  final int questionNumber;
  final SubjectiveDifficulty? subjectiveDifficulty;
  final Correctness correctness;
  final ErrorType? errorType;
  final DateTime startedAt;
  final int? timeTakenSeconds;

  /// null => this is the currently-open, unfinished question in its session.
  final DateTime? timestamp;
  final int? positionInSession;
  final ConfidenceRating? confidenceRating;
  final int? originalQuestionId;
  final String? photoPath;

  const Question({
    required this.questionId,
    required this.sessionId,
    required this.sourceId,
    this.exerciseId,
    required this.topicId,
    this.subtopicId,
    this.track = Track.jee,
    required this.questionNumber,
    this.subjectiveDifficulty,
    this.correctness = Correctness.pending,
    this.errorType,
    required this.startedAt,
    this.timeTakenSeconds,
    this.timestamp,
    this.positionInSession,
    this.confidenceRating,
    this.originalQuestionId,
    this.photoPath,
  });

  bool get isOpen => timestamp == null;
  bool get isUngraded => !isOpen && correctness == Correctness.pending;

  factory Question.fromJson(Map<String, dynamic> j) => Question(
    questionId: j['question_id'] as int,
    sessionId: j['session_id'] as int,
    sourceId: j['source_id'] as int,
    exerciseId: j['exercise_id'] as int?,
    topicId: j['topic_id'] as int,
    subtopicId: j['subtopic_id'] as int?,
    track: Track.fromJson(j['track'] as String),
    questionNumber: j['question_number'] as int,
    subjectiveDifficulty: _opt(
      j['subjective_difficulty'],
      SubjectiveDifficulty.fromJson,
    ),
    correctness: Correctness.fromJson(j['correctness'] as String),
    errorType: _opt(j['error_type'], ErrorType.fromJson),
    startedAt: _dt(j['started_at'])!,
    timeTakenSeconds: j['time_taken_seconds'] as int?,
    timestamp: _dt(j['timestamp']),
    positionInSession: j['position_in_session'] as int?,
    confidenceRating: _opt(j['confidence_rating'], ConfidenceRating.fromJson),
    originalQuestionId: j['original_question_id'] as int?,
    photoPath: j['photo_path'] as String?,
  );

  Map<String, dynamic> toJson() => {
    'question_id': questionId,
    'session_id': sessionId,
    'source_id': sourceId,
    'exercise_id': exerciseId,
    'topic_id': topicId,
    'subtopic_id': subtopicId,
    'track': track.value,
    'question_number': questionNumber,
    'subjective_difficulty': subjectiveDifficulty?.value,
    'correctness': correctness.value,
    'error_type': errorType?.value,
    'started_at': _iso(startedAt),
    'time_taken_seconds': timeTakenSeconds,
    'timestamp': _iso(timestamp),
    'position_in_session': positionInSession,
    'confidence_rating': confidenceRating?.value,
    'original_question_id': originalQuestionId,
    'photo_path': photoPath,
  };
}

// ============================================================
// Error queue
// ============================================================

class ErrorQueueItem {
  final int queueId;
  final int questionId;
  final ErrorType errorType;
  final int timesReviewed;
  final DateTime? lastReviewed;
  final DateTime? nextReviewDate; // date-only
  final QueueStatus status;

  const ErrorQueueItem({
    required this.queueId,
    required this.questionId,
    required this.errorType,
    this.timesReviewed = 0,
    this.lastReviewed,
    this.nextReviewDate,
    this.status = QueueStatus.pending,
  });

  factory ErrorQueueItem.fromJson(Map<String, dynamic> j) => ErrorQueueItem(
    queueId: j['queue_id'] as int,
    questionId: j['question_id'] as int,
    errorType: ErrorType.fromJson(j['error_type'] as String),
    timesReviewed: j['times_reviewed'] as int? ?? 0,
    lastReviewed: _dt(j['last_reviewed']),
    nextReviewDate: _dt(j['next_review_date']),
    status: QueueStatus.fromJson(j['status'] as String),
  );

  Map<String, dynamic> toJson() => {
    'queue_id': queueId,
    'question_id': questionId,
    'error_type': errorType.value,
    'times_reviewed': timesReviewed,
    'last_reviewed': _iso(lastReviewed),
    'next_review_date': _dateOnly(nextReviewDate),
    'status': status.value,
  };
}

// ============================================================
// Tests (TWT / MT)
// Named TestEntry to avoid clashing with `package:test`'s `test`/`Test`.
// ============================================================

class TestEntry {
  final int testId;
  final DateTime date; // date-only
  final TestType type;
  final Track track;

  /// Free-form JSON blob, e.g. {"Physics": 62, "Maths": 48}
  final Map<String, dynamic>? subjectScores;
  final double? overallPercentile;
  final String? paperPdfPath;
  final String? answerKeyPdfPath;

  const TestEntry({
    required this.testId,
    required this.date,
    required this.type,
    this.track = Track.jee,
    this.subjectScores,
    this.overallPercentile,
    this.paperPdfPath,
    this.answerKeyPdfPath,
  });

  factory TestEntry.fromJson(Map<String, dynamic> j) => TestEntry(
    testId: j['test_id'] as int,
    date: _dt(j['date'])!,
    type: TestType.fromJson(j['type'] as String),
    track: Track.fromJson(j['track'] as String),
    subjectScores: j['subject_scores'] as Map<String, dynamic>?,
    overallPercentile: _dbl(j['overall_percentile']),
    paperPdfPath: j['paper_pdf_path'] as String?,
    answerKeyPdfPath: j['answer_key_pdf_path'] as String?,
  );

  Map<String, dynamic> toJson() => {
    'test_id': testId,
    'date': _dateOnly(date),
    'type': type.value,
    'track': track.value,
    'subject_scores': subjectScores,
    'overall_percentile': overallPercentile,
    'paper_pdf_path': paperPdfPath,
    'answer_key_pdf_path': answerKeyPdfPath,
  };
}

// ============================================================
// Assignments (teacher homework)
// ============================================================

class Assignment {
  final int assignmentId;
  final int? sourceId;
  final int topicId;
  final DateTime dueDate; // date-only
  final AssignmentStatus status;

  const Assignment({
    required this.assignmentId,
    this.sourceId,
    required this.topicId,
    required this.dueDate,
    this.status = AssignmentStatus.assigned,
  });

  factory Assignment.fromJson(Map<String, dynamic> j) => Assignment(
    assignmentId: j['assignment_id'] as int,
    sourceId: j['source_id'] as int?,
    topicId: j['topic_id'] as int,
    dueDate: _dt(j['due_date'])!,
    status: AssignmentStatus.fromJson(j['status'] as String),
  );

  Map<String, dynamic> toJson() => {
    'assignment_id': assignmentId,
    'source_id': sourceId,
    'topic_id': topicId,
    'due_date': _dateOnly(dueDate),
    'status': status.value,
  };
}

// ============================================================
// Board syllabus
// ============================================================

class BoardSyllabus {
  final int syllabusId;
  final String subject;
  final String chapter;
  final int?
  topicId; // only set when the chapter genuinely overlaps JEE content
  final DateTime dueDate; // date-only
  final SyllabusStatus status;

  const BoardSyllabus({
    required this.syllabusId,
    required this.subject,
    required this.chapter,
    this.topicId,
    required this.dueDate,
    this.status = SyllabusStatus.notStarted,
  });

  factory BoardSyllabus.fromJson(Map<String, dynamic> j) => BoardSyllabus(
    syllabusId: j['syllabus_id'] as int,
    subject: j['subject'] as String,
    chapter: j['chapter'] as String,
    topicId: j['topic_id'] as int?,
    dueDate: _dt(j['due_date'])!,
    status: SyllabusStatus.fromJson(j['status'] as String),
  );

  Map<String, dynamic> toJson() => {
    'syllabus_id': syllabusId,
    'subject': subject,
    'chapter': chapter,
    'topic_id': topicId,
    'due_date': _dateOnly(dueDate),
    'status': status.value,
  };
}

// ============================================================
// API response wrappers (shapes from API.md)
// ============================================================

/// GET /sessions/<id>
class SessionStatus {
  final Session session;
  final Question? currentQuestion;
  final List<Question> questions;

  const SessionStatus({
    required this.session,
    this.currentQuestion,
    required this.questions,
  });

  factory SessionStatus.fromJson(Map<String, dynamic> j) => SessionStatus(
    session: Session.fromJson(j['session'] as Map<String, dynamic>),
    currentQuestion: j['current_question'] == null
        ? null
        : Question.fromJson(j['current_question'] as Map<String, dynamic>),
    questions: (j['questions'] as List)
        .map((e) => Question.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}

/// POST /sessions  (also reusable for any {session, current_question} reply)
class SessionStarted {
  final Session session;
  final Question currentQuestion;

  const SessionStarted({required this.session, required this.currentQuestion});

  factory SessionStarted.fromJson(Map<String, dynamic> j) => SessionStarted(
    session: Session.fromJson(j['session'] as Map<String, dynamic>),
    currentQuestion: Question.fromJson(
      j['current_question'] as Map<String, dynamic>,
    ),
  );
}

/// POST /sessions/<id>/questions/complete
class CompleteQuestionResult {
  final Question completedQuestion;
  final bool batchComplete;
  final Question? currentQuestion; // null when batchComplete is true

  const CompleteQuestionResult({
    required this.completedQuestion,
    required this.batchComplete,
    this.currentQuestion,
  });

  factory CompleteQuestionResult.fromJson(Map<String, dynamic> j) =>
      CompleteQuestionResult(
        completedQuestion: Question.fromJson(
          j['completed_question'] as Map<String, dynamic>,
        ),
        batchComplete: j['batch_complete'] as bool,
        currentQuestion: j['current_question'] == null
            ? null
            : Question.fromJson(j['current_question'] as Map<String, dynamic>),
      );
}

/// One entry of the `results` array sent to POST /sessions/<id>/grade
class GradeEntry {
  final int questionId;
  final Correctness correctness;
  final ErrorType errorType;

  const GradeEntry({
    required this.questionId,
    required this.correctness,
    required this.errorType,
  });

  Map<String, dynamic> toJson() => {
    'question_id': questionId,
    'correctness': correctness.value,
    'error_type': errorType.value,
  };
}

/// POST /sessions/<id>/grade
class GradeResult {
  final List<Question> gradedQuestions;
  final Question? currentQuestion;

  const GradeResult({required this.gradedQuestions, this.currentQuestion});

  factory GradeResult.fromJson(Map<String, dynamic> j) => GradeResult(
    gradedQuestions: (j['graded_questions'] as List)
        .map((e) => Question.fromJson(e as Map<String, dynamic>))
        .toList(),
    currentQuestion: j['current_question'] == null
        ? null
        : Question.fromJson(j['current_question'] as Map<String, dynamic>),
  );
}

/// POST /sessions/<id>/end
class EndSessionResult {
  final Session session;
  final List<Question> ungradedQuestions;

  const EndSessionResult({
    required this.session,
    required this.ungradedQuestions,
  });

  factory EndSessionResult.fromJson(Map<String, dynamic> j) => EndSessionResult(
    session: Session.fromJson(j['session'] as Map<String, dynamic>),
    ungradedQuestions: (j['ungraded_questions'] as List)
        .map((e) => Question.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}
