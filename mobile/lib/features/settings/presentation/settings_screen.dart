import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/models/models.dart';
import '../../../core/providers.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../home/presentation/home_screen.dart' show AppBottomNav;
import '../data/settings_repository.dart';

const kDirectionLabels = {
  'FRONT': 'Từ → Nghĩa',
  'REVERSE': 'Nghĩa → Từ',
  'LISTENING': 'Nghe → Từ',
  'MIXED': 'Trộn cả ba',
};

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  Future<void> _patchUser(WidgetRef ref, Map<String, dynamic> patch) async {
    await ref.read(settingsRepositoryProvider).update(patch);
    ref.invalidate(userSettingsProvider);
  }

  Future<void> _applyReminder(
      BuildContext context, WidgetRef ref, UserSettings s,
      {required bool enabled, int? hour}) async {
    final h = hour ?? s.reminderHour;
    await _patchUser(ref, {'reminderEnabled': enabled, 'reminderHour': h});
    final reminder = ref.read(reminderServiceProvider);
    if (enabled) {
      final ok = await reminder.scheduleDaily(hour: h, timezone: s.timezone);
      if (!ok && context.mounted && !kIsWeb) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Cần cấp quyền thông báo cho app trong cài đặt máy')));
      }
    } else {
      await reminder.cancel();
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(userSettingsProvider);
    final languages = ref.watch(settingsLanguagesProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings'), backgroundColor: AppColors.bg),
      body: settings.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: OutlinedButton(
              onPressed: () => ref.invalidate(userSettingsProvider),
              child: const Text('Thử lại')),
        ),
        data: (s) => ListView(
          padding: const EdgeInsets.all(AppDimens.screenPadding),
          children: [
            const Text('Phát âm (TTS)',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
            const SizedBox(height: 10),
            Card(
              child: Column(
                children: [
                  SwitchListTile(
                    title: const Text('Tự đọc khi mở thẻ',
                        style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600)),
                    value: s.autoSpeakOnCardOpen,
                    onChanged: (v) => _patchUser(ref, {'autoSpeakOnCardOpen': v}),
                  ),
                  ListTile(
                    title: const Text('Tốc độ đọc',
                        style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600)),
                    subtitle: Slider(
                      value: s.speechRate.clamp(0.5, 1.5),
                      min: 0.5,
                      max: 1.5,
                      divisions: 10,
                      label: '${s.speechRate.toStringAsFixed(1)}×',
                      onChangeEnd: (v) =>
                          _patchUser(ref, {'speechRate': v.toStringAsFixed(2)}),
                      onChanged: (_) {},
                    ),
                    trailing: Text('${s.speechRate.toStringAsFixed(1)}×'),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 18),
            const Text('Nhắc học hằng ngày',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
            const SizedBox(height: 10),
            Card(
              child: Column(
                children: [
                  SwitchListTile(
                    title: const Text('Bật nhắc học',
                        style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600)),
                    subtitle: Text(kIsWeb
                        ? 'Chỉ hỗ trợ trên app Android/iOS'
                        : 'Thông báo lúc ${s.reminderHour}:00 mỗi ngày'),
                    value: s.reminderEnabled,
                    onChanged: kIsWeb
                        ? null
                        : (v) => _applyReminder(context, ref, s, enabled: v),
                  ),
                  if (s.reminderEnabled && !kIsWeb)
                    ListTile(
                      title: const Text('Giờ nhắc',
                          style:
                              TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600)),
                      trailing: Text('${s.reminderHour}:00 ›',
                          style: const TextStyle(
                              fontSize: 14, fontWeight: FontWeight.w700)),
                      onTap: () async {
                        final picked = await showTimePicker(
                          context: context,
                          initialTime: TimeOfDay(hour: s.reminderHour, minute: 0),
                        );
                        if (picked != null && context.mounted) {
                          await _applyReminder(context, ref, s,
                              enabled: true, hour: picked.hour);
                        }
                      },
                    ),
                ],
              ),
            ),

            // Per-language study settings
            ...languages.when(
              loading: () => const [SizedBox.shrink()],
              error: (e, _) => const [SizedBox.shrink()],
              data: (langs) => [
                for (final lang in langs) _LanguageSettingsCard(language: lang),
                if (langs.isNotEmpty)
                  const Padding(
                    padding: EdgeInsets.only(top: 4, bottom: 8),
                    child: Text(
                      'Thay đổi áp dụng từ phiên học MỚI — phiên hôm nay đã tạo sẽ giữ nguyên.',
                      style: TextStyle(fontSize: 12, color: AppColors.textSub),
                    ),
                  ),
              ],
            ),

            const Text('Tài khoản',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
            const SizedBox(height: 10),
            Card(
              child: Column(
                children: [
                  ListTile(
                    title: const Text('Múi giờ',
                        style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600)),
                    trailing: Text(s.timezone,
                        style: const TextStyle(
                            fontSize: 13, color: AppColors.textSub)),
                  ),
                  ListTile(
                    title: const Text('Đăng xuất',
                        style: TextStyle(
                            fontSize: 14.5,
                            fontWeight: FontWeight.w600,
                            color: AppColors.fail)),
                    onTap: () =>
                        ref.read(authControllerProvider.notifier).logout(),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: const AppBottomNav(selectedIndex: 2),
    );
  }
}

class _LanguageSettingsCard extends ConsumerWidget {
  const _LanguageSettingsCard({required this.language});

  final Language language;

  Future<void> _patch(
      WidgetRef ref, String languageId, Map<String, dynamic> patch) async {
    await ref
        .read(settingsRepositoryProvider)
        .updateLanguageSettings(languageId, patch);
    ref.invalidate(languageSettingsProvider(languageId));
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(languageSettingsProvider(language.id));
    final accent = AppColors.forLanguage(language.code);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 18),
        Text(language.name,
            style: TextStyle(
                fontSize: 15, fontWeight: FontWeight.w800, color: accent)),
        const SizedBox(height: 10),
        Card(
          child: settings.when(
            loading: () => const Padding(
                padding: EdgeInsets.all(24),
                child: Center(child: CircularProgressIndicator())),
            error: (e, _) => ListTile(
                title: const Text('Không tải được cài đặt'),
                trailing: IconButton(
                    icon: const Icon(Icons.refresh),
                    onPressed: () =>
                        ref.invalidate(languageSettingsProvider(language.id)))),
            data: (ls) {
              final vocabCount = (ls.dailyLimit * ls.vocabularyRatio).round();
              final sentenceCount = ls.dailyLimit - vocabCount;
              return Column(
                children: [
                  _SettingRow(
                    label: 'Chiều học',
                    value: kDirectionLabels[ls.studyDirection] ?? ls.studyDirection,
                    onTap: () => _pickDirection(context, ref, ls),
                  ),
                  _SettingRow(
                    label: 'Số thẻ mỗi bài',
                    value: '${ls.dailyLimit} thẻ',
                    onTap: () => _editSlider(
                      context,
                      title: 'Số thẻ mỗi bài — ${language.name}',
                      value: ls.dailyLimit.toDouble(),
                      min: 5, max: 100, divisions: 19,
                      format: (v) => '${v.round()} thẻ',
                      onSave: (v) =>
                          _patch(ref, language.id, {'dailyLimit': v.round()}),
                    ),
                  ),
                  _SettingRow(
                    label: 'Tỷ lệ Từ vựng / Câu',
                    value:
                        '${(ls.vocabularyRatio * 100).round()}% / ${100 - (ls.vocabularyRatio * 100).round()}%'
                        '  ($vocabCount từ · $sentenceCount câu)',
                    onTap: () => _editSlider(
                      context,
                      title: 'Tỷ lệ từ vựng — ${language.name}',
                      value: ls.vocabularyRatio,
                      min: 0, max: 1, divisions: 20,
                      format: (v) =>
                          '${(v * 100).round()}% từ · ${100 - (v * 100).round()}% câu',
                      onSave: (v) => _patch(ref, language.id, {
                        'vocabularyRatio': v.toStringAsFixed(3),
                        'sentenceRatio': (1 - v).toStringAsFixed(3),
                      }),
                    ),
                  ),
                  _SettingRow(
                    label: 'Tỷ lệ Mới / Ôn tập',
                    value:
                        '${(ls.newRatio * 100).round()}% / ${100 - (ls.newRatio * 100).round()}%',
                    onTap: () => _editSlider(
                      context,
                      title: 'Tỷ lệ thẻ mới — ${language.name}',
                      value: ls.newRatio,
                      min: 0, max: 1, divisions: 20,
                      format: (v) =>
                          '${(v * 100).round()}% mới · ${100 - (v * 100).round()}% ôn',
                      onSave: (v) => _patch(ref, language.id, {
                        'newRatio': v.toStringAsFixed(3),
                        'reviewRatio': (1 - v).toStringAsFixed(3),
                      }),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }

  Future<void> _pickDirection(
      BuildContext context, WidgetRef ref, LanguageSetting ls) async {
    final picked = await showDialog<String>(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: Text('Chiều học — ${language.name}',
            style: const TextStyle(fontSize: 17)),
        children: [
          for (final entry in kDirectionLabels.entries)
            RadioListTile<String>(
              title: Text(entry.value),
              subtitle: Text(switch (entry.key) {
                'FRONT' => 'Nhìn từ, nhớ nghĩa (mặc định)',
                'REVERSE' => 'Nhìn nghĩa Việt, nhớ lại từ',
                'LISTENING' => 'Nghe phát âm, nhớ lại từ',
                _ => 'Mỗi thẻ ngẫu nhiên một chiều',
              }, style: const TextStyle(fontSize: 12)),
              value: entry.key,
              groupValue: ls.studyDirection,
              onChanged: (v) => Navigator.pop(ctx, v),
            ),
        ],
      ),
    );
    if (picked != null && picked != ls.studyDirection) {
      await _patch(ref, language.id, {'studyDirection': picked});
    }
  }

  Future<void> _editSlider(
    BuildContext context, {
    required String title,
    required double value,
    required double min,
    required double max,
    required int divisions,
    required String Function(double) format,
    required Future<void> Function(double) onSave,
  }) async {
    var current = value.clamp(min, max);
    final saved = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          title: Text(title, style: const TextStyle(fontSize: 17)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(format(current),
                  style: const TextStyle(
                      fontSize: 16, fontWeight: FontWeight.w700)),
              Slider(
                value: current,
                min: min,
                max: max,
                divisions: divisions,
                onChanged: (v) => setState(() => current = v),
              ),
            ],
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Hủy')),
            FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Lưu')),
          ],
        ),
      ),
    );
    if (saved == true) {
      await onSave(current);
    }
  }
}

class _SettingRow extends StatelessWidget {
  const _SettingRow(
      {required this.label, required this.value, required this.onTap});

  final String label;
  final String value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      title: Text(label,
          style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600)),
      subtitle: Text(value,
          style: const TextStyle(fontSize: 12.5, color: AppColors.textSub)),
      trailing: const Icon(Icons.chevron_right, color: AppColors.textSub),
      onTap: onTap,
    );
  }
}
