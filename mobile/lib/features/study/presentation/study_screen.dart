import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/models/models.dart';
import '../../../core/providers.dart';
import '../../settings/data/settings_repository.dart';
import 'study_controller.dart';

/// Study flow (spec §5.5) + UX decisions:
/// - Pronunciation hidden behind a small button (recalling the sound is part
///   of active recall — showing pinyin immediately gives the answer away).
/// - Back/forward arrows browse ANSWERED cards read-only; results can't be
///   changed (they're already applied to the SRS state server-side).
/// - Close (✕) opens a sheet: pause (resume later) / end session / cancel.
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
    final item = state.viewing?.item;
    // Only auto-speak the active (unanswered) card, once per card.
    if (item == null || state.viewingAnswered || item.id == _lastSpokenItemId) {
      return;
    }
    _lastSpokenItemId = item.id;
    final settings = ref.read(userSettingsProvider).valueOrNull;
    if (settings?.autoSpeakOnCardOpen ?? true) {
      _speak(item);
    }
  }

  Future<void> _showExitSheet(StudyController controller) async {
    final action = await showModalBottomSheet<String>(
      context: context,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 8),
            ListTile(
              leading: const Icon(Icons.pause_circle_outline),
              title: const Text('Tạm dừng',
                  style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Giữ phiên học, quay lại làm tiếp sau'),
              onTap: () => Navigator.pop(ctx, 'pause'),
            ),
            ListTile(
              leading: const Icon(Icons.flag_outlined, color: AppColors.fail),
              title: const Text('Kết thúc bài',
                  style: TextStyle(
                      fontWeight: FontWeight.w700, color: AppColors.fail)),
              subtitle: const Text(
                  'Chốt kết quả; thẻ chưa làm sẽ quay lại ở phiên sau'),
              onTap: () => Navigator.pop(ctx, 'end'),
            ),
            ListTile(
              leading: const Icon(Icons.close),
              title: const Text('Hủy'),
              onTap: () => Navigator.pop(ctx),
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
    if (!mounted) return;
    if (action == 'pause') {
      context.pop();
    } else if (action == 'end') {
      await controller.endSession(); // completion view will render
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
            if (state.finished || state.viewing == null) {
              return _CompletionView(session: state.session, accent: accent);
            }
            WidgetsBinding.instance.addPostFrameCallback((_) => _maybeAutoSpeak(state));
            return _CardView(
              state: state,
              accent: accent,
              title: widget.launch.languageName ??
                  (widget.launch.source == StudySource.hard ? 'Hard Items' : 'Study'),
              canSpeak: widget.launch.ttsLang != null,
              onSpeak: () => _speak(state.viewing!.item),
              onToggleMeaning: controller.toggleMeaning,
              onTogglePronunciation: controller.togglePronunciation,
              onBack: controller.goBack,
              onForward: controller.goForward,
              onClose: () => _showExitSheet(controller),
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
    required this.onTogglePronunciation,
    required this.onBack,
    required this.onForward,
    required this.onClose,
    required this.onSubmit,
  });

  final StudyState state;
  final Color accent;
  final String title;
  final bool canSpeak;
  final VoidCallback onSpeak;
  final VoidCallback onToggleMeaning;
  final VoidCallback onTogglePronunciation;
  final VoidCallback onBack;
  final VoidCallback onForward;
  final VoidCallback onClose;
  final ValueChanged<String> onSubmit;

  @override
  Widget build(BuildContext context) {
    final sessionItem = state.viewing!;
    final item = sessionItem.item;
    final isSentence = item.itemType == 'SENTENCE';
    final answered = state.resultOf(sessionItem);
    final answeredCount =
        state.firstUnanswered < 0 ? state.session.items.length : state.firstUnanswered;

    return Column(
      children: [
        // Header: close, title, position
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 4, 20, 0),
          child: Row(
            children: [
              IconButton(
                  icon: const Icon(Icons.close, color: AppColors.textSub),
                  onPressed: onClose),
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
                  : answeredCount / state.session.totalItems,
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
                // Badges + browse arrows
                Row(
                  children: [
                    IconButton(
                      onPressed: state.canGoBack ? onBack : null,
                      icon: const Icon(Icons.chevron_left),
                      tooltip: 'Xem thẻ trước',
                    ),
                    Expanded(
                      child: Wrap(
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
                            _Badge(
                                label: item.hardLevel,
                                color: AppColors.hardItems),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: state.canGoForward ? onForward : null,
                      icon: const Icon(Icons.chevron_right),
                      tooltip: 'Thẻ tiếp theo',
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                Text(item.text,
                    textAlign: TextAlign.center,
                    style: isSentence
                        ? StudyTextStyles.sentenceText
                        : StudyTextStyles.mainText),
                const SizedBox(height: 8),
                // Pronunciation: hidden behind a small button (active recall)
                if (item.pronunciation != null)
                  state.showPronunciation
                      ? Text(item.pronunciation!,
                          textAlign: TextAlign.center,
                          style: StudyTextStyles.pronunciation)
                      : TextButton.icon(
                          onPressed: onTogglePronunciation,
                          icon: const Icon(Icons.hearing, size: 16),
                          label: const Text('Phiên âm'),
                          style: TextButton.styleFrom(
                              foregroundColor: AppColors.textSub),
                        ),
                if (canSpeak) ...[
                  const SizedBox(height: 12),
                  IconButton.filledTonal(
                    iconSize: 26,
                    onPressed: onSpeak,
                    icon: Icon(Icons.volume_up, color: accent),
                  ),
                ],
                const SizedBox(height: 20),
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
                            Text(item.example!,
                                style: TextStyle(
                                    fontSize: 15,
                                    fontFamilyFallback: StudyTextStyles
                                        .sentenceText.fontFamilyFallback)),
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
        // Bottom bar: answer buttons for the active card,
        // read-only result + next for answered cards.
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
          child: answered != null
              ? Row(
                  children: [
                    Expanded(
                      child: Container(
                        height: AppDimens.resultButtonHeight,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: _resultColor(answered).withOpacity(0.12),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Text('Đã trả lời: $answered',
                            style: TextStyle(
                                fontWeight: FontWeight.w800,
                                color: _resultColor(answered))),
                      ),
                    ),
                    const SizedBox(width: 10),
                    FilledButton(
                      style: FilledButton.styleFrom(
                        backgroundColor: accent,
                        minimumSize:
                            const Size(90, AppDimens.resultButtonHeight),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16)),
                      ),
                      onPressed: onForward,
                      child: const Text('Tiếp →',
                          style: TextStyle(fontWeight: FontWeight.w800)),
                    ),
                  ],
                )
              : Row(
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

  static Color _resultColor(String result) => switch (result) {
        'PASS' => AppColors.pass,
        'FAIL' => AppColors.fail,
        _ => AppColors.skip,
      };
}

class _CompletionView extends StatelessWidget {
  const _CompletionView({required this.session, required this.accent});

  final StudySession session;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final empty = session.totalItems == 0;
    final remaining = session.totalItems - session.completedItems;
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
            Text(
                '${session.completedItems}/${session.totalItems} thẻ'
                '${remaining > 0 ? ' · $remaining thẻ chưa làm sẽ quay lại sau' : ''}',
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
