import { ProviderClient } from "./backend.js";

const modeSection = document.getElementById("mode-selection");
const customSettingsSection = document.getElementById("custom-settings");
const chatSection = document.getElementById("chat-screen");
const defaultWarning = document.getElementById("default-warning");
const defaultModeButton = document.getElementById("default-mode-button");
const customModeButton = document.getElementById("custom-mode-button");
const customContinueButton = document.getElementById("custom-continue-button");
const customBackButton = document.getElementById("custom-back-button");
const providerSelect = document.getElementById("provider-select");
const endpointInput = document.getElementById("endpoint-input");
const modelInput = document.getElementById("model-input");
const apiKeyInput = document.getElementById("api-key-input");
const rememberKeyCheckbox = document.getElementById("remember-key-checkbox");
const queryInput = document.getElementById("query-input");
const micButton = document.getElementById("mic-button");
const cameraButton = document.getElementById("camera-button");
const sendQueryButton = document.getElementById("send-query-button");
const resetButton = document.getElementById("reset-button");
const responseOutput = document.getElementById("response-output");
const statusText = document.getElementById("status-text");
const avatarStatus = document.getElementById("avatar-status");
const avatarScreen = document.getElementById("avatar-screen");

const STORAGE_KEYS = {
  provider: "pra_sush_provider",
  endpoint: "pra_sush_endpoint",
  model: "pra_sush_model",
  rememberKey: "pra_sush_remember_key",
  apiKey: "pra_sush_api_key",
};

const defaultConfig = {
  provider: window.PRA_SUSH_DEFAULT_PROVIDER || "nvidia",
  endpoint: window.PRA_SUSH_DEFAULT_ENDPOINT || ProviderClient.defaultEndpoint("nvidia"),
  model: window.PRA_SUSH_DEFAULT_MODEL || ProviderClient.defaultModel("nvidia"),
  apiKey: window.PRA_SUSH_DEFAULT_API_KEY || "",
};

let client = null;
let currentMode = null;
let recognition = null;

function showSection(section) {
  modeSection.classList.toggle("hidden", section !== "mode");
  customSettingsSection.classList.toggle("hidden", section !== "custom");
  chatSection.classList.toggle("hidden", section !== "chat");
}

function setAvatar(text, status) {
  avatarScreen.textContent = text;
  avatarStatus.textContent = status;
}

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.style.color = isError ? "#b91c1c" : "#1f2937";
}

function loadSavedSettings() {
  const provider = localStorage.getItem(STORAGE_KEYS.provider) || "openai";
  const rememberKey = localStorage.getItem(STORAGE_KEYS.rememberKey) === "true";
  const endpoint = localStorage.getItem(STORAGE_KEYS.endpoint) || ProviderClient.defaultEndpoint(provider);
  const model = localStorage.getItem(STORAGE_KEYS.model) || ProviderClient.defaultModel(provider);
  const apiKey = rememberKey ? localStorage.getItem(STORAGE_KEYS.apiKey) || "" : "";

  providerSelect.value = provider;
  endpointInput.value = endpoint;
  modelInput.value = model;
  rememberKeyCheckbox.checked = rememberKey;
  apiKeyInput.value = apiKey;
}

function saveCustomSettings() {
  const provider = providerSelect.value;
  const endpoint = endpointInput.value.trim();
  const model = modelInput.value.trim();
  const rememberKey = rememberKeyCheckbox.checked;

  localStorage.setItem(STORAGE_KEYS.provider, provider);
  localStorage.setItem(STORAGE_KEYS.endpoint, endpoint);
  localStorage.setItem(STORAGE_KEYS.model, model);
  localStorage.setItem(STORAGE_KEYS.rememberKey, rememberKey ? "true" : "false");

  if (rememberKey) {
    localStorage.setItem(STORAGE_KEYS.apiKey, apiKeyInput.value.trim());
  } else {
    localStorage.removeItem(STORAGE_KEYS.apiKey);
  }
}

function updateEndpointAndModel(provider) {
  if (provider === "custom") {
    endpointInput.placeholder = "Enter your custom endpoint URL";
    endpointInput.value = "";
    modelInput.value = "";
    return;
  }
  endpointInput.value = ProviderClient.defaultEndpoint(provider);
  modelInput.value = ProviderClient.defaultModel(provider);
}

function validateApiConfig(provider, endpoint, model, apiKey) {
  if (!endpoint) {
    throw new Error("Endpoint URL is required.");
  }
  if (!model) {
    throw new Error("Model name is required.");
  }
  if (!apiKey) {
    throw new Error("API key is required.");
  }
}

function isVisionQuery(text) {
  return /\b(see|look|describe|camera|what do you see|what can you see|what is around|tell me what you see)\b/i.test(text);
}

function enableChatControls() {
  queryInput.disabled = false;
  sendQueryButton.disabled = false;
  micButton.disabled = false;
  cameraButton.disabled = false;
}

function disableChatControls() {
  queryInput.disabled = true;
  sendQueryButton.disabled = true;
  micButton.disabled = true;
  cameraButton.disabled = true;
}

function enterDefaultMode() {
  currentMode = "default";
  showSection("chat");
  setAvatar("Say hi to start chat.", "Ready for voice or text input.");
  setStatus("Default NVIDIA provider is selected.");

  if (!defaultConfig.apiKey) {
    setStatus("Default API key is not configured. Please fill docs/js/default-config.js or use custom mode.", true);
    defaultWarning.textContent = "Default key is missing. Add your NVIDIA key to docs/js/default-config.js before publishing.";
    defaultWarning.classList.remove("hidden");
    disableChatControls();
    return;
  }

  defaultWarning.classList.add("hidden");
  enableChatControls();
  client = new ProviderClient({
    provider: defaultConfig.provider,
    endpoint: defaultConfig.endpoint,
    model: defaultConfig.model,
    apiKey: defaultConfig.apiKey,
  });
}

function enterCustomMode() {
  currentMode = "custom";
  showSection("custom");
  loadSavedSettings();
  setStatus("Fill your provider and credentials.");
}

async function captureScenePhoto() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error("Camera access is not supported in this browser.");
  }

  setAvatar("Requesting camera permission...", "Camera pending");
  setStatus("Requesting camera permission...");

  const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
  const video = document.createElement("video");
  video.srcObject = stream;
  video.play();

  await new Promise((resolve, reject) => {
    video.onloadedmetadata = () => resolve();
    video.onerror = reject;
  });

  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  stream.getTracks().forEach((track) => track.stop());
  video.srcObject = null;

  setStatus("Camera captured scene.");
  return canvas.toDataURL("image/jpeg", 0.8);
}

async function sendChat(message, imageData = null) {
  if (!message) {
    setStatus("Enter a message to send.", true);
    return;
  }

  if (!client) {
    setStatus("Provider client is not initialized.", true);
    return;
  }

  setAvatar("Thinking...", "Processing your request.");
  setStatus("Sending request to the provider...");
  disableChatControls();

  try {
    const response = await client.chat(message, imageData);
    responseOutput.textContent = response;
    setAvatar(response, "Response received.");
    setStatus("Success.");
    enableChatControls();
  } catch (error) {
    const message = error?.message || "Unknown error.";
    responseOutput.textContent = "";
    setAvatar(`Error encountered - ${message}\nBye.`, "Error");
    setStatus(`Error encountered - ${message}`, true);
    disableChatControls();
  }
}

async function sendQuery() {
  const query = queryInput.value.trim();
  if (!query) {
    setStatus("Type your question first.", true);
    return;
  }

  if (isVisionQuery(query)) {
    try {
      const imageData = await captureScenePhoto();
      await sendChat(query, imageData);
    } catch (error) {
      setStatus(error?.message || "Camera capture failed.", true);
      setAvatar(`Error encountered - ${error?.message || "Camera capture failed."}`, "Error");
    }
    return;
  }

  await sendChat(query);
}

function initializeSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    return null;
  }

  const recognitionInstance = new SpeechRecognition();
  recognitionInstance.lang = "en-IN";
  recognitionInstance.interimResults = false;
  recognitionInstance.maxAlternatives = 1;
  recognitionInstance.continuous = false;

  recognitionInstance.addEventListener("start", () => {
    setAvatar("Listening...", "Speak now.");
    setStatus("Listening for your question...");
  });

  recognitionInstance.addEventListener("result", async (event) => {
    const transcript = event.results[0][0].transcript;
    queryInput.value = transcript;
    setStatus(`Heard: ${transcript}`);

    if (isVisionQuery(transcript)) {
      try {
        const imageData = await captureScenePhoto();
        await sendChat(transcript, imageData);
      } catch (error) {
        setStatus(error?.message || "Camera capture failed.", true);
        setAvatar(`Error encountered - ${error?.message || "Camera capture failed."}`, "Error");
      }
      return;
    }

    await sendChat(transcript);
  });

  recognitionInstance.addEventListener("error", (event) => {
    setStatus(`Voice recognition error: ${event.error}`, true);
    setAvatar(`Error encountered - ${event.error}`, "Error");
  });

  recognitionInstance.addEventListener("end", () => {
    if (!queryInput.value) {
      setStatus("Voice capture ended. Try again or type your message.");
      setAvatar("Waiting for wake word", "Ready for text or voice.");
    }
  });

  return recognitionInstance;
}

async function startVoiceRecognition() {
  if (!recognition) {
    recognition = initializeSpeechRecognition();
  }

  if (!recognition) {
    setStatus("Voice recognition is not supported by this browser.", true);
    return;
  }

  try {
    recognition.start();
  } catch (error) {
    setStatus(error?.message || "Unable to start voice recognition.", true);
  }
}

async function triggerCameraQuery() {
  const query = queryInput.value.trim();
  if (!query) {
    setStatus("Type your question before capturing the scene.", true);
    return;
  }

  try {
    const imageData = await captureScenePhoto();
    await sendChat(query, imageData);
  } catch (error) {
    setStatus(error?.message || "Camera capture failed.", true);
    setAvatar(`Error encountered - ${error?.message || "Camera capture failed."}`, "Error");
  }
}

function finishSetup() {
  try {
    const provider = providerSelect.value;
    const endpoint = endpointInput.value.trim();
    const model = modelInput.value.trim();
    const apiKey = apiKeyInput.value.trim();

    validateApiConfig(provider, endpoint, model, apiKey);
    saveCustomSettings();

    client = new ProviderClient({ provider, endpoint, model, apiKey });
    enableChatControls();
    showSection("chat");
    setAvatar("Say hi to start chat.", "Ready for voice or text input.");
    setStatus("Custom provider configured.");
  } catch (error) {
    setStatus(error.message, true);
    disableChatControls();
  }
}

function resetToStart() {
  client = null;
  currentMode = null;
  queryInput.value = "";
  queryInput.disabled = false;
  responseOutput.textContent = "No response yet.";
  setAvatar("Say hi to start chat.", "Waiting for wake word.");
  setStatus("Choose default or custom mode.");
  sendQueryButton.disabled = false;
  micButton.disabled = false;
  cameraButton.disabled = false;
  showSection("mode");
}

defaultModeButton.addEventListener("click", enterDefaultMode);
customModeButton.addEventListener("click", enterCustomMode);
customContinueButton.addEventListener("click", finishSetup);
customBackButton.addEventListener("click", resetToStart);
providerSelect.addEventListener("change", () => updateEndpointAndModel(providerSelect.value));
sendQueryButton.addEventListener("click", sendQuery);
resetButton.addEventListener("click", resetToStart);
micButton.addEventListener("click", startVoiceRecognition);
cameraButton.addEventListener("click", triggerCameraQuery);

window.addEventListener("DOMContentLoaded", () => {
  showSection("mode");
  defaultWarning.classList.add("hidden");
  queryInput.placeholder = "Type hi or your question here...";
  updateEndpointAndModel(providerSelect.value);
});
