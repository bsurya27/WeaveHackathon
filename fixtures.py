from schemas import PitchDeck

DUMMY_PITCH_DECK = PitchDeck(
    problem=(
        "AI moves faster than anyone can track. Every day brings more papers, threads, "
        "and community discussions than a person can read, and most of it is irrelevant "
        "to any given individual. Existing feeds optimize for engagement, not usefulness."
    ),
    customer=(
        "People who need to stay current on AI — ML researchers, applied AI engineers, and "
        "technical founders. A specific beachhead segment is not yet chosen."
    ),
    solution=(
        "A personal agent that scrapes ArXiv, Reddit, and technical communities overnight, "
        "scores everything against a per-user preference vector, and delivers a grounded "
        "morning briefing. The vector is learned from how you read — ratings, skips, follow-ups."
    ),
    wedge=(
        "The preference vector compounds and is unique per user, so the relevance "
        "advantage can't be copied."
    ),
    current_stage=(
        "Personal prototype. Founder uses it daily. A few interested users, none onboarded. "
        "No funding."
    ),
    founder_background=(
        "Solo founder. Master's in AI from Boston University; specializes in building AI "
        "systems. Strong technically, new to the business side."
    ),
    traction=(
        "Founder is the only daily active user. A few people expressed interest but none "
        "have been onboarded."
    ),
    key_assumptions=[
        "Per-user preference vectors can be learned quickly enough from reading behavior to deliver value.",
        "ArXiv, Reddit, and technical communities cover most of what target users need to track.",
        "A morning briefing is the right delivery format versus real-time feeds.",
        "A viable beachhead exists among ML researchers or applied AI engineers with acute pain.",
    ],
    current_ask=(
        "Turn the personal prototype into a product others can use. Help finding investors "
        "and raising a first round, getting and onboarding real users, and deciding what to "
        "build next."
    ),
)
