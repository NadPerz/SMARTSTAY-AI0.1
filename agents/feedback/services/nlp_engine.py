"""Rule-based sentiment and aspect-extraction engine for guest reviews.

Deliberately NOT backed by spaCy/transformers/an LLM: nothing else in this
repo has an ML/LLM dependency installed yet, and a lexicon approach is
fully deterministic, has zero install/runtime cost, and is easy to unit
test and explain in a viva. See docs/agents/feedback-analytics.md for the
documented upgrade path to a transformer-based pipeline.

Every function here is pure (no DB, no I/O) so it can be tested in
isolation from the rest of the agent.
"""

import re
from typing import Dict, List, Tuple

# Words that flip the sign of sentiment found shortly after them
# ("not good", "wasn't friendly"). Word-final "n't" is checked separately
# so contractions (isn't, wasn't, don't...) are covered without listing
# every one of them.
NEGATIONS = {"not", "no", "never", "none", "without", "hardly", "barely", "cannot"}

# How many tokens after a negation word still count as negated.
_NEGATION_SCOPE = 3

# Deliberately excludes context-dependent words like "cheap" (could be
# praise for value or a complaint about quality) — those are left as
# aspect-only keywords below rather than guessed at.
POSITIVE_WORDS: Dict[str, float] = {
    "amazing": 2.0, "excellent": 2.0, "wonderful": 2.0, "fantastic": 2.0,
    "perfect": 2.0, "outstanding": 2.0, "great": 1.5, "beautiful": 1.5,
    "friendly": 1.5, "helpful": 1.5, "lovely": 1.5, "impressive": 1.5,
    "attentive": 1.5, "love": 1.5, "loved": 1.5, "best": 1.5,
    "welcoming": 1.5, "good": 1.0, "nice": 1.0, "comfortable": 1.0,
    "clean": 1.0, "spacious": 1.0, "delicious": 1.0, "quiet": 1.0,
    "convenient": 1.0, "affordable": 1.0, "fresh": 1.0, "polite": 1.0,
    "recommend": 1.0, "recommended": 1.0, "enjoyed": 1.0, "satisfied": 1.0,
    "pleasant": 1.0, "smooth": 1.0, "fast": 0.5,
}

NEGATIVE_WORDS: Dict[str, float] = {
    "terrible": 2.0, "horrible": 2.0, "awful": 2.0, "worst": 2.0,
    "filthy": 2.0, "unacceptable": 2.0, "rude": 2.0, "bad": 1.5,
    "poor": 1.5, "dirty": 1.5, "unfriendly": 1.5, "disappointing": 1.5,
    "disappointed": 1.5, "overpriced": 1.5, "broken": 1.5, "smelly": 1.5,
    "unhelpful": 1.5, "cramped": 1.0, "slow": 1.0, "uncomfortable": 1.0,
    "noisy": 1.0, "expensive": 1.0, "complaint": 1.0, "complaints": 1.0,
    "problem": 1.0, "problems": 1.0, "issue": 1.0, "issues": 1.0,
    "delayed": 1.0, "understaffed": 1.0, "disorganized": 1.0,
    "mediocre": 1.0, "dated": 0.5, "outdated": 0.5, "small": 0.5, "cold": 0.5,
}

ASPECT_KEYWORDS: Dict[str, List[str]] = {
    "room": ["room", "rooms", "bed", "bedroom", "bathroom", "suite"],
    "staff": ["staff", "receptionist", "reception", "employee", "waiter", "waitress"],
    "breakfast": ["breakfast", "buffet"],
    "price": ["price", "pricing", "cost", "expensive", "cheap", "value", "rate", "rates", "overpriced"],
    "location": ["location", "located", "nearby", "distance", "central"],
    "cleanliness": ["clean", "cleanliness", "dirty", "filthy", "dust", "hygiene", "smell", "smelly"],
    "service": ["service", "check-in", "check in", "checkin", "check-out", "checkout", "front desk"],
}

_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")
_CONTRAST_SPLIT_RE = re.compile(r"\b(?:but|however|although|though|yet)\b", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[a-zA-Z]+(?:'[a-zA-Z]+)?")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def split_clauses(text: str) -> List[str]:
    """Split review text into sentence- and clause-level chunks.

    Splitting further on contrastive conjunctions ("but", "however", ...)
    is what lets a single sentence like "The room was beautiful but
    breakfast was slow" produce two independently-scored clauses instead
    of one sentence-level average that would wash the negative part out.
    """
    clauses: List[str] = []
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        sentence = sentence.strip()
        if not sentence:
            continue
        for part in _CONTRAST_SPLIT_RE.split(sentence):
            part = part.strip(" ,")
            if part:
                clauses.append(part)
    return clauses


def score_clause(clause: str) -> float:
    """Sum of lexicon weights in a clause, with negation flipping the sign
    of any sentiment word found within `_NEGATION_SCOPE` tokens after a
    negation word (so "not good" scores negative, not positive)."""
    score = 0.0
    negation_countdown = 0

    for token in _tokenize(clause):
        is_negation = token in NEGATIONS or token.endswith("n't")
        weight = 0.0
        if token in POSITIVE_WORDS:
            weight = POSITIVE_WORDS[token]
        elif token in NEGATIVE_WORDS:
            weight = -NEGATIVE_WORDS[token]

        if weight != 0.0:
            score += -weight if negation_countdown > 0 else weight

        if is_negation:
            negation_countdown = _NEGATION_SCOPE
        elif negation_countdown > 0:
            negation_countdown -= 1

    return score


def classify_score(score: float) -> str:
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"


def extract_aspect_sentiments(text: str) -> List[Dict[str, object]]:
    """Return one entry per (aspect, clause) match: which aspect was
    mentioned, the sentiment of the specific clause it was mentioned in,
    a rough confidence, and the clause itself as supporting evidence."""
    results: List[Dict[str, object]] = []

    for clause in split_clauses(text):
        clause_lower = clause.lower()
        score = score_clause(clause)
        sentiment = classify_score(score)
        confidence = round(min(1.0, abs(score) / 3.0), 2) if score != 0 else 0.3

        for aspect, keywords in ASPECT_KEYWORDS.items():
            if any(keyword in clause_lower for keyword in keywords):
                results.append(
                    {
                        "aspect": aspect,
                        "sentiment": sentiment,
                        "confidence": confidence,
                        "snippet": clause,
                    }
                )

    return results


def overall_sentiment(text: str) -> Tuple[str, float]:
    """Whole-review sentiment. Labelled "mixed" (not just averaged away)
    when the review contains both a clearly positive and a clearly
    negative clause — e.g. "beautiful room but terrible breakfast" should
    never come out as a falsely-confident "neutral"."""
    clauses = split_clauses(text)
    if not clauses:
        return "neutral", 0.0

    scores = [score_clause(clause) for clause in clauses]
    average = sum(scores) / len(scores)

    has_positive = any(s > 0 for s in scores)
    has_negative = any(s < 0 for s in scores)
    label = "mixed" if has_positive and has_negative else classify_score(average)

    return label, round(average, 2)
