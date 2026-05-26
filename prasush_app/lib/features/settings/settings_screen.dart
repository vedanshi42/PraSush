import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/theme/app_theme.dart';
import '../../core/api/api_service.dart';
import '../auth/auth_provider.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final TextEditingController _urlController = TextEditingController();
  bool _testingConnection = false;
  bool? _isConnected;

  @override
  void initState() {
    super.initState();
    _loadCurrentUrl();
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _loadCurrentUrl() async {
    final apiService = ref.read(apiServiceProvider);
    final url = await apiService.getBaseUrl();
    setState(() {
      _urlController.text = url;
    });
    _testConnection();
  }

  Future<void> _testConnection() async {
    setState(() {
      _testingConnection = true;
      _isConnected = null;
    });
    final apiService = ref.read(apiServiceProvider);
    final online = await apiService.checkConnection();
    if (mounted) {
      setState(() {
        _isConnected = online;
        _testingConnection = false;
      });
    }
  }

  Future<void> _saveUrl() async {
    final apiService = ref.read(apiServiceProvider);
    final newUrl = _urlController.text.trim();
    if (newUrl.isNotEmpty) {
      await apiService.setBaseUrl(newUrl);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Backend URL saved successfully!')),
      );
      _testConnection();
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new_rounded, color: isDark ? Colors.white : AppTheme.deepSlate),
          onPressed: () => context.pop(),
        ),
        title: Text(
          'Settings',
          style: GoogleFonts.outfit(
            fontWeight: FontWeight.bold,
            color: isDark ? Colors.white : AppTheme.deepSlate,
          ),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 8.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // User profile details card
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: isDark ? AppTheme.darkCard : Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: isDark ? Colors.white.withValues(alpha: 0.04) : AppTheme.sagePrimary.withValues(alpha: 0.08),
                    width: 1.5,
                  ),
                ),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 30,
                      backgroundColor: AppTheme.sagePrimary.withValues(alpha: 0.12),
                      child: Text(
                        authState.userName != null && authState.userName!.isNotEmpty
                            ? authState.userName![0].toUpperCase()
                            : 'P',
                        style: GoogleFonts.outfit(
                          color: AppTheme.sagePrimary,
                          fontWeight: FontWeight.bold,
                          fontSize: 24,
                        ),
                      ),
                    ),
                    const SizedBox(width: 20),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            authState.userName ?? 'Friend',
                            style: GoogleFonts.outfit(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: isDark ? Colors.white : AppTheme.deepSlate,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            authState.userEmail ?? 'No email associated',
                            style: GoogleFonts.inter(
                              fontSize: 13,
                              color: isDark ? Colors.white38 : Colors.black45,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: authState.isSandboxMode
                                  ? AppTheme.warningOrange.withValues(alpha: 0.1)
                                  : AppTheme.sagePrimary.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              authState.isSandboxMode ? 'Sandbox User' : 'Google Persistent Session',
                              style: GoogleFonts.inter(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: authState.isSandboxMode ? AppTheme.warningOrange : AppTheme.sagePrimary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),

              Text(
                'Server Configuration',
                style: GoogleFonts.outfit(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : AppTheme.deepSlate,
                ),
              ),
              const SizedBox(height: 12),

              // Backend IP Input Panel
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: isDark ? AppTheme.darkCard : Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: isDark ? Colors.white.withValues(alpha: 0.04) : AppTheme.sagePrimary.withValues(alpha: 0.08),
                    width: 1.5,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Uvicorn Backend URL',
                      style: GoogleFonts.outfit(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: isDark ? Colors.white70 : AppTheme.deepSlate.withValues(alpha: 0.8),
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _urlController,
                      style: GoogleFonts.inter(fontSize: 14),
                      decoration: const InputDecoration(
                        hintText: 'e.g. http://192.168.1.100:8000',
                        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        ElevatedButton(
                          onPressed: _saveUrl,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.sagePrimary,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          child: const Text('Save & Apply'),
                        ),
                        OutlinedButton.icon(
                          onPressed: _testingConnection ? null : _testConnection,
                          style: OutlinedButton.styleFrom(
                            foregroundColor: AppTheme.sagePrimary,
                            side: const BorderSide(color: AppTheme.sagePrimary),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          icon: _testingConnection
                              ? const SizedBox(
                                  width: 12,
                                  height: 12,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.sagePrimary),
                                )
                              : const Icon(Icons.flash_on_rounded, size: 14),
                          label: const Text('Test Connection'),
                        ),
                      ],
                    ),
                    if (_isConnected != null) ...[
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: _isConnected! ? Colors.green : AppTheme.errorRed,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            _isConnected!
                                ? 'Connected to PraSush Uvicorn server!'
                                : 'Connection failed. App will run in Offline Sandbox Mode.',
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              color: _isConnected! ? Colors.green : AppTheme.errorRed,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 32),

              Text(
                'Aesthetics & Pacing',
                style: GoogleFonts.outfit(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : AppTheme.deepSlate,
                ),
              ),
              const SizedBox(height: 12),

              Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                decoration: BoxDecoration(
                  color: isDark ? AppTheme.darkCard : Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: isDark ? Colors.white.withValues(alpha: 0.04) : AppTheme.sagePrimary.withValues(alpha: 0.08),
                    width: 1.5,
                  ),
                ),
                child: Column(
                  children: [
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.translate_rounded, color: AppTheme.sagePrimary),
                      title: const Text('Primary Language'),
                      trailing: DropdownButton<String>(
                        value: 'English (US)',
                        items: ['English (US)', 'Hindi (हिंदी)', 'Hinglish'].map((lang) {
                          return DropdownMenuItem<String>(
                            value: lang,
                            child: Text(lang, style: GoogleFonts.inter(fontSize: 14)),
                          );
                        }).toList(),
                        onChanged: (_) {},
                      ),
                    ),
                    const Divider(height: 1),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.speed_rounded, color: AppTheme.sagePrimary),
                      title: const Text('Voice Speech Pacing'),
                      subtitle: const Text('Calm and comfortable for elderly users'),
                      trailing: SizedBox(
                        width: 100,
                        child: Slider(
                          value: 0.5,
                          min: 0.3,
                          max: 0.8,
                          activeColor: AppTheme.sagePrimary,
                          inactiveColor: AppTheme.sagePrimary.withValues(alpha: 0.12),
                          onChanged: (_) {},
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 40),

              // Logout Button
              SizedBox(
                width: double.infinity,
                height: 58,
                child: ElevatedButton.icon(
                  onPressed: () async {
                    await ref.read(authProvider.notifier).signOut();
                    if (!context.mounted) return;
                    context.go('/login');
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.errorRed.withValues(alpha: 0.1),
                    foregroundColor: AppTheme.errorRed,
                    elevation: 0,
                    side: const BorderSide(color: AppTheme.errorRed, width: 1.5),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  ),
                  icon: const Icon(Icons.logout_rounded, size: 20),
                  label: Text(
                    'Log Out Session',
                    style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                ),
              ),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }
}
