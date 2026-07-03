import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:vocab_app/main.dart';

void main() {
  testWidgets('App khởi động không crash', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: VocabApp()));
    await tester.pump();
    // Splash hiển thị trong lúc bootstrap auth.
    expect(find.text('📚'), findsOneWidget);
  });
}
