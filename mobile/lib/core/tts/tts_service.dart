import 'package:flutter_tts/flutter_tts.dart';

/// TTS per spec §5.6 / §11.6.
///
/// Race fix: on web (Web Speech API) calling speak() right after stop() can
/// silently drop the new utterance — especially when the user advances cards
/// while the previous one is still being read. We stop, wait a beat, and use
/// a sequence counter so only the LATEST request actually speaks.
class TtsService {
  final FlutterTts _tts = FlutterTts();
  int _seq = 0;

  Future<void> speak({
    required String text,
    required String ttsLang, // languages.tts_lang from backend
    double rate = 0.9,
    double volume = 1.0,
  }) async {
    final my = ++_seq;
    await _tts.stop();
    // Let the previous utterance actually cancel (web engine quirk).
    await Future<void>.delayed(const Duration(milliseconds: 120));
    if (my != _seq) return; // a newer card already requested speech

    await _tts.setLanguage(ttsLang);
    await _tts.setSpeechRate(rate);
    await _tts.setVolume(volume);
    if (my != _seq) return;
    await _tts.speak(text);
  }

  Future<void> stop() async {
    _seq++;
    await _tts.stop();
  }
}
