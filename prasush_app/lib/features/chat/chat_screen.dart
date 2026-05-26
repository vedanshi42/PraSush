import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'dart:math' as math;

import '../../core/theme/app_theme.dart';
import '../../core/api/api_service.dart';
import '../../core/voice/voice_service.dart';
import '../auth/auth_provider.dart';
import '../camera/camera_screen.dart';

// ---------------------------------------------------------------------------
// Data model for a single chat message (user or AI)
// ---------------------------------------------------------------------------
class ChatMessage {
  final String? text;
  final String? imageBase64;
  final bool isUser;
  final GuidanceResponse? response;
  final DateTime timestamp;

  ChatMessage({
    this.text,
    this.imageBase64,
    required this.isUser,
    this.response,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
}

// ---------------------------------------------------------------------------
// Screen widget
// ---------------------------------------------------------------------------
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
  final List<ChatMessage> _messages = [];
  String? _attachedImageBase64;

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
      final pendingCaption = getCapturedImageCaption();

      if (base64Image != null) {
        // Image was attached — user bubble already shown from camera; send immediately
        final caption = pendingCaption?.isNotEmpty == true
            ? pendingCaption!
            : _defaultQueryForMode();
        _sendMessage(caption, imageBase64: base64Image, showUserBubble: true);
      } else {
        // Pure text mode — greet silently
        _sendMessage(
          'Hello! What would you like help with today?',
          showUserBubble: false,
          autoGreeting: true,
        );
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

  String _defaultQueryForMode() {
    switch (widget.mode) {
      case 'repair':
        return 'Analyze this and tell me what the issue is.';
      case 'cook':
        return 'Describe what you see and how I can use this.';
      default:
        return 'What is this and how does it work?';
    }
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

  // Core send logic — adds user bubble + gets AI response
  Future<void> _sendMessage(
    String text, {
    String? imageBase64,
    bool showUserBubble = true,
    bool autoGreeting = false,
  }) async {
    final imageToSend = imageBase64 ?? _attachedImageBase64;
    
    if (text.trim().isEmpty && imageToSend == null) return;

    _textController.clear();
    final currentImage = imageToSend;
    
    setState(() {
      _attachedImageBase64 = null;
    });

    if (showUserBubble) {
      setState(() {
        _messages.add(ChatMessage(
          text: text.trim().isNotEmpty ? text.trim() : null,
          imageBase64: currentImage,
          isUser: true,
        ));
        _isLoading = true;
      });
    } else {
      setState(() => _isLoading = true);
    }

    _scrollToBottom();

    final apiService = ref.read(apiServiceProvider);
    final voiceService = ref.read(voiceServiceProvider);
    final authState = ref.read(authProvider);

    try {
      final response = await apiService.sendChatRequest(
        sessionId: _sessionId,
        query: text.trim().isNotEmpty ? text.trim() : _defaultQueryForMode(),
        imageBase64: currentImage,
        userName: authState.userName,
        mode: widget.mode,
      );

      setState(() {
        _messages.add(ChatMessage(
          isUser: false,
          response: response,
        ));
        _isLoading = false;
      });

      _scrollToBottom();

      if (!autoGreeting) {
        voiceService.speak(
          response.spokenResponse,
          locale: VoiceService.detectLocale(response.spokenResponse),
        );
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _messages.add(ChatMessage(
          text: 'Sorry, I could not connect to the server. Please try again.',
          isUser: false,
        ));
      });
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent + 120,
          duration: const Duration(milliseconds: 350),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _triggerVoiceInput() async {
    final voiceService = ref.read(voiceServiceProvider);
    if (voiceService.isListening) {
      await voiceService.stopListening();
    } else {
      await voiceService.stopSpeaking();
      await voiceService.startListening((transcription) {
        setState(() {
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
      _messages.clear();
      _isLoading = false;
      _attachedImageBase64 = null;
    });
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picker = ImagePicker();
      final pickedFile = await picker.pickImage(
        source: source,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 80,
      );

      if (pickedFile != null) {
        final bytes = await pickedFile.readAsBytes();
        setState(() {
          _attachedImageBase64 = base64Encode(bytes);
        });
      }
    } catch (e) {
      debugPrint('Error picking image: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------
  @override
  Widget build(BuildContext context) {
    final voiceService = ref.watch(voiceServiceProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? AppTheme.darkBackground : AppTheme.creamBackground,
      appBar: AppBar(
        backgroundColor: isDark ? AppTheme.darkBackground : AppTheme.creamBackground,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
            color: isDark ? Colors.white : AppTheme.deepSlate,
            size: 20,
          ),
          onPressed: () {
            voiceService.stopSpeaking();
            context.pop();
          },
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _getModeTitle(),
              style: GoogleFonts.outfit(
                fontWeight: FontWeight.bold,
                fontSize: 17,
                color: isDark ? Colors.white : AppTheme.deepSlate,
              ),
            ),
            Text(
              'PraSush AI',
              style: GoogleFonts.inter(
                fontSize: 11,
                color: AppTheme.sagePrimary.withValues(alpha: 0.8),
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(
              Icons.delete_sweep_rounded,
              color: AppTheme.sagePrimary.withValues(alpha: 0.7),
              size: 22,
            ),
            tooltip: 'Clear Chat',
            onPressed: _clearConversation,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Divider line
            Divider(
              height: 1,
              color: isDark
                  ? Colors.white.withValues(alpha: 0.06)
                  : Colors.black.withValues(alpha: 0.06),
            ),

            // Chat messages list
            Expanded(
              child: _messages.isEmpty && !_isLoading
                  ? _buildEmptyState(isDark)
                  : ListView.builder(
                      controller: _scrollController,
                      physics: const BouncingScrollPhysics(),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 12),
                      itemCount: _messages.length + (_isLoading ? 1 : 0),
                      itemBuilder: (context, index) {
                        if (index == _messages.length && _isLoading) {
                          return _buildTypingIndicator(isDark);
                        }
                        final msg = _messages[index];
                        return msg.isUser
                            ? _buildUserBubble(msg, isDark)
                            : _buildAIBubble(msg, isDark);
                      },
                    ),
            ),

            // Voice wave visualizer
            if (voiceService.isListening)
              _buildVoiceWave(isDark),

            // Input bar
            _buildInputBar(voiceService, isDark),
          ],
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Empty State
  // ---------------------------------------------------------------------------
  Widget _buildEmptyState(bool isDark) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppTheme.sagePrimary.withValues(alpha: 0.08),
            ),
            child: const Icon(
              Icons.chat_bubble_outline_rounded,
              size: 40,
              color: AppTheme.sagePrimary,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Start the conversation',
            style: GoogleFonts.outfit(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: isDark ? Colors.white60 : Colors.black45,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Type a message or use the microphone',
            style: GoogleFonts.inter(
              fontSize: 13,
              color: isDark ? Colors.white38 : Colors.black38,
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // User Bubble
  // ---------------------------------------------------------------------------
  Widget _buildUserBubble(ChatMessage msg, bool isDark) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12, left: 48),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: AppTheme.sagePrimary,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(20),
                  topRight: Radius.circular(20),
                  bottomLeft: Radius.circular(20),
                  bottomRight: Radius.circular(4),
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.sagePrimary.withValues(alpha: 0.25),
                    blurRadius: 8,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Image thumbnail
                  if (msg.imageBase64 != null) ...[
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.memory(
                        base64Decode(msg.imageBase64!),
                        width: 200,
                        height: 150,
                        fit: BoxFit.cover,
                      ),
                    ),
                    if (msg.text != null) const SizedBox(height: 8),
                  ],
                  // Text
                  if (msg.text != null)
                    Text(
                      msg.text!,
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        height: 1.45,
                        color: Colors.white,
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 8),
          CircleAvatar(
            radius: 14,
            backgroundColor: AppTheme.sagePrimary.withValues(alpha: 0.15),
            child: const Icon(Icons.person, size: 16, color: AppTheme.sagePrimary),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // AI Bubble
  // ---------------------------------------------------------------------------
  Widget _buildAIBubble(ChatMessage msg, bool isDark) {
    // Simple error / fallback text message
    if (msg.response == null && msg.text != null) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 12, right: 48),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            _buildAIAvatar(),
            const SizedBox(width: 8),
            Flexible(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: isDark ? AppTheme.darkCard : Colors.white,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(4),
                    topRight: Radius.circular(20),
                    bottomLeft: Radius.circular(20),
                    bottomRight: Radius.circular(20),
                  ),
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.06)
                        : Colors.black.withValues(alpha: 0.06),
                  ),
                ),
                child: Text(
                  msg.text!,
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    height: 1.45,
                    color: isDark ? Colors.white70 : AppTheme.deepSlate,
                  ),
                ),
              ),
            ),
          ],
        ),
      );
    }

    final resp = msg.response!;
    final voiceService = ref.watch(voiceServiceProvider);

    return Padding(
      padding: const EdgeInsets.only(bottom: 16, right: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildAIAvatar(),
          const SizedBox(width: 8),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Issue badge
                Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppTheme.sagePrimary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.info_outline_rounded,
                          size: 14, color: AppTheme.sagePrimary),
                      const SizedBox(width: 6),
                      Flexible(
                        child: Text(
                          resp.probableIssue,
                          style: GoogleFonts.outfit(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.sagePrimary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                // Safety warning
                if (resp.isDangerous && resp.safetyWarning != null) ...[
                  _buildSafetyCard(resp.safetyWarning!, isDark),
                  const SizedBox(height: 8),
                ],

                // Main explanation bubble
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: isDark ? AppTheme.darkCard : Colors.white,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(4),
                      topRight: Radius.circular(20),
                      bottomLeft: Radius.circular(20),
                      bottomRight: Radius.circular(20),
                    ),
                    border: Border.all(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.06)
                          : AppTheme.sagePrimary.withValues(alpha: 0.08),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.04),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Explanation text
                      Text(
                        resp.explanation,
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          height: 1.55,
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.9)
                              : AppTheme.deepSlate.withValues(alpha: 0.9),
                        ),
                      ),

                      // Steps / Instructions
                      if (resp.nextSteps.isNotEmpty) ...[
                        const SizedBox(height: 14),
                        Divider(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.08)
                              : Colors.black.withValues(alpha: 0.06),
                          height: 1,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          widget.mode == 'cook'
                              ? 'Steps & Ingredients'
                              : 'Step-by-Step Guide',
                          style: GoogleFonts.outfit(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.sagePrimary,
                          ),
                        ),
                        const SizedBox(height: 10),
                        ...resp.nextSteps.asMap().entries.map((entry) {
                          return _buildStepRow(
                            entry.key + 1,
                            entry.value,
                            isDark,
                          );
                        }),
                      ],

                      // Listen button
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          GestureDetector(
                            onTap: () {
                              if (voiceService.isSpeaking) {
                                voiceService.stopSpeaking();
                              } else {
                                voiceService.speak(
                                  resp.spokenResponse,
                                  locale: VoiceService.detectLocale(resp.spokenResponse),
                                );
                              }
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 14, vertical: 7),
                              decoration: BoxDecoration(
                                color: AppTheme.sagePrimary.withValues(alpha: 0.08),
                                borderRadius: BorderRadius.circular(20),
                                border: Border.all(
                                  color: AppTheme.sagePrimary.withValues(alpha: 0.2),
                                ),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    voiceService.isSpeaking
                                        ? Icons.stop_rounded
                                        : Icons.volume_up_rounded,
                                    size: 14,
                                    color: AppTheme.sagePrimary,
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    voiceService.isSpeaking ? 'Stop' : 'Listen',
                                    style: GoogleFonts.outfit(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: AppTheme.sagePrimary,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAIAvatar() {
    return Container(
      width: 30,
      height: 30,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: AppTheme.sagePrimary.withValues(alpha: 0.12),
      ),
      child: const Icon(
        Icons.assistant_navigation,
        size: 16,
        color: AppTheme.sagePrimary,
      ),
    );
  }

  // Numbered step row — clean, no checkbox
  Widget _buildStepRow(int number, String text, bool isDark) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 22,
            height: 22,
            margin: const EdgeInsets.only(top: 1),
            decoration: BoxDecoration(
              color: AppTheme.sagePrimary.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                '$number',
                style: GoogleFonts.outfit(
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.sagePrimary,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: GoogleFonts.inter(
                fontSize: 13,
                height: 1.45,
                color: isDark
                    ? Colors.white.withValues(alpha: 0.85)
                    : AppTheme.deepSlate.withValues(alpha: 0.85),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSafetyCard(String warning, bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.errorRed.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: AppTheme.errorRed.withValues(alpha: 0.3),
          width: 1.5,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.warning_amber_rounded,
              color: AppTheme.errorRed, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              warning,
              style: GoogleFonts.inter(
                fontSize: 13,
                height: 1.4,
                fontWeight: FontWeight.w600,
                color: AppTheme.errorRed,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Typing indicator (AI thinking)
  // ---------------------------------------------------------------------------
  Widget _buildTypingIndicator(bool isDark) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16, right: 48),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          _buildAIAvatar(),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
            decoration: BoxDecoration(
              color: isDark ? AppTheme.darkCard : Colors.white,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(4),
                topRight: Radius.circular(20),
                bottomLeft: Radius.circular(20),
                bottomRight: Radius.circular(20),
              ),
              border: Border.all(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.06)
                    : Colors.black.withValues(alpha: 0.06),
              ),
            ),
            child: AnimatedBuilder(
              animation: _pulseController,
              builder: (context, child) {
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: List.generate(3, (i) {
                    final delay = i * 0.3;
                    final value = math.sin(
                            (_pulseController.value * math.pi * 2) + delay) *
                        0.5 +
                        0.5;
                    return Container(
                      width: 7,
                      height: 7,
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppTheme.sagePrimary.withValues(alpha: 0.4 + 0.6 * value),
                      ),
                    );
                  }),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Voice wave visualizer
  // ---------------------------------------------------------------------------
  Widget _buildVoiceWave(bool isDark) {
    return Container(
      height: 44,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(
          14,
          (index) => AnimatedBuilder(
            animation: _pulseController,
            builder: (context, child) {
              final height = (index % 4 + 1) *
                  6.0 *
                  (1.0 +
                      0.5 *
                          math.sin(_pulseController.value * 2 * math.pi +
                              index));
              return Container(
                width: 3,
                height: height.clamp(4.0, 28.0),
                margin: const EdgeInsets.symmetric(horizontal: 2.5),
                decoration: BoxDecoration(
                  color: AppTheme.sagePrimary.withValues(alpha: 0.65),
                  borderRadius: BorderRadius.circular(3),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Input bar
  // ---------------------------------------------------------------------------
  Widget _buildInputBar(VoiceService voiceService, bool isDark) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : Colors.white,
        border: Border(
          top: BorderSide(
            color: isDark
                ? Colors.white.withValues(alpha: 0.06)
                : Colors.black.withValues(alpha: 0.06),
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Image Preview Attachment
          if (_attachedImageBase64 != null) ...[
            Stack(
              children: [
                Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: AppTheme.sagePrimary.withValues(alpha: 0.2),
                      width: 2,
                    ),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.memory(
                      base64Decode(_attachedImageBase64!),
                      width: 80,
                      height: 80,
                      fit: BoxFit.cover,
                    ),
                  ),
                ),
                Positioned(
                  top: -8,
                  right: -8,
                  child: IconButton(
                    icon: Container(
                      padding: const EdgeInsets.all(2),
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppTheme.errorRed,
                      ),
                      child: const Icon(Icons.close, size: 16, color: Colors.white),
                    ),
                    onPressed: () => setState(() => _attachedImageBase64 = null),
                  ),
                ),
              ],
            ),
          ],
          Row(
            children: [
              // Add Image Button
              IconButton(
                icon: Icon(
                  Icons.add_photo_alternate_rounded,
                  color: AppTheme.sagePrimary.withValues(alpha: 0.8),
                  size: 24,
                ),
                onPressed: () {
                  // Show bottom sheet to choose camera or gallery
                  showModalBottomSheet(
                    context: context,
                    backgroundColor: isDark ? AppTheme.darkCard : Colors.white,
                    builder: (context) => SafeArea(
                      child: Wrap(
                        children: [
                          ListTile(
                            leading: const Icon(Icons.photo_library, color: AppTheme.sagePrimary),
                            title: const Text('Gallery'),
                            onTap: () {
                              Navigator.pop(context);
                              _pickImage(ImageSource.gallery);
                            },
                          ),
                          ListTile(
                            leading: const Icon(Icons.camera_alt, color: AppTheme.sagePrimary),
                            title: const Text('Camera'),
                            onTap: () {
                              Navigator.pop(context);
                              _pickImage(ImageSource.camera);
                            },
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
              const SizedBox(width: 4),

              // Mic button
              AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: voiceService.isListening
                      ? AppTheme.errorRed.withValues(alpha: 0.1)
                      : AppTheme.sagePrimary.withValues(alpha: 0.08),
                ),
                child: IconButton(
                  icon: Icon(
                    voiceService.isListening
                        ? Icons.mic_off_rounded
                        : Icons.mic_rounded,
                    color: voiceService.isListening
                        ? AppTheme.errorRed
                        : AppTheme.sagePrimary,
                    size: 22,
                  ),
                  onPressed: _triggerVoiceInput,
                ),
              ),
              const SizedBox(width: 8),

              // Text field
              Expanded(
                child: TextField(
                  controller: _textController,
                  style: GoogleFonts.inter(fontSize: 14),
                  minLines: 1,
                  maxLines: 4,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: InputDecoration(
                    hintText: voiceService.isListening
                        ? 'Listening...'
                        : 'Ask PraSush anything...',
                    hintStyle: GoogleFonts.inter(
                      fontSize: 14,
                      color: isDark ? Colors.white38 : Colors.black38,
                    ),
                    filled: true,
                    fillColor: isDark
                        ? Colors.white.withValues(alpha: 0.05)
                        : Colors.black.withValues(alpha: 0.03),
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 10),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(24),
                      borderSide: BorderSide.none,
                    ),
                  ),
                  onSubmitted: (text) => _sendMessage(text),
                ),
              ),
              const SizedBox(width: 8),

              // Send button
              GestureDetector(
                onTap: () => _sendMessage(_textController.text),
                child: Container(
                  width: 44,
                  height: 44,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppTheme.sagePrimary,
                  ),
                  child: const Icon(
                    Icons.send_rounded,
                    color: Colors.white,
                    size: 20,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
