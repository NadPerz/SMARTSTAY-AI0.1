# Concierge services

`entities.py` extracts booking entities (ISO check-in/check-out dates, guest
count, and normalized room type) from free text without requiring a model.

`rag.py` chunks the Markdown policies in `knowledge_base/documents`, embeds
them with FastEmbed (`BAAI/bge-small-en-v1.5` via ONNX Runtime), and searches
a FAISS inner-product index.
The Concierge uses those results for FAQ responses and returns an explicit
“can't verify” response when dependencies, documents, or a confidence
threshold do not provide supporting policy text. The current `0.72` threshold
is based on `scripts/debug_rag_scores.py`: the unsupported pool/shuttle query
peaked at `0.625427`, while the supported breakfast query reached `0.824990`.

Run the score diagnostic from the repository root with:

```powershell
$env:PYTHONPATH = ".;backend"
backend\venv\Scripts\python.exe scripts\debug_rag_scores.py
```
