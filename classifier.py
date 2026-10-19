"""Classificazione euristica locale: nessuna richiesta API aggiuntiva."""
import re

RULES = [
    ("Nintendo Switch 2", r"\b(?:nintendo\s+)?switch\s*2\b"),
    ("Nintendo Switch", r"\b(?:nintendo\s+)?switch\b|\bjoy[ -]?con\b"),
    ("Nintendo 3DS", r"\b(?:new\s+)?(?:nintendo\s+)?3ds\s*(?:xl|ll)?\b"),
    ("Nintendo 2DS", r"\b(?:new\s+)?(?:nintendo\s+)?2ds\s*(?:xl|ll)?\b"),
    ("Nintendo DS", r"\b(?:nintendo\s+)?(?:dsi|ds\s*lite|ds\s*fat|ds)\b"),
    ("Game Boy Advance", r"\b(?:game\s*boy\s*advance|gba)(?:\s*sp)?\b"),
    ("Game Boy Color", r"\b(?:game\s*boy\s*color|gbc)\b"),
    ("Game Boy", r"\bgame\s*boy\b|\bgameboy\b"),
    ("Nintendo 64", r"\b(?:nintendo\s*64|n64)\b"),
    ("Super Nintendo", r"\b(?:super\s*nintendo|snes)\b"),
    ("Nintendo NES", r"\b(?:nintendo\s*entertainment\s*system|nes)\b"),
    ("Nintendo Wii U", r"\bwii\s*u\b"),
    ("Nintendo Wii", r"\bwii\b"),
    ("Nintendo GameCube", r"\b(?:game\s*cube|gamecube|ngc)\b"),
    ("PlayStation 5", r"\b(?:playstation\s*5|ps\s*5)\b"),
    ("PlayStation 4", r"\b(?:playstation\s*4|ps\s*4)\b"),
    ("PlayStation 3", r"\b(?:playstation\s*3|ps\s*3)\b"),
    ("PlayStation 2", r"\b(?:playstation\s*2|ps\s*2)\b"),
    ("PlayStation 1", r"\b(?:playstation(?:\s*1)?|ps\s*1|psx)\b"),
    ("PS Vita", r"\b(?:ps\s*vita|playstation\s*vita|psvita)\b"),
    ("PSP", r"\b(?:psp|playstation\s*portable)\b"),
    ("Xbox Series", r"\bxbox\s*series\s*[xs]\b"),
    ("Xbox One", r"\bxbox\s*one\b"),
    ("Xbox 360", r"\bxbox\s*360\b"),
    ("Xbox", r"\bxbox\b"),
    ("Sega Dreamcast", r"\bdreamcast\b"),
    ("Sega Saturn", r"\b(?:sega\s*)?saturn\b"),
    ("Sega Mega Drive", r"\b(?:mega\s*drive|genesis)\b"),
    ("Sega Game Gear", r"\bgame\s*gear\b"),
    ("Atari", r"\batari\b"),
]
COMPILED = [(name, re.compile(pattern, re.IGNORECASE)) for name, pattern in RULES]

def classify(title):
    text = str(title or "")
    for name, pattern in COMPILED:
        if pattern.search(text):
            return name
    return "Altri / da classificare"
