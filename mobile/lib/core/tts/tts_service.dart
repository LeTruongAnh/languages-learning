import 'package:audioplayers/audioplayers.dart';

import '../storage/token_storage.dart';

/// Pronunciation playback — plays server-generated mp3 (edge-tts neural
/// voices) instead of on-device TTS. Identical voice on every platform,
/// no Web Speech API quirks, works for hard sessions too (voice is chosen
/// server-side from the item's language).
///
/// Audio URL carries the short-lived access token as a query param because
/// HTML <audio> elements (Flutter web) cannot send Authorization headers.
class TtsService {
  TtsService({required this.baseUrl, required TokenStorage tokens})
      : _tokens = tokens;

  final String baseUrl;
  final TokenStorage _tokens;
  final AudioPlayer _player = AudioPlayer();
  int _seq = 0;

  /// Plays the pronunciation for [itemId]. [rate] maps to playback speed.
  Future<void> speak({
    required String itemId,
    double rate = 0.9,
    double volume = 1.0,
  }) async {
    final my = ++_seq;
    await _player.stop();
    final token = await _tokens.accessToken;
    if (token == null || my != _seq) return;

    try {
      await _player.setPlaybackRate(rate.clamp(0.5, 1.5));
      await _player.setVolume(volume.clamp(0.0, 1.0));
      if (my != _seq) return;
      await _player.play(UrlSource('$baseUrl/tts/$itemId?token=$token'));
    } catch (_) {
      // Offline / server down: silent failure, the card is still usable.
    }
  }

  Future<void> stop() async {
    _seq++;
    await _player.stop();
  }
}
