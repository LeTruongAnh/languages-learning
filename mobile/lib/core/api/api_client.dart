import 'dart:async';

import 'package:dio/dio.dart';

import '../storage/token_storage.dart';

/// Dio client with auth interceptor:
/// - attaches Bearer access token to every request
/// - on 401: refreshes ONCE (single-flight — concurrent 401s share one
///   refresh future), retries the original request, or logs out on failure.
/// (PLAN.md §3.4)
class ApiClient {
  ApiClient({
    required this.baseUrl,
    required TokenStorage tokenStorage,
    required this.onSessionExpired,
  }) : _tokens = tokenStorage {
    dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 20),
    ));
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: _onRequest,
      onError: _onError,
    ));
  }

  final String baseUrl;
  final TokenStorage _tokens;

  /// Called when refresh fails — app should clear state and go to login.
  final void Function() onSessionExpired;

  late final Dio dio;
  Completer<bool>? _refreshing; // single-flight guard

  Future<void> _onRequest(
      RequestOptions options, RequestInterceptorHandler handler) async {
    final access = await _tokens.accessToken;
    if (access != null) {
      options.headers['Authorization'] = 'Bearer $access';
    }
    handler.next(options);
  }

  Future<void> _onError(DioException err, ErrorInterceptorHandler handler) async {
    final isAuthCall = err.requestOptions.path.startsWith('/auth/');
    if (err.response?.statusCode != 401 || isAuthCall) {
      return handler.next(err);
    }

    final ok = await _refreshTokens();
    if (!ok) {
      onSessionExpired();
      return handler.next(err);
    }

    // Retry original request with the new access token.
    try {
      final response = await dio.fetch(err.requestOptions);
      return handler.resolve(response);
    } on DioException catch (e) {
      return handler.next(e);
    }
  }

  Future<bool> _refreshTokens() async {
    // If a refresh is already in flight, await its result.
    final inFlight = _refreshing;
    if (inFlight != null) return inFlight.future;

    final completer = Completer<bool>();
    _refreshing = completer;
    try {
      final refresh = await _tokens.refreshToken;
      if (refresh == null) {
        completer.complete(false);
        return false;
      }
      // Bare Dio: no interceptors, so a failing refresh can't loop.
      final bare = Dio(BaseOptions(baseUrl: baseUrl));
      final res = await bare.post('/auth/refresh', data: {'refreshToken': refresh});
      await _tokens.save(
        access: res.data['accessToken'] as String,
        refresh: res.data['refreshToken'] as String,
      );
      completer.complete(true);
      return true;
    } catch (_) {
      await _tokens.clear();
      completer.complete(false);
      return false;
    } finally {
      _refreshing = null;
    }
  }
}
