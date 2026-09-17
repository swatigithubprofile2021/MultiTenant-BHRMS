import re


def get_product_grade(query: str, answer: str, docs: list):
    """
    get_product_grade

    Summary of the "Grade"
    Component	| What it uses	| Purpose
    Retrieval	| docs + scores	|Did the DB find the right PDF?
    Faithfulness |	answer + docs	|Did the LLM lie about the numbers?
    Relevance	| query + answer	| Did the bot actually answer the user?
    """
    # --- 1. Retrieval Quality ---
    retrieval_quality = (
        sum(d.metadata.get("original_score", 0) for d in docs) / len(docs)
        if docs
        else 0
    )

    # --- 2. Faithfulness (Anti-Hallucination) ---
    answer_numbers = set(re.findall(r"\d+", answer))
    context_text = " ".join([d.page_content for d in docs])
    context_numbers = set(re.findall(r"\d+", context_text))
    faithfulness = 1.0 if answer_numbers.issubset(context_numbers) else 0.4

    # --- 3. Answer Relevance (Using the Query) ---
    # We strip common "stop words" to focus on real intent
    stop_words = {
        "can",
        "i",
        "get",
        "tell",
        "me",
        "show",
        "please",
        "kindly",
        "want",
        "to",
        "know",
        "my",
        "your",
        "his",
        "her",
        "their",
        "our",
        "an",
        "at",
        "by",
        "for",
        "from",
        "in",
        "into",
        "on",
        "over",
        "to",
        "with",
        "about",
        "regarding",
        "document",
        "information",
        "details",
        "employee",
        "official",
        "applicable",
        "covered",
        "mentioned",
        "what",
        "is",
        "the",
        "are",
        "under",
        "company",
        "policy",
        "types",
        "of",
    }

    query_keywords = set(re.findall(r"\w{3,}", query.lower())) - stop_words

    answer_lower = answer.lower()

    if not query_keywords:
        relevance_score = 1.0
    else:
        # Check for matches
        matches = [word for word in query_keywords if word in answer_lower]

        # PRO-TIP: If the answer is short but contains at least ONE key noun
        # from the query (like "travel" or "cab"), it shouldn't be 0.0.
        relevance_score = len(matches) / len(query_keywords)

        # Soften the penalty: If there is at least one match, give a minimum floor
        if len(matches) > 0 and relevance_score < 0.5:
            relevance_score = 0.5

    # --- 4. Final Weighted Grade ---
    # We now balance all three: Search, Accuracy, and Relevance to the User.
    final_grade = (
        (retrieval_quality * 0.5) + (faithfulness * 0.2) + (relevance_score * 0.3)
    )

    return {
        "score": round(final_grade, 2),
        "status": (
            "Verified"
            if final_grade > 0.7 or (faithfulness == 1.0 and retrieval_quality > 0.6)
            else "Uncertain"
        ),
        "metrics": {
            "retrieval": round(retrieval_quality, 2),
            "faithfulness": faithfulness,
            "relevance": round(relevance_score, 2),
        },
    }
