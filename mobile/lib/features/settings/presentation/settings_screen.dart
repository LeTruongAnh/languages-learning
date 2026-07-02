import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../home/presentation/home_screen.dart' show AppBottomNav;
import '../data/settings_repository.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  Future<void> _patch(WidgetRef ref, Map<String, dynamic> patch) async {
    await ref.read(settingsRepositoryProvider).update(patch);
    ref.invalidate(userSettingsProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(userSettingsProvider);

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
                    onChanged: (v) => _patch(ref, {'autoSpeakOnCardOpen': v}),
                  ),
                  SwitchListTile(
                    title: const Text('Đọc cả câu ví dụ',
                        style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600)),
                    value: s.speakExample,
                    onChanged: (v) => _patch(ref, {'speakExample': v}),
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
                          _patch(ref, {'speechRate': v.toStringAsFixed(2)}),
                      onChanged: (_) {},
                    ),
                    trailing: Text('${s.speechRate.toStringAsFixed(1)}×'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
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
            const SizedBox(height: 12),
            const Text(
              'Cài đặt riêng từng ngôn ngữ (giới hạn ngày, tỷ lệ, chu kỳ ôn) chỉnh qua web companion hoặc API.',
              style: TextStyle(fontSize: 12, color: AppColors.textSub),
            ),
          ],
        ),
      ),
      bottomNavigationBar: const AppBottomNav(selectedIndex: 2),
    );
  }
}
