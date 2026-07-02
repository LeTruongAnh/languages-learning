import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/models/models.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../study/presentation/study_controller.dart';
import '../data/home_repository.dart';

Color _accentFor(LanguageSummary lang) {
  final hex = lang.accentColor;
  if (hex != null && hex.startsWith('#') && hex.length == 7) {
    return Color(int.parse('FF${hex.substring(1)}', radix: 16));
  }
  return AppColors.forLanguage(lang.code);
}

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(homeDataProvider);
    final name = ref.watch(authControllerProvider.notifier).displayName;

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () => ref.refresh(homeDataProvider.future),
          child: data.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => _ErrorRetry(onRetry: () => ref.invalidate(homeDataProvider)),
            data: (home) => ListView(
              padding: const EdgeInsets.all(AppDimens.screenPadding),
              children: [
                Text('Chào ${name ?? 'bạn'} 👋',
                    style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(
                  '🔥 Chuỗi ${home.summary.streakDays} ngày · Hôm nay đã học ${home.summary.todayLearned} thẻ',
                  style: const TextStyle(fontSize: 13, color: AppColors.textSub),
                ),
                const SizedBox(height: 16),
                if (home.languages.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(20),
                      child: Text(
                        'Chưa có ngôn ngữ nào.\nThêm ngôn ngữ và từ vựng qua web/API, hoặc import CSV.',
                        style: TextStyle(color: AppColors.textSub),
                      ),
                    ),
                  ),
                for (final lang in home.languages)
                  _LanguageCard(lang: lang, accent: _accentFor(lang)),
                if (home.summary.hardItemsCount > 0)
                  Card(
                    child: ListTile(
                      contentPadding:
                          const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                      title: const Text('🔥 Hard Items',
                          style: TextStyle(fontWeight: FontWeight.w800)),
                      subtitle: Text('${home.summary.hardItemsCount} mục khó cần ôn thêm'),
                      trailing: FilledButton(
                        style:
                            FilledButton.styleFrom(backgroundColor: AppColors.hardItems),
                        onPressed: () => context.push('/hard-items'),
                        child: const Text('Xem'),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
      bottomNavigationBar: const AppBottomNav(selectedIndex: 0),
    );
  }
}

class _LanguageCard extends ConsumerWidget {
  const _LanguageCard({required this.lang, required this.accent});

  final LanguageSummary lang;
  final Color accent;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final progress =
        lang.dailyLimit == 0 ? 0.0 : (lang.todayLearned / lang.dailyLimit).clamp(0.0, 1.0);
    final done = lang.todayLearned >= lang.dailyLimit;

    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      child: Container(
        decoration: BoxDecoration(
          border: Border(left: BorderSide(color: accent, width: 5)),
          borderRadius: BorderRadius.circular(AppDimens.radius),
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(lang.name,
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                Text('${lang.todayLearned}/${lang.dailyLimit} hôm nay',
                    style: TextStyle(
                        fontSize: 12, fontWeight: FontWeight.w700, color: accent)),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              'Due ${lang.dueCount} · New ${lang.newCount} · Vocab ${lang.vocabDueNew} · Câu ${lang.sentenceDueNew}',
              style: const TextStyle(fontSize: 13, color: AppColors.textSub),
            ),
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(99),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 6,
                color: accent,
                backgroundColor: const Color(0xFFEDEEF2),
              ),
            ),
            const SizedBox(height: 12),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: accent),
              onPressed: () async {
                final launch = done
                    ? StudyLaunch.extra(lang.languageId,
                        ttsLang: lang.ttsLang,
                        languageName: lang.name,
                        accentColor: lang.accentColor)
                    : StudyLaunch.daily(lang.languageId,
                        ttsLang: lang.ttsLang,
                        languageName: lang.name,
                        accentColor: lang.accentColor);
                await context.push('/study', extra: launch);
                ref.invalidate(homeDataProvider); // refresh counts after studying
              },
              child: Text(done
                  ? 'Học thêm phiên phụ'
                  : lang.todayLearned > 0
                      ? 'Tiếp tục học'
                      : 'Bắt đầu học'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorRetry extends StatelessWidget {
  const _ErrorRetry({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 160),
        const Text('Không kết nối được máy chủ',
            textAlign: TextAlign.center, style: TextStyle(color: AppColors.textSub)),
        const SizedBox(height: 12),
        Center(child: OutlinedButton(onPressed: onRetry, child: const Text('Thử lại'))),
      ],
    );
  }
}

/// Shared bottom navigation (Home · Dashboard · Settings).
class AppBottomNav extends StatelessWidget {
  const AppBottomNav({super.key, required this.selectedIndex});

  final int selectedIndex;

  @override
  Widget build(BuildContext context) {
    return NavigationBar(
      selectedIndex: selectedIndex,
      onDestinationSelected: (i) {
        if (i == selectedIndex) return;
        switch (i) {
          case 0:
            context.go('/home');
          case 1:
            context.go('/dashboard');
          case 2:
            context.go('/settings');
        }
      },
      destinations: const [
        NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Home'),
        NavigationDestination(icon: Icon(Icons.bar_chart), label: 'Dashboard'),
        NavigationDestination(icon: Icon(Icons.settings_outlined), label: 'Settings'),
      ],
    );
  }
}
