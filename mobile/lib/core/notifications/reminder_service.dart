import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

/// Daily study reminder (local notification — no server involved).
/// Not supported on Flutter web; all methods are no-ops there.
class ReminderService {
  static const _notificationId = 1001;

  final _plugin = FlutterLocalNotificationsPlugin();
  bool _initialized = false;

  Future<void> _ensureInit() async {
    if (kIsWeb || _initialized) return;
    tzdata.initializeTimeZones();
    await _plugin.initialize(const InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      iOS: DarwinInitializationSettings(),
    ));
    _initialized = true;
  }

  /// Schedules a daily reminder at [hour]:00 in the user's timezone
  /// (user_settings.timezone from the backend). Replaces any previous one.
  Future<bool> scheduleDaily({required int hour, required String timezone}) async {
    if (kIsWeb) return false;
    await _ensureInit();

    // Android 13+ needs runtime permission.
    final android = _plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    final granted = await android?.requestNotificationsPermission() ?? true;
    if (!granted) return false;

    tz.Location location;
    try {
      location = tz.getLocation(timezone);
    } catch (_) {
      location = tz.getLocation('Asia/Ho_Chi_Minh');
    }
    var when = tz.TZDateTime.now(location);
    when = tz.TZDateTime(location, when.year, when.month, when.day, hour);
    if (when.isBefore(tz.TZDateTime.now(location))) {
      when = when.add(const Duration(days: 1));
    }

    await _plugin.zonedSchedule(
      _notificationId,
      'Đến giờ học rồi 📚',
      'Vào ôn vài thẻ để giữ chuỗi ngày học nhé!',
      when,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'study_reminder',
          'Nhắc học hằng ngày',
          channelDescription: 'Thông báo nhắc học từ vựng mỗi ngày',
          importance: Importance.high,
        ),
        iOS: DarwinNotificationDetails(),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
      matchDateTimeComponents: DateTimeComponents.time, // repeat daily
    );
    return true;
  }

  Future<void> cancel() async {
    if (kIsWeb) return;
    await _ensureInit();
    await _plugin.cancel(_notificationId);
  }
}
