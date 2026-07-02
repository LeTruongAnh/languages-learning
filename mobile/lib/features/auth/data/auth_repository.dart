import 'package:dio/dio.dart';

import '../../../core/storage/token_storage.dart';

class AuthRepository {
  AuthRepository({required this.dio, required this.tokens});

  final Dio dio;
  final TokenStorage tokens;

  Future<void> login(String email, String password) async {
    final res = await dio.post('/auth/login', data: {
      'email': email,
      'password': password,
    });
    await tokens.save(
      access: res.data['accessToken'] as String,
      refresh: res.data['refreshToken'] as String,
    );
  }

  Future<void> register(String email, String password, String? displayName) async {
    await dio.post('/auth/register', data: {
      'email': email,
      'password': password,
      if (displayName != null) 'displayName': displayName,
    });
  }

  Future<Map<String, dynamic>> me() async {
    final res = await dio.get('/auth/me');
    return res.data as Map<String, dynamic>;
  }

  Future<void> logout() async {
    final refresh = await tokens.refreshToken;
    if (refresh != null) {
      try {
        await dio.post('/auth/logout', data: {'refreshToken': refresh});
      } catch (_) {
        // Best effort — clear local tokens regardless.
      }
    }
    await tokens.clear();
  }
}
