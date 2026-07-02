/// API base URL.
/// - Android emulator: http://10.0.2.2:8000/api (maps to host localhost)
/// - iOS simulator:    http://localhost:8000/api
/// - Production:       https://yourdomain.com/api
///
/// Override at build time:
///   flutter run --dart-define=API_BASE_URL=https://yourdomain.com/api
const String kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000/api',
);
