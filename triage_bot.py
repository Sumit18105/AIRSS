# triage_bot.py — Simple emergency helper (NOT a doctor)

from datetime import datetime

DISCLAIMER = (
    "⚠️ This chatbot is NOT a doctor. "
    "If there is severe pain, heavy bleeding, breathing problems, "
    "chest pain, confusion, or the person is not waking up, "
    "seek emergency medical help immediately."
)

def triage_reply(message: str) -> str:
    """
    Very simple rule-based helper for post‑rescue situations.
    Message is plain text from user.
    Returns plain text response.
    """

    if not message or not message.strip():
        return (
            "I can give you basic first‑aid style guidance after rescue, "
            "but I cannot provide medical treatment or diagnosis.\n\n"
            + DISCLAIMER
        )

    text = message.lower()

    # Red‑flag emergencies
    red_flags = [
        "not breathing", "stopped breathing", "no breathing",
        "can't breathe", "cannot breathe", "breathing problem",
        "chest pain", "severe chest", "very bad chest",
        "unconscious", "not waking", "not responding",
        "heavy bleeding", "bleeding a lot", "blood everywhere",
        "seizure", "fits", "convulsion",
    ]
    if any(flag in text for flag in red_flags):
        return (
            "This sounds like a possible life‑threatening emergency.\n"
            "- Make sure the scene is safe for you.\n"
            "- Do NOT move the person if you suspect a head, neck, or spine injury.\n"
            "- Call your local emergency number or go to the nearest hospital **immediately**.\n\n"
            + DISCLAIMER
        )

    # Bleeding / wound
    if any(w in text for w in ["bleeding", "cut", "wound", "injury", "blood"]):
        return (
            "For bleeding or wounds:\n"
            "- If there is visible bleeding, apply firm direct pressure with a clean cloth.\n"
            "- Keep the injured part elevated if possible.\n"
            "- Do NOT remove deeply embedded objects.\n"
            "- If bleeding does not slow down in a few minutes, or blood is spurting, "
            "go to a hospital immediately.\n\n"
            + DISCLAIMER
        )

    # Fracture / broken bone / sprain
    if any(w in text for w in ["fracture", "broken", "bone", "sprain"]):
        return (
            "For possible fracture or broken bone:\n"
            "- Keep the injured area still; do not try to straighten it.\n"
            "- Support with a makeshift splint (rolled cloth or board) if you know how.\n"
            "- Apply cold pack wrapped in cloth to reduce swelling (not directly on skin).\n"
            "- Arrange medical evaluation as soon as possible.\n\n"
            + DISCLAIMER
        )

    # Burns
    if any(w in text for w in ["burn", "burnt", "burning"]):
        return (
            "For simple burns (not severe):\n"
            "- Cool the burned area with cool **running** water for 15–20 minutes.\n"
            "- Do NOT apply ice, butter, toothpaste, or unknown creams.\n"
            "- Cover loosely with a clean, non‑stick cloth or dressing.\n"
            "- If the burn is large, deep, on face, hands, feet, or genitals, "
            "seek urgent medical care.\n\n"
            + DISCLAIMER
        )

    # Fever / infection‑like
    if any(w in text for w in ["fever", "temperature", "infection", "cough", "cold"]):
        return (
            "For mild fever or infection‑like symptoms:\n"
            "- Encourage fluids (water, oral rehydration if available).\n"
            "- Let the person rest in a comfortable position.\n"
            "- If fever is very high, lasts more than 1–2 days, "
            "or there is difficulty breathing, confusion, or chest pain, "
            "they should see a doctor urgently.\n\n"
            + DISCLAIMER
        )

    # Pain in general
    if "pain" in text:
        return (
            "For general pain after rescue:\n"
            "- Let the person rest in a comfortable position.\n"
            "- Avoid moving the painful area unnecessarily.\n"
            "- If pain is sudden, severe, associated with chest pain, "
            "breathing difficulty, or confusion, go to emergency care.\n\n"
            + DISCLAIMER
        )

    # Default generic response
    return (
        "I can give only very basic first‑aid style suggestions.\n"
        "Please describe the problem — for example: "
        "\"bleeding from leg\", \"severe chest pain\", \"burn on hand\", "
        "or \"possible fracture\".\n\n"
        + DISCLAIMER
    )
