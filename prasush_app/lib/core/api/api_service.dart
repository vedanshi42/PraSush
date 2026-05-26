import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class GuidanceResponse {
  final String probableIssue;
  final String explanation;
  final bool isDangerous;
  final String? safetyWarning;
  final List<String> nextSteps;
  final String spokenResponse;

  GuidanceResponse({
    required this.probableIssue,
    required this.explanation,
    required this.isDangerous,
    this.safetyWarning,
    required this.nextSteps,
    required this.spokenResponse,
  });

  factory GuidanceResponse.fromJson(Map<String, dynamic> json) {
    return GuidanceResponse(
      probableIssue: json['probable_issue'] ?? 'Troubleshooting',
      explanation: json['explanation'] ?? 'I will guide you through this.',
      isDangerous: json['is_dangerous'] ?? false,
      safetyWarning: json['safety_warning'],
      nextSteps: List<String>.from(json['next_steps'] ?? []),
      spokenResponse: json['spoken_response'] ?? 'I have analyzed the situation.',
    );
  }

  factory GuidanceResponse.fallback(String query, String mode) {
    return GuidanceResponse(
      probableIssue: 'Connecting to PraSush AI...',
      explanation: 'Please ensure your local FastAPI server is running. I am preparing your step-by-step guidance.',
      isDangerous: false,
      nextSteps: [
        'Start the FastAPI backend with: uvicorn app.main:app --reload',
        'Verify your device is on the same Wi-Fi network.',
        'Use the public ngrok address or local IP in Settings.',
        'Ask your question again to see structured visual guidance!'
      ],
      spokenResponse: 'Please make sure the backend server is running in the background. I am ready to guide you.',
    );
  }
}

class ApiService {
  static const String _baseUrlKey = 'backend_base_url';
  static const String defaultBaseUrl = 'http://10.0.2.2:8000'; // Default for Android Emulator

  Future<String> getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_baseUrlKey) ?? defaultBaseUrl;
  }

  Future<void> setBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_baseUrlKey, url);
  }

  Future<bool> checkConnection() async {
    try {
      final baseUrl = await getBaseUrl();
      final response = await http.get(
        Uri.parse('$baseUrl/api/status'),
      ).timeout(const Duration(seconds: 4));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['status'] == 'ok';
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<GuidanceResponse> sendChatRequest({
    required String sessionId,
    required String query,
    String? imageBase64,
    String? userName,
    required String mode,
  }) async {
    final baseUrl = await getBaseUrl();
    final url = Uri.parse('$baseUrl/api/chat');

    final body = jsonEncode({
      'session_id': sessionId,
      'query': query,
      'image_data': imageBase64,
      'user_name': userName,
      'mode': mode,
    });

    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: body,
      ).timeout(const Duration(seconds: 45));

      if (response.statusCode == 200) {
        final jsonDecoded = jsonDecode(utf8.decode(response.bodyBytes));
        return GuidanceResponse.fromJson(jsonDecoded);
      } else {
        throw Exception('Server returned status: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('API Error: $e');
      return GuidanceResponse.fallback(query, mode);
    }
  }

  Future<void> clearMemory(String sessionId) async {
    final baseUrl = await getBaseUrl();
    final url = Uri.parse('$baseUrl/api/clear_memory');
    try {
      await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'session_id': sessionId}),
      ).timeout(const Duration(seconds: 5));
    } catch (e) {
      debugPrint('Failed to clear memory: $e');
    }
  }
}

final apiServiceProvider = Provider<ApiService>((ref) => ApiService());
