import 'dart:async';
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

  @override
  void initState() {
    super.initState();
    _requestPermissionsAndInit();
  }

  Future<void> _requestPermissionsAndInit() async {
    final status = await Permission.camera.request();
    if (status.isGranted) {
      if (mounted) {
        setState(() {
          _isPermissionGranted = true;
        });
      }
      await _initializeCamera();
    } else {
      if (mounted) {
        setState(() {
          _isPermissionGranted = false;
          _isInitializing = false;
        });
      }
    }
  }

  Future<void> _initializeCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras != null && _cameras!.isNotEmpty) {
        _controller = CameraController(
          _cameras![0], // First camera (rear)
          ResolutionPreset.medium,
          enableAudio: false,
        );

        await _controller!.initialize();
        if (mounted) {
          setState(() {
            _isInitializing = false;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _isInitializing = false;
          });
        }
      }
    } catch (e) {
      print("Camera Init Error: $e");
      if (mounted) {
        setState(() {
          _isInitializing = false;
        });
      }
    }
  }

  Future<void> _toggleFlash() async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    try {
      if (_isFlashOn) {
        await _controller!.setFlashMode(FlashMode.off);
      } else {
        await _controller!.setFlashMode(FlashMode.torch);
      }
      setState(() {
        _isFlashOn = !_isFlashOn;
      });
    } catch (e) {
      print("Failed to set flash: $e");
    }
  }

  Future<void> _captureImage() async {
    if (_isCapturing) return;
    
    setState(() {
      _isCapturing = true;
    });

    try {
      String? base64Image;
      String? imagePath;

      if (_controller != null && _controller!.value.isInitialized) {
        // Real camera capture
        final XFile file = await _controller!.takePicture();
        final bytes = await File(file.path).readAsBytes();
        base64Image = base64.encode(bytes);
        imagePath = file.path;
      } else {
        // Sandbox mock capture
        await Future.delayed(const Duration(seconds: 1)); // Simulate shutter sound/delay
        // Use a dummy tiny 1x1 black pixel base64 as placeholder
        base64Image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";
        imagePath = "sandbox_captured.jpg";
      }

      if (mounted) {
        // Turn off flash torch if it was on
        if (_isFlashOn && _controller != null) {
          await _controller!.setFlashMode(FlashMode.off);
        }
        
        if (!mounted) return;
        
        // Pass base64 image and local image path to the chat screen
        // We will store base64 in a shared memory provider or parameter
        // For GoRouter parameters, we can use the imagePath parameter.
        // To make it robust, we'll store the captured base64 in a global parameter or let chat handle it.
        // Let's pass the image path locally. In a real application, the path is used to read and upload the file.
        // We can save the captured base64 string in a static or shared singleton for the session,
        // or write the file to SharedPreferences or a temporary memory cache.
        // Let's store the base64 string globally in static memory so the Chat screen can access it.
        _CapturedImageHolder.base64Content = base64Image;
        _CapturedImageHolder.localPath = imagePath;

        context.pushReplacement(
          '/chat?mode=${widget.mode}&imagePath=${Uri.encodeComponent(imagePath)}',
        );
      }
    } catch (e) {
      print("Failed to capture: $e");
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Capture failed: $e")),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isCapturing = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    Widget cameraWidget;

    if (_isInitializing) {
      cameraWidget = Container(
        color: Colors.black,
        child: const Center(
          child: CircularProgressIndicator(color: Colors.white),
        ),
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
          // Camera Preview viewport
          Positioned.fill(child: cameraWidget),

          // Upper controller header bar
          Positioned(
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
                    icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
                    onPressed: () => context.pop(),
                  ),
                  Text(
                    widget.mode == 'repair'
                        ? 'Repair Visual Guidance'
                        : 'Visual Learning Scan',
                    style: GoogleFonts.outfit(
                      color: Colors.white,
                      fontSize: 18,
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
          ),

          // Bottom capture controls panel
          Positioned(
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
                        ? 'Position the appliance or hazard in the box grid.'
                        : 'Place the item you wish to learn about in the box.',
                    textAlign: TextAlign.center,
                    style: GoogleFonts.inter(
                      color: Colors.white.withValues(alpha: 0.8),
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Shutter button
                      GestureDetector(
                        onTap: _isCapturing ? null : _captureImage,
                        child: Container(
                          width: 84,
                          height: 84,
                          padding: const EdgeInsets.all(4),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 4),
                          ),
                          child: Container(
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: _isCapturing ? Colors.grey : Colors.white,
                            ),
                            child: _isCapturing
                                ? const Center(
                                    child: SizedBox(
                                      width: 24,
                                      height: 24,
                                      child: CircularProgressIndicator(color: Colors.black, strokeWidth: 3),
                                    ),
                                  )
                                : null,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
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
            // Darken outer bounds
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
            // Glowing alignment box
            Center(
              child: Container(
                width: boxWidth,
                height: boxHeight,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: AppTheme.sagePrimary.withValues(alpha: 0.7),
                    width: 3.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.sagePrimary.withValues(alpha: 0.15),
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
          const Icon(Icons.videocam_off_rounded, size: 64, color: AppTheme.errorRed),
          const SizedBox(height: 24),
          Text(
            'Camera Access Blocked',
            style: GoogleFonts.outfit(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          Text(
            'PraSush needs camera permission to perform visual troubleshooting and learning scan.',
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(color: Colors.white60, fontSize: 14, height: 1.4),
          ),
          const SizedBox(height: 32),
          ElevatedButton(
            onPressed: () => openAppSettings(),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.sagePrimary,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            ),
            child: const Text('Open System Settings'),
          ),
        ],
      ),
    );
  }

  Widget _buildSandboxCameraView() {
    return Container(
      color: const Color(0xFF151515),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Abstract camera visual
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.camera_alt_outlined, color: Colors.white.withValues(alpha: 0.15), size: 100),
              const SizedBox(height: 16),
              Text(
                'Sandbox Camera Sandbox Mode Active',
                style: GoogleFonts.outfit(color: Colors.white54, fontSize: 15, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 6),
              Text(
                '(Perfect for local emulator/PC testing)',
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

// Global Static Holder to pass Base64 and Local paths between routes without GoRouter character limits
class _CapturedImageHolder {
  static String? base64Content;
  static String? localPath;
}

// Global access function for the Chat screen
String? getCapturedImageBase64() => _CapturedImageHolder.base64Content;
String? getCapturedImagePath() => _CapturedImageHolder.localPath;
void clearCapturedImage() {
  _CapturedImageHolder.base64Content = null;
  _CapturedImageHolder.localPath = null;
}
