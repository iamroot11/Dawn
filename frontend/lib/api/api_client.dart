/// DAWN — API client.
///
/// One method per route in API.md, returning the typed models from
/// ../models/models.dart. Place this at frontend/api/api_client.dart.
///
/// Dependency (pubspec.yaml):
///   http: ^1.2.0
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io' show SocketException;

import 'package:http/http.dart' as http;

import '../models/models.dart';

// ============================================================
// Errors
// ============================================================

/// Thrown for any failed request. Catch this one type in the UI.
///
/// [statusCode] is null for network-level failures (offline, timeout, etc.).
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  const ApiException(this.message, {this.statusCode});

  bool get isNetworkError => statusCode == null;

  @override
  String toString() => 'ApiException(${statusCode ?? 'network'}): $message';
}

// ============================================================
// Client
// ============================================================

class ApiClient {
  /// e.g. "http://192.168.1.10:5000" (no trailing slash). On the iOS
  /// simulator "http://127.0.0.1:5000" works; on a real device use your
  /// machine's LAN IP or the deployed URL.
  final String baseUrl;
  final Duration timeout;
  final http.Client _http;

  ApiClient({
    required this.baseUrl,
    http.Client? httpClient,
    this.timeout = const Duration(seconds: 15),
  }) : _http = httpClient ?? http.Client();

  void close() => _http.close();

  // ----------------------------------------------------------
  // Core request plumbing
  // ----------------------------------------------------------

  Uri _uri(String path, [Map<String, String?>? query]) {
    final q = <String, String>{
      for (final e in (query ?? {}).entries)
        if (e.value != null) e.key: e.value!,
    };
    return Uri.parse('$baseUrl$path')
        .replace(queryParameters: q.isEmpty ? null : q);
  }

  /// Drops null values so optional fields are *omitted* from the body,
  /// which is what API.md specifies (omitted == null/default).
  Map<String, dynamic> _body(Map<String, dynamic> fields) => {
    for (final e in fields.entries)
      if (e.value != null) e.key: e.value,
  };

  Future<dynamic> _send(
    String method,
    String path, {
    Map<String, String?>? query,
    Map<String, dynamic>? body,
  }) async {
    final request = http.Request(method, _uri(path, query));
    request.headers['Accept'] = 'application/json';
    if (body != null) {
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
    }

    http.Response res;
    try {
      res = await http.Response.fromStream(
        await _http.send(request).timeout(timeout),
      );
    } on TimeoutException {
      throw const ApiException('Request timed out');
    } on SocketException {
      throw const ApiException('Could not reach the server');
    } on http.ClientException catch (e) {
      throw ApiException('Network error: ${e.message}');
    }

    dynamic decoded;
    if (res.body.isNotEmpty) {
      try {
        decoded = jsonDecode(utf8.decode(res.bodyBytes));
      } on FormatException {
        if (res.statusCode >= 400) {
          throw ApiException(
            'Server error (${res.statusCode})',
            statusCode: res.statusCode,
          );
        }
        throw ApiException(
          'Invalid JSON in response',
          statusCode: res.statusCode,
        );
      }
    }

    if (res.statusCode >= 400) {
      final msg = (decoded is Map && decoded['error'] is String)
          ? decoded['error'] as String
          : 'Request failed (${res.statusCode})';
      throw ApiException(msg, statusCode: res.statusCode);
    }
    return decoded;
  }

  Future<dynamic> _get(String path, {Map<String, String?>? query}) =>
      _send('GET', path, query: query);

  Future<dynamic> _post(String path, [Map<String, dynamic>? body]) =>
      _send('POST', path, body: body ?? const {});

  Future<dynamic> _patch(String path, Map<String, dynamic> body) =>
      _send('PATCH', path, body: body);

  Future<void> _delete(String path) => _send('DELETE', path);

  // Parsing helpers
  List<T> _list<T>(dynamic json, T Function(Map<String, dynamic>) f) =>
      (json as List).map((e) => f(e as Map<String, dynamic>)).toList();

  /// Tolerates either a bare session object or {"session": {...}}, since
  /// API.md doesn't pin down the pause/resume response shape.
  Session _session(dynamic json) {
    final m = json as Map<String, dynamic>;
    return Session.fromJson(
      m['session'] is Map ? m['session'] as Map<String, dynamic> : m,
    );
  }

  // ============================================================
  // Subjects
  // ============================================================

  Future<List<Subject>> listSubjects() async =>
      _list(await _get('/subjects'), Subject.fromJson);

  Future<Subject> createSubject({required String subjectName}) async =>
      Subject.fromJson(await _post('/subjects', {'subject_name': subjectName}));

  Future<Subject> renameSubject(
    int subjectId, {
    required String newName,
  }) async => Subject.fromJson(
    await _patch('/subjects/$subjectId', {'new_name': newName}),
  );

  Future<void> deleteSubject(int subjectId) => _delete('/subjects/$subjectId');

  // ============================================================
  // Topics
  // ============================================================

  Future<List<Topic>> listTopics({int? subjectId}) async => _list(
    await _get('/topics', query: {'subject_id': subjectId?.toString()}),
    Topic.fromJson,
  );

  Future<Topic> createTopic({
    required String topicName,
    required int subjectId,
    required Track track,
  }) async => Topic.fromJson(
    await _post('/topics', {
      'topic_name': topicName,
      'subject_id': subjectId,
      'track': track.value,
    }),
  );

  Future<Topic> updateTopic(
    int topicId, {
    String? newName,
    int? newSubjectId,
    Track? newTrack,
  }) async => Topic.fromJson(
    await _patch(
      '/topics/$topicId',
      _body({
        'new_name': newName,
        'new_subject_id': newSubjectId,
        'new_track': newTrack?.value,
      }),
    ),
  );

  Future<void> deleteTopic(int topicId) => _delete('/topics/$topicId');

  /// Re-parents the source topic's subtopics onto the target, then
  /// hard-deletes the source topic.
  Future<void> mergeTopics({
    required int sourceTopicId,
    required int targetTopicId,
  }) => _post('/topics/merge', {
    'source_topic_id': sourceTopicId,
    'target_topic_id': targetTopicId,
  });

  // ============================================================
  // Subtopics
  // ============================================================

  Future<List<Subtopic>> listSubtopics({int? topicId}) async => _list(
    await _get('/subtopics', query: {'topic_id': topicId?.toString()}),
    Subtopic.fromJson,
  );

  Future<Subtopic> createSubtopic({
    required String subtopicName,
    required int topicId,
  }) async => Subtopic.fromJson(
    await _post('/subtopics', {
      'subtopic_name': subtopicName,
      'topic_id': topicId,
    }),
  );

  Future<Subtopic> updateSubtopic(
    int subtopicId, {
    String? newName,
    int? newTopicId,
  }) async => Subtopic.fromJson(
    await _patch(
      '/subtopics/$subtopicId',
      _body({'new_name': newName, 'new_topic_id': newTopicId}),
    ),
  );

  Future<void> deleteSubtopic(int subtopicId) =>
      _delete('/subtopics/$subtopicId');

  // ============================================================
  // Sources
  // ============================================================

  Future<List<Source>> listSources({int? topicId}) async => _list(
    await _get('/sources', query: {'topic_id': topicId?.toString()}),
    Source.fromJson,
  );

  Future<Source> createSource({
    required String bookName,
    required int topicId,
    required Track track,
    RatedDifficulty? ratedDifficulty,
    DifficultyScheme? difficultyScheme,
    int? totalProblems,
    int? problemsSolved,
  }) async => Source.fromJson(
    await _post(
      '/sources',
      _body({
        'book_name': bookName,
        'topic_id': topicId,
        'track': track.value,
        'rated_difficulty': ratedDifficulty?.value,
        'difficulty_scheme': difficultyScheme?.value,
        'total_problems': totalProblems,
        'problems_solved': problemsSolved,
      }),
    ),
  );

  Future<Source> updateSource(
    int sourceId, {
    String? newName,
    int? newTopicId,
    Track? newTrack,
    RatedDifficulty? newRatedDifficulty,
    DifficultyScheme? newDifficultyScheme,
    int? newTotalProblems,
    int? newProblemsSolved,
  }) async => Source.fromJson(
    await _patch(
      '/sources/$sourceId',
      _body({
        'new_name': newName,
        'new_topic_id': newTopicId,
        'new_track': newTrack?.value,
        'new_rated_difficulty': newRatedDifficulty?.value,
        'new_difficulty_scheme': newDifficultyScheme?.value,
        'new_total_problems': newTotalProblems,
        'new_problems_solved': newProblemsSolved,
      }),
    ),
  );

  Future<void> deleteSource(int sourceId) => _delete('/sources/$sourceId');

  // ============================================================
  // Source exercises
  // ============================================================

  Future<List<SourceExercise>> listExercises(int sourceId) async => _list(
    await _get('/sources/$sourceId/exercises'),
    SourceExercise.fromJson,
  );

  Future<SourceExercise> createExercise(
    int sourceId, {
    required String exerciseNumber,
    int? problemsInExercise,
    int? problemsSolved,
  }) async => SourceExercise.fromJson(
    await _post(
      '/sources/$sourceId/exercises',
      _body({
        'exercise_number': exerciseNumber,
        'problems_in_exercise': problemsInExercise,
        'problems_solved': problemsSolved,
      }),
    ),
  );

  Future<SourceExercise> updateExercise(
    int exerciseId, {
    int? newSourceId,
    String? newExerciseNumber,
    int? newProblemsInExercise,
    int? newProblemsSolved,
  }) async => SourceExercise.fromJson(
    await _patch(
      '/exercises/$exerciseId',
      _body({
        'new_source_id': newSourceId,
        'new_exercise_number': newExerciseNumber,
        'new_problems_in_exercise': newProblemsInExercise,
        'new_problems_solved': newProblemsSolved,
      }),
    ),
  );

  Future<void> deleteExercise(int exerciseId) =>
      _delete('/exercises/$exerciseId');

  // ============================================================
  // Sessions
  // ============================================================

  Future<SessionStatus> getSession(int sessionId) async =>
      SessionStatus.fromJson(await _get('/sessions/$sessionId'));

  Future<SessionStarted> startSession({
    required int topicId,
    required int sourceId,
    required Track track,
    int? startingQuestionNumber,
    int? subtopicId,
    int? exerciseId,
    int? batchSize,
  }) async => SessionStarted.fromJson(
    await _post(
      '/sessions',
      _body({
        'topic_id': topicId,
        'source_id': sourceId,
        'track': track.value,
        'starting_question_number': startingQuestionNumber,
        'subtopic_id': subtopicId,
        'exercise_id': exerciseId,
        'batch_size': batchSize,
      }),
    ),
  );

  Future<Session> pauseSession(int sessionId) async =>
      _session(await _post('/sessions/$sessionId/pause'));

  Future<Session> resumeSession(int sessionId) async =>
      _session(await _post('/sessions/$sessionId/resume'));

  /// Fills in the currently-open question and, unless the batch just closed,
  /// opens the next one. Timing is computed server-side.
  Future<CompleteQuestionResult> completeQuestion(
    int sessionId, {
    required SubjectiveDifficulty subjectiveDifficulty,
    ConfidenceRating? confidenceRating,
    String? photoPath,
  }) async => CompleteQuestionResult.fromJson(
    await _post(
      '/sessions/$sessionId/questions/complete',
      _body({
        'subjective_difficulty': subjectiveDifficulty.value,
        'confidence_rating': confidenceRating?.value,
        'photo_path': photoPath,
      }),
    ),
  );

  /// Grades a batch of already-completed questions. Does not pause the session.
  Future<GradeResult> gradeBatch(
    int sessionId, {
    required List<GradeEntry> results,
  }) async => GradeResult.fromJson(
    await _post('/sessions/$sessionId/grade', {
      'results': results.map((r) => r.toJson()).toList(),
    }),
  );

  /// [subjectiveDifficulty] is required only if a question is currently open
  /// (the server returns a 400 otherwise).
  Future<EndSessionResult> endSession(
    int sessionId, {
    SubjectiveDifficulty? subjectiveDifficulty,
    ConfidenceRating? confidenceRating,
    String? photoPath,
  }) async => EndSessionResult.fromJson(
    await _post(
      '/sessions/$sessionId/end',
      _body({
        'subjective_difficulty': subjectiveDifficulty?.value,
        'confidence_rating': confidenceRating?.value,
        'photo_path': photoPath,
      }),
    ),
  );
}
