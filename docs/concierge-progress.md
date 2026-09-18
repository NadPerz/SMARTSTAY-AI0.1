# Concierge NLP/IR Progress

This document summarizes the Concierge work completed so far. It is for
reading and handoff only; deleting or ignoring it does not change application
behavior.

## 1. Entity extraction

The Concierge now extracts booking information from natural-language
messages in `agents/concierge/services/entities.py`:

- `check_in_date`
- `check_out_date`
- `guests`
- `room_type`

Dates are normalized to ISO format (`YYYY-MM-DD`). Short ranges such as
`June 12 to 15` reuse the first date's month and year for the checkout date.

Example:

```text
Book a king room for 2 guests from October 6 to October 9
```

Extracted values:

```json
{
  "check_in_date": "YYYY-10-06",
  "check_out_date": "YYYY-10-09",
  "guests": 2,
  "room_type": "king"
}
```

## 2. Reservation delegation

`agents/concierge/agent.py` merges extracted entities into the structured
reservation payload. Explicit values already supplied in `payload` take
precedence over extracted values.

When a booking request has a room type but no `room_id`, Concierge searches
available rooms first:

- One matching room: its `room_id` is used.
- Multiple matching rooms: the guest is asked to choose one.
- No matching rooms: a clear availability error is returned.
- A failed room search returns the delegated error instead of trying to read
  missing room data.

`room_type` is removed before calling `create_booking`, because that operation
requires `room_id`.

## 3. FAQ intent and cancellation handling

FAQ questions are routed to the policy retriever instead of being treated as
bookings.

For example:

```text
What is the cancellation policy?
```

is an FAQ and retrieves the cancellation policy.

Structured cancellation requests remain reservation operations even if their
message contains policy words:

```json
{
  "message": "Cancel my booking and refund the charge",
  "operation": "cancel_booking",
  "payload": {
    "booking_id": 1,
    "confirm": true
  }
}
```

The explicit `operation` takes priority over FAQ classification.

## 4. Minimal RAG pipeline

`agents/concierge/services/rag.py` implements the policy retrieval pipeline:

1. Load Markdown hotel policy documents.
2. Split documents into overlapping chunks.
3. Generate embeddings using FastEmbed and ONNX Runtime.
4. Store normalized vectors in a FAISS inner-product index.
5. Retrieve relevant chunks.
6. Remove low-confidence matches.
7. Return the answer and policy source filenames.

The embedding model is:

```text
BAAI/bge-small-en-v1.5
```

The RAG dependencies are declared in `backend/requirements.txt`:

```text
fastembed
faiss-cpu
```

FastEmbed replaced `sentence-transformers` because the PyTorch dependency
caused a Windows `torch.dll` Application Control error.

## 5. Policy documents

The current policy documents are in `knowledge_base/documents/`:

- `breakfast-policy.md`
- `cancellation-policy.md`
- `check-in-and-check-out.md`
- `parking-policy.md`
- `pet-policy.md`
- `wifi-policy.md`

## 6. Retrieval confidence and fallback

FAQ retrieval uses a confidence threshold and a small result count. The
current behavior is:

- Supported questions return only the strongest relevant policy results.
- Unsupported questions return no sources.
- Failed model loading or retrieval returns:

```text
I can't verify that from the hotel policies right now.
```

When retrieval completes but no chunk passes the confidence threshold, the
response is:

```text
I can't verify that from the hotel policies.
```

The unsupported test question is:

```text
Does the hotel have a swimming pool and airport shuttle?
```

It must return an empty `sources` list.

## 7. Score debugging

The script `scripts/debug_rag_scores.py` prints the raw similarity score for
every policy chunk for:

- The unsupported swimming-pool/airport-shuttle question.
- A supported breakfast question.

Run it from the repository root:

```powershell
$env:PYTHONPATH = ".;backend"
backend\venv\Scripts\python.exe scripts\debug_rag_scores.py
```

The measured examples used to select the current threshold were:

- Unsupported query maximum: approximately `0.625`
- Supported breakfast result: approximately `0.825`

## 8. Testing completed

Concierge regression tests cover:

- Date, guest-count, and room-type extraction.
- Short date ranges.
- Entity propagation into reservation delegation.
- Explicit cancellation operation routing.
- Cancellation-policy FAQ routing.
- Room-search failure propagation.
- Breakfast FAQ retrieval.
- Check-in/check-out FAQ retrieval.
- Unsupported FAQ fallback.
- Embedding backend failure fallback.

Latest validation:

```text
Concierge tests: 10 passed
Full test suite: 75 passed
```

The full suite also reports existing deprecation and JWT key-length warnings;
these did not fail the tests.

## 9. Running the backend locally

From PowerShell:

```powershell
cd D:\SMARTSTAY-AI0.1\backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = ".;.."
uvicorn app.main:app --reload --port 8000
```

Then open:

```text
http://localhost:8000/docs
```

Use `POST /auth/register`, authorize Swagger with the returned bearer token,
and then test `POST /concierge/chat`.

Example FAQ request:

```json
{
  "message": "What time is check-in and check-out?",
  "operation": null,
  "payload": {}
}
```

Example unsupported question:

```json
{
  "message": "Does the hotel have a swimming pool and airport shuttle?",
  "operation": null,
  "payload": {}
}
```
