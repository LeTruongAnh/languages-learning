import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../study/data/study_repository.dart';
import '../../study/presentation/study_controller.dart';

/// Hard Items (spec §10.6): list wrong_count >= 2 items + start HARD_ITEMS session.
class HardItemsScreen extends ConsumerWidget {
  const HardItemsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final items = ref.watch(hardItemsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('🔥 Hard Items'), backgroundColor: AppColors.bg),
      body: items.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: OutlinedButton(
              onPressed: () => ref.invalidate(hardItemsProvider),
              child: const Text('Thử lại')),
        ),
        data: (list) => list.isEmpty
            ? const Center(
                child: Text('Không có mục khó nào 🎉',
                    style: TextStyle(color: AppColors.textSub)))
            : ListView(
                padding: const EdgeInsets.all(AppDimens.screenPadding),
                children: [
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: AppColors.hardItems,
                        minimumSize: const Size.fromHeight(52)),
                    onPressed: () async {
                      await context.push('/study', extra: const StudyLaunch.hard());
                      ref.invalidate(hardItemsProvider);
                    },
                    child: Text('Ôn ngay ${list.length} mục khó'),
                  ),
                  const SizedBox(height: 14),
                  for (final item in list)
                    Card(
                      margin: const EdgeInsets.only(bottom: 10),
                      child: ListTile(
                        title: Text.rich(TextSpan(
                          text: item.text,
                          style: const TextStyle(
                              fontSize: 17, fontWeight: FontWeight.w800),
                          children: [
                            if (item.pronunciation != null)
                              TextSpan(
                                text: '  ${item.pronunciation}',
                                style: const TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w400,
                                    color: AppColors.textSub),
                              ),
                          ],
                        )),
                        subtitle: Text(item.vietnameseMeaning ?? '',
                            style: const TextStyle(fontSize: 12.5)),
                        trailing: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppColors.hardItems.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(99),
                          ),
                          child: Text(item.hardLevel,
                              style: const TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.hardItems)),
                        ),
                      ),
                    ),
                ],
              ),
      ),
    );
  }
}
