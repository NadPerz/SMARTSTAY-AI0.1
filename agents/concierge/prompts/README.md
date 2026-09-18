# Concierge intent guidance

If an LLM classifier is added, it must classify room inventory requests as
`Reservation` with `operation="search_rooms"` rather than `FAQ`.

Room-search examples:

- “Find available deluxe rooms for 2 guests from December 1 to December 4,
  2026” -> `search_rooms`
- “What rooms are available for two people next weekend?” -> `search_rooms`
- “Do you have a suite from June 12 to 15?” -> `search_rooms`

Extract and pass `check_in_date`, `check_out_date`, `room_type`, and `guests`
to the search tool. FAQ is reserved for informational questions about hotel
policies and services, such as “What is the cancellation policy?”.
