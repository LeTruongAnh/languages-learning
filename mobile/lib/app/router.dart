import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/models/models.dart';
import '../features/auth/presentation/auth_controller.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/dashboard/presentation/dashboard_screen.dart';
import '../features/hard_items/presentation/hard_items_screen.dart';
import '../features/home/presentation/home_screen.dart';
import '../features/settings/presentation/language_advanced_screen.dart';
import '../features/settings/presentation/settings_screen.dart';
import '../features/study/presentation/study_controller.dart';
import '../features/study/presentation/study_screen.dart';

/// Router with auth guard: unauthenticated users always land on /login;
/// authenticated users are pushed away from /login and /splash.
final routerProvider = Provider<GoRouter>((ref) {
  final authListenable = ValueNotifier<AuthStatus>(AuthStatus.unknown);
  ref.listen<AuthStatus>(
    authControllerProvider,
    (_, next) => authListenable.value = next,
    fireImmediately: true,
  );

  final router = GoRouter(
    initialLocation: '/splash',
    refreshListenable: authListenable,
    redirect: (context, state) {
      final status = authListenable.value;
      final location = state.matchedLocation;
      if (status == AuthStatus.unknown) {
        return location == '/splash' ? null : '/splash';
      }
      if (status == AuthStatus.unauthenticated) {
        return location == '/login' ? null : '/login';
      }
      if (location == '/login' || location == '/splash') return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const _SplashScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
      GoRoute(
        path: '/study',
        builder: (_, state) => StudyScreen(launch: state.extra! as StudyLaunch),
      ),
      GoRoute(path: '/dashboard', builder: (_, __) => const DashboardScreen()),
      GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
      GoRoute(
        path: '/settings/language-advanced',
        builder: (_, state) =>
            LanguageAdvancedScreen(language: state.extra! as Language),
      ),
      GoRoute(path: '/hard-items', builder: (_, __) => const HardItemsScreen()),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
});

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: Text('📚', style: TextStyle(fontSize: 56))),
    );
  }
}
