import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/models/models.dart';
import '../../../core/providers.dart';
import '../../home/data/home_repository.dart';

/// Catalog languages with the user's enrollment flags.
final catalogLanguagesProvider =
    FutureProvider.autoDispose<List<Language>>((ref) async {
  final res = await ref.watch(dioProvider).get('/languages');
  return (res.data as List<dynamic>)
      .map((e) => Language.fromJson(e as Map<String, dynamic>))
      .toList();
});

const _flagByCode = {
  'zh': '🇨🇳', 'en': '🇬🇧', 'vi': '🇻🇳', 'ja': '🇯🇵',
  'ko': '🇰🇷', 'fr': '🇫🇷', 'de': '🇩🇪', 'es': '🇪🇸',
};

/// Multi-select "which languages do I study" screen.
///
/// Shown right after sign-up (new accounts have zero enrollments) and
/// reachable later from Settings. Un-selecting only HIDES a language —
/// progress is kept server-side and returns when re-enrolled.
class ChooseLanguagesScreen extends ConsumerStatefulWidget {
  const ChooseLanguagesScreen({super.key, this.isOnboarding = false});

  final bool isOnboarding;

  @override
  ConsumerState<ChooseLanguagesScreen> createState() =>
      _ChooseLanguagesScreenState();
}

class _ChooseLanguagesScreenState extends ConsumerState<ChooseLanguagesScreen> {
  Set<String>? _selected; // null until first data arrives
  bool _saving = false;

  Future<void> _save() async {
    final selected = _selected ?? {};
    setState(() => _saving = true);
    try {
      await ref.read(dioProvider).put('/languages/enrollments',
          data: {'languageIds': selected.toList()});
      ref.invalidate(homeDataProvider);
      if (!mounted) return;
      if (context.canPop()) {
        context.pop();
      } else {
        context.go('/home');
      }
    } on DioException {
      setState(() => _saving = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Lưu thất bại — kiểm tra kết nối')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(catalogLanguagesProvider);
    return Scaffold(
      appBar: widget.isOnboarding
          ? null
          : AppBar(
              title: const Text('Ngôn ngữ đang học',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800))),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: async.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text('Không tải được danh sách ngôn ngữ',
                        style: TextStyle(color: AppColors.textSub)),
                    const SizedBox(height: 8),
                    OutlinedButton(
                        onPressed: () =>
                            ref.invalidate(catalogLanguagesProvider),
                        child: const Text('Thử lại')),
                  ],
                ),
              ),
              data: (langs) {
                _selected ??= {
                  for (final l in langs)
                    if (l.enrolled) l.id
                };
                final selected = _selected!;
                return Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (widget.isOnboarding) ...[
                        const SizedBox(height: 24),
                        const Text('🌍',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 44)),
                        const SizedBox(height: 8),
                        const Text('Bạn muốn học ngôn ngữ nào?',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                                fontSize: 22, fontWeight: FontWeight.w800)),
                        const SizedBox(height: 4),
                        const Text(
                            'Chọn một hoặc nhiều — có thể thay đổi trong Settings',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                                fontSize: 13, color: AppColors.textSub)),
                        const SizedBox(height: 20),
                      ],
                      Expanded(
                        child: ListView(
                          children: [
                            for (final lang in langs)
                              Card(
                                margin: const EdgeInsets.only(bottom: 10),
                                child: CheckboxListTile(
                                  value: selected.contains(lang.id),
                                  onChanged: (v) => setState(() {
                                    if (v == true) {
                                      selected.add(lang.id);
                                    } else {
                                      selected.remove(lang.id);
                                    }
                                  }),
                                  title: Text(
                                    '${_flagByCode[lang.code] ?? '🌐'}  ${lang.name}'
                                    '${lang.nativeName != null ? ' · ${lang.nativeName}' : ''}',
                                    style: const TextStyle(
                                        fontWeight: FontWeight.w700),
                                  ),
                                  subtitle: lang.enrolled &&
                                          !selected.contains(lang.id)
                                      ? const Text(
                                          'Tiến độ được giữ lại — bật lại là học tiếp',
                                          style: TextStyle(
                                              fontSize: 12,
                                              color: AppColors.textSub))
                                      : null,
                                  controlAffinity:
                                      ListTileControlAffinity.leading,
                                ),
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 8),
                      FilledButton(
                        style: FilledButton.styleFrom(
                            backgroundColor: AppColors.english),
                        onPressed:
                            _saving || selected.isEmpty ? null : _save,
                        child: _saving
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2, color: Colors.white))
                            : Text(widget.isOnboarding
                                ? 'Bắt đầu học'
                                : 'Lưu thay đổi'),
                      ),
                      if (selected.isEmpty)
                        const Padding(
                          padding: EdgeInsets.only(top: 8),
                          child: Text('Chọn ít nhất 1 ngôn ngữ',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                  fontSize: 12, color: AppColors.textSub)),
                        ),
                    ],
                  ),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}
