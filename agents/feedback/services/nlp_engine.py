"""Sentiment and aspect-extraction engine for guest reviews.

Built on two small, well-established libraries rather than a hand-rolled
lexicon or a full transformer/LLM pipeline:

- spaCy (en_core_web_sm) for tokenization, lemmatization and sentence
  segmentation — so "room"/"rooms"/"roomy" and different tenses all
  normalize to a comparable form for aspect matching, and sentences are
  split linguistically rather than by naive punctuation splitting.
- VADER (Hutto & Gilbert, 2014) for sentiment polarity — a lexicon of
  ~7,500 words tuned for exactly this kind of short, informal text, with
  negation, intensifiers, punctuation and capitalization already handled.
  This replaces an earlier hand-rolled ~70-word lexicon that scored any
  word outside its list as neutral; VADER's much larger, published
  lexicon covers far more real review vocabulary out of the box.

Deliberately still NOT a transformer/LLM pipeline: nothing else in this
repo depends on torch/transformers, and this keeps install size and
startup time small while remaining "real" NLP tooling (spaCy + a
peer-reviewed sentiment lexicon), not ad hoc string matching. See
docs/agents/feedback-analytics.md for the documented upgrade path.

`_NLP` and `_VADER` are loaded once at import time and reused for every
call — reloading a spaCy model per-request would be needlessly slow.
"""

from typing import Dict, List, Tuple

import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_NLP = spacy.load("en_core_web_sm")
_VADER = SentimentIntensityAnalyzer()

# VADER's ~7,500-word lexicon is tuned for general/social-media text and
# was found (during manual REPL testing — see docs/agents/feedback-analytics.md)
# to be missing common hospitality complaint words that carry no
# exclamatory tone but are still clearly negative in a review ("the room
# was small", "breakfast was expensive"). VADER's own supported way to
# domain-adapt without retraining is extending its lexicon directly, on
# its normal valence scale (roughly -4..+4).
_HOSPITALITY_LEXICON: Dict[str, float] = {
    "expensive": -1.5, "overpriced": -2.2, "slow": -1.4, "understaffed": -1.8,
    "cramped": -1.6, "outdated": -1.2, "dated": -1.0, "noisy": -1.5,
    "unhelpful": -2.0,
    "spacious": 1.8, "convenient": 1.6, "comfortable": 1.9, "affordable": 1.4,
    "attentive": 2.0, "welcoming": 2.1, "polite": 1.6,
}
_VADER.lexicon.update(_HOSPITALITY_LEXICON)

# VADER's own recommended thresholds for its compound score (-1..1).
_POSITIVE_THRESHOLD = 0.05
_NEGATIVE_THRESHOLD = -0.05

_CONTRAST_WORDS = {"but", "however", "although", "though", "yet"}

ASPECT_KEYWORDS: Dict[str, List[str]] = {
    "room": ["room", "bed", "bedroom", "bathroom", "suite"],
    "staff": ["staff", "receptionist", "reception", "employee", "waiter", "waitress"],
    "breakfast": ["breakfast", "buffet"],
    "price": ["price", "pricing", "cost", "expensive", "cheap", "value", "rate", "overpriced"],
    "location": ["location", "locate", "nearby", "distance", "central"],
    "cleanliness": ["clean", "cleanliness", "dirty", "filthy", "dust", "hygiene", "smell", "smelly"],
    "service": ["service", "check-in", "check in", "checkin", "check-out", "checkout", "front desk"],
}


def split_clauses(text: str) -> List[str]:
    """Split review text into clause-level chunks: spaCy sentence
    segmentation, then a further split on contrastive conjunctions
    ("but", "however", ...) so mixed sentences like "The room was
    beautiful but breakfast was slow" produce two independently-scored
    clauses instead of one sentence-level average that would wash the
    negative half out.
    """
    clauses: List[str] = []

    for sent in _NLP(text).sents:
        current: List[str] = []
        for token in sent:
            if token.lower_ in _CONTRAST_WORDS and current:
                clause = "".join(current).strip(" ,")
                if clause:
                    clauses.append(clause)
                current = []
                continue
            current.append(token.text_with_ws)

        clause = "".join(current).strip(" ,")
        if clause:
            clauses.append(clause)

    return clauses


def score_clause(clause: str) -> float:
    """VADER's compound sentiment score for a clause, in [-1, 1]."""
    return _VADER.polarity_scores(clause)["compound"]


def classify_score(score: float) -> str:
    """Map a VADER compound score to a label using VADER's own
    recommended thresholds."""
    if score >= _POSITIVE_THRESHOLD:
        return "positive"
    if score <= _NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"


def extract_aspect_sentiments(text: str) -> List[Dict[str, object]]:
    """Return one entry per (aspect, clause) match: which aspect was
    mentioned, the sentiment of the specific clause it was mentioned in,
    VADER's confidence for that clause, and the clause itself as
    supporting evidence.

    Aspect matching checks both the clause's surface text and its
    spaCy lemmas, so "rooms"/"roomy stay" etc. still match the "room"
    keyword without needing every inflection listed by hand.
    """
    results: List[Dict[str, object]] = []

    for clause in split_clauses(text):
        clause_doc = _NLP(clause)
        clause_lower = clause.lower()
        lemma_text = " ".join(token.lemma_.lower() for token in clause_doc)

        scores = _VADER.polarity_scores(clause)
        compound = scores["compound"]
        sentiment = classify_score(compound)
        confidence = round(max(scores["pos"], scores["neg"], scores["neu"]), 2)

        for aspect, keywords in ASPECT_KEYWORDS.items():
            if any(kw in clause_lower or kw in lemma_text for kw in keywords):
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

    has_positive = any(s >= _POSITIVE_THRESHOLD for s in scores)
    has_negative = any(s <= _NEGATIVE_THRESHOLD for s in scores)
    label = "mixed" if has_positive and has_negative else classify_score(average)

    return label, round(average, 4)
