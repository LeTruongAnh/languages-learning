import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/models/models.dart';
import '../../../core/providers.dart';
import '../../settings/data/settings_repository.dart';
import 'study_controller.dart';

/// Card direction for a single card (resolved from language settings).
enum CardDirection { front, reverse, listening }

CardDirection resolveDirection(String setting, String itemId) {
  switch (setting) {
    case 'REVERSE':
      return CardDirection.reverse;
    case 'LISTENING':
      return CardDirection.listening;
    case 'MIXED':
      // Stable per item within the session.
      return CardDirection.values[itemId.hashCode.abs() % 3];
    default:
      return CardDirection.front;
  }
}

/// Content max width — keeps the card compact on desktop web / tablets.
const double _kMaxContentWidth = 520;

/// Study flow (spec §5.5) + UX decisions:
/// - Grade buttons appear ONLY after the answer is revealed (Anki-style:
///   you must verify before you grade — no self-deception).
/// - Pronunciation audio comes from the server (edge-tts mp3), so the
///   speaker works identically everywhere, including hard sessions.
/// - Back/forward arrows browse ANSWERED cards read-only.
/// - Close (✕) opens a sheet: pause / end session / cancel.
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

  String get _directionSetting {
    if (widget.launch.source == StudySource.hard) return 'FRONT';
    final languageId = widget.launch.languageId;
    if (languageId == null) return 'FRONT';
    return ref
            .watch(languageSettingsProvider(languageId))
            .valueOrNull
            ?.studyDirection ??
        'FRONT';
  }

  Future<void> _speak(StudyItemModel item) async {
    final settings = ref.read(userSettingsProvider).valueOrNull;
    await ref.read(ttsServiceProvider).speak(
          itemId: item.id,
          rate: settings?.speechRate ?? 0.9,
          volume: settings?.speechVolume ?? 1.0,
        );
  }

  void _maybeAutoSpeak(StudyState state, CardDirection direction) {
    final item = state.viewing?.item;
    if (item == null || state.viewingAnswered || item.id == _lastSpokenItemId) {
      return;
    }
    // REVERSE: speaking the word up-front would reveal the answer.
    if (direction == CardDirection.reverse) return;
    _lastSpokenItemId = item.id;
    final settings = ref.read(userSettingsProvider).valueOrNull;
    final auto = settings?.autoSpeakOnCardOpen ?? true;
    if (auto || direction == CardDirection.listening) {
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
      await controller.endSession();
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(studyControllerProvider(widget.launch));
    final controller = ref.read(studyControllerProvider(widget.launch).notifier);
    final accent = _accent;
    final directionSetting = _directionSetting;
    // Keep user settings alive while studying: the provider is autoDispose,
    // so without a watcher every ref.read() in _speak would see a fresh
    // "loading" state and silently fall back to the DEFAULT speech rate.
    ref.watch(userSettingsProvider);

    return Scaffold(
      body: SafeArea(
        child: asyncState.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => _StudyError(onRetry: controller.load),
          data: (state) {
            if (state.finished || state.viewing == null) {
              return _CompletionView(session: state.session, accent: accent);
            }
            final direction =
                resolveDirection(directionSetting, state.viewing!.item.id);
            WidgetsBinding.instance
                .addPostFrameCallback((_) => _maybeAutoSpeak(state, direction));
            return _CardView(
              state: state,
              accent: accent,
              direction: direction,
              title: widget.launch.languageName ??
                  (widget.launch.source == StudySource.hard ? 'Hard Items' : 'Study'),
              onSpeak: () => _speak(state.viewing!.item),
              onReveal: () {
                controller.toggleMeaning();
                // REVERSE: speak the word once the answer is revealed.
                if (direction == CardDirection.reverse && !state.showMeaning) {
                  _speak(state.viewing!.item);
                }
              },
              onTogglePronunciation: controller.togglePronunciation,
              onBack: controller.goBack,
              onForward: controller.goForward,
              onUndo: state.canUndo
                  ? () {
                      HapticFeedback.lightImpact();
                      controller.undo();
                    }
                  : null,
              onClose: () => _showExitSheet(controller),
              onSubmit: (grade) {
                HapticFeedback.lightImpact();
                controller.submit(grade);
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
    required this.direction,
    required this.title,
    required this.onSpeak,
    required this.onReveal,
    required this.onTogglePronunciation,
    required this.onBack,
    required this.onForward,
    required this.onUndo,
    required this.onClose,
    required this.onSubmit,
  });

  final StudyState state;
  final Color accent;
  final CardDirection direction;
  final String title;
  final VoidCallback onSpeak;
  final VoidCallback onReveal;
  final VoidCallback onTogglePronunciation;
  final VoidCallback onBack;
  final VoidCallback onForward;
  final VoidCallback? onUndo;
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
    final revealed = state.showMeaning || answered != null;

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: _kMaxContentWidth),
        child: Column(
          children: [
            // Header: close, title, undo, position
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 4, 12, 0),
              child: Row(
                children: [
                  IconButton(
                      icon: const Icon(Icons.close, color: AppColors.textSub),
                      onPressed: onClose),
                  Expanded(
                    child: Text(title,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            color: accent,
                            fontSize: 15,
                            fontWeight: FontWeight.w800)),
                  ),
                  IconButton(
                    icon: const Icon(Icons.undo),
                    color: AppColors.textSub,
                    tooltip: 'Hoàn tác thẻ vừa chấm',
                    onPressed: onUndo,
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
                                  label: switch (direction) {
                                    CardDirection.reverse => 'Nghĩa → Từ',
                                    CardDirection.listening => 'Nghe → Từ',
                                    _ => sessionItem.isReview
                                        ? 'Ôn tập · lần ${item.timesReview + 1}'
                                        : 'Mới',
                                  },
                                  color: switch (direction) {
                                    CardDirection.front => sessionItem.isReview
                                        ? AppColors.review
                                        : AppColors.pass,
                                    _ => AppColors.review,
                                  }),
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
                    ..._buildPrompt(item, isSentence, revealed),
                    if (revealed) ...[
                      const SizedBox(height: 20),
                      _buildAnswer(item, isSentence),
                    ],
                  ],
                ),
              ),
            ),
            // Bottom bar:
            //  - unanswered + hidden  -> big reveal button (Anki-style)
            //  - unanswered + shown   -> skip + 4 grade buttons
            //  - answered (browsing)  -> read-only result + next
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 14),
              child: _buildBottomBar(revealed, answered),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBottomBar(bool revealed, String? answered) {
    if (answered != null) {
      return _AnsweredBar(result: answered, accent: accent, onForward: onForward);
    }
    if (!revealed) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextButton(
            onPressed: state.submitting ? null : () => onSubmit(kGradeSkip),
            child: const Text('Bỏ qua thẻ này',
                style: TextStyle(color: AppColors.skip, fontSize: 13)),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: accent,
              minimumSize: const Size.fromHeight(AppDimens.resultButtonHeight),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16)),
            ),
            onPressed: onReveal,
            child: Text(
              direction == CardDirection.front
                  ? '👁  Hiện nghĩa'
                  : '👁  Hiện đáp án',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
            ),
          ),
        ],
      );
    }
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        TextButton(
          onPressed: state.submitting ? null : () => onSubmit(kGradeSkip),
          child: const Text('Bỏ qua thẻ này',
              style: TextStyle(color: AppColors.skip, fontSize: 13)),
        ),
        Row(
          children: [
            _GradeButton('Quên', AppColors.fail,
                state.submitting ? null : () => onSubmit(kGradeAgain)),
            const SizedBox(width: 8),
            _GradeButton('Khó', AppColors.hardItems,
                state.submitting ? null : () => onSubmit(kGradeHard)),
            const SizedBox(width: 8),
            _GradeButton('Nhớ', AppColors.pass,
                state.submitting ? null : () => onSubmit(kGradeGood)),
            const SizedBox(width: 8),
            _GradeButton('Dễ', AppColors.english,
                state.submitting ? null : () => onSubmit(kGradeEasy)),
          ],
        ),
      ],
    );
  }

  /// The question side, depending on direction.
  List<Widget> _buildPrompt(StudyItemModel item, bool isSentence, bool revealed) {
    switch (direction) {
      case CardDirection.reverse:
        return [
          Text(item.vietnameseMeaning ?? '—',
              textAlign: TextAlign.center, style: StudyTextStyles.sentenceText),
          if (revealed) ...[
            const SizedBox(height: 16),
            Text(item.text,
                textAlign: TextAlign.center,
                style: isSentence
                    ? StudyTextStyles.sentenceText
                    : StudyTextStyles.mainText),
            if (item.pronunciation != null)
              Text(item.pronunciation!,
                  textAlign: TextAlign.center,
                  style: StudyTextStyles.pronunciation),
            IconButton.filledTonal(
                iconSize: 26,
                onPressed: onSpeak,
                icon: Icon(Icons.volume_up, color: accent)),
          ],
        ];
      case CardDirection.listening:
        return [
          IconButton.filledTonal(
            iconSize: 44,
            padding: const EdgeInsets.all(20),
            onPressed: onSpeak,
            icon: Icon(Icons.volume_up, color: accent),
          ),
          const SizedBox(height: 6),
          const Text('Nghe và nhớ lại từ',
              style: TextStyle(fontSize: 13, color: AppColors.textSub)),
          if (revealed) ...[
            const SizedBox(height: 16),
            Text(item.text,
                textAlign: TextAlign.center,
                style: isSentence
                    ? StudyTextStyles.sentenceText
                    : StudyTextStyles.mainText),
            if (item.pronunciation != null)
              Text(item.pronunciation!,
                  textAlign: TextAlign.center,
                  style: StudyTextStyles.pronunciation),
          ],
        ];
      case CardDirection.front:
        return [
          Text(item.text,
              textAlign: TextAlign.center,
              style: isSentence
                  ? StudyTextStyles.sentenceText
                  : StudyTextStyles.mainText),
          const SizedBox(height: 8),
          if (item.pronunciation != null)
            state.showPronunciation || revealed
                ? Text(item.pronunciation!,
                    textAlign: TextAlign.center,
                    style: StudyTextStyles.pronunciation)
                : TextButton.icon(
                    onPressed: onTogglePronunciation,
                    icon: const Icon(Icons.hearing, size: 16),
                    label: const Text('Phiên âm'),
                    style:
                        TextButton.styleFrom(foregroundColor: AppColors.textSub),
                  ),
          const SizedBox(height: 12),
          IconButton.filledTonal(
              iconSize: 26,
              onPressed: onSpeak,
              icon: Icon(Icons.volume_up, color: accent)),
        ];
    }
  }

  /// The answer side.
  Widget _buildAnswer(StudyItemModel item, bool isSentence) {
    final showMeaningInAnswer = direction != CardDirection.reverse;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: SizedBox(
          width: double.infinity,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (showMeaningInAnswer)
                Text(item.vietnameseMeaning ?? '—', style: StudyTextStyles.meaning),
              if (item.example != null) ...[
                const SizedBox(height: 10),
                Text(item.example!,
                    style: TextStyle(
                        fontSize: 15,
                        fontFamilyFallback:
                            StudyTextStyles.sentenceText.fontFamilyFallback)),
              ],
              if (item.exampleVietnamese != null)
                Text(item.exampleVietnamese!,
                    style: const TextStyle(fontSize: 14, color: AppColors.textSub)),
            ],
          ),
        ),
      ),
    );
  }
}

class _AnsweredBar extends StatelessWidget {
  const _AnsweredBar(
      {required this.result, required this.accent, required this.onForward});

  final String result;
  final Color accent;
  final VoidCallback onForward;

  static const _labels = {
    'AGAIN': 'Quên', 'HARD': 'Khó', 'GOOD': 'Nhớ', 'EASY': 'Dễ',
    'SKIP': 'Bỏ qua', 'PASS': 'Nhớ', 'FAIL': 'Quên',
  };

  static Color _color(String r) => switch (r) {
        'GOOD' || 'EASY' || 'PASS' => AppColors.pass,
        'HARD' => AppColors.hardItems,
        'AGAIN' || 'FAIL' => AppColors.fail,
        _ => AppColors.skip,
      };

  @override
  Widget build(BuildContext context) {
    final color = _color(result);
    return Row(
      children: [
        Expanded(
          child: Container(
            height: AppDimens.resultButtonHeight,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: color.withOpacity(0.12),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Text('Đã trả lời: ${_labels[result] ?? result}',
                style: TextStyle(fontWeight: FontWeight.w800, color: color)),
          ),
        ),
        const SizedBox(width: 10),
        FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: accent,
            minimumSize: const Size(90, AppDimens.resultButtonHeight),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          ),
          onPressed: onForward,
          child: const Text('Tiếp →',
              style: TextStyle(fontWeight: FontWeight.w800)),
        ),
      ],
    );
  }
}

class _GradeButton extends StatelessWidget {
  const _GradeButton(this.label, this.color, this.onTap);

  final String label;
  final Color color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: FilledButton(
        style: FilledButton.styleFrom(
          backgroundColor: color,
          padding: EdgeInsets.zero,
          minimumSize: const Size.fromHeight(AppDimens.resultButtonHeight),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
        onPressed: onTap,
        child: Text(label,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
      ),
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
    final remaining = session.totalItems - session.completedItems;
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: _kMaxContentWidth),
        child: Padding(
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
                    _StatBox('${session.passCount}', 'Nhớ', AppColors.pass),
                    const SizedBox(width: 10),
                    _StatBox('${session.failCount}', 'Quên', AppColors.fail),
                    const SizedBox(width: 10),
                    _StatBox('${session.skipCount}', 'Bỏ qua', AppColors.skip),
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
        ),
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
