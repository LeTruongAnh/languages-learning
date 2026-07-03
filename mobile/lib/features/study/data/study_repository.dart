import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/models/models.dart';
import '../../../core/providers.dart';

class StudyRepository {
  StudyRepository(this._dio);

  final Dio _dio;

  Future<StudySession> createDaily(String languageId) async {
    final res = await _dio.post('/languages/$languageId/study-sessions/daily');
    return StudySession.fromJson(res.data as Map<String, dynamic>);
  }

  Future<StudySession> createExtra(String languageId) async {
    final res = await _dio.post('/languages/$languageId/study-sessions/extra');
    return StudySession.fromJson(res.data as Map<String, dynamic>);
  }

  Future<StudySession> createWeekly(String languageId) async {
    final res = await _dio.post('/languages/$languageId/study-sessions/weekly');
    return StudySession.fromJson(res.data as Map<String, dynamic>);
  }

  Future<StudySession> createHardSession() async {
    final res = await _dio.post('/hard-items/study-sessions');
    return StudySession.fromJson(res.data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> submitReview({
    required String sessionId,
    required String sessionItemId,
    required String result,
  }) async {
    final res = await _dio.post(
      '/study-sessions/$sessionId/items/$sessionItemId/review',
      data: {'result': result},
    );
    return res.data as Map<String, dynamic>;
  }

  /// Completes the session; the response carries emotional-completion stats
  /// (streak, record, graduated cards).
  Future<CompletionStats?> completeSession(String sessionId) async {
    final res = await _dio.post('/study-sessions/$sessionId/complete');
    return CompletionStats.fromJson(res.data as Map<String, dynamic>);
  }

  /// Anki-style single-step undo of the most recently answered card.
  Future<Map<String, dynamic>> undoReview({
    required String sessionId,
    required String sessionItemId,
  }) async {
    final res =
        await _dio.post('/study-sessions/$sessionId/items/$sessionItemId/undo');
    return res.data as Map<String, dynamic>;
  }

  Future<List<StudyItemModel>> hardItems() async {
    final res = await _dio.get('/hard-items');
    return (res.data as List<dynamic>)
        .map((e) => StudyItemModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

final studyRepositoryProvider =
    Provider<StudyRepository>((ref) => StudyRepository(ref.watch(dioProvider)));

final hardItemsProvider = FutureProvider.autoDispose<List<StudyItemModel>>(
    (ref) => ref.watch(studyRepositoryProvider).hardItems());
