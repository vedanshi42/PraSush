import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:permission_handler/permission_handler.dart';
import '../../core/theme/app_theme.dart';

class CameraScreen extends StatefulWidget {
  final String mode;
  const CameraScreen({super.key, required this.mode});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  bool _isPermissionGranted = false;
  bool _isInitializing = true;
  bool _isCapturing = false;
  bool _isFlashOn = false;

  // After capture — show preview + caption input
  String? _capturedBase64;
  final TextEditingController _captionController = TextEditingController();
  bool _isSending = false;

  @override
  void initState() {
    super.initState();
    _requestPermissionsAndInit();
  }

  @override
  void dispose() {
    _controller?.dispose();
    _captionController.dispose();
    super.dispose();
  }

  Future<void> _requestPermissionsAndInit() async {
    final status = await Permission.camera.request();
    if (status.isGranted) {
      setState(() => _isPermissionGranted = true);
      await _initializeCamera();
    } else {
      setState(() {
        _isPermissionGranted = false;
        _isInitializing = false;
      });
    }
  }

  Future<void> _initializeCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras != null && _cameras!.isNotEmpty) {
        _controller = CameraController(
          _cameras![0],
          ResolutionPreset.medium,
          enableAudio: false,
        );
        await _controller!.initialize();
      }
    } catch (e) {
      debugPrint('Camera init error: $e');
    } finally {
      if (mounted) setState(() => _isInitializing = false);
    }
  }

  Future<void> _toggleFlash() async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    try {
      await _controller!.setFlashMode(
        _isFlashOn ? FlashMode.off : FlashMode.torch,
      );
      setState(() => _isFlashOn = !_isFlashOn);
    } catch (e) {
      debugPrint('Flash error: $e');
    }
  }

  Future<void> _captureImage() async {
    if (_isCapturing) return;
    setState(() => _isCapturing = true);

    try {
      String base64Image;

      if (_controller != null && _controller!.value.isInitialized) {
        if (_isFlashOn) await _controller!.setFlashMode(FlashMode.off);
        final XFile file = await _controller!.takePicture();
        final bytes = await File(file.path).readAsBytes();
        base64Image = base64.encode(bytes);
      } else {
        // Sandbox mock — tiny placeholder
        await Future.delayed(const Duration(milliseconds: 800));
        base64Image =
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
      }

      if (mounted) {
        setState(() {
          _capturedBase64 = base64Image;
          _isCapturing = false;
        });
      }
    } catch (e) {
      debugPrint('Capture error: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Capture failed: $e')),
        );
        setState(() => _isCapturing = false);
      }
    }
  }

  void _sendToChat() {
    if (_capturedBase64 == null) return;
    setState(() => _isSending = true);

    // Store image + caption for chat screen to pick up
    _CapturedImageHolder.base64Content = _capturedBase64;
    _CapturedImageHolder.captionText =
        _captionController.text.trim().isNotEmpty
            ? _captionController.text.trim()
            : null;

    context.pushReplacement('/chat?mode=${widget.mode}');
  }

  void _retakePhoto() {
    setState(() {
      _capturedBase64 = null;
      _captionController.clear();
    });
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------
  @override
  Widget build(BuildContext context) {
    // Show caption/preview screen after capture
    if (_capturedBase64 != null) {
      return _buildCaptionScreen();
    }

    Widget cameraWidget;
    if (_isInitializing) {
      cameraWidget = const ColoredBox(
        color: Colors.black,
        child: Center(child: CircularProgressIndicator(color: Colors.white)),
      );
    } else if (!_isPermissionGranted) {
      cameraWidget = _buildPermissionDeniedView();
    } else if (_controller == null || !_controller!.value.isInitialized) {
      cameraWidget = _buildSandboxCameraView();
    } else {
      cameraWidget = Stack(
        fit: StackFit.expand,
        children: [
          CameraPreview(_controller!),
          _buildOverlayGuidelines(),
        ],
      );
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          Positioned.fill(child: cameraWidget),
          _buildTopBar(),
          _buildBottomControls(),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Caption / Preview screen
  // ---------------------------------------------------------------------------
  Widget _buildCaptionScreen() {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            // Top bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back_ios_new_rounded,
                        color: Colors.white),
                    onPressed: _retakePhoto,
                  ),
                  Expanded(
                    child: Text(
                      'Add a message',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.outfit(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(width: 48), // Balance back button
                ],
              ),
            ),

            // Image preview — takes most of the screen
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: Image.memory(
                    base64Decode(_capturedBase64!),
                    width: double.infinity,
                    fit: BoxFit.cover,
                  ),
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Caption input bar
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 16),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(28),
                border: Border.all(
                  color: AppTheme.sagePrimary.withValues(alpha: 0.5),
                  width: 1.5,
                ),
              ),
              child: Row(
                children: [
                  const Icon(Icons.chat_bubble_outline_rounded,
                      color: AppTheme.sagePrimary, size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: TextField(
                      controller: _captionController,
                      style: GoogleFonts.inter(
                          color: Colors.white, fontSize: 14),
                      maxLines: null,
                      textCapitalization: TextCapitalization.sentences,
                      decoration: InputDecoration(
                        hintText: widget.mode == 'repair'
                            ? 'e.g. Help me fix this cooler wiring...'
                            : widget.mode == 'cook'
                                ? 'e.g. What can I make with these ingredients?'
                                : 'Add a message or question...',
                        hintStyle: GoogleFonts.inter(
                          color: Colors.white38,
                          fontSize: 14,
                        ),
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // Send button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: SizedBox(
                width: double.infinity,
                height: 54,
                child: ElevatedButton(
                  onPressed: _isSending ? null : _sendToChat,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.sagePrimary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                    elevation: 0,
                  ),
                  child: _isSending
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                              color: Colors.white, strokeWidth: 2.5),
                        )
                      : Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.send_rounded, size: 20),
                            const SizedBox(width: 10),
                            Text(
                              'Send to PraSush',
                              style: GoogleFonts.outfit(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                ),
              ),
            ),

            // Retake option
            TextButton(
              onPressed: _retakePhoto,
              child: Text(
                'Retake Photo',
                style: GoogleFonts.inter(
                  color: Colors.white54,
                  fontSize: 13,
                ),
              ),
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Camera viewfinder UI parts
  // ---------------------------------------------------------------------------
  Widget _buildTopBar() {
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: Container(
        padding: const EdgeInsets.only(top: 50, bottom: 20, left: 16, right: 16),
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Colors.black54, Colors.transparent],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            IconButton(
              icon: const Icon(Icons.arrow_back_ios_new_rounded,
                  color: Colors.white),
              onPressed: () => context.pop(),
            ),
            Text(
              widget.mode == 'repair'
                  ? 'Repair — Visual Scan'
                  : 'Visual Learning Scan',
              style: GoogleFonts.outfit(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w600,
              ),
            ),
            IconButton(
              icon: Icon(
                _isFlashOn ? Icons.flash_on_rounded : Icons.flash_off_rounded,
                color: _isFlashOn ? Colors.yellow : Colors.white,
              ),
              onPressed: _controller != null ? _toggleFlash : null,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBottomControls() {
    return Positioned(
      bottom: 0,
      left: 0,
      right: 0,
      child: Container(
        padding: const EdgeInsets.only(top: 30, bottom: 50, left: 24, right: 24),
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Colors.transparent, Colors.black87],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: Column(
          children: [
            Text(
              widget.mode == 'repair'
                  ? 'Position the appliance or hazard in the frame'
                  : 'Place the item you want to learn about in view',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                color: Colors.white.withValues(alpha: 0.75),
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 24),
            // Shutter button
            GestureDetector(
              onTap: _isCapturing ? null : _captureImage,
              child: Container(
                width: 80,
                height: 80,
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 3.5),
                ),
                child: Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _isCapturing ? Colors.grey : Colors.white,
                  ),
                  child: _isCapturing
                      ? const Center(
                          child: SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(
                                color: Colors.black, strokeWidth: 2.5),
                          ),
                        )
                      : null,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOverlayGuidelines() {
    return LayoutBuilder(
      builder: (context, constraints) {
        final boxWidth = constraints.maxWidth * 0.75;
        final boxHeight = constraints.maxHeight * 0.45;
        return Stack(
          children: [
            ColorFiltered(
              colorFilter: ColorFilter.mode(
                Colors.black.withValues(alpha: 0.4),
                BlendMode.srcOut,
              ),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Container(
                    decoration: const BoxDecoration(
                      color: Colors.black,
                      backgroundBlendMode: BlendMode.dstOut,
                    ),
                  ),
                  Center(
                    child: Container(
                      width: boxWidth,
                      height: boxHeight,
                      decoration: BoxDecoration(
                        color: Colors.red,
                        borderRadius: BorderRadius.circular(24),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Center(
              child: Container(
                width: boxWidth,
                height: boxHeight,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: AppTheme.sagePrimary.withValues(alpha: 0.7),
                    width: 3,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.sagePrimary.withValues(alpha: 0.12),
                      blurRadius: 10,
                      spreadRadius: 2,
                    ),
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildPermissionDeniedView() {
    return Container(
      color: Colors.black,
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.videocam_off_rounded,
              size: 64, color: AppTheme.errorRed),
          const SizedBox(height: 24),
          Text(
            'Camera Access Blocked',
            style: GoogleFonts.outfit(
                color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          Text(
            'PraSush needs camera permission to perform visual troubleshooting and learning.',
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
                color: Colors.white60, fontSize: 14, height: 1.4),
          ),
          const SizedBox(height: 32),
          ElevatedButton(
            onPressed: () => openAppSettings(),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.sagePrimary,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16)),
              padding:
                  const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            ),
            child: const Text('Open System Settings'),
          ),
        ],
      ),
    );
  }

  Widget _buildSandboxCameraView() {
    return Container(
      color: const Color(0xFF141414),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.camera_alt_outlined,
                  color: Colors.white.withValues(alpha: 0.12), size: 90),
              const SizedBox(height: 16),
              Text(
                'Sandbox Camera Mode',
                style: GoogleFonts.outfit(
                    color: Colors.white54,
                    fontSize: 15,
                    fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 6),
              Text(
                'Tap the shutter to capture a mock image',
                style: GoogleFonts.inter(color: Colors.white24, fontSize: 12),
              ),
            ],
          ),
          _buildOverlayGuidelines(),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Global image + caption holder — shared between camera and chat screens
// ---------------------------------------------------------------------------
class _CapturedImageHolder {
  static String? base64Content;
  static String? captionText;
}

String? getCapturedImageBase64() => _CapturedImageHolder.base64Content;
String? getCapturedImageCaption() => _CapturedImageHolder.captionText;

void clearCapturedImage() {
  _CapturedImageHolder.base64Content = null;
  _CapturedImageHolder.captionText = null;
}
