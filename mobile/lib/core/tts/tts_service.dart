import 'package:audioplayers/audioplayers.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../storage/token_storage.dart';

/// Pronunciation playback — plays server-generated mp3 (edge-tts neural
/// voices) instead of on-device TTS.
///
/// Playback-rate gotcha (web): the browser resets `playbackRate` to 1.0
/// whenever a new source loads, and the load may finish AFTER play()
/// returns. So the rate is re-applied on every "playing" state event —
/// the only moment it reliably sticks.
class TtsService {
  TtsService({
    required this.baseUrl,
    required Dio dio,
    required TokenStorage tokens,
  })  : _dio = dio,
        _tokens = tokens {
    _player.onPlayerStateChanged.listen((state) {
      if (state == PlayerState.playing) {
        _player.setPlaybackRate(_currentRate);
      }
    });
  }

  final String baseUrl;
  final Dio _dio;
  final TokenStorage _tokens;
  final AudioPlayer _player = AudioPlayer();
  int _seq = 0;
  double _currentRate = 0.9;

  Future<void> speak({
    required String itemId,
    double rate = 0.9,
    double volume = 1.0,
  }) async {
    final my = ++_seq;
    await _player.stop();

    // 1. Prefetch: triggers server-side generation, surfaces real errors.
    try {
      await _dio.get(
        '/tts/$itemId',
        options: Options(responseType: ResponseType.bytes),
      );
    } on DioException catch (e) {
      final status = e.response?.statusCode;
      final body = e.response?.data;
      final detail = body is List<int>
          ? String.fromCharCodes(body.take(300))
          : body?.toString();
      debugPrint('TTS prefetch failed: HTTP $status — $detail');
      return; // don't hand a broken URL to the media element
    } catch (e) {
      debugPrint('TTS prefetch failed: $e');
      return;
    }
    if (my != _seq) return; // a newer card already requested speech

    // 2. Play — served from the warm server cache.
    final token = await _tokens.accessToken;
    if (token == null || my != _seq) return;
    try {
      _currentRate = rate.clamp(0.5, 1.5);
      await _player.setVolume(volume.clamp(0.0, 1.0));
      if (my != _seq) return;
      await _player.play(UrlSource('$baseUrl/tts/$itemId?token=$token'));
      // Applied again by the onPlayerStateChanged listener once actually
      // playing; this immediate call covers native platforms.
      await _player.setPlaybackRate(_currentRate);
    } catch (e) {
      debugPrint('TTS playback failed: $e');
    }
  }

  Future<void> stop() async {
    _seq++;
    await _player.stop();
  }
}
