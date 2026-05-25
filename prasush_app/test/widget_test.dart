import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:prasush_app/main.dart';

void main() {
  testWidgets('PraSush app smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: PraSushApp(),
      ),
    );
    // Just verify the app renders without crashing
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
