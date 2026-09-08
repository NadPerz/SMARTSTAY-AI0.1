#!/usr/bin/env bash
set -euo pipefail

echo "Adding evaluation/ folder..."
mkdir -p evaluation/datasets evaluation/ir evaluation/nlp evaluation/agents evaluation/security

cat > evaluation/README.md <<'EOF'
# Evaluation

Quantitative evidence for the marking criteria (blueprint section 20).
Each subfolder holds a small, reproducible test set and a script/notebook
that computes the metric — not just a written claim.

- datasets/   — labelled/curated queries and expected results (IR, intent, NER, sentiment)
- ir/         — Precision@K, Recall@K, Hit@K scripts for retrieval
- nlp/        — accuracy/F1 scripts for intent, NER, sentiment, aspect extraction
- agents/     — task success rate + delegation accuracy test scripts
- security/   — pass/fail scripts for auth, prompt-injection, rate-limit tests

Add results here as you build each component — do not wait until the final week.
EOF

cat > evaluation/datasets/README.md <<'EOF'
# Evaluation datasets

Small labelled test sets, e.g.:
- intent_queries.jsonl        (query -> expected intent)
- ner_examples.jsonl          (text -> expected entities)
- retrieval_queries.jsonl     (query -> expected relevant doc ids)
- sentiment_reviews.jsonl     (review text -> expected sentiment)
EOF

echo "Replacing bare .gitkeep files with explanatory READMEs..."

declare -A folder_notes=(
  ["agents/common/tests"]="Shared tests for agent base classes and message schemas."
  ["agents/common/protocols"]="A2A-style message contract definitions (see a2a_protocol.md)."
  ["agents/concierge/prompts"]="System/task prompts for the Concierge Agent's LLM calls."
  ["agents/concierge/schemas"]="Pydantic schemas for Concierge request/response payloads."
  ["agents/concierge/services"]="Business logic the Concierge agent.py delegates to (intent handling, RAG calls)."
  ["agents/concierge/tests"]="Unit tests for Concierge intent/entity extraction and delegation."
  ["agents/concierge/tools"]="Tool wrappers the Concierge agent is allowed to call (e.g. retrieve_hotel_info)."
  ["agents/reservation/schemas"]="Pydantic schemas for booking/availability requests and responses."
  ["agents/reservation/services"]="Booking business logic called by the Reservation agent's tools."
  ["agents/reservation/tests"]="Unit tests for availability, booking, and cancellation flows."
  ["agents/reservation/tools"]="check_availability / create_booking / cancel_booking tool implementations."
  ["agents/recommendation/tests"]="Unit tests for ranking and recommendation retrieval."
  ["agents/feedback/tests"]="Unit tests for sentiment/aspect extraction and summarization."
)

for dir in "${!folder_notes[@]}"; do
  if [ -d "$dir" ]; then
    rm -f "$dir/.gitkeep"
    echo "# ${folder_notes[$dir]}" > "$dir/README.md"
    echo "Updated: $dir/README.md"
  else
    echo "SKIP (not found): $dir"
  fi
done

echo ""
echo "Done. Review changes with: git status"
