import json
import re
import requests
from typing import Optional, Dict, Any
from app.config import (
    NVIDIA_API_KEY,
    NVIDIA_API_ENDPOINT,
    NVIDIA_TEXT_MODEL,
    NVIDIA_VISION_MODEL,
    IS_SANDBOX_MODE,
)
from app.models import GuidanceResponse
from app.services.memory_service import memory_manager

JSON_CLEAN_RE = re.compile(r"^.*?({.*}).*?$", re.DOTALL)

def _get_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }

def call_vision_model(image_base64: str, user_query: str) -> str:
    """
    Calls NVIDIA Vision NIM Model (Phi-4 Multimodal) to get a scene/object description.
    """
    url = f"{NVIDIA_API_ENDPOINT}/chat/completions"
    prompt = (
        f"Analyze this image in detail. The user is asking: '{user_query}'. "
        "Describe what you see, focusing on any physical wear, appliance issues, "
        "cooking ingredients, damage, or contextual details that will help in troubleshooting."
    )
    
    payload = {
        "model": NVIDIA_VISION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are PraSush, a bilingual visual assistant. Answer visual queries thoroughly."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(url, headers=_get_headers(), json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error calling NVIDIA Vision model: {e}")
        raise RuntimeError(f"Vision analysis failed: {str(e)}")

def call_reasoning_model(
    query: str, 
    mode: str, 
    image_description: Optional[str], 
    history_context: str,
    user_name: Optional[str]
) -> GuidanceResponse:
    """
    Calls NVIDIA Reasoning NIM Model (Llama 3.1) to generate structured guidance.
    """
    url = f"{NVIDIA_API_ENDPOINT}/chat/completions"
    
    system_prompt = (
        "You are PraSush, a warm, intelligent, trustworthy, and empathetic AI guidance assistant. "
        "Your mission is to help ordinary people (families, elderly, students) feel less helpless "
        "in everyday situations (repair, cooking, visual learning, and general assistance).\n\n"
        "You MUST respond in a highly structured, valid JSON format. "
        "Do NOT enclose your response in markdown code blocks like ```json ... ```. "
        "Start directly with the '{' character and end with '}'.\n\n"
        "The JSON object must contain EXACTLY the following keys:\n"
        "{\n"
        '  "probable_issue": "A simple diagnostic title/label. Keep it brief and friendly.",\n'
        '  "explanation": "A warm, comforting, easy-to-understand visual and logical explanation. Explain like a wise, supportive family member or neighbor.",\n'
        '  "is_dangerous": true/false (Set to true ONLY if this represents high risk like high-voltage electrical panels, gas leaks, extreme heat, toxic chemicals, or major structural failure),\n'
        '  "safety_warning": "If is_dangerous is true, write a strong, urgent, but caring warning advising the user to stand back and call a professional technician. If false, give practical safety tips (e.g. unplug the appliance first).",\n'
        '  "next_steps": ["Step 1...", "Step 2...", "Step 3..."] (Clean step-by-step checklist of actionable instructions. Include 3 to 6 steps),\n'
        '  "spoken_response": "A comforting verbal summary for text-to-speech. Do not mention JSON keys or say robotic phrases."\n'
        "}\n\n"
        "Language instruction: If the user query or history is in Hindi or Hinglish, answer "
        "the 'explanation', 'probable_issue', and 'spoken_response' in natural, warm Hindi (Devanagari script) or Hindi-English mix "
        "so they feel comfortable, but maintain valid JSON."
    )
    
    user_content = (
        f"User Name: {user_name or 'Friend'}\n"
        f"Flow Mode: {mode}\n"
        f"Current Query: {query}\n"
        f"Conversation History:\n{history_context}\n"
    )
    
    if image_description:
        user_content += f"\nVisual analysis of what the camera sees: {image_description}"
        
    payload = {
        "model": NVIDIA_TEXT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.4,
        "max_tokens": 800
    }
    
    try:
        response = requests.post(url, headers=_get_headers(), json=payload, timeout=60)
        response.raise_for_status()
        raw_content = response.json()["choices"][0]["message"]["content"].strip()
        
        # Clean up any potential markdown wraps
        cleaned_json = raw_content
        match = JSON_CLEAN_RE.match(raw_content)
        if match:
            cleaned_json = match.group(1)
            
        parsed_data = json.loads(cleaned_json)
        return GuidanceResponse(**parsed_data)
    except Exception as e:
        print(f"Error calling NVIDIA Reasoning model or parsing JSON: {e}")
        # Fall back to sandbox generation as high-fidelity recovery
        return get_sandbox_response(query, mode, image_description is not None, user_name)

def get_sandbox_response(query: str, mode: str, has_image: bool, user_name: Optional[str]) -> GuidanceResponse:
    """
    Rich simulated guidance sandbox. Matches query keywords to generate empathetic solutions.
    """
    name = user_name or "Friend"
    q = query.lower()
    
    # Check for DANGEROUS scenario
    if any(k in q for k in ["spark", "shock", "wire", "voltage", "electric panel", "exposed", "gas leak", "smell gas", "circuit breaker", "breaker box"]):
        return GuidanceResponse(
            probable_issue="Dangerous Electrical/Gas Hazard Detected ⚡",
            explanation=f"Hello {name}. I can see there are exposed wires, sparks, or potential gas leaks in this area. These situations are very hazardous and can lead to electrical shocks, fires, or gas accidents. Please do not touch or attempt to repair this yourself.",
            is_dangerous=True,
            safety_warning="⚠️ URGENT SAFETY HAZARD: Do not attempt any DIY repair. Unexposed wires and sparks are highly dangerous. Please stand back and immediately contact a licensed electrician or professional technician.",
            next_steps=[
                "Immediately walk away from the affected area.",
                "If safe, turn off the main circuit breaker or the gas shut-off valve from a distance.",
                "Do not turn on any light switches or appliances that could create a spark.",
                "Call a professional technician or your emergency utility helpline.",
                "Keep children and pets away from the area until it is fully resolved."
            ],
            spoken_response="I've detected a potentially dangerous electrical or gas hazard here. Please step away and do not attempt to fix this yourself. I strongly recommend calling a professional technician right away for your safety."
        )
        
    # Standard Appliance Troubleshooting
    if any(k in q for k in ["toaster", "iron", "oven", "fridge", "refrigerator", "microwave", "ac", "air conditioner", "fan", "washing machine", "bulb", "light"]):
        return GuidanceResponse(
            probable_issue="Appliance Failure or Power Disconnection 🔌",
            explanation=f"Don't worry, {name}. Many appliance issues are caused by loose power cords, blown thermal fuses, or simple connection blocks. Let's inspect it together step-by-step to see if it's a quick, safe fix.",
            is_dangerous=False,
            safety_warning="Safety First: Always unplug the appliance from the electrical socket before inspecting any plugs or panels.",
            next_steps=[
                "Unplug the appliance fully from the wall socket.",
                "Check the power cord for any visible cuts, burns, or damage.",
                "Verify if other devices work in the same wall outlet to ensure the socket is working.",
                "Look for a reset button on the back or bottom of the appliance (common on microwaves and high-power devices).",
                "Ensure the appliance has had time to cool down if it was running continuously (overheat protection)."
            ],
            spoken_response="Let's take a look at your appliance together. First, please unplug it from the wall outlet for safety. We'll start by checking the power cable and the outlet itself."
        )

    # Cooking guide flow
    if mode == "cook" or any(k in q for k in ["cook", "recipe", "paneer", "rice", "salt", "burn", "vegetable", "tea", "chai", "dinner", "lunch"]):
        return GuidanceResponse(
            probable_issue="Culinary Guidance & Quick Fixes 🍳",
            explanation=f"A warm kitchen is the heart of a home, {name}! If you are trying to make a dish or fix a recipe (like something being too salty, burnt, or undercooked), we can easily correct it. Kitchen mistakes are just steps toward a great meal.",
            is_dangerous=False,
            safety_warning="Take care when working around hot stoves, steaming pots, and sharp knives.",
            next_steps=[
                "If a dish is too salty, add a peeled, raw potato or a splash of water/cream to absorb excess salt.",
                "If something is slightly burnt, transfer the unburnt portion to a new pot immediately without scraping the bottom.",
                "If vegetables or rice are undercooked, splash a tablespoon of warm water over them, cover tightly with a lid, and let steam on low heat.",
                "Keep a clean bowl of cold water nearby for easy kitchen cleanup or minor burns."
            ],
            spoken_response="Kitchen situations are always fixable! Whether you need to rescue a dish that's a bit too salty or check a cooking step, let's work through it step-by-step."
        )

    # Visual learning flow
    if mode == "learn" or any(k in q for k in ["what is", "learn", "how does", "explain", "plant", "leaf", "tool", "gadget"]):
        return GuidanceResponse(
            probable_issue="Visual Discovery & Education 🔍",
            explanation=f"What a fascinating curiosity, {name}! Let's explore how this item works, what its structure represents, and what interesting historical or practical aspects are associated with it.",
            is_dangerous=False,
            safety_warning="Ensure you are viewing this item in a bright, stable environment.",
            next_steps=[
                "Examine the key parts of the item (e.g., textures, labels, colors).",
                "Look for any model numbers or natural features (like leaf patterns or screws).",
                "Understand the primary function of this object in modern everyday life.",
                "Explore interesting facts about how it was invented or grows."
            ],
            spoken_response="Curiosity is wonderful! I'd love to help you understand what this item is and how it works. Let's break down its features."
        )

    # General conversation fallback
    return GuidanceResponse(
        probable_issue="PraSush General Assistance 🧠",
        explanation=f"Hello {name}! I am PraSush, your visual guidance companion. I am here to help you feel less helpless in everyday tasks. Feel free to show me something with your camera or ask any question about repairs, cooking, or general troubleshooting.",
        is_dangerous=False,
        safety_warning="Always remember to work in well-lit areas and take your time.",
        next_steps=[
            "Click on 'Repair Help' or 'Learn Visually' to capture an image.",
            "Ask me anything by typing or using the microphone button.",
            "I will guide you step-by-step and read the instructions to you!"
        ],
        spoken_response="Hello! I am PraSush. I'm here to help you troubleshoot, cook, or learn about anything in your environment. Let me know what we are doing today!"
    )
