import 'package:flutter_tts/flutter_tts.dart';

/// TTS per spec §5.6 / §11.6:
/// - language-specific voice (zh -> zh-CN, en -> en-US, ja -> ja-JP)
/// - reads the item's main text; never the pronunciation line.
class TtsService {
  final FlutterTts _tts = FlutterTts();

  Future<void> speak({
    required String text,
    required String ttsLang, // languages.tts_lang from backend
    double rate = 0.9,
    double volume = 1.0,
  }) async {
    await _tts.stop();
    await _tts.setLanguage(ttsLang);
    await _tts.setSpeechRate(rate);
    await _tts.setVolume(volume);
    await _tts.speak(text);
  }

  Future<void> stop() => _tts.stop();
}
