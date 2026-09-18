"""Seed demo recommendation places for local development and manual API
testing.

Safe to re-run: skips any place matched by (name, city) that already
exists. Uses the same five cities as seed_rooms.py (Colombo, Kandy,
Galle, Ella, Negombo).

Usage (from repo root, with backend/ on PYTHONPATH):
    PYTHONPATH=backend python database/seeds/demo_fixtures/seed_places.py
"""

from app.db.database import SessionLocal
from app.models.place import Place

DEMO_PLACES = [
    # --- Colombo ---------------------------------------------------------
    {
        "name": "Ministry of Crab", "category": "restaurant", "cuisine": "seafood",
        "city": "Colombo", "address": "Old Dutch Hospital, Colombo 01",
        "description": "A landmark seafood restaurant inside a restored Dutch-era building, famous for its jumbo crab dishes and lively open kitchen.",
        "budget_tier": "premium", "rating": 4.7, "tags": "seafood,fine dining,landmark",
    },
    {
        "name": "Café Kumbuk", "category": "restaurant", "cuisine": "cafe",
        "city": "Colombo", "address": "Independence Arcade, Colombo 07",
        "description": "A relaxed garden cafe serving all-day breakfast, salads, and coffee in a leafy courtyard setting.",
        "budget_tier": "moderate", "rating": 4.4, "tags": "cafe,brunch,outdoor",
    },
    {
        "name": "Galle Face Green", "category": "attraction", "cuisine": None,
        "city": "Colombo", "address": "Galle Face, Colombo 03",
        "description": "A long oceanside promenade popular at sunset for kite flying, street snacks, and sea breeze walks.",
        "budget_tier": "budget", "rating": 4.5, "tags": "outdoor,sunset,walking",
    },
    {
        "name": "Gangaramaya Temple", "category": "attraction", "cuisine": None,
        "city": "Colombo", "address": "61 Sri Jinarathana Rd, Colombo 02",
        "description": "A historic Buddhist temple complex with an eclectic museum, popular with visitors interested in local culture and architecture.",
        "budget_tier": "budget", "rating": 4.6, "tags": "temple,culture,history",
    },
    {
        "name": "One Galle Face Mall", "category": "shopping", "cuisine": None,
        "city": "Colombo", "address": "1A Centre Road, Colombo 02",
        "description": "A modern waterfront shopping mall with international brands, a food court, and a cinema.",
        "budget_tier": "moderate", "rating": 4.2, "tags": "mall,shopping,family",
    },
    {
        "name": "Colombo Cricket Club Bar", "category": "entertainment", "cuisine": None,
        "city": "Colombo", "address": "Maitland Place, Colombo 07",
        "description": "A relaxed sports bar with live screenings, pub food, and a good selection of local beers.",
        "budget_tier": "moderate", "rating": 4.1, "tags": "bar,nightlife,sports",
    },
    # --- Kandy -------------------------------------------------------------
    {
        "name": "The Empire Cafe", "category": "restaurant", "cuisine": "sri lankan",
        "city": "Kandy", "address": "21 Temple Street, Kandy",
        "description": "A friendly local eatery near the lake serving authentic Sri Lankan rice and curry with fresh, home-style flavors.",
        "budget_tier": "budget", "rating": 4.3, "tags": "local,rice and curry,casual",
    },
    {
        "name": "Slightly Chilled Lounge Bar", "category": "restaurant", "cuisine": "western",
        "city": "Kandy", "address": "29 Dalada Veediya, Kandy",
        "description": "A rooftop restaurant with lake views serving Western comfort food alongside local dishes.",
        "budget_tier": "moderate", "rating": 4.4, "tags": "rooftop,lake view,western",
    },
    {
        "name": "Temple of the Sacred Tooth Relic", "category": "attraction", "cuisine": None,
        "city": "Kandy", "address": "Sri Dalada Veediya, Kandy",
        "description": "Sri Lanka's most revered Buddhist temple, housing a relic of the tooth of the Buddha, with daily rituals and ornate architecture.",
        "budget_tier": "budget", "rating": 4.8, "tags": "temple,culture,unesco",
    },
    {
        "name": "Royal Botanical Gardens Peradeniya", "category": "attraction", "cuisine": None,
        "city": "Kandy", "address": "Peradeniya, Kandy",
        "description": "Expansive botanical gardens with giant bamboo groves, an orchid house, and a famous avenue of royal palms.",
        "budget_tier": "budget", "rating": 4.7, "tags": "outdoor,nature,family",
    },
    {
        "name": "Kandy Lake Walk & Cycling Tour", "category": "activity", "cuisine": None,
        "city": "Kandy", "address": "Kandy Lake, Kandy",
        "description": "A guided cycling and walking tour around Kandy Lake covering local history, wildlife, and viewpoints.",
        "budget_tier": "moderate", "rating": 4.5, "tags": "cycling,outdoor,guided tour",
    },
    # --- Galle ---------------------------------------------------------
    {
        "name": "Fortaleza", "category": "restaurant", "cuisine": "seafood",
        "city": "Galle", "address": "Church Street, Galle Fort",
        "description": "A relaxed seafood restaurant inside Galle Fort's ramparts, known for grilled catch-of-the-day and ocean views.",
        "budget_tier": "moderate", "rating": 4.5, "tags": "seafood,fort,ocean view",
    },
    {
        "name": "Pedlar's Inn Cafe", "category": "restaurant", "cuisine": "cafe",
        "city": "Galle", "address": "92 Pedlar Street, Galle Fort",
        "description": "A cosy heritage-house cafe serving good coffee, sandwiches, and cake in a shaded courtyard.",
        "budget_tier": "budget", "rating": 4.3, "tags": "cafe,heritage,quiet",
    },
    {
        "name": "Galle Fort Ramparts", "category": "attraction", "cuisine": None,
        "city": "Galle", "address": "Galle Fort, Galle",
        "description": "A UNESCO World Heritage colonial fort with cobbled lanes, boutique shops, and sweeping ocean-facing ramparts, best explored at sunset.",
        "budget_tier": "budget", "rating": 4.8, "tags": "unesco,history,sunset",
    },
    {
        "name": "Galle Lighthouse", "category": "attraction", "cuisine": None,
        "city": "Galle", "address": "Rampart Street, Galle Fort",
        "description": "Sri Lanka's oldest lighthouse, a short scenic walk along the fort ramparts with photogenic sea views.",
        "budget_tier": "budget", "rating": 4.4, "tags": "landmark,walking,photography",
    },
    {
        "name": "Galle Fort Snorkeling Trip", "category": "activity", "cuisine": None,
        "city": "Galle", "address": "Jungle Beach, Galle",
        "description": "A half-day guided snorkeling trip to a sheltered reef just outside Galle, suitable for beginners.",
        "budget_tier": "moderate", "rating": 4.2, "tags": "snorkeling,beach,guided tour",
    },
    # --- Ella ---------------------------------------------------------
    {
        "name": "Cafe Chill", "category": "restaurant", "cuisine": "western",
        "city": "Ella", "address": "Main Street, Ella",
        "description": "A backpacker-favourite restaurant with mountain views, serving pizza, burgers, and local rice and curry.",
        "budget_tier": "budget", "rating": 4.3, "tags": "casual,mountain view,backpacker",
    },
    {
        "name": "Nine Arches Bridge", "category": "attraction", "cuisine": None,
        "city": "Ella", "address": "Gotuwala, Ella",
        "description": "An iconic colonial-era railway viaduct surrounded by tea plantations, one of Sri Lanka's most photographed landmarks.",
        "budget_tier": "budget", "rating": 4.8, "tags": "landmark,photography,railway",
    },
    {
        "name": "Little Adam's Peak Hike", "category": "activity", "cuisine": None,
        "city": "Ella", "address": "Ella, Uva Province",
        "description": "A gentle 1-2 hour hike with panoramic views of the Ella Gap, popular at sunrise and requiring no special gear.",
        "budget_tier": "budget", "rating": 4.7, "tags": "hiking,sunrise,outdoor",
    },
    {
        "name": "Ella Flying Ravana Zipline", "category": "activity", "cuisine": None,
        "city": "Ella", "address": "Flying Ravana Adventure Park, Ella",
        "description": "A high-adrenaline zipline circuit over the valley near Ella, with several lines of varying length and height.",
        "budget_tier": "moderate", "rating": 4.4, "tags": "adventure,zipline,valley view",
    },
    {
        "name": "Ella Spice Garden Market", "category": "shopping", "cuisine": None,
        "city": "Ella", "address": "Passara Road, Ella",
        "description": "A small local market and spice garden selling Ceylon tea, spices, and handmade souvenirs.",
        "budget_tier": "budget", "rating": 4.0, "tags": "souvenirs,tea,local market",
    },
    # --- Negombo ---------------------------------------------------------
    {
        "name": "Lagoon View Seafood Restaurant", "category": "restaurant", "cuisine": "seafood",
        "city": "Negombo", "address": "Lewis Place, Negombo",
        "description": "A beachfront restaurant specializing in freshly caught prawns, crab, and fish, popular for first/last-night dinners near the airport.",
        "budget_tier": "moderate", "rating": 4.4, "tags": "seafood,beachfront,dinner",
    },
    {
        "name": "Negombo Fish Market (Lellama)", "category": "attraction", "cuisine": None,
        "city": "Negombo", "address": "Lellama, Negombo",
        "description": "A bustling early-morning fish market where local fishermen sell the day's catch, offering an authentic local scene.",
        "budget_tier": "budget", "rating": 4.1, "tags": "local,morning,authentic",
    },
    {
        "name": "Negombo Beach Sunset Walk", "category": "attraction", "cuisine": None,
        "city": "Negombo", "address": "Negombo Beach, Negombo",
        "description": "A long, calm stretch of golden-sand beach ideal for an evening walk and watching the sunset over the Indian Ocean.",
        "budget_tier": "budget", "rating": 4.3, "tags": "beach,sunset,relaxing",
    },
    {
        "name": "Negombo Lagoon Boat Safari", "category": "activity", "cuisine": None,
        "city": "Negombo", "address": "Negombo Lagoon, Negombo",
        "description": "A guided boat trip through the Negombo Lagoon and mangroves, spotting birdlife and traditional stake-net fishing.",
        "budget_tier": "moderate", "rating": 4.5, "tags": "boat,nature,birdwatching",
    },
    {
        "name": "St. Mary's Church Negombo", "category": "attraction", "cuisine": None,
        "city": "Negombo", "address": "Church Street, Negombo",
        "description": "One of the largest churches in Sri Lanka, known for its ornate painted ceiling reflecting Negombo's Catholic heritage.",
        "budget_tier": "budget", "rating": 4.4, "tags": "church,heritage,architecture",
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        created, skipped = 0, 0
        for data in DEMO_PLACES:
            existing = (
                db.query(Place)
                .filter(Place.name == data["name"], Place.city == data["city"])
                .first()
            )
            if existing:
                skipped += 1
                continue
            db.add(Place(**data))
            created += 1

        db.commit()
        print(f"Seeded {created} new place(s) (skipped {skipped} already present).")
    finally:
        db.close()


if __name__ == "__main__":
    main()