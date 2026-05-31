from schemas import PitchDeck

DUMMY_PITCH_DECK = PitchDeck(
    company="AI Research Curator",
    tagline="A personal agent that surfaces the AI research actually useful to you",
    problem=(
        "AI moves faster than anyone can track. Every day brings more papers, threads, "
        "and community discussions than a person can read, and most of it is irrelevant "
        "to any given individual. Existing feeds optimize for engagement, not usefulness."
    ),
    solution=(
        "A personal agent that scrapes ArXiv, Reddit, and technical communities overnight, "
        "scores everything against a per-user preference vector, and delivers a grounded "
        "morning briefing. The vector is learned from how you read — ratings, skips, follow-ups. "
        "Wedge: the preference vector compounds and is unique per user, so the relevance "
        "advantage can't be copied."
    ),
    market=(
        "People who need to stay current on AI — ML researchers, applied AI engineers, and "
        "technical founders. A specific beachhead segment is not yet chosen."
    ),
    team=(
        "Solo founder. Master's in AI from Boston University; specializes in building AI systems. "
        "Strong technically, new to the business side."
    ),
    ask=(
        "Turn a personal prototype (founder uses it daily; a few interested users, none onboarded; "
        "no funding) into a product others can use. Wants help finding investors and raising a first "
        "round, getting and onboarding real users, and deciding what to build next."
    ),
)