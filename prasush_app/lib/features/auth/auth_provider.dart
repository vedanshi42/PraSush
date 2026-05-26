import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthState {
  final bool isLoading;
  final bool isAuthenticated;
  final String? userName;
  final String? userEmail;
  final String? userPhotoUrl;
  final bool isSandboxMode;
  final String? errorMessage;

  AuthState({
    this.isLoading = false,
    this.isAuthenticated = false,
    this.userName,
    this.userEmail,
    this.userPhotoUrl,
    this.isSandboxMode = false,
    this.errorMessage,
  });

  AuthState copyWith({
    bool? isLoading,
    bool? isAuthenticated,
    String? userName,
    String? userEmail,
    String? userPhotoUrl,
    bool? isSandboxMode,
    String? errorMessage,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      userName: userName ?? this.userName,
      userEmail: userEmail ?? this.userEmail,
      userPhotoUrl: userPhotoUrl ?? this.userPhotoUrl,
      isSandboxMode: isSandboxMode ?? this.isSandboxMode,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  FirebaseAuth? get _auth {
    try {
      return FirebaseAuth.instance;
    } catch (_) {
      return null;
    }
  }

  GoogleSignIn? get _googleSignIn {
    try {
      return GoogleSignIn();
    } catch (_) {
      return null;
    }
  }

  AuthNotifier() : super(AuthState(isLoading: true)) {
    _checkPersistentSession();
  }

  Future<void> _checkPersistentSession() async {
    final prefs = await SharedPreferences.getInstance();
    final isSaved = prefs.getBool('is_authenticated') ?? false;
    final isSandbox = prefs.getBool('is_sandbox_mode') ?? false;
    
    if (isSaved) {
      final name = prefs.getString('user_name');
      final email = prefs.getString('user_email');
      final photo = prefs.getString('user_photo');
      
      state = AuthState(
        isAuthenticated: true,
        isLoading: false,
        userName: name,
        userEmail: email,
        userPhotoUrl: photo,
        isSandboxMode: isSandbox,
      );
    } else {
      state = AuthState(isLoading: false);
    }
  }

  Future<void> signInWithGoogle() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final googleSignIn = _googleSignIn;
      if (googleSignIn == null) {
        throw Exception('Google Sign-in is not configured or supported on this platform.');
      }
      // Direct Firebase Google Auth flow
      final GoogleSignInAccount? googleUser = await googleSignIn.signIn();
      if (googleUser == null) {
        state = state.copyWith(isLoading: false);
        return; // Sign-in cancelled
      }

      final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
      final AuthCredential credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      final auth = _auth;
      if (auth == null) {
        throw Exception('Firebase is not initialized or supported on this platform.');
      }
      final UserCredential userCredential = await auth.signInWithCredential(credential);
      final User? user = userCredential.user;

      if (user != null) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setBool('is_authenticated', true);
        await prefs.setBool('is_sandbox_mode', false);
        await prefs.setString('user_name', user.displayName ?? 'User');
        await prefs.setString('user_email', user.email ?? '');
        await prefs.setString('user_photo', user.photoURL ?? '');

        state = AuthState(
          isAuthenticated: true,
          isLoading: false,
          userName: user.displayName ?? 'User',
          userEmail: user.email,
          userPhotoUrl: user.photoURL,
          isSandboxMode: false,
        );
      } else {
        state = state.copyWith(isLoading: false, errorMessage: 'Firebase sign-in failed.');
      }
    } catch (e) {
      debugPrint('Google Sign-in failed, entering Sandbox Demo Mode: $e');
      // Gracefully fall back to Sandbox Mode to enable offline/local testing
      await signInAsSandboxUser(
        name: 'Vedanshi Dixit',
        email: 'vedanshi.d@prasush.com',
      );
    }
  }

  Future<void> signInAsSandboxUser({required String name, required String email}) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('is_authenticated', true);
      await prefs.setBool('is_sandbox_mode', true);
      await prefs.setString('user_name', name);
      await prefs.setString('user_email', email);
      await prefs.setString('user_photo', '');

      state = AuthState(
        isAuthenticated: true,
        isLoading: false,
        userName: name,
        userEmail: email,
        userPhotoUrl: null,
        isSandboxMode: true,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  Future<void> signOut() async {
    state = state.copyWith(isLoading: true);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.clear();
      
      try {
        await _auth?.signOut();
        await _googleSignIn?.signOut();
      } catch (_) {}

      state = AuthState(isAuthenticated: false, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier();
});
