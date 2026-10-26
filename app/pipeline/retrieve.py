"""TF-IDF retrieval over rules and ledger entries."""

from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class Retriever:
    """TF-IDF based retriever for rules and ledger entries."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=5000,
        )
        self.documents: List[Dict[str, Any]] = []
        self.doc_texts: List[str] = []
        self.tfidf_matrix = None

    def index(self, rules: List[Dict[str, Any]], ledger: List[Dict[str, Any]]):
        """Build TF-IDF index from rules and ledger entries."""
        self.documents = []
        self.doc_texts = []

        for rule in rules:
            doc_text = f"{rule['code']} {rule['title']} {rule['text']}"
            self.documents.append({
                "type": "rule",
                "id": rule.get("id"),
                "code": rule["code"],
                "text": rule["text"],
                "title": rule["title"],
                "full_text": doc_text,
            })
            self.doc_texts.append(doc_text)

        for entry in ledger:
            doc_text = f"{entry['claim']} {entry.get('evidence', '')} {entry.get('allowed_wording', '')}"
            self.documents.append({
                "type": "ledger",
                "id": entry.get("id"),
                "claim": entry["claim"],
                "text": doc_text,
                "status": entry.get("status", "active"),
                "full_text": doc_text,
            })
            self.doc_texts.append(doc_text)

        if self.doc_texts:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.doc_texts)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve top-k most relevant documents for a query."""
        if self.tfidf_matrix is None or not self.doc_texts:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0.01:  # Minimum relevance threshold
                doc = self.documents[idx].copy()
                doc["score"] = float(similarities[idx])
                results.append(doc)

        return results
