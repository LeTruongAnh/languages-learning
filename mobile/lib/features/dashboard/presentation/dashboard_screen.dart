import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../home/data/home_repository.dart';
import '../../home/presentation/home_screen.dart' show AppBottomNav;

/// Dashboard (spec §5.7): simple stat cards, per-language breakdown.
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(homeDataProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Dashboard'), backgroundColor: AppColors.bg),
      body: data.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: OutlinedButton(
              onPressed: () => ref.invalidate(homeDataProvider),
              child: const Text('Thử lại')),
        ),
        data: (home) {
          final s = home.summary;
          return RefreshIndicator(
            onRefresh: () => ref.refresh(homeDataProvider.future),
            child: ListView(
              padding: const EdgeInsets.all(AppDimens.screenPadding),
              children: [
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                  childAspectRatio: 1.9,
                  children: [
                    _StatCard('${s.todayLearned}', 'Đã học hôm nay'),
                    _StatCard('${(s.passRate * 100).round()}%', 'Tỷ lệ Pass',
                        color: AppColors.pass),
                    _StatCard('🔥 ${s.streakDays}', 'Chuỗi ngày'),
                    _StatCard('${s.hardItemsCount}', 'Mục khó',
                        color: AppColors.hardItems),
                  ],
                ),
                const SizedBox(height: 14),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _MiniStat('${s.passCount}', 'Pass', AppColors.pass),
                        _MiniStat('${s.failCount}', 'Fail', AppColors.fail),
                        _MiniStat('${s.skipCount}', 'Skip', AppColors.skip),
                        _MiniStat('${s.dueToday}', 'Due còn lại', AppColors.review),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                const Text('Theo ngôn ngữ',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
                const SizedBox(height: 10),
                Card(
                  child: Column(
                    children: [
                      for (final lang in home.languages)
                        ListTile(
                          leading: CircleAvatar(
                            radius: 6,
                            backgroundColor: AppColors.forLanguage(lang.code),
                          ),
                          title: Text(lang.name,
                              style: const TextStyle(
                                  fontSize: 14, fontWeight: FontWeight.w700)),
                          subtitle: Text(
                              'Due ${lang.dueCount} · New ${lang.newCount}',
                              style: const TextStyle(fontSize: 12)),
                          trailing: Text('${lang.todayLearned} thẻ hôm nay',
                              style: const TextStyle(
                                  fontSize: 13, fontWeight: FontWeight.w700)),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
      bottomNavigationBar: const AppBottomNav(selectedIndex: 1),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard(this.value, this.label, {this.color});

  final String value, label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(value,
                style: TextStyle(
                    fontSize: 24, fontWeight: FontWeight.w800, color: color)),
            Text(label,
                style: const TextStyle(fontSize: 12, color: AppColors.textSub)),
          ],
        ),
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  const _MiniStat(this.value, this.label, this.color);

  final String value, label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value,
            style:
                TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: color)),
        Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textSub)),
      ],
    );
  }
}
