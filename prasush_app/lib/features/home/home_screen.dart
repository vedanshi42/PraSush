import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/theme/app_theme.dart';
import '../../core/api/api_service.dart';
import '../auth/auth_provider.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  bool _isBackendOnline = false;
  bool _checkingStatus = true;

  @override
  void initState() {
    super.initState();
    _checkBackendStatus();
  }

  Future<void> _checkBackendStatus() async {
    setState(() {
      _checkingStatus = true;
    });
    final apiService = ref.read(apiServiceProvider);
    final online = await apiService.checkConnection();
    if (mounted) {
      setState(() {
        _isBackendOnline = online;
        _checkingStatus = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header Row
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        CircleAvatar(
                          radius: 24,
                          backgroundColor: AppTheme.sagePrimary.withValues(alpha: 0.12),
                          child: Text(
                            authState.userName != null && authState.userName!.isNotEmpty
                                ? authState.userName![0].toUpperCase()
                                : 'P',
                            style: GoogleFonts.outfit(
                              color: AppTheme.sagePrimary,
                              fontWeight: FontWeight.bold,
                              fontSize: 18,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Hello, ${authState.userName ?? "Friend"}',
                              style: GoogleFonts.outfit(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: isDark ? Colors.white : AppTheme.deepSlate,
                              ),
                            ),
                            const SizedBox(height: 2),
                            // Backend Status indicator
                            GestureDetector(
                              onTap: _checkBackendStatus,
                              child: Row(
                                children: [
                                  Container(
                                    width: 8,
                                    height: 8,
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: _checkingStatus
                                          ? Colors.grey
                                          : (_isBackendOnline ? Colors.green : AppTheme.warningOrange),
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    _checkingStatus
                                        ? 'Checking Server...'
                                        : (_isBackendOnline ? 'PraSush Active' : 'Offline Mode (Sandbox)'),
                                    style: GoogleFonts.inter(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w500,
                                      color: isDark ? Colors.white54 : Colors.black45,
                                    ),
                                  ),
                                  const SizedBox(width: 4),
                                  const Icon(Icons.refresh, size: 10, color: Colors.grey),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    IconButton(
                      icon: Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: isDark ? AppTheme.darkCard : Colors.white,
                          border: Border.all(
                            color: AppTheme.sagePrimary.withValues(alpha: 0.08),
                            width: 1.5,
                          ),
                        ),
                        child: const Icon(Icons.settings_rounded, size: 20, color: AppTheme.sagePrimary),
                      ),
                      onPressed: () => context.push('/settings'),
                    ),
                  ],
                ),
                const SizedBox(height: 32),

                // Greeting Pitch card
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: isDark
                          ? [AppTheme.sagePrimary.withValues(alpha: 0.2), const Color(0xFF23352A)]
                          : [AppTheme.sageLight, const Color(0xFFD6E3D8)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(28),
                    border: Border.all(
                      color: AppTheme.sagePrimary.withValues(alpha: 0.15),
                      width: 1.5,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'How can I guide you today?',
                        style: GoogleFonts.outfit(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : AppTheme.deepSlate,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Select an option below to open camera visual analysis, or start asking questions in warm English, Hindi or Hinglish.',
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          height: 1.4,
                          color: isDark ? Colors.white70 : AppTheme.deepSlate.withValues(alpha: 0.7),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 32),

                Text(
                  'Core Capabilities',
                  style: GoogleFonts.outfit(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: isDark ? Colors.white : AppTheme.deepSlate,
                  ),
                ),
                const SizedBox(height: 16),

                // Grid Layout for Modern cards
                GridView.count(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisCount: 2,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  childAspectRatio: 0.9,
                  children: [
                    _buildFeatureCard(
                      context,
                      title: 'Repair Help',
                      subtitle: 'Troubleshoot and fix home appliances safely.',
                      icon: Icons.plumbing_rounded,
                      gradient: AppTheme.sageGradient,
                      onTap: () => context.push('/camera?mode=repair'),
                    ),
                    _buildFeatureCard(
                      context,
                      title: 'Cooking Guide',
                      subtitle: 'Rescue salty foods, baking steps & recipes.',
                      icon: Icons.outdoor_grill_rounded,
                      gradient: AppTheme.amberGradient,
                      onTap: () => context.push('/chat?mode=cook'),
                    ),
                    _buildFeatureCard(
                      context,
                      title: 'Ask PraSush',
                      subtitle: 'General conversations, memory and reminders.',
                      icon: Icons.forum_rounded,
                      color: isDark ? AppTheme.darkCard : Colors.white,
                      textColor: isDark ? Colors.white : AppTheme.deepSlate,
                      onTap: () => context.push('/chat?mode=ask'),
                    ),
                    _buildFeatureCard(
                      context,
                      title: 'Learn Visually',
                      subtitle: 'Scan objects, plants or tools to understand them.',
                      icon: Icons.visibility_rounded,
                      color: isDark ? AppTheme.darkCard : Colors.white,
                      textColor: isDark ? Colors.white : AppTheme.deepSlate,
                      onTap: () => context.push('/camera?mode=learn'),
                    ),
                  ],
                ),
                const SizedBox(height: 32),

                // Support footer
                Center(
                  child: Column(
                    children: [
                      const Icon(Icons.shield_outlined, size: 20, color: Colors.grey),
                      const SizedBox(height: 8),
                      Text(
                        'AI recommendations do not replace licensed professionals.',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          color: Colors.grey,
                        ),
                      ),
                      Text(
                        'Safety remains our absolute top priority.',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.sagePrimary.withValues(alpha: 0.7),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFeatureCard(
    BuildContext context, {
    required String title,
    required String subtitle,
    required IconData icon,
    LinearGradient? gradient,
    Color? color,
    Color textColor = Colors.white,
    required VoidCallback onTap,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: color,
          gradient: gradient,
          borderRadius: BorderRadius.circular(24),
          border: gradient != null
              ? null
              : Border.all(
                  color: isDark ? Colors.white.withValues(alpha: 0.04) : AppTheme.sagePrimary.withValues(alpha: 0.08),
                  width: 1.5,
                ),
          boxShadow: [
            BoxShadow(
              color: AppTheme.sagePrimary.withValues(alpha: 0.04),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: gradient != null ? Colors.white.withValues(alpha: 0.2) : AppTheme.sagePrimary.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: Icon(
                icon,
                color: gradient != null ? Colors.white : AppTheme.sagePrimary,
                size: 26,
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.outfit(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: textColor,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  subtitle,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.inter(
                    fontSize: 11,
                    height: 1.3,
                    color: gradient != null ? Colors.white70 : (isDark ? Colors.white38 : Colors.black54),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
