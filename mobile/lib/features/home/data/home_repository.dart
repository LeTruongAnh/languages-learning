import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/models/models.dart';
import '../../../core/providers.dart';

class HomeData {
  const HomeData({required this.summary, required this.languages});

  final TodaySummary summary;
  final List<LanguageSummary> languages;
}

class HomeRepository {
  HomeRepository(this._dio);

  final Dio _dio;

  Future<HomeData> load() async {
    final results = await Future.wait([
      _dio.get('/dashboard/summary'),
      _dio.get('/dashboard/languages'),
    ]);
    return HomeData(
      summary: TodaySummary.fromJson(results[0].data as Map<String, dynamic>),
      languages: (results[1].data as List<dynamic>)
          .map((e) => LanguageSummary.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

final homeRepositoryProvider =
    Provider<HomeRepository>((ref) => HomeRepository(ref.watch(dioProvider)));

final homeDataProvider = FutureProvider.autoDispose<HomeData>(
    (ref) => ref.watch(homeRepositoryProvider).load());
