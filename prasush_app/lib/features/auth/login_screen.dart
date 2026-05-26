import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/theme/app_theme.dart';
import 'auth_provider.dart';

class LoginScreen extends ConsumerWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    ref.listen<AuthState>(authProvider, (previous, next) {
      if (next.isAuthenticated) {
        context.go('/home');
      }
    });

    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: isDark
                ? [AppTheme.darkBackground, const Color(0xFF1E2E25)]
                : [AppTheme.creamBackground, const Color(0xFFEDF2EE)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            physics: const BouncingScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 28.0, vertical: 24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const SizedBox(height: 32),

                // Logo icon
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isDark ? AppTheme.darkCard : Colors.white,
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.sagePrimary.withValues(alpha: 0.12),
                        blurRadius: 24,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.assistant_navigation,
                    size: 52,
                    color: AppTheme.sagePrimary,
                  ),
                ),
                const SizedBox(height: 24),

                // Title
                Text(
                  'Welcome to PraSush',
                  style: GoogleFonts.outfit(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: isDark ? Colors.white : AppTheme.deepSlate,
                  ),
                ),
                const SizedBox(height: 12),

                // Tagline
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12.0),
                  child: Text(
                    'An AI that helps you feel less helpless\nin everyday real-world situations.',
                    textAlign: TextAlign.center,
                    style: GoogleFonts.inter(
                      fontSize: 15,
                      height: 1.55,
                      fontWeight: FontWeight.w400,
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.65)
                          : AppTheme.deepSlate.withValues(alpha: 0.65),
                    ),
                  ),
                ),
                const SizedBox(height: 36),

                // Feature cards
                _buildFeatureItem(
                  context,
                  icon: Icons.plumbing_rounded,
                  title: 'Everyday Repairs & Hazards',
                  subtitle: 'Step-by-step visuals and professional routing.',
                ),
                const SizedBox(height: 14),
                _buildFeatureItem(
                  context,
                  icon: Icons.soup_kitchen_rounded,
                  title: 'Interactive Kitchen Aid',
                  subtitle: 'Culinary rescue tips and safe baking instructions.',
                ),
                const SizedBox(height: 14),
                _buildFeatureItem(
                  context,
                  icon: Icons.psychology_alt_rounded,
                  title: 'Warm & Bilingual Guidance',
                  subtitle: 'Chat naturally in English, Hindi, or Hinglish.',
                ),
                const SizedBox(height: 40),

                // Error message
                if (authState.errorMessage != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16.0),
                    child: Text(
                      authState.errorMessage!,
                      textAlign: TextAlign.center,
                      style: GoogleFonts.inter(color: AppTheme.errorRed, fontSize: 13),
                    ),
                  ),

                // Google Sign-In button
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton(
                    onPressed: authState.isLoading
                        ? null
                        : () => ref.read(authProvider.notifier).signInWithGoogle(),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: AppTheme.deepSlate,
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                        side: BorderSide(
                          color: AppTheme.sagePrimary.withValues(alpha: 0.2),
                          width: 1.5,
                        ),
                      ),
                    ),
                    child: authState.isLoading
                        ? const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(strokeWidth: 2.5),
                          )
                        : Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.login_rounded,
                                color: AppTheme.sagePrimary.withValues(alpha: 0.8),
                                size: 22,
                              ),
                              const SizedBox(width: 14),
                              Text(
                                'Sign In with Google',
                                style: GoogleFonts.outfit(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                  ),
                ),
                const SizedBox(height: 14),

                // Sandbox Demo Mode button
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: OutlinedButton(
                    onPressed: authState.isLoading
                        ? null
                        : () => ref.read(authProvider.notifier).signInAsSandboxUser(
                              name: 'Vedanshi Dixit',
                              email: 'vedanshi.d@prasush.com',
                            ),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.sagePrimary,
                      side: BorderSide(
                        color: AppTheme.sagePrimary.withValues(alpha: 0.4),
                        width: 1.5,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.explore_rounded, size: 20),
                        const SizedBox(width: 12),
                        Text(
                          'Try Sandbox Demo Mode',
                          style: GoogleFonts.outfit(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),

                Text(
                  'No Firebase setup? Tap Sandbox Mode to preview instantly.',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 11,
                    color: isDark ? Colors.white38 : Colors.black38,
                  ),
                ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFeatureItem(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isDark
              ? Colors.white.withValues(alpha: 0.04)
              : AppTheme.sagePrimary.withValues(alpha: 0.08),
          width: 1.5,
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppTheme.sagePrimary.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: AppTheme.sagePrimary, size: 22),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.outfit(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: isDark ? Colors.white : AppTheme.deepSlate,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  subtitle,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: isDark ? Colors.white38 : Colors.black45,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
