"""Print FastEmbed/FAISS similarity scores for representative FAQ queries."""

from agents.concierge.services.rag import PolicyRetriever


QUERIES = (
    "Does the hotel have a swimming pool and airport shuttle?",
    "What time is breakfast served and is it included?",
)


def main() -> None:
    retriever = PolicyRetriever()
    for query in QUERIES:
        print(f"\nQUERY: {query}")
        for chunk in sorted(
            retriever.score_chunks(query),
            key=lambda item: item.score,
            reverse=True,
        ):
            print(f"{chunk.score:.6f}\t{chunk.source}\t{chunk.text}")


if __name__ == "__main__":
    main()
