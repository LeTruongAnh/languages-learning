import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/router.dart';
import 'app/theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Fire-and-forget: CJK font is usually ready before the first study card;
  // if not, Flutter re-renders automatically when it finishes loading.
  preloadCjkFonts();
  runApp(const ProviderScope(child: VocabApp()));
}

class VocabApp extends ConsumerWidget {
  const VocabApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'Vocab',
      theme: buildAppTheme(),
      routerConfig: ref.watch(routerProvider),
      debugShowCheckedModeBanner: false,
    );
  }
}
