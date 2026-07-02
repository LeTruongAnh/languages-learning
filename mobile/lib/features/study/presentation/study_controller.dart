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

class StudyState {
  const StudyState({
    required this.session,
    required this.index,
    this.showMeaning = false,
    this.submitting = false,
    this.finished = false,
  });

  final StudySession session;
  final int index;
  final bool showMeaning;
  final bool submitting;
  final bool finished;

  SessionItem? get current =>
      index < session.items.length ? session.items[index] : null;

  StudyState copyWith({
    StudySession? session,
    int? index,
    bool? showMeaning,
    bool? submitting,
    bool? finished,
  }) =>
      StudyState(
        session: session ?? this.session,
        index: index ?? this.index,
        showMeaning: showMeaning ?? this.showMeaning,
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
      // Resume: skip items that already have a result.
      final firstPending = session.items.indexWhere((i) => i.result == null);
      state = AsyncValue.data(StudyState(
        session: session,
        index: firstPending < 0 ? session.items.length : firstPending,
        finished: firstPending < 0 || session.items.isEmpty,
      ));
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  void toggleMeaning() {
    final s = state.valueOrNull;
    if (s == null) return;
    state = AsyncValue.data(s.copyWith(showMeaning: !s.showMeaning));
  }

  /// Submits PASS/FAIL/SKIP for the current card and advances.
  Future<void> submit(String result) async {
    final s = state.valueOrNull;
    final current = s?.current;
    if (s == null || current == null || s.submitting) return;

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
      final nextIndex = s.index + 1;
      final finished = nextIndex >= updated.items.length;
      if (finished) {
        // Best effort — session stats already correct server-side.
        try {
          await _repo.completeSession(updated.id);
        } catch (_) {}
      }
      state = AsyncValue.data(s.copyWith(
        session: updated,
        index: nextIndex,
        showMeaning: false,
        submitting: false,
        finished: finished,
      ));
    } catch (e) {
      // Keep the card; let the user retry (e.g. network hiccup).
      state = AsyncValue.data(s.copyWith(submitting: false));
    }
  }
}
