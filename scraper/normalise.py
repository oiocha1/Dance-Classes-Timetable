"""Turn raw class titles from each booking system into a clean name + standard level."""
import re

# Standard levels, in display order. Key -> (short tag shown after the class name, full label)
LEVELS = {
    "abs_beg": ("Abs Beg", "Absolute Beginners"),
    "foundations": ("Foundations", "Foundations"),
    "beginner": ("Beg", "Beginner"),
    "beg_int": ("Beg/Int", "Beginner/Intermediate"),
    "intermediate": ("Int", "Intermediate"),
    "int_adv": ("Int/Adv", "Intermediate/Advanced"),
    "open": ("Open", "Open"),
    "unlabelled": ("", "Unlabelled"),
}

# Checked in order: the first match wins, so the specific patterns come first.
_LEVEL_PATTERNS = [
    ("abs_beg", r"absolute\s*beg\w*|abs\.?\s*beg\w*"),
    ("int_adv", r"int(?:ermediate)?\s*[/>\-]\s*adv\w*|int\s*to\s*adv"),
    ("beg_int", r"beg(?:inner)?s?\s*[/\-]\s*int(?:ermediate)?|beginner-intermediate"),
    ("intermediate", r"\binter(?:mediate)?\b|\bint\b"),
    ("foundations", r"\bbasics?\b"),
    ("beginner", r"\bbeg(?:inner)?s?\b"),
    ("open", r"\bopen\b"),
]

# Anything that matches is a kids/youth class and is dropped.
_KIDS = re.compile(r"under\s*\d+|\bkids?\b|\bjunior\b|\byouth\b|\bY\d+\s*-\s*Y\d+|\bK\s*-\s*Y\d", re.I)

# A title segment that is *only* a level word, e.g. "Basics" or "Absolute Beginners".
_LEVEL_ONLY = re.compile(
    r"^(absolute\s*beg\w*|abs\.?\s*beg\w*|beg(?:inner)?s?|beg(?:inner)?s?\s*[/\-]\s*int\w*|"
    r"inter(?:mediate)?|int\s*[/>\-]\s*adv\w*|basics?|open)$",
    re.I,
)
# A level word at the very start of a segment, e.g. "Beginner Hip Hop".
_LEVEL_PREFIX = re.compile(
    r"^(absolute\s*beg\w*|abs\.?\s*beg\w*|beg(?:inner)?s?\s*[/\-]\s*int\w*|int\w*\s*[/>\-]\s*adv\w*|"
    r"beg(?:inner)?s?|inter(?:mediate)?|basics?|open)\s+",
    re.I,
)
# A level in brackets, e.g. "Hip Hop (Absolute Beginners)".
_LEVEL_PAREN = re.compile(r"\s*\(([^)]*)\)\s*$")
# Segments that are noise rather than the class name.
_NOISE = re.compile(r"^(pop\s*up|class\s*@\s*xo2s)$", re.I)
_ROOM = re.compile(r"^studio\s+(\w+)$", re.I)
# Wix titles end in the teacher: "Beginner Hip Hop W Jeff", "... with Daniel".
_TEACHER_SUFFIX = re.compile(r"\s+(?:w|with)\s+[\w'.\- ]+$", re.I)


def detect_level(title: str) -> str:
    for key, pattern in _LEVEL_PATTERNS:
        if re.search(pattern, title, re.I):
            return key
    return "unlabelled"


def is_kids(title: str) -> bool:
    return bool(_KIDS.search(title))


def clean_teacher(name: str) -> str:
    """'Han B X Mel | @han_b_k @so____0g' -> 'Han B x Mel'."""
    name = name.split("|")[0]
    name = re.sub(r"@\S+", "", name)
    name = re.sub(r"\s+X\s+", " x ", name)
    return re.sub(r"\s+", " ", name).strip()


def clean_title(title: str, strip_teacher_suffix: bool = False):
    """Return (base class name without level/noise, room or None)."""
    room = None
    kept = []
    for part in (p.strip() for p in title.split("|")):
        if not part:
            continue
        m = _ROOM.match(part)
        if m:
            room = f"Studio {m.group(1)}"
            continue
        if _NOISE.match(part) or _LEVEL_ONLY.match(part):
            continue
        if strip_teacher_suffix:
            part = _TEACHER_SUFFIX.sub("", part)
        paren = _LEVEL_PAREN.search(part)
        if paren and _LEVEL_ONLY.match(paren.group(1).strip()):
            part = part[: paren.start()]
        part = _LEVEL_PREFIX.sub("", part).strip()
        if part and not _LEVEL_ONLY.match(part):
            kept.append(part)
    return " · ".join(kept), room


def display_name(base: str, level: str) -> str:
    """'Popping' + abs_beg -> 'Popping (Abs Beg)'. Empty base -> the level's full label."""
    tag, full = LEVELS[level]
    if not base:
        return full
    return f"{base} ({tag})" if tag else base
