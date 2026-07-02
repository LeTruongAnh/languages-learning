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

  Future<void> completeSession(String sessionId) async {
    await _dio.post('/study-sessions/$sessionId/complete');
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
