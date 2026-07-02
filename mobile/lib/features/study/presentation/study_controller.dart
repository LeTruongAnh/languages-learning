import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/models/models.dart';
import '../data/study_repository.dart';

/// How a study session is launched from the UI.
enum StudySource { daily, extra, weekly, hard }

class StudyLaunch {
  const StudyLaunch.daily(this.languageId, {this.ttsLang, this.accentColor, this.languageName})
      : source = StudySource.daily;
  const StudyLaunch.extra(this.languageId, {this.ttsLang, this.accentColor, this.languageName})
      : source = StudySource.extra;
  const StudyLaunch.weekly(this.languageId, {this.ttsLang, this.accentColor, this.languageName})
      : source = StudySource.weekly;
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

/// Grades (Anki-style) — sent to the backend as-is.
const kGradeAgain = 'AGAIN';
const kGradeHard = 'HARD';
const kGradeGood = 'GOOD';
const kGradeEasy = 'EASY';
const kGradeSkip = 'SKIP';

/// UX model (see PLAN.md — SRS integrity):
/// - Cards are answered in order; the user can browse BACK to re-read
///   answered cards (read-only).
/// - Single-step UNDO (Anki-style): only the most recently answered card,
///   while the session is still active.
class StudyState {
  const StudyState({
    required this.session,
    required this.index,
    this.localResults = const {},
    this.lastAnsweredItemId,
    this.showMeaning = false,
    this.showPronunciation = false,
    this.submitting = false,
    this.finished = false,
  });

  final StudySession session;
  final int index;
  final Map<String, String> localResults;

  /// Session-item id of the most recent answer — undo target.
  final String? lastAnsweredItemId;
  final bool showMeaning;
  final bool showPronunciation;
  final bool submitting;
  final bool finished;

  SessionItem? get viewing =>
      index < session.items.length ? session.items[index] : null;

  String? resultOf(SessionItem item) => item.result ?? localResults[item.id];

  int get firstUnanswered =>
      session.items.indexWhere((i) => resultOf(i) == null);

  bool get viewingAnswered => viewing != null && resultOf(viewing!) != null;

  bool get canGoBack => index > 0;

  bool get canGoForward => viewingAnswered && index < session.items.length - 1;

  bool get canUndo => lastAnsweredItemId != null && !finished;

  StudyState copyWith({
    StudySession? session,
    int? index,
    Map<String, String>? localResults,
    String? lastAnsweredItemId,
    bool clearLastAnswered = false,
    bool? showMeaning,
    bool? showPronunciation,
    bool? submitting,
    bool? finished,
  }) =>
      StudyState(
        session: session ?? this.session,
        index: index ?? this.index,
        localResults: localResults ?? this.localResults,
        lastAnsweredItemId: clearLastAnswered
            ? null
            : (lastAnsweredItemId ?? this.lastAnsweredItemId),
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
        StudySource.weekly => await _repo.createWeekly(_launch.languageId!),
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

  void goBack() => _update((s) => s.canGoBack
      ? s.copyWith(index: s.index - 1, showMeaning: true, showPronunciation: true)
      : s);

  void goForward() => _update((s) {
        if (!s.canGoForward) return s;
        final next = s.index + 1;
        final answered = s.resultOf(s.session.items[next]) != null;
        return s.copyWith(
            index: next, showMeaning: answered, showPronunciation: answered);
      });

  SessionProgressPatch _progressPatch(Map<String, dynamic> progress) =>
      SessionProgressPatch(
        completedItems: progress['completedItems'] as int,
        passCount: progress['passCount'] as int,
        failCount: progress['failCount'] as int,
        skipCount: progress['skipCount'] as int,
      );

  /// Submits AGAIN/HARD/GOOD/EASY/SKIP for the current answerable card.
  Future<void> submit(String grade) async {
    final s = state.valueOrNull;
    final current = s?.viewing;
    if (s == null || current == null || s.submitting) return;
    if (s.resultOf(current) != null) return; // read-only: already answered

    state = AsyncValue.data(s.copyWith(submitting: true));
    try {
      final res = await _repo.submitReview(
        sessionId: s.session.id,
        sessionItemId: current.id,
        result: grade,
      );
      final patch = _progressPatch(res['sessionProgress'] as Map<String, dynamic>);
      final updated = patch.applyTo(s.session);
      final results = {...s.localResults, current.id: grade};
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
        lastAnsweredItemId: current.id,
        index: finished ? s.index : nextIndex,
        showMeaning: false,
        showPronunciation: false,
        submitting: false,
        finished: finished,
      ));
    } catch (e) {
      state = AsyncValue.data(s.copyWith(submitting: false));
    }
  }

  /// Undo the most recent answer (single step, Anki-style).
  Future<void> undo() async {
    final s = state.valueOrNull;
    final targetId = s?.lastAnsweredItemId;
    if (s == null || targetId == null || s.submitting) return;

    state = AsyncValue.data(s.copyWith(submitting: true));
    try {
      final res = await _repo.undoReview(
        sessionId: s.session.id,
        sessionItemId: targetId,
      );
      final patch = _progressPatch(res['sessionProgress'] as Map<String, dynamic>);
      final updated = patch.applyTo(s.session);
      final results = {...s.localResults}..remove(targetId);
      final targetIndex =
          s.session.items.indexWhere((i) => i.id == targetId);
      state = AsyncValue.data(s.copyWith(
        session: updated,
        localResults: results,
        clearLastAnswered: true, // single-step: no chained undo
        index: targetIndex < 0 ? s.index : targetIndex,
        showMeaning: false,
        showPronunciation: false,
        submitting: false,
        finished: false,
      ));
    } catch (e) {
      state = AsyncValue.data(s.copyWith(submitting: false));
    }
  }

  /// Ends the session early. Unanswered cards are NOT counted as SKIP.
  Future<void> endSession() async {
    final s = state.valueOrNull;
    if (s == null) return;
    try {
      await _repo.completeSession(s.session.id);
    } catch (_) {}
    _update((st) => st.copyWith(finished: true, clearLastAnswered: true));
  }
}

class SessionProgressPatch {
  const SessionProgressPatch({
    required this.completedItems,
    required this.passCount,
    required this.failCount,
    required this.skipCount,
  });

  final int completedItems, passCount, failCount, skipCount;

  StudySession applyTo(StudySession session) => session.copyWith(
        completedItems: completedItems,
        passCount: passCount,
        failCount: failCount,
        skipCount: skipCount,
      );
}
