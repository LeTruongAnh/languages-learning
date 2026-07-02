import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/models/models.dart';
import '../../../core/providers.dart';
import '../../settings/data/settings_repository.dart';
import 'study_controller.dart';

/// Study flow (spec §5.5): fetches/creates the session, shows cards one by
/// one, submits PASS/FAIL/SKIP, auto-TTS, then a completion view.
class StudyScreen extends ConsumerStatefulWidget {
  const StudyScreen({super.key, required this.launch});

  final StudyLaunch launch;

  @override
  ConsumerState<StudyScreen> createState() => _StudyScreenState();
}

class _StudyScreenState extends ConsumerState<StudyScreen> {
  String? _lastSpokenItemId;

  Color get _accent {
    final hex = widget.launch.accentColor;
    if (hex != null && hex.startsWith('#') && hex.length == 7) {
      return Color(int.parse('FF${hex.substring(1)}', radix: 16));
    }
    return widget.launch.source == StudySource.hard
        ? AppColors.hardItems
        : AppColors.english;
  }

  Future<void> _speak(StudyItemModel item) async {
    final ttsLang = widget.launch.ttsLang;
    if (ttsLang == null) return; // hard sessions mix languages — manual only
    final settings = ref.read(userSettingsProvider).valueOrNull;
    await ref.read(ttsServiceProvider).speak(
          text: item.text,
          ttsLang: ttsLang,
          rate: settings?.speechRate ?? 0.9,
          volume: settings?.speechVolume ?? 1.0,
        );
  }

  void _maybeAutoSpeak(StudyState state) {
    final item = state.current?.item;
    if (item == null || item.id == _lastSpokenItemId) return;
    _lastSpokenItemId = item.id;
    final settings = ref.read(userSettingsProvider).valueOrNull;
    if (settings?.autoSpeakOnCardOpen ?? true) {
      _speak(item);
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(studyControllerProvider(widget.launch));
    final controller = ref.read(studyControllerProvider(widget.launch).notifier);
    final accent = _accent;

    return Scaffold(
      body: SafeArea(
        child: asyncState.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => _StudyError(onRetry: controller.load),
          data: (state) {
            if (state.finished || state.current == null) {
              return _CompletionView(session: state.session, accent: accent);
            }
            WidgetsBinding.instance.addPostFrameCallback((_) => _maybeAutoSpeak(state));
            return _CardView(
              state: state,
              accent: accent,
              title: widget.launch.languageName ??
                  (widget.launch.source == StudySource.hard ? 'Hard Items' : 'Study'),
              canSpeak: widget.launch.ttsLang != null,
              onSpeak: () => _speak(state.current!.item),
              onToggleMeaning: controller.toggleMeaning,
              onSubmit: (result) {
                HapticFeedback.lightImpact();
                controller.submit(result);
              },
            );
          },
        ),
      ),
    );
  }
}

class _CardView extends StatelessWidget {
  const _CardView({
    required this.state,
    required this.accent,
    required this.title,
    required this.canSpeak,
    required this.onSpeak,
    required this.onToggleMeaning,
    required this.onSubmit,
  });

  final StudyState state;
  final Color accent;
  final String title;
  final bool canSpeak;
  final VoidCallback onSpeak;
  final VoidCallback onToggleMeaning;
  final ValueChanged<String> onSubmit;

  @override
  Widget build(BuildContext context) {
    final sessionItem = state.current!;
    final item = sessionItem.item;
    final isSentence = item.itemType == 'SENTENCE';

    return Column(
      children: [
        // Header: close, title, progress
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 4, 20, 0),
          child: Row(
            children: [
              IconButton(
                  icon: const Icon(Icons.close, color: AppColors.textSub),
                  onPressed: () => context.pop()),
              Expanded(
                child: Text(title,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                        color: accent, fontSize: 15, fontWeight: FontWeight.w800)),
              ),
              Text('${state.index + 1} / ${state.session.totalItems}',
                  style: const TextStyle(
                      fontWeight: FontWeight.w700, color: AppColors.textSub)),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(99),
            child: LinearProgressIndicator(
              value: state.session.totalItems == 0
                  ? 0
                  : state.index / state.session.totalItems,
              minHeight: 4,
              color: accent,
              backgroundColor: AppColors.border,
            ),
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppDimens.screenPadding),
            child: Column(
              children: [
                Wrap(
                  spacing: 8,
                  alignment: WrapAlignment.center,
                  children: [
                    _Badge(
                        label: isSentence ? 'Câu' : 'Từ vựng',
                        color: accent),
                    _Badge(
                        label: sessionItem.isReview
                            ? 'Ôn tập · lần ${item.timesReview + 1}'
                            : 'Mới',
                        color: sessionItem.isReview
                            ? AppColors.review
                            : AppColors.pass),
                    if (item.hardLevel != 'Normal')
                      _Badge(label: item.hardLevel, color: AppColors.hardItems),
                  ],
                ),
                const SizedBox(height: 28),
                Text(item.text,
                    textAlign: TextAlign.center,
                    style: isSentence
                        ? const TextStyle(
                            fontSize: 28, fontWeight: FontWeight.w800, height: 1.35)
                        : StudyTextStyles.mainText),
                if (item.pronunciation != null) ...[
                  const SizedBox(height: 6),
                  Text(item.pronunciation!,
                      textAlign: TextAlign.center,
                      style: StudyTextStyles.pronunciation),
                ],
                if (canSpeak) ...[
                  const SizedBox(height: 18),
                  IconButton.filledTonal(
                    iconSize: 26,
                    onPressed: onSpeak,
                    icon: Icon(Icons.volume_up, color: accent),
                  ),
                ],
                const SizedBox(height: 22),
                if (!state.showMeaning)
                  OutlinedButton(
                    onPressed: onToggleMeaning,
                    child: const Text('👁  Hiện nghĩa'),
                  )
                else
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(item.vietnameseMeaning ?? '—',
                              style: StudyTextStyles.meaning),
                          if (item.example != null) ...[
                            const SizedBox(height: 10),
                            Text(item.example!, style: const TextStyle(fontSize: 15)),
                          ],
                          if (item.exampleVietnamese != null)
                            Text(item.exampleVietnamese!,
                                style: const TextStyle(
                                    fontSize: 14, color: AppColors.textSub)),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
        // Fixed result bar — thumb-reachable, 56dp (PLAN.md §4.3).
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
          child: Row(
            children: [
              Expanded(
                  flex: 12,
                  child: _ResultButton('FAIL', AppColors.fail,
                      state.submitting ? null : () => onSubmit('FAIL'))),
              const SizedBox(width: 10),
              Expanded(
                  flex: 8,
                  child: _ResultButton('SKIP', AppColors.skip,
                      state.submitting ? null : () => onSubmit('SKIP'))),
              const SizedBox(width: 10),
              Expanded(
                  flex: 12,
                  child: _ResultButton('PASS', AppColors.pass,
                      state.submitting ? null : () => onSubmit('PASS'))),
            ],
          ),
        ),
      ],
    );
  }
}

class _CompletionView extends StatelessWidget {
  const _CompletionView({required this.session, required this.accent});

  final StudySession session;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final empty = session.totalItems == 0;
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(empty ? '🌤' : '🎉',
              textAlign: TextAlign.center, style: const TextStyle(fontSize: 64)),
          const SizedBox(height: 12),
          Text(empty ? 'Không có thẻ nào hôm nay' : 'Hoàn thành!',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w800)),
          if (!empty) ...[
            const SizedBox(height: 6),
            Text('${session.totalItems} thẻ',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, color: AppColors.textSub)),
            const SizedBox(height: 24),
            Row(
              children: [
                _StatBox('${session.passCount}', 'PASS', AppColors.pass),
                const SizedBox(width: 10),
                _StatBox('${session.failCount}', 'FAIL', AppColors.fail),
                const SizedBox(width: 10),
                _StatBox('${session.skipCount}', 'SKIP', AppColors.skip),
              ],
            ),
          ],
          const SizedBox(height: 24),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: accent),
            onPressed: () => context.pop(),
            child: const Text('Về Home'),
          ),
        ],
      ),
    );
  }
}

class _StudyError extends StatelessWidget {
  const _StudyError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text('Không tải được phiên học',
              style: TextStyle(color: AppColors.textSub)),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onRetry, child: const Text('Thử lại')),
          TextButton(
              onPressed: () => context.pop(), child: const Text('Quay lại')),
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(label,
          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: color)),
    );
  }
}

class _ResultButton extends StatelessWidget {
  const _ResultButton(this.label, this.color, this.onTap);

  final String label;
  final Color color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      style: FilledButton.styleFrom(
        backgroundColor: color,
        minimumSize: const Size.fromHeight(AppDimens.resultButtonHeight),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
      onPressed: onTap,
      child: Text(label, style: const TextStyle(fontWeight: FontWeight.w800)),
    );
  }
}

class _StatBox extends StatelessWidget {
  const _StatBox(this.value, this.label, this.color);

  final String value, label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 14),
          child: Column(
            children: [
              Text(value,
                  style: TextStyle(
                      fontSize: 24, fontWeight: FontWeight.w800, color: color)),
              Text(label,
                  style: const TextStyle(fontSize: 11, color: AppColors.textSub)),
            ],
          ),
        ),
      ),
    );
  }
}
