import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/models/models.dart';
import '../../../core/providers.dart';

class SettingsRepository {
  SettingsRepository(this._dio);

  final Dio _dio;

  Future<UserSettings> load() async {
    final res = await _dio.get('/user-settings');
    return UserSettings.fromJson(res.data as Map<String, dynamic>);
  }

  Future<UserSettings> update(Map<String, dynamic> patch) async {
    final res = await _dio.patch('/user-settings', data: patch);
    return UserSettings.fromJson(res.data as Map<String, dynamic>);
  }
}

final settingsRepositoryProvider =
    Provider<SettingsRepository>((ref) => SettingsRepository(ref.watch(dioProvider)));

final userSettingsProvider = FutureProvider.autoDispose<UserSettings>(
    (ref) => ref.watch(settingsRepositoryProvider).load());
