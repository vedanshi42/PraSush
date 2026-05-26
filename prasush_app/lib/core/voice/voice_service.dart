import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_riverpod/flutter_riverpod.dart';

class VoiceService extends ChangeNotifier {
  final FlutterTts _tts = FlutterTts();
  final stt.SpeechToText _stt = stt.SpeechToText();

  bool _isListening = false;
  String _lastWords = '';
  bool _isSpeaking = false;
  bool _sttAvailable = false;

  bool get isListening => _isListening;
  String get lastWords => _lastWords;
  bool get isSpeaking => _isSpeaking;

  VoiceService() {
    _initTts();
    _initStt();
  }

  void _initTts() {
    _tts.setStartHandler(() {
      _isSpeaking = true;
      notifyListeners();
    });

    _tts.setCompletionHandler(() {
      _isSpeaking = false;
      notifyListeners();
    });

    _tts.setErrorHandler((msg) {
      _isSpeaking = false;
      notifyListeners();
      debugPrint('TTS Error: $msg');
    });

    // Set warm voice settings
    _tts.setLanguage('en-US');
    _tts.setSpeechRate(0.5); // Calm pacing
    _tts.setPitch(1.0);
  }

  Future<void> _initStt() async {
    try {
      _sttAvailable = await _stt.initialize(
        onStatus: (status) {
          if (status == 'done' || status == 'notListening') {
            _isListening = false;
            notifyListeners();
          }
        },
        onError: (error) {
          _isListening = false;
          notifyListeners();
          debugPrint('STT Error: $error');
        },
      );
    } catch (e) {
      debugPrint('Failed to init STT: $e');
    }
  }

  Future<void> speak(String text) async {
    if (text.isEmpty) return;
    await stopSpeaking();
    await _tts.speak(text);
  }

  Future<void> stopSpeaking() async {
    await _tts.stop();
    _isSpeaking = false;
    notifyListeners();
  }

  Future<void> startListening(Function(String) onResult) async {
    if (!_sttAvailable) {
      // Re-try initialization
      await _initStt();
    }

    if (_sttAvailable) {
      _lastWords = '';
      _isListening = true;
      notifyListeners();

      await _stt.listen(
        onResult: (result) {
          _lastWords = result.recognizedWords;
          onResult(_lastWords);
          notifyListeners();
        },
        listenOptions: stt.SpeechListenOptions(
          listenFor: const Duration(seconds: 15),
          pauseFor: const Duration(seconds: 4),
          cancelOnError: true,
          partialResults: true,
        ),
      );
    } else {
      debugPrint('Speech recognition not available on this device.');
    }
  }

  Future<void> stopListening() async {
    await _stt.stop();
    _isListening = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _tts.stop();
    _stt.stop();
    super.dispose();
  }
}

final voiceServiceProvider = ChangeNotifierProvider<VoiceService>((ref) {
  final service = VoiceService();
  ref.onDispose(() => service.dispose());
  return service;
});
