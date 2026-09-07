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
