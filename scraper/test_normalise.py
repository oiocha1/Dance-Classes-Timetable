"""Checks the name/level rules against real class titles. Run: python scraper/test_normalise.py"""
from normalise import clean_teacher, clean_title, detect_level, display_name, is_kids

# (raw title, is it a Wix title?, expected level, expected display name)
CASES = [
    # IMI (Mindbody)
    ("Absolute Beginners | Studio B", False, "abs_beg", "Absolute Beginners"),
    ("Beg/Int Choreography | Studio 1", False, "beg_int", "Choreography (Beg/Int)"),
    ("Pop Up | Int/Adv Collab Choreography | Studio A", False, "int_adv", "Collab Choreography (Int/Adv)"),
    ("Pop Up | Basics | Hip-Hop Foundation | Studio B", False, "foundations", "Hip-Hop Foundation (Foundations)"),
    ("Pop Up | Basics | Foundations | Studio B", False, "foundations", "Foundations (Foundations)"),
    ("Int/Adv Choreography | Studio A", False, "int_adv", "Choreography (Int/Adv)"),
    ("Beginner | House Foundations | Studio B", False, "beginner", "House Foundations (Beg)"),
    ("Pop Up | Open Choreography | Studio 1", False, "open", "Choreography (Open)"),
    # Crossover (Mindbody)
    ("Hip Hop (Beginners)", False, "beginner", "Hip Hop (Beg)"),
    ("Kpop | Good Boy - Taeyang x Gdragon (Beg)", False, "beginner", "Kpop · Good Boy - Taeyang x Gdragon (Beg)"),
    ("Class@XO2S | Popping (Absolute Beginners)", False, "abs_beg", "Popping (Abs Beg)"),
    ("Hip Hop Foundations (Absolute Beginners)", False, "abs_beg", "Hip Hop Foundations (Abs Beg)"),
    ("Hip Hop Rhythm Training (Beginner-Intermediate)", False, "beg_int", "Hip Hop Rhythm Training (Beg/Int)"),
    ("Class@XO2S | Choreography (Abs Beg)", False, "abs_beg", "Choreography (Abs Beg)"),
    ("Choreo (Beg-Int)", False, "beg_int", "Choreo (Beg/Int)"),
    ("Popping/Boogaloo (Intermediate)", False, "intermediate", "Popping/Boogaloo (Int)"),
    ("Class@XO2S | Girls Choreo/Heels (Beg)", False, "beginner", "Girls Choreo/Heels (Beg)"),
    ("Girls Choreo (Absolute Beginners)", False, "abs_beg", "Girls Choreo (Abs Beg)"),
    ("Party Groove / Soul (Beginners)", False, "beginner", "Party Groove / Soul (Beg)"),
    # Movement Nation (Wix)
    ("Kpop W Sam", True, "unlabelled", "Kpop"),
    ("Beginner Hip Hop W Jeff", True, "beginner", "Hip Hop (Beg)"),
    ("Intermediate Choreography W Christian", True, "intermediate", "Choreography (Int)"),
    ("Absolute Beginners W Tracey", True, "abs_beg", "Absolute Beginners"),
    ("Waving Pop up class with Daniel", True, "unlabelled", "Waving Pop up class"),
    ("Beginner Choreo W Rishika", True, "beginner", "Choreo (Beg)"),
    ("Open Choreography W Tiana", True, "open", "Choreography (Open)"),
    # IX (Wix)
    ("Heels | Beginners", True, "beginner", "Heels (Beg)"),
    ("K-pop | Absolute Beginner", True, "abs_beg", "K-pop (Abs Beg)"),
    ("K-pop", True, "unlabelled", "K-pop"),
]
KIDS = ["K-pop (Under 15s)", "Youth K-pop (Y7-Y9)", "Kids K-pop (K-Y3)", "Junior K-pop (Y4-Y6)"]
ADULT = ["Hip Hop (Beginners)", "K-pop | Absolute Beginner", "Heels | Beginners"]
TEACHERS = [("Han B X Mel | @han_b_k @so____0g", "Han B x Mel"), ("Ivy | @ivy.moon", "Ivy"), ("Hu Jeffery", "Hu Jeffery")]

fails = 0
for raw, wix, lvl, name in CASES:
    got_lvl = detect_level(raw)
    got_name = display_name(clean_title(raw, wix)[0], got_lvl)
    if (got_lvl, got_name) != (lvl, name):
        fails += 1
        print(f"FAIL {raw!r}: got ({got_lvl}, {got_name!r}) want ({lvl}, {name!r})")
for t in KIDS:
    if not is_kids(t):
        fails += 1; print(f"FAIL kids not detected: {t}")
for t in ADULT:
    if is_kids(t):
        fails += 1; print(f"FAIL adult marked kids: {t}")
for raw, want in TEACHERS:
    if clean_teacher(raw) != want:
        fails += 1; print(f"FAIL teacher {raw!r} -> {clean_teacher(raw)!r}")
assert clean_title("Absolute Beginners | Studio B")[1] == "Studio B"
print(f"{len(CASES) + len(KIDS) + len(ADULT) + len(TEACHERS)} checks, {fails} failed")
raise SystemExit(1 if fails else 0)
