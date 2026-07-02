import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/models/models.dart';
import '../data/settings_repository.dart';

const kWeekdayLabels = {
  'MONDAY': 'Thứ 2', 'TUESDAY': 'Thứ 3', 'WEDNESDAY': 'Thứ 4',
  'THURSDAY': 'Thứ 5', 'FRIDAY': 'Thứ 6', 'SATURDAY': 'Thứ 7',
  'SUNDAY': 'Chủ nhật',
};

const kSortModeLabels = {
  'random': 'Ngẫu nhiên',
  'priority': 'Ưu tiên từ khó (sai nhiều trước)',
  'oldest_first': 'Từ cũ trước',
};

/// Advanced per-language settings: filters, SRS knobs, weekly review.
class LanguageAdvancedScreen extends ConsumerWidget {
  const LanguageAdvancedScreen({super.key, required this.language});

  final Language language;

  Future<void> _patch(WidgetRef ref, Map<String, dynamic> patch) async {
    await ref
        .read(settingsRepositoryProvider)
        .updateLanguageSettings(language.id, patch);
    ref.invalidate(languageSettingsProvider(language.id));
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(languageSettingsProvider(language.id));
    final facets = ref.watch(languageFacetsProvider(language.id));
    final accent = AppColors.forLanguage(language.code);

    return Scaffold(
      appBar: AppBar(
        title: Text('${language.name} — Nâng cao'),
        backgroundColor: AppColors.bg,
        foregroundColor: accent,
      ),
      body: settings.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
            child: OutlinedButton(
                onPressed: () =>
                    ref.invalidate(languageSettingsProvider(language.id)),
                child: const Text('Thử lại'))),
        data: (ls) => ListView(
          padding: const EdgeInsets.all(AppDimens.screenPadding),
          children: [
            // ---------- Bộ lọc ----------
            const Text('Bộ lọc nội dung học',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            const Text('Chỉ chọn từ/câu khớp bộ lọc khi tạo bài học.',
                style: TextStyle(fontSize: 12, color: AppColors.textSub)),
            const SizedBox(height: 10),
            facets.when(
              loading: () => const Padding(
                  padding: EdgeInsets.all(20),
                  child: Center(child: CircularProgressIndicator())),
              error: (e, _) => const Text('Không tải được bộ lọc',
                  style: TextStyle(color: AppColors.textSub)),
              data: (f) => Column(
                children: [
                  _FilterCard(
                    title: 'Độ khó (từ vựng)',
                    values: f.difficulties,
                    selected: ls.difficultyFilter,
                    accent: accent,
                    onChanged: (v) => _patch(ref, {'difficultyFilter': v}),
                  ),
                  _FilterCard(
                    title: 'Chủ đề',
                    values: f.topics,
                    selected: ls.topicFilter,
                    accent: accent,
                    onChanged: (v) => _patch(ref, {'topicFilter': v}),
                  ),
                  _FilterCard(
                    title: 'Tần suất sử dụng',
                    values: f.frequencyLevels,
                    selected: ls.frequencyFilter,
                    accent: accent,
                    onChanged: (v) => _patch(ref, {'frequencyFilter': v}),
                  ),
                  if (f.situations.isNotEmpty)
                    _FilterCard(
                      title: 'Tình huống (câu)',
                      values: f.situations,
                      selected: ls.situationFilter,
                      accent: accent,
                      onChanged: (v) => _patch(ref, {'situationFilter': v}),
                    ),
                ],
              ),
            ),

            // ---------- SRS ----------
            const SizedBox(height: 18),
            const Text('Thuật toán ôn tập',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
            const SizedBox(height: 10),
            Card(
              child: Column(
                children: [
                  ListTile(
                    title: const Text('Số lần Nhớ để hoàn thành',
                        style: TextStyle(
                            fontSize: 14.5, fontWeight: FontWeight.w600)),
                    subtitle: const Text(
                        'Từ đạt đủ số lần sẽ được "tốt nghiệp", không ôn nữa',
                        style: TextStyle(fontSize: 12)),
                    trailing: DropdownButton<int>(
                      value: ls.timesLimit,
                      items: [
                        for (var i = 1; i <= 10; i++)
                          DropdownMenuItem(value: i, child: Text('$i lần')),
                      ],
                      onChanged: (v) => v == null
                          ? null
                          : _patch(ref,
                              {'timesLimit': v, 'sentenceTimesLimit': v}),
                    ),
                  ),
                  ListTile(
                    title: const Text('Chu kỳ ôn cơ sở (ngày)',
                        style: TextStyle(
                            fontSize: 14.5, fontWeight: FontWeight.w600)),
                    subtitle: Text(ls.reviewIntervals.join(', '),
                        style: const TextStyle(
                            fontSize: 12.5, color: AppColors.textSub)),
                    trailing:
                        const Icon(Icons.edit, size: 18, color: AppColors.textSub),
                    onTap: () => _editIntervals(context, ref, ls),
                  ),
                  SwitchListTile(
                    title: const Text('Quên thì học lại từ đầu',
                        style: TextStyle(
                            fontSize: 14.5, fontWeight: FontWeight.w600)),
                    subtitle: const Text('Bấm Quên → số lần Nhớ về 0',
                        style: TextStyle(fontSize: 12)),
                    value: ls.resetOnFail,
                    onChanged: (v) => _patch(ref, {'resetOnFail': v}),
                  ),
                  SwitchListTile(
                    title: const Text('Không lặp từ đã học trong ngày',
                        style: TextStyle(
                            fontSize: 14.5, fontWeight: FontWeight.w600)),
                    value: ls.avoidSameDayRepeat,
                    onChanged: (v) => _patch(ref, {'avoidSameDayRepeat': v}),
                  ),
                  SwitchListTile(
                    title: const Text('Ôn lại từ đã hoàn thành',
                        style: TextStyle(
                            fontSize: 14.5, fontWeight: FontWeight.w600)),
                    subtitle: Text(
                        ls.includePassedItems
                            ? 'Sau ${ls.passedReviewAfterDays} ngày sẽ đưa vào ôn lại'
                            : 'Từ đã hoàn thành không quay lại',
                        style: const TextStyle(fontSize: 12)),
                    value: ls.includePassedItems,
                    onChanged: (v) => _patch(ref, {'includePassedItems': v}),
                  ),
                  if (ls.includePassedItems)
                    ListTile(
                      title: const Text('Ôn lại sau (ngày)',
                          style: TextStyle(
                              fontSize: 14.5, fontWeight: FontWeight.w600)),
                      trailing: DropdownButton<int>(
                        value: ls.passedReviewAfterDays,
                        items: const [30, 60, 100, 180, 365]
                            .map((d) => DropdownMenuItem(
                                value: d, child: Text('$d ngày')))
                            .toList(),
                        onChanged: (v) => v == null
                            ? null
                            : _patch(ref, {'passedReviewAfterDays': v}),
                      ),
                    ),
                  ListTile(
                    title: const Text('Thứ tự chọn thẻ',
                        style: TextStyle(
                            fontSize: 14.5, fontWeight: FontWeight.w600)),
                    subtitle: Text(kSortModeLabels[ls.sortMode] ?? ls.sortMode,
                        style: const TextStyle(
                            fontSize: 12.5, color: AppColors.textSub)),
                    trailing: const Icon(Icons.chevron_right,
                        color: AppColors.textSub),
                    onTap: () => _pickSortMode(context, ref, ls),
                  ),
                ],
              ),
            ),

            // ---------- Weekly review ----------
            const SizedBox(height: 18),
            const Text('Ôn tập tuần',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            const Text(
                'Ôn lại các thẻ đã học trong 7 ngày, ưu tiên thẻ sai nhiều. Nút "Ôn tuần" hiện trên Home vào đúng ngày.',
                style: TextStyle(fontSize: 12, color: AppColors.textSub)),
            const SizedBox(height: 10),
            Card(
              child: Column(
                children: [
                  ListTile(
                    title: const Text('Ngày ôn tuần',
                        style: TextStyle(
                            fontSize: 14.5, fontWeight: FontWeight.w600)),
                    trailing: DropdownButton<String>(
                      value: ls.weeklyReviewDay,
                      items: kWeekdayLabels.entries
                          .map((e) => DropdownMenuItem(
                              value: e.key, child: Text(e.value)))
                          .toList(),
                      onChanged: (v) =>
                          v == null ? null : _patch(ref, {'weeklyReviewDay': v}),
                    ),
                  ),
                  ListTile(
                    title: const Text('Số thẻ tối đa',
                        style: TextStyle(
                            fontSize: 14.5, fontWeight: FontWeight.w600)),
                    trailing: DropdownButton<int>(
                      value: ls.weeklyReviewLimit,
                      items: const [20, 30, 40, 60, 80, 100]
                          .map((d) =>
                              DropdownMenuItem(value: d, child: Text('$d thẻ')))
                          .toList(),
                      onChanged: (v) => v == null
                          ? null
                          : _patch(ref, {'weeklyReviewLimit': v}),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Thay đổi áp dụng từ phiên học MỚI.',
              style: TextStyle(fontSize: 12, color: AppColors.textSub),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _editIntervals(
      BuildContext context, WidgetRef ref, LanguageSetting ls) async {
    final controller =
        TextEditingController(text: ls.reviewIntervals.join(', '));
    final saved = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Chu kỳ ôn cơ sở', style: TextStyle(fontSize: 17)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
                'Số ngày giữa các lần ôn đầu tiên, cách nhau dấu phẩy. Sau đó khoảng cách tự giãn theo độ dễ của từng từ.',
                style: TextStyle(fontSize: 12.5, color: AppColors.textSub)),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              keyboardType: TextInputType.text,
              decoration: const InputDecoration(hintText: '1, 3, 7'),
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
    );
    if (saved != true) return;
    final parsed = controller.text
        .split(RegExp(r'[,\s]+'))
        .where((s) => s.isNotEmpty)
        .map(int.tryParse)
        .toList();
    if (parsed.isEmpty || parsed.any((v) => v == null || v < 1)) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Chu kỳ không hợp lệ — nhập các số dương, ví dụ: 1, 3, 7')));
      }
      return;
    }
    final values = parsed.cast<int>();
    await _patch(ref, {
      'reviewIntervals': values,
      'sentenceReviewIntervals': values,
    });
  }

  Future<void> _pickSortMode(
      BuildContext context, WidgetRef ref, LanguageSetting ls) async {
    final picked = await showDialog<String>(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: const Text('Thứ tự chọn thẻ', style: TextStyle(fontSize: 17)),
        children: [
          for (final entry in kSortModeLabels.entries)
            RadioListTile<String>(
              title: Text(entry.value, style: const TextStyle(fontSize: 14)),
              value: entry.key,
              groupValue: ls.sortMode,
              onChanged: (v) => Navigator.pop(ctx, v),
            ),
        ],
      ),
    );
    if (picked != null && picked != ls.sortMode) {
      await _patch(ref, {'sortMode': picked});
    }
  }
}

/// Multi-select chip filter. Empty selection == ['ALL'] (no filter).
class _FilterCard extends StatelessWidget {
  const _FilterCard({
    required this.title,
    required this.values,
    required this.selected,
    required this.accent,
    required this.onChanged,
  });

  final String title;
  final List<String> values;
  final List<String> selected;
  final Color accent;
  final ValueChanged<List<String>> onChanged;

  bool get isAll => selected.isEmpty || selected.contains('ALL');

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title,
                style: const TextStyle(
                    fontSize: 14, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilterChip(
                  label: const Text('Tất cả'),
                  selected: isAll,
                  selectedColor: accent.withOpacity(0.15),
                  checkmarkColor: accent,
                  onSelected: (_) => onChanged(['ALL']),
                ),
                for (final value in values)
                  FilterChip(
                    label: Text(value),
                    selected: !isAll && selected.contains(value),
                    selectedColor: accent.withOpacity(0.15),
                    checkmarkColor: accent,
                    onSelected: (on) {
                      final current =
                          isAll ? <String>{} : selected.toSet();
                      if (on) {
                        current.add(value);
                      } else {
                        current.remove(value);
                      }
                      onChanged(
                          current.isEmpty ? ['ALL'] : current.toList());
                    },
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
