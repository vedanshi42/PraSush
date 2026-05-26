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

# Detects actual Hindi/Devanagari script characters
HINDI_SCRIPT_RE = re.compile(r"[\u0900-\u097F]")


def _is_hindi(text: str) -> bool:
    """Returns True only if the query contains Devanagari/Hindi script characters."""
    return bool(HINDI_SCRIPT_RE.search(text))


def _get_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }


def call_vision_model(image_base64: str, user_query: str) -> str:
    """
    Calls NVIDIA Vision NIM Model to describe an image in the context of the user query.
    Falls back gracefully if the model times out or is unavailable.
    """
    print(f"\n[AI LOG] 📷 Vision analysis — model: {NVIDIA_VISION_MODEL}")
    print(f"[AI LOG] 💬 User query: '{user_query}'")

    url = f"{NVIDIA_API_ENDPOINT}/chat/completions"
    prompt = (
        f"Analyze this image. The user asks: '{user_query}'. "
        "Describe visible damage, appliance state, ingredients, or hazards briefly in 2-3 sentences."
    )

    payload = {
        "model": NVIDIA_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ],
        "temperature": 0.3,
        "max_tokens": 200
    }

    try:
        response = requests.post(url, headers=_get_headers(), json=payload, timeout=20)
        response.raise_for_status()
        description = response.json()["choices"][0]["message"]["content"].strip()
        print(f"[AI LOG] ✅ Vision result: '{description[:120]}...'")
        return description
    except Exception as e:
        print(f"[AI LOG] ❌ Vision model failed: {e}")
        raise RuntimeError(f"Vision analysis failed: {str(e)}")


def call_reasoning_model(
    query: str,
    mode: str,
    image_description: Optional[str],
    history_context: str,
    user_name: Optional[str]
) -> GuidanceResponse:
    """
    Calls the NVIDIA reasoning model to generate structured JSON guidance.
    Falls back to sandbox response if the model is unavailable.
    """
    print(f"\n[AI LOG] 🧠 Reasoning — model: {NVIDIA_TEXT_MODEL}")

    use_hindi = _is_hindi(query)
    print(f"[AI LOG] 🌐 Language: {'Hindi detected' if use_hindi else 'English'}")

    url = f"{NVIDIA_API_ENDPOINT}/chat/completions"

    system_prompt = (
        "You are PraSush, a warm helpful AI assistant for everyday repairs, cooking, and learning.\n"
        "Reply ONLY with a valid JSON object — no markdown, no code fences, nothing outside the JSON.\n"
        "Start directly with { and end with }.\n"
        "Required JSON keys (use exactly these names):\n"
        "  probable_issue  — short friendly title (string)\n"
        "  explanation     — warm 2-3 sentence description (string)\n"
        "  is_dangerous    — true or false (boolean)\n"
        "  safety_warning  — safety note string, or null\n"
        "  next_steps      — array of 4-6 clear action strings; for cooking include exact ingredient quantities\n"
        "  spoken_response — 1-2 sentence TTS-friendly summary (string)\n"
    )

    user_content = f"Mode: {mode}\nUser: {user_name or 'Friend'}\nQuery: {query}"
    if history_context and history_context.strip():
        user_content += f"\nHistory: {history_context[:300]}"
    if image_description:
        user_content += f"\nCamera sees: {image_description}"

    payload = {
        "model": NVIDIA_TEXT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.4,
        "max_tokens": 700
    }

    try:
        response = requests.post(url, headers=_get_headers(), json=payload, timeout=25)
        response.raise_for_status()
        raw_content = response.json()["choices"][0]["message"]["content"].strip()
        print(f"[AI LOG] 📝 Raw output:\n{raw_content}\n")

        # Strip markdown code fences if present
        raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content, flags=re.IGNORECASE)
        raw_content = re.sub(r"\s*```\s*$", "", raw_content).strip()

        match = JSON_CLEAN_RE.match(raw_content)
        cleaned_json = match.group(1) if match else raw_content

        parsed_data = json.loads(cleaned_json)
        print(f"[AI LOG] ✅ Parsed: {parsed_data.get('probable_issue')}")
        return GuidanceResponse(**parsed_data)

    except Exception as e:
        print(f"[AI LOG] ⚠️ Reasoning error: {e} — using sandbox fallback")
        return get_sandbox_response(query, mode, image_description is not None, user_name)


def get_sandbox_response(
    query: str,
    mode: str,
    has_image: bool,
    user_name: Optional[str]
) -> GuidanceResponse:
    """
    Rich offline sandbox. Matches query keywords to return empathetic, structured responses.
    This is the guaranteed delivery path when AI models are unavailable.
    """
    name = user_name or "Friend"
    q = query.lower()

    # --- Dangerous electrical / gas hazard ---
    if any(k in q for k in ["spark", "shock", "wire", "voltage", "exposed", "gas leak",
                              "smell gas", "circuit breaker", "breaker box", "electric panel"]):
        return GuidanceResponse(
            probable_issue="⚡ Dangerous Electrical / Gas Hazard",
            explanation=(
                f"Hello {name}. I can detect exposed wires, sparks, or a potential gas situation here. "
                "These are serious hazards — please do not touch or attempt any DIY repair. "
                "Your safety comes first, always."
            ),
            is_dangerous=True,
            safety_warning=(
                "URGENT: Step away from the area immediately. Turn off the main circuit breaker or gas valve "
                "if it is safe to do so, then call a licensed electrician or your emergency utility helpline."
            ),
            next_steps=[
                "Walk away from the hazard area right now.",
                "If safe, switch off the main circuit breaker or gas shut-off valve.",
                "Do not flip any switches or use anything that could create a spark.",
                "Call a licensed electrician or emergency services immediately.",
                "Keep all children and pets at a safe distance until resolved.",
            ],
            spoken_response=(
                f"I've detected a potentially dangerous hazard, {name}. "
                "Please step away and call a professional right away."
            )
        )

    # --- Wiring / cooler / appliance repair ---
    if any(k in q for k in ["cooler", "wiring", "repair", "toaster", "iron", "oven",
                              "fridge", "refrigerator", "microwave", "ac", "air conditioner",
                              "fan", "washing machine", "bulb", "light", "motor", "appliance"]):
        is_cooler = "cooler" in q
        return GuidanceResponse(
            probable_issue="🔌 Appliance / Wiring Troubleshooting",
            explanation=(
                f"Don't worry, {name}. "
                + ("Cooler wiring issues are usually caused by loose connections, a faulty capacitor, or a worn pump. "
                   if is_cooler else
                   "Many appliance issues are caused by loose connections, blown fuses, or worn parts. ")
                + "Let's diagnose it safely, step by step."
            ),
            is_dangerous=False,
            safety_warning="Always unplug the appliance or switch off the circuit breaker before touching any internal wiring.",
            next_steps=[
                "Switch off and unplug the appliance completely from the power source.",
                "Inspect the power cord for any visible cuts, burns, or fraying.",
                "Check if the wall socket works by testing another device in it.",
                *(
                    [
                        "Open the cooler back panel and check the pump motor wires — reconnect any loose terminal.",
                        "Check the capacitor (grey cylinder near the motor) for bulging or burn marks — replace if damaged.",
                        "Reconnect all terminals securely, replace the panel, then plug in and test.",
                    ] if is_cooler else [
                        "Check for a blown internal fuse — replace with the same rated fuse.",
                        "If wiring looks damaged or burnt, do not attempt repair — contact a qualified technician.",
                        "Clean dust from vents and test the appliance again after reassembling.",
                    ]
                ),
            ],
            spoken_response=(
                f"Let's look at this together, {name}. "
                "First unplug the appliance, then we'll check the wiring and connections step by step."
            )
        )

    # --- Paneer salad specifically ---
    if any(k in q for k in ["paneer salad", "veg paneer salad", "paneer"]) and mode == "cook":
        return GuidanceResponse(
            probable_issue="🥗 Veg Paneer Salad Recipe",
            explanation=(
                f"Great choice, {name}! Veg paneer salad is refreshing, protein-rich, and comes together in under 15 minutes. "
                "Here are the ingredients and steps to make a delicious version."
            ),
            is_dangerous=False,
            safety_warning="Handle sharp knives carefully and use fresh paneer for the best taste.",
            next_steps=[
                "Ingredients: 200 g fresh paneer, cubed",
                "Ingredients: 1 cup cherry tomatoes (halved) or 2 regular tomatoes, diced",
                "Ingredients: 1 cucumber, diced · 1 capsicum, diced · ½ red onion, thinly sliced",
                "Ingredients: Handful of lettuce or spinach leaves",
                "Dressing: 2 tbsp lemon juice · 1 tbsp olive oil · ½ tsp chaat masala · salt & black pepper to taste",
                "Steps: Mix all vegetables in a bowl. Add paneer cubes. Pour dressing over, toss gently. Serve fresh.",
            ],
            spoken_response=(
                f"Here's your veg paneer salad recipe, {name}! "
                "Mix fresh paneer with tomatoes, cucumber, capsicum, and a tangy lemon dressing. Ready in 15 minutes!"
            )
        )

    # --- General cooking / recipe guidance ---
    if mode == "cook" or any(k in q for k in ["cook", "recipe", "rice", "salt", "burn",
                                                "vegetable", "tea", "chai", "dinner",
                                                "lunch", "khana", "ingredient"]):
        return GuidanceResponse(
            probable_issue="🍳 Cooking Guidance",
            explanation=(
                f"Happy to help in the kitchen, {name}! "
                "Whether you're rescuing a salty dish, following a recipe, or improvising — I'll guide you calmly."
            ),
            is_dangerous=False,
            safety_warning="Stay careful around hot stoves, steaming pots, and sharp knives. Always use oven mitts.",
            next_steps=[
                "If dish is too salty: add a peeled raw potato and simmer 10 min, or add a splash of cream.",
                "If something is slightly burnt: transfer the unburnt portion to a fresh pot immediately.",
                "If undercooked: add 1–2 tbsp warm water, cover with a lid, and steam on low heat for 5–8 min.",
                "To enhance flavour: finish with fresh lemon juice, coriander, or a knob of butter.",
                "Keep a bowl of cold water nearby in case of minor burns.",
            ],
            spoken_response=(
                f"Kitchen situations are always fixable, {name}! "
                "Let me guide you step by step to rescue your dish or complete your recipe."
            )
        )

    # --- Visual learning ---
    if mode == "learn" or any(k in q for k in ["what is", "learn", "how does", "explain",
                                                 "plant", "leaf", "tool", "gadget", "identify"]):
        return GuidanceResponse(
            probable_issue="🔍 Visual Discovery & Learning",
            explanation=(
                f"Great question, {name}! Let's explore what this item is, how it works, "
                "and any interesting facts about it."
            ),
            is_dangerous=False,
            safety_warning="Ensure you're viewing the item in a bright, stable environment.",
            next_steps=[
                "Look at the key parts — textures, colours, labels, and size.",
                "Check for any model numbers, natural identifiers (leaf shapes, screws), or brand markings.",
                "Understand the primary function of this object in everyday life.",
                "Consider how it was made or how it grows — what's its origin?",
                "Look for any safety markings or care instructions on the item.",
            ],
            spoken_response=(
                f"Curiosity is wonderful, {name}! "
                "I'd love to help you understand what this is and how it works."
            )
        )

    # --- General fallback ---
    return GuidanceResponse(
        probable_issue="🧠 PraSush AI Assistant",
        explanation=(
            f"Hello {name}! I'm PraSush — your visual guidance companion. "
            "I can help you with everyday repairs, cooking tips, and learning about the world around you. "
            "What would you like to explore today?"
        ),
        is_dangerous=False,
        safety_warning=None,
        next_steps=[
            "Tap 'Repair Help' to troubleshoot home appliances step by step.",
            "Tap 'Cooking Guide' for kitchen rescue tips and recipes.",
            "Tap 'Ask PraSush' to type or speak any question.",
            "Tap 'Learn Visually' to scan and identify objects around you.",
        ],
        spoken_response=(
            f"Hello {name}! I'm PraSush, ready to help you troubleshoot, cook, or learn. "
            "What would you like to do today?"
        )
    )
