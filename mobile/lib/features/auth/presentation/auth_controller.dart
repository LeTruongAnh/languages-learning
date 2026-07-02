import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers.dart';
import '../data/auth_repository.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

final authRepositoryProvider = Provider<AuthRepository>((ref) => AuthRepository(
      dio: ref.watch(dioProvider),
      tokens: ref.watch(tokenStorageProvider),
    ));

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthStatus>((ref) {
  return AuthController(ref)..bootstrap();
});

class AuthController extends StateNotifier<AuthStatus> {
  AuthController(this._ref) : super(AuthStatus.unknown);

  final Ref _ref;
  String? displayName;

  AuthRepository get _repo => _ref.read(authRepositoryProvider);

  /// On app start: if we have a token, validate it via /auth/me
  /// (the interceptor transparently refreshes an expired access token).
  Future<void> bootstrap() async {
    final access = await _ref.read(tokenStorageProvider).accessToken;
    if (access == null) {
      state = AuthStatus.unauthenticated;
      return;
    }
    try {
      final me = await _repo.me();
      displayName = me['displayName'] as String?;
      state = AuthStatus.authenticated;
    } catch (_) {
      state = AuthStatus.unauthenticated;
    }
  }

  /// Returns an error message, or null on success.
  Future<String?> login(String email, String password) async {
    try {
      await _repo.login(email.trim(), password);
      final me = await _repo.me();
      displayName = me['displayName'] as String?;
      state = AuthStatus.authenticated;
      return null;
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) return 'Email hoặc mật khẩu không đúng';
      if (e.response?.statusCode == 429) {
        return 'Thử lại sau ít phút (quá nhiều lần đăng nhập)';
      }
      return 'Không kết nối được máy chủ';
    }
  }

  /// Returns an error message, or null on success (auto-login after register).
  Future<String?> register(String email, String password, String? name) async {
    try {
      await _repo.register(email.trim(), password, name);
      return login(email, password);
    } on DioException catch (e) {
      if (e.response?.statusCode == 409) return 'Email đã được đăng ký';
      if (e.response?.statusCode == 422) {
        return 'Mật khẩu tối thiểu 8 ký tự, gồm chữ và số';
      }
      return 'Không kết nối được máy chủ';
    }
  }

  Future<void> logout() async {
    await _repo.logout();
    state = AuthStatus.unauthenticated;
  }

  /// Called by the API client when token refresh fails.
  void sessionExpired() {
    state = AuthStatus.unauthenticated;
  }
}
