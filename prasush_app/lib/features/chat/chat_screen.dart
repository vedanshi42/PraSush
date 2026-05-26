import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'dart:math' as math;

import '../../core/theme/app_theme.dart';
import '../../core/api/api_service.dart';
import '../../core/voice/voice_service.dart';
import '../auth/auth_provider.dart';
import '../camera/camera_screen.dart';

class ChatScreen extends ConsumerStatefulWidget {
  final String mode;
  final String? imagePath;

  const ChatScreen({
    super.key,
    required this.mode,
    this.imagePath,
  });

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  late String _sessionId;
  bool _isLoading = false;
  GuidanceResponse? _guidance;
  String _liveSubtitle = 'Standing by for your guidance...';
  List<bool> _checkedSteps = [];

  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _sessionId = 'session_${DateTime.now().millisecondsSinceEpoch}';

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final base64Image = getCapturedImageBase64();
      if (base64Image != null) {
        _sendInitialVisualQuery(base64Image);
      } else {
        _sendTextMessage('Hello! Please help me understand what we are doing.',
            autoGreeting: true);
      }
    });
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _textController.dispose();
    _scrollController.dispose();
    clearCapturedImage();
    super.dispose();
  }

  Future<void> _sendInitialVisualQuery(String base64) async {
    setState(() {
      _isLoading = true;
      _liveSubtitle = 'Sending captured image to visual models...';
    });

    final apiService = ref.read(apiServiceProvider);
    final voiceService = ref.read(voiceServiceProvider);
    final authState = ref.read(authProvider);

    final String initialQuery = widget.mode == 'repair'
        ? 'Analyze this appliance or hazard and tell me what the issue is.'
        : 'Describe this object in detail and explain its function.';

    try {
      final response = await apiService.sendChatRequest(
        sessionId: _sessionId,
        query: initialQuery,
        imageBase64: base64,
        userName: authState.userName,
        mode: widget.mode,
      );

      setState(() {
        _guidance = response;
        _checkedSteps = List<bool>.filled(response.nextSteps.length, false);
        _isLoading = false;
        _liveSubtitle = response.probableIssue;
      });

      voiceService.speak(response.spokenResponse);
    } catch (e) {
      _handleError(e);
    }
  }

  Future<void> _sendTextMessage(String text,
      {bool autoGreeting = false}) async {
    if (text.trim().isEmpty) return;

    _textController.clear();
    setState(() {
      _isLoading = true;
      _liveSubtitle = 'PraSush is analyzing your request...';
    });

    final apiService = ref.read(apiServiceProvider);
    final voiceService = ref.read(voiceServiceProvider);
    final authState = ref.read(authProvider);

    try {
      final response = await apiService.sendChatRequest(
        sessionId: _sessionId,
        query: text,
        userName: authState.userName,
        mode: widget.mode,
      );

      setState(() {
        _guidance = response;
        _checkedSteps = List<bool>.filled(response.nextSteps.length, false);
        _isLoading = false;
        _liveSubtitle = response.probableIssue;
      });

      if (!autoGreeting) {
        voiceService.speak(response.spokenResponse);
      }
    } catch (e) {
      _handleError(e);
    }
  }

  void _handleError(dynamic e) {
    setState(() {
      _isLoading = false;
      _liveSubtitle = 'Connection error. Playing offline backup.';
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Failed to connect to backend: $e')),
    );
  }

  Future<void> _triggerVoiceInput() async {
    final voiceService = ref.read(voiceServiceProvider);
    if (voiceService.isListening) {
      await voiceService.stopListening();
    } else {
      await voiceService.stopSpeaking();
      await voiceService.startListening((transcription) {
        setState(() {
          _liveSubtitle = transcription;
          _textController.text = transcription;
        });
      });
    }
  }

  Future<void> _clearConversation() async {
    final apiService = ref.read(apiServiceProvider);
    final voiceService = ref.read(voiceServiceProvider);
    await voiceService.stopSpeaking();
    await apiService.clearMemory(_sessionId);
    clearCapturedImage();
    setState(() {
      _guidance = null;
      _checkedSteps = [];
      _liveSubtitle = 'Conversation cleared. Standing by...';
    });
  }

  String _getModeTitle() {
    switch (widget.mode) {
      case 'repair':
        return 'Repair Help';
      case 'cook':
        return 'Cooking Guide';
      case 'learn':
        return 'Visual Learning';
      default:
        return 'Ask PraSush';
    }
  }

  @override
  Widget build(BuildContext context) {
    final voiceService = ref.watch(voiceServiceProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final base64Image = getCapturedImageBase64();

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new_rounded,
              color: isDark ? Colors.white : AppTheme.deepSlate),
          onPressed: () {
            voiceService.stopSpeaking();
            context.pop();
          },
        ),
        title: Text(
          _getModeTitle(),
          style: GoogleFonts.outfit(
            fontWeight: FontWeight.bold,
            color: isDark ? Colors.white : AppTheme.deepSlate,
          ),
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.delete_sweep_rounded,
                color: AppTheme.sagePrimary.withValues(alpha: 0.8)),
            tooltip: 'Clear Context',
            onPressed: _clearConversation,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Live Subtitle Bar
            Container(
              width: double.infinity,
              margin:
                  const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              decoration: BoxDecoration(
                color: isDark ? AppTheme.darkCard : Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: AppTheme.sagePrimary.withValues(alpha: 0.12),
                  width: 1.5,
                ),
              ),
              child: Row(
                children: [
                  ScaleTransition(
                    scale: _isLoading
                        ? _pulseController
                        : const AlwaysStoppedAnimation(1.0),
                    child: Container(
                      width: 12,
                      height: 12,
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppTheme.sagePrimary,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      _liveSubtitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.7)
                            : AppTheme.deepSlate.withValues(alpha: 0.8),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Scrollable Guidance Area
            Expanded(
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                controller: _scrollController,
                padding: const EdgeInsets.symmetric(
                    horizontal: 24.0, vertical: 8.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Captured image preview
                    if (base64Image != null) ...[
                      Center(
                        child: Container(
                          width: double.infinity,
                          height: 190,
                          margin: const EdgeInsets.only(bottom: 24),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(28),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.08),
                                blurRadius: 15,
                                offset: const Offset(0, 6),
                              ),
                            ],
                            border: Border.all(
                              color:
                                  AppTheme.sagePrimary.withValues(alpha: 0.15),
                              width: 2,
                            ),
                          ),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(26),
                            child: Image.memory(
                              base64Decode(base64Image),
                              fit: BoxFit.cover,
                            ),
                          ),
                        ),
                      ),
                    ],

                    // Loading state
                    if (_isLoading && _guidance == null) ...[
                      Center(
                        child: Column(
                          children: [
                            const SizedBox(height: 50),
                            ScaleTransition(
                              scale: _pulseController,
                              child: Container(
                                width: 72,
                                height: 72,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: AppTheme.sagePrimary
                                      .withValues(alpha: 0.1),
                                ),
                                child: const Icon(Icons.psychology_rounded,
                                    size: 36, color: AppTheme.sagePrimary),
                              ),
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'PraSush is thinking...',
                              style: GoogleFonts.outfit(
                                fontSize: 16,
                                color: isDark
                                    ? Colors.white.withValues(alpha: 0.6)
                                    : Colors.black.withValues(alpha: 0.54),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ] else if (_guidance != null) ...[
                      // Probable Issue Badge
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 8),
                        decoration: BoxDecoration(
                          color:
                              AppTheme.sagePrimary.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(30),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.info_outline_rounded,
                                size: 16, color: AppTheme.sagePrimary),
                            const SizedBox(width: 8),
                            Flexible(
                              child: Text(
                                _guidance!.probableIssue,
                                style: GoogleFonts.outfit(
                                  fontSize: 13,
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.sagePrimary,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Safety Warning Card
                      if (_guidance!.isDangerous) ...[
                        _buildSafetyWarningCard(context,
                            _guidance!.safetyWarning ?? 'Safety Hazard Detected.'),
                        const SizedBox(height: 20),
                      ],

                      // Explanation Card
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: isDark ? AppTheme.darkCard : Colors.white,
                          borderRadius: BorderRadius.circular(24),
                          border: Border.all(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.04)
                                : AppTheme.sagePrimary.withValues(alpha: 0.06),
                            width: 1.5,
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(
                                    Icons.chat_bubble_outline_rounded,
                                    color: AppTheme.sagePrimary,
                                    size: 20),
                                const SizedBox(width: 10),
                                Text(
                                  'PraSush Advice',
                                  style: GoogleFonts.outfit(
                                    fontSize: 15,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.sagePrimary,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 14),
                            Text(
                              _guidance!.explanation,
                              style: GoogleFonts.inter(
                                fontSize: 15,
                                height: 1.55,
                                color: isDark
                                    ? Colors.white.withValues(alpha: 0.9)
                                    : AppTheme.deepSlate.withValues(alpha: 0.9),
                              ),
                            ),
                            const SizedBox(height: 16),
                            Align(
                              alignment: Alignment.bottomRight,
                              child: TextButton.icon(
                                style: TextButton.styleFrom(
                                  foregroundColor: AppTheme.sagePrimary,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                ),
                                icon: Icon(
                                  voiceService.isSpeaking
                                      ? Icons.volume_up_rounded
                                      : Icons.volume_mute_rounded,
                                  size: 18,
                                ),
                                label: Text(
                                  voiceService.isSpeaking
                                      ? 'Speaking...'
                                      : 'Listen',
                                  style: GoogleFonts.outfit(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 13),
                                ),
                                onPressed: () {
                                  if (voiceService.isSpeaking) {
                                    voiceService.stopSpeaking();
                                  } else {
                                    voiceService.speak(
                                        _guidance!.spokenResponse);
                                  }
                                },
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Step-by-Step Checklist
                      if (_guidance!.nextSteps.isNotEmpty) ...[
                        Text(
                          'Step-by-Step Instructions',
                          style: GoogleFonts.outfit(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: isDark ? Colors.white : AppTheme.deepSlate,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Container(
                          decoration: BoxDecoration(
                            color: isDark ? AppTheme.darkCard : Colors.white,
                            borderRadius: BorderRadius.circular(24),
                            border: Border.all(
                              color: isDark
                                  ? Colors.white.withValues(alpha: 0.04)
                                  : AppTheme.sagePrimary
                                      .withValues(alpha: 0.06),
                              width: 1.5,
                            ),
                          ),
                          child: ListView.separated(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: _guidance!.nextSteps.length,
                            separatorBuilder: (context, index) => Divider(
                              color: isDark
                                  ? Colors.white.withValues(alpha: 0.1)
                                  : Colors.black.withValues(alpha: 0.04),
                              height: 1,
                            ),
                            itemBuilder: (context, index) {
                              final isChecked = _checkedSteps[index];
                              return CheckboxListTile(
                                activeColor: AppTheme.sagePrimary,
                                checkboxShape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                contentPadding: const EdgeInsets.symmetric(
                                    horizontal: 20, vertical: 8),
                                title: Text(
                                  _guidance!.nextSteps[index],
                                  style: GoogleFonts.inter(
                                    fontSize: 14,
                                    decoration: isChecked
                                        ? TextDecoration.lineThrough
                                        : null,
                                    color: isChecked
                                        ? Colors.grey
                                        : (isDark
                                            ? Colors.white.withValues(alpha: 0.9)
                                            : AppTheme.deepSlate),
                                    height: 1.4,
                                  ),
                                ),
                                value: isChecked,
                                onChanged: (value) {
                                  setState(() {
                                    _checkedSteps[index] = value ?? false;
                                  });
                                },
                              );
                            },
                          ),
                        ),
                      ],
                    ],
                  ],
                ),
              ),
            ),

            // Voice wave visualizer
            if (voiceService.isListening) ...[
              Container(
                height: 48,
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(
                    12,
                    (index) => AnimatedBuilder(
                      animation: _pulseController,
                      builder: (context, child) {
                        final height = (index % 3 + 1) *
                            8.0 *
                            (1.0 +
                                0.5 *
                                    math.sin(_pulseController.value *
                                        2 *
                                        math.pi +
                                        index));
                        return Container(
                          width: 4,
                          height: height.clamp(8.0, 32.0),
                          margin:
                              const EdgeInsets.symmetric(horizontal: 3),
                          decoration: BoxDecoration(
                            color: AppTheme.sagePrimary
                                .withValues(alpha: 0.7),
                            borderRadius: BorderRadius.circular(4),
                          ),
                        );
                      },
                    ),
                  ),
                ),
              ),
            ],

            // Input bar
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: isDark ? AppTheme.darkCard : Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 10,
                    offset: const Offset(0, -4),
                  ),
                ],
              ),
              child: Row(
                children: [
                  IconButton(
                    icon: AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: voiceService.isListening
                            ? AppTheme.errorRed.withValues(alpha: 0.12)
                            : AppTheme.sagePrimary.withValues(alpha: 0.08),
                        border: Border.all(
                          color: voiceService.isListening
                              ? AppTheme.errorRed
                              : Colors.transparent,
                          width: 1.5,
                        ),
                      ),
                      child: Icon(
                        voiceService.isListening
                            ? Icons.mic_off_rounded
                            : Icons.mic_rounded,
                        color: voiceService.isListening
                            ? AppTheme.errorRed
                            : AppTheme.sagePrimary,
                      ),
                    ),
                    onPressed: _triggerVoiceInput,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      style: GoogleFonts.inter(fontSize: 14),
                      decoration: InputDecoration(
                        hintText: voiceService.isListening
                            ? 'Listening...'
                            : 'Ask PraSush anything...',
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 12),
                      ),
                      onSubmitted: _sendTextMessage,
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppTheme.sagePrimary,
                      ),
                      child: const Icon(Icons.send_rounded,
                          color: Colors.white, size: 20),
                    ),
                    onPressed: () => _sendTextMessage(_textController.text),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSafetyWarningCard(BuildContext context, String warningText) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.errorRed.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: AppTheme.errorRed.withValues(alpha: 0.3),
          width: 2,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.warning_amber_rounded,
                  color: AppTheme.errorRed, size: 24),
              const SizedBox(width: 12),
              Text(
                'Safety Warning',
                style: GoogleFonts.outfit(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.errorRed,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            warningText,
            style: GoogleFonts.inter(
              fontSize: 14,
              height: 1.45,
              fontWeight: FontWeight.w600,
              color: AppTheme.errorRed,
            ),
          ),
        ],
      ),
    );
  }
}
