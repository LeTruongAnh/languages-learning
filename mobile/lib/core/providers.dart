import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/auth/presentation/auth_controller.dart';
import 'api/api_client.dart';
import 'api/endpoints.dart';
import 'notifications/reminder_service.dart';
import 'storage/token_storage.dart';
import 'tts/tts_service.dart';

final tokenStorageProvider = Provider<TokenStorage>((ref) => const TokenStorage());

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(
    baseUrl: kApiBaseUrl,
    tokenStorage: ref.watch(tokenStorageProvider),
    onSessionExpired: () =>
        ref.read(authControllerProvider.notifier).sessionExpired(),
  );
});

final dioProvider = Provider<Dio>((ref) => ref.watch(apiClientProvider).dio);

final ttsServiceProvider = Provider<TtsService>((ref) => TtsService(
      baseUrl: kApiBaseUrl,
      tokens: ref.watch(tokenStorageProvider),
    ));

final reminderServiceProvider =
    Provider<ReminderService>((ref) => ReminderService());
