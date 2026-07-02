import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Tokens live ONLY in secure storage (Keychain / Android Keystore).
/// Never SharedPreferences, never logs. (PLAN.md §3.4)
class TokenStorage {
  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';

  final FlutterSecureStorage _storage;

  const TokenStorage([this._storage = const FlutterSecureStorage()]);

  Future<String?> get accessToken => _storage.read(key: _kAccess);
  Future<String?> get refreshToken => _storage.read(key: _kRefresh);

  Future<void> save({required String access, required String refresh}) async {
    await _storage.write(key: _kAccess, value: access);
    await _storage.write(key: _kRefresh, value: refresh);
  }

  Future<void> clear() async {
    await _storage.delete(key: _kAccess);
    await _storage.delete(key: _kRefresh);
  }
}
