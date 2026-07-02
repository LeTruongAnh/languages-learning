import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/models/models.dart';
import '../data/study_repository.dart';

/// How a study session is launched from the UI.
enum StudySource { daily, extra, hard }

class StudyLaunch {
  const StudyLaunch.daily(this.languageId, {this.ttsLang, this.accentColor, this.languageName})
      : source = StudySource.daily;
  const StudyLaunch.extra(this.languageId, {this.ttsLang, this.accentColor, this.languageName})
      : source = StudySource.extra;
  const StudyLaunch.hard()
      : source = StudySource.hard,
        languageId = null,
        ttsLang = null,
        accentColor = null,
        languageName = null;

  final StudySource source;
  final String? languageId;
  final String? ttsLang;
  final String? accentColor;
  final String? languageName;
}

/// UX model (see PLAN.md — SRS integrity):
/// - The user answers cards strictly in order, but can navigate BACK to
///   re-read answered cards (read-only: results are already applied to the
///   spaced-repetition state server-side and must not change).
/// - `index` is the card being VIEWED; `firstUnanswered` is the card that
///   can still be answered. Forward navigation stops at firstUnanswered.
class StudyState {
  const StudyState({
    required this.session,
    required this.index,
    this.localResults = const {},
    this.showMeaning = false,
    this.showPronunciation = false,
    this.submitting = false,
    this.finished = false,
  });

  final StudySession session;
  final int index;

  /// Results submitted during this screen's lifetime (server truth mirror).
  final Map<String, String> localResults;
  final bool showMeaning;
  final bool showPronunciation;
  final bool submitting;
  final bool finished;

  SessionItem? get viewing =>
      index < session.items.length ? session.items[index] : null;

  String? resultOf(SessionItem item) => item.result ?? localResults[item.id];

  /// Index of the first card without a result; -1 when all are answered.
  int get firstUnanswered =>
      session.items.indexWhere((i) => resultOf(i) == null);

  bool get viewingAnswered => viewing != null && resultOf(viewing!) != null;

  bool get canGoBack => index > 0;

  bool get canGoForward => viewingAnswered && index < session.items.length - 1;

  StudyState copyWith({
    StudySession? session,
    int? index,
    Map<String, String>? localResults,
    bool? showMeaning,
    bool? showPronunciation,
    bool? submitting,
    bool? finished,
  }) =>
      StudyState(
        session: session ?? this.session,
        index: index ?? this.index,
        localResults: localResults ?? this.localResults,
        showMeaning: showMeaning ?? this.showMeaning,
        showPronunciation: showPronunciation ?? this.showPronunciation,
        submitting: submitting ?? this.submitting,
        finished: finished ?? this.finished,
      );
}

final studyControllerProvider = StateNotifierProvider.autoDispose
    .family<StudyController, AsyncValue<StudyState>, StudyLaunch>(
  (ref, launch) => StudyController(ref.watch(studyRepositoryProvider), launch)..load(),
);

class StudyController extends StateNotifier<AsyncValue<StudyState>> {
  StudyController(this._repo, this._launch) : super(const AsyncValue.loading());

  final StudyRepository _repo;
  final StudyLaunch _launch;

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final session = switch (_launch.source) {
        StudySource.daily => await _repo.createDaily(_launch.languageId!),
        StudySource.extra => await _repo.createExtra(_launch.languageId!),
        StudySource.hard => await _repo.createHardSession(),
      };
      final firstPending = session.items.indexWhere((i) => i.result == null);
      state = AsyncValue.data(StudyState(
        session: session,
        index: firstPending < 0 ? 0 : firstPending,
        finished: firstPending < 0 || session.items.isEmpty,
      ));
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  void _update(StudyState Function(StudyState) fn) {
    final s = state.valueOrNull;
    if (s != null) state = AsyncValue.data(fn(s));
  }

  void toggleMeaning() => _update((s) => s.copyWith(showMeaning: !s.showMeaning));

  void togglePronunciation() =>
      _update((s) => s.copyWith(showPronunciation: !s.showPronunciation));

  /// Browse back to an answered card (read-only).
  void goBack() => _update((s) => s.canGoBack
      ? s.copyWith(index: s.index - 1, showMeaning: true, showPronunciation: true)
      : s);

  /// Browse forward, up to the first unanswered card.
  void goForward() => _update((s) {
        if (!s.canGoForward) return s;
        final next = s.index + 1;
        final answered = s.resultOf(s.session.items[next]) != null;
        // Answered cards open fully revealed; the active card starts hidden.
        return s.copyWith(
            index: next, showMeaning: answered, showPronunciation: answered);
      });

  /// Submits PASS/FAIL/SKIP for the current answerable card and advances.
  Future<void> submit(String result) async {
    final s = state.valueOrNull;
    final current = s?.viewing;
    if (s == null || current == null || s.submitting) return;
    if (s.resultOf(current) != null) return; // read-only: already answered

    state = AsyncValue.data(s.copyWith(submitting: true));
    try {
      final res = await _repo.submitReview(
        sessionId: s.session.id,
        sessionItemId: current.id,
        result: result,
      );
      final progress = res['sessionProgress'] as Map<String, dynamic>;
      final updated = s.session.copyWith(
        completedItems: progress['completedItems'] as int,
        passCount: progress['passCount'] as int,
        failCount: progress['failCount'] as int,
        skipCount: progress['skipCount'] as int,
      );
      final results = {...s.localResults, current.id: result};
      final nextIndex = s.index + 1;
      final finished = nextIndex >= updated.items.length;
      if (finished) {
        try {
          await _repo.completeSession(updated.id);
        } catch (_) {}
      }
      state = AsyncValue.data(s.copyWith(
        session: updated,
        localResults: results,
        index: finished ? s.index : nextIndex,
        showMeaning: false,
        showPronunciation: false,
        submitting: false,
        finished: finished,
      ));
    } catch (e) {
      // Keep the card; let the user retry (e.g. network hiccup).
      state = AsyncValue.data(s.copyWith(submitting: false));
    }
  }

  /// Ends the session early. Unanswered cards are left untouched (they are
  /// NOT counted as SKIP — no unfair penalty) and will be eligible again
  /// in a future session.
  Future<void> endSession() async {
    final s = state.valueOrNull;
    if (s == null) return;
    try {
      await _repo.completeSession(s.session.id);
    } catch (_) {}
    _update((st) => st.copyWith(finished: true));
  }
}
