# PraSush AI Visual Guidance Assistant 🛡️🍳⚡

PraSush is a production-grade visual guidance assistant that helps ordinary people troubleshoot everyday real-world problems (appliance failures, electrical hazards, cooking saves, visual learning, and elderly assistance) using real-time camera visual reasoning, speech synthesis, and comforting conversational AI.

> *"An AI that helps people feel less helpless in everyday real-world situations."*

---

## 🏗️ Project Architecture

The project is clean, lightweight, and structured into two premium components:
1. **`prasush_app/` (Flutter Frontend)**: Built with Apple-level Cupertino aesthetics, soft card gradients, GoRouter navigation, Riverpod state management, custom grid camera guidelines, and voice controls (Speech-to-Text & Text-to-Speech).
2. **`backend/` (FastAPI Backend)**: Running local REST APIs powered by NVIDIA NIM endpoints (Phi-4 Multimodal for vision context and Llama-3.1 Nemotron for warm conversational reasoning). Features session-based rolling memory context and a built-in safety check routing layer.

---

## ⚡ FastAPI Backend Setup

### Prerequisites
- Python 3.9 or higher
- An active `NVIDIA_API_KEY` (configured automatically in your `.env` during migration!)

### Step-by-Step Installation
1. **Navigate to the Backend directory**:
   ```bash
   cd backend
   ```
2. **Create and Activate a Virtual Environment** (if not already active):
   - **Windows Powershell**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Environment Variables (`.env`)**:
   Verify your `.env` file exists inside the `backend/` folder and contains:
   ```env
   NVIDIA_API_KEY=your_nvidia_api_key_here
   FIREBASE_CONFIG=
   HOST=0.0.0.0
   PORT=8000
   ```
   *Note: If no NVIDIA key is provided, the backend automatically operates in an intelligent "Sandbox Mode" to return high-fidelity mock troubleshooting analyses instantly.*

5. **Start the Uvicorn Server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Verify it works by opening `http://localhost:8000/api/status` in your browser.

---

## 📱 Testing on Android Devices (Local & Online)

When running the backend on your local PC and testing the app on a mobile device, standard `localhost` or `127.0.0.1` will not work because the phone looks within itself for those ports. Use one of these three elegant options:

### Option A: Using the Android Emulator (Easiest)
- Inside the Android emulator, `10.0.2.2` is a special loopback address that points directly to your PC's localhost.
- Navigate to the **Settings Screen** in the PraSush app.
- Enter `http://10.0.2.2:8000` as the backend URL and press **Save & Apply**.

### Option B: Local Wi-Fi Sharing (For Physical Phones)
1. Ensure both your PC and physical Android phone are connected to the **same Wi-Fi network**.
2. Find your PC's local IP address:
   - On Windows Command Prompt / Powershell: run `ipconfig` (look for the IPv4 Address under your active Wi-Fi adapter, e.g., `192.168.1.45`).
   - On macOS/Linux terminal: run `ifconfig` or `ip a`.
3. Inside the **Settings Screen** of the PraSush app on your phone, enter `http://192.168.1.45:8000` (substitute with your actual IP address) and tap **Save & Apply**.

### Option C: Using a Secure Tunnel (ngrok - Highly Recommended)
This creates a secure public HTTPS gateway that works on any phone, anywhere in the world, with zero Wi-Fi restrictions!
1. Download and install [ngrok](https://ngrok.com/).
2. Run the tunnel command in a separate terminal while your Uvicorn server is running:
   ```bash
   ngrok http 8000
   ```
3. Copy the secure forwarding URL (e.g., `https://abcd-12-34.ngrok-free.app`).
4. Inside the **Settings Screen** of the PraSush app, paste that URL and tap **Save & Apply**.

### ☁️ Hosting the Server Online (Production Deployment)
To host the backend online so it runs 24/7 without your PC:
- **Railway.app** (Recommended): Push this repository to GitHub, link it on Railway, configure a "Python" start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and set `NVIDIA_API_KEY` in the environment variables dashboard.
- **Render.com**: Set up a free Web Service, link your repo, set the build command to `pip install -r backend/requirements.txt`, start command to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and configure your secrets.

---

## 🛠️ Flutter Mobile App Setup

### Prerequisites
- [Flutter SDK](https://docs.flutter.dev/get-started/install) installed on your system.
- Android Studio or VS Code with Flutter extensions.
- USB Debugging enabled on your physical Android device.

### Setup and Running
1. **Navigate to the App directory**:
   ```bash
   cd prasush_app
   ```
2. **Download Packages**:
   ```bash
   flutter pub get
   ```
3. **Verify Device Connection**:
   Connect your physical phone via USB (with USB Debugging enabled) and run:
   ```bash
   flutter devices
   ```
4. **Run the Application**:
   ```bash
   flutter run
   ```
5. **Build APK for manual installation**:
   To install the app directly on your phone or share it with family members, build a release-ready debug APK:
   ```bash
   flutter build apk --debug
   ```
   Once built, copy the APK from `build/app/outputs/flutter-apk/app-debug.apk` directly onto your phone's internal storage using a USB cable, open any File Manager app on your phone, and tap the APK to install it immediately!

---

## 🌟 Premium Features Implemented
- **Breathing Ambient Splash Screen**: Features an elegant glowing halo that breathes while checking the user session.
- **Persistent Sessions & Sandbox Fallback**: Safe, automated Google Sign-In persistence with a full Sandbox fallback button for immediate visual previews.
- **Core Guidance Modules**: High-fidelity dashboard directing to Repair Help, Cooking Guide, Ask PraSush, and Visual Learning.
- **Active Grid Camera View**: Tailored overlays, torch/flash manual control, and preview verification.
- **Structured AI Card Carousel**: Generates beautiful issue summaries, detailed human explanations, safety warnings, and an **interactive checkbox checklist** to tick off tasks dynamically.
- **Micro-Animations & Voice Waves**: Real-time subtitles, live wave visualizer while transcribing voice, and responsive buttons.
