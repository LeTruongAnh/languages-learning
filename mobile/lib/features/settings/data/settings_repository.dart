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

  Future<List<Language>> loadLanguages() async {
    final res = await _dio.get('/languages');
    return (res.data as List<dynamic>)
        .map((e) => Language.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<LanguageSetting> loadLanguageSettings(String languageId) async {
    final res = await _dio.get('/languages/$languageId/settings');
    return LanguageSetting.fromJson(res.data as Map<String, dynamic>);
  }

  /// Ratios must be sent in pairs summing to 1 (backend validation).
  Future<LanguageSetting> updateLanguageSettings(
      String languageId, Map<String, dynamic> patch) async {
    final res = await _dio.patch('/languages/$languageId/settings', data: patch);
    return LanguageSetting.fromJson(res.data as Map<String, dynamic>);
  }
}

final settingsRepositoryProvider =
    Provider<SettingsRepository>((ref) => SettingsRepository(ref.watch(dioProvider)));

final userSettingsProvider = FutureProvider.autoDispose<UserSettings>(
    (ref) => ref.watch(settingsRepositoryProvider).load());

final settingsLanguagesProvider = FutureProvider.autoDispose<List<Language>>(
    (ref) => ref.watch(settingsRepositoryProvider).loadLanguages());

final languageSettingsProvider = FutureProvider.autoDispose
    .family<LanguageSetting, String>(
        (ref, languageId) =>
            ref.watch(settingsRepositoryProvider).loadLanguageSettings(languageId));
