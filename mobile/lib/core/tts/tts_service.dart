import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// TTS per spec §5.6 / §11.6.
///
/// Web quirks handled here (Chrome Web Speech API):
/// - speak() right after cancel() can be silently dropped -> stop, wait,
///   then speak; retry ONCE if the engine never actually started speaking
///   (detected via the start handler, so no double-reading).
/// - A sequence counter ensures only the LATEST request speaks when the
///   user advances cards quickly.
class TtsService {
  TtsService() {
    _tts.setStartHandler(() => _started = true);
  }

  final FlutterTts _tts = FlutterTts();
  int _seq = 0;
  bool _started = false;

  Future<void> speak({
    required String text,
    required String ttsLang, // languages.tts_lang from backend
    double rate = 0.9,
    double volume = 1.0,
  }) async {
    final my = ++_seq;
    await _tts.stop();
    // Let the previous utterance actually cancel (web engine quirk).
    await Future<void>.delayed(const Duration(milliseconds: 150));
    if (my != _seq) return; // a newer card already requested speech

    await _tts.setLanguage(ttsLang);
    await _tts.setSpeechRate(rate.clamp(0.3, 1.5));
    await _tts.setVolume(volume.clamp(0.1, 1.0));
    if (my != _seq) return;

    _started = false;
    await _tts.speak(text);

    // Chrome sometimes swallows the utterance after a cancel storm: the
    // engine never fires "start". Wait a beat and retry once if so.
    if (kIsWeb) {
      await Future<void>.delayed(const Duration(milliseconds: 500));
      if (my != _seq || _started) return;
      await _tts.stop();
      await Future<void>.delayed(const Duration(milliseconds: 150));
      if (my != _seq) return;
      await _tts.speak(text);
    }
  }

  Future<void> stop() async {
    _seq++;
    await _tts.stop();
  }
}
