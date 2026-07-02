import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Design tokens — must match design/mobile_mockup.html and PLAN.md §4.1.
abstract final class AppColors {
  static const bg = Color(0xFFF7F8FA);
  static const surface = Colors.white;
  static const text = Color(0xFF1A1D26);
  static const textSub = Color(0xFF6B7280);
  static const border = Color(0xFFE5E7EB);

  // Language accents (spec §5.2)
  static const chinese = Color(0xFFE0533D);
  static const english = Color(0xFF2563EB);
  static const hardItems = Color(0xFFF59E0B);
  static const review = Color(0xFF8B5CF6);

  // Result actions
  static const pass = Color(0xFF16A34A);
  static const fail = Color(0xFFDC2626);
  static const skip = Color(0xFF9CA3AF);

  /// Accent per language code; backend can also send accent_color.
  static Color forLanguage(String code) => switch (code) {
        'zh' => chinese,
        'en' => english,
        _ => review,
      };
}

abstract final class AppDimens {
  static const radius = 16.0;
  static const minTapTarget = 48.0; // accessibility floor
  static const resultButtonHeight = 56.0;
  static const screenPadding = 20.0;
}

/// CJK font fallback. On Flutter web the default fonts lack CJK glyphs, so
/// Chinese briefly renders as tofu squares (□) until canvaskit lazy-loads a
/// fallback. Preloading Noto Sans SC at startup removes that flash; Flutter
/// re-renders text automatically once the font finishes loading.
List<String> _cjkFallback = [];

Future<void> preloadCjkFonts() async {
  final noto = GoogleFonts.notoSansSc();
  _cjkFallback = [if (noto.fontFamily != null) noto.fontFamily!];
  await GoogleFonts.pendingFonts([noto]);
}

ThemeData buildAppTheme() {
  final base = ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: AppColors.bg,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.english,
      surface: AppColors.surface,
    ),
  );
  return base.copyWith(
    textTheme: base.textTheme.apply(
      bodyColor: AppColors.text,
      displayColor: AppColors.text,
      fontFamilyFallback: _cjkFallback,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(AppDimens.minTapTarget),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
      ),
    ),
  );
}

/// Typography for the study card (spec §5.5): big main text, smaller pinyin.
/// Not const: fontFamilyFallback is resolved after the CJK font registers.
abstract final class StudyTextStyles {
  static TextStyle get mainText => TextStyle(
      fontSize: 48,
      fontWeight: FontWeight.w800,
      height: 1.2,
      fontFamilyFallback: _cjkFallback);
  static TextStyle get sentenceText => TextStyle(
      fontSize: 28,
      fontWeight: FontWeight.w800,
      height: 1.35,
      fontFamilyFallback: _cjkFallback);
  static TextStyle get pronunciation =>
      const TextStyle(fontSize: 20, color: AppColors.textSub);
  static TextStyle get meaning =>
      const TextStyle(fontSize: 20, fontWeight: FontWeight.w700);
}
