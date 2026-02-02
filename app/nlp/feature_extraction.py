import spacy
import numpy as np
import faiss
import networkx as nx
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize
from typing import List, Dict
from app.logger import logger

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# python -m spacy download en_core_web_trf
nlp = spacy.load("en_core_web_trf")
sentence_transformer = SentenceTransformer(EMBED_MODEL)

# ----------------------------
# Vector Embedding using sentence-transformers
# ----------------------------
def embed_text(texts: List[str]):
    vecs = sentence_transformer.encode(
        texts,
        convert_to_numpy=True,   # VERY IMPORTANT
        show_progress_bar=False,
        normalize_embeddings=False  # we normalize manually
    )
    vecs = normalize(vecs, axis=1)  # returns float64
    vecs = np.ascontiguousarray(vecs.astype(np.float32))
    return vecs

def extract_features_nlp(claim: str) -> List[str]:
    """
    NLP-based claim tech feature extraction using dependency + noun phrase parsing
    """
    doc = nlp(claim)  # full linguistic parse tree of the claim.
    features = set()

    # Extract noun chunks, minimal noun phrase, tech component of patent novelty.
    for chunk in doc.noun_chunks:
        if len(chunk.text) > 4: # avoid a, an, the, etc.
            features.add(chunk.text.lower())

    # Extract verb-object patterns, extract "control motor"
    for token in doc:
        if token.pos_ == "VERB":
            dobj = [child for child in token.children if child.dep_ in ("dobj", "pobj")]
            for obj in dobj:
                phrase = f"{token.lemma_} {obj.text}" # canonicalize verbs.
                features.add(phrase.lower())

    logger.info(f"Extracted features: {features}")
    return list(features)


# ----------------------------
# LLM-assisted Feature Refinement (stub)
# ----------------------------
def llm_refine_features(features: List[str]) -> List[str]:
    """
    Replace with OpenAI / Claude / local LLM call.
    This stub simulates semantic normalization.
    """
    refined = []
    for f in features:
        f = f.replace("performing", "perform")
        refined.append(f)
    return list(set(refined))

# ----------------------------
# CPC Prediction (Stub ML Model)
# ----------------------------
def predict_cpc_codes(claim: str) -> List[str]:
    """
    Replace with fine-tuned transformer classifier.
    This stub maps keywords to CPC.
    """
    mapping = {
        "consensus": "G06F 9/50",
        "leader election": "G06F 9/54",
        "distributed": "G06F 9/52",
        "lock": "G06F 9/48"
    }

    preds = set()
    text = claim.lower()

    for k, v in mapping.items():
        if k in text:
            preds.add(v)

    return list(preds) if preds else ["G06F 9/50"]


# ----------------------------
# CPC Expansion Graph
# ----------------------------

def build_cpc_graph():
    G = nx.Graph()
    edges = [
        ("G06F 9/50", "G06F 9/52"),
        ("G06F 9/52", "G06F 9/54"),
        ("G06F 9/54", "G06F 9/56"),
        ("G06F 9/48", "G06F 9/50")
    ]
    G.add_edges_from(edges)
    return G


def expand_cpc(codes: List[str], graph, hops=2) -> List[str]:
    expanded = set(codes)
    for c in codes:
        for node in nx.single_source_shortest_path_length(graph, c, cutoff=hops):
            expanded.add(node)
    return list(expanded)

# ----------------------------
# Vector Index (FAISS)
# ----------------------------
class VectorIndex:
    def __init__(self, dim):
        self.index = faiss.IndexFlatIP(dim)
        self.patent_ids = []

    def add(self, vectors, patent_ids):
        self.index.add(vectors)
        self.patent_ids.extend(patent_ids)

    def search(self, query_vec, k=10):
        if query_vec.ndim == 1:
            query_vec = query_vec.reshape(1, -1)
        query_vec = np.ascontiguousarray(query_vec.astype(np.float32))

        scores, ids = self.index.search(query_vec, k)
        results = []
        for i, idx in enumerate(ids[0]):
            if idx != -1:
                results.append((self.patent_ids[idx], float(scores[0][i])))
        return results


# ----------------------------
# claims → features → CPC → vector → patent retrieval
# ----------------------------
class PatentSearchEngine:
    def __init__(self):
        self.graph = build_cpc_graph()
        self.index = None
        self.patents = []
        self.patent_map = {}

    def build_index(self, patents: List[Dict]):
        self.patents = patents
        self.patent_map = {p["id"]: p for p in patents}
        embeddings = embed_text([p["claim"] for p in patents])

        self.index = VectorIndex(embeddings.shape[1])
        self.index.add(embeddings, [p["id"] for p in patents])

    def search(self, claim: str, k=10):
        features = extract_features_nlp(claim)
        #features = llm_refine_features(features)

        cpc = predict_cpc_codes(claim)
        expanded_cpc = expand_cpc(cpc, self.graph)

        # --- Dual embeddings ---
        q_claim = embed_text([claim])[0]  
        q_feat  = embed_text([" ".join(features)])[0]
        vec_results_claim = self.index.search(q_claim, k=100)
        vec_results_feat  = self.index.search(q_feat,  k=100)

        # --- Score fusion ---
        scores = {}
        for pid, score in vec_results_claim:
            scores[pid] = scores.get(pid, 0) + 0.55 * score

        for pid, score in vec_results_feat:
            scores[pid] = scores.get(pid, 0) + 0.30 * score

        # CPC filter + rerank
        final = []
        for pid, base_score in scores.items():
            p = self.patent_map[pid]
            cpc_overlap = len(set(p["cpc"]) & set(expanded_cpc))
            total = (
                base_score
                + 0.15 * cpc_overlap
            )
            final.append((p, total))

        final.sort(key=lambda x: -x[1])
        return final[:k]

if __name__ == "__main__":
    patents = [
        {
            "id": "P1",
            "claim": "A distributed consensus system using leader election and quorum voting",
            "cpc": ["G06F 9/50", "G06F 9/54"]
        },
        {
            "id": "P2",
            "claim": "A distributed locking mechanism using leases",
            "cpc": ["G06F 9/48"]
        },
        {
            "id": "P3",
            "claim": "A centralized scheduling system",
            "cpc": ["G06F 9/52"]
        }
    ]
    engine = PatentSearchEngine()
    engine.build_index(patents)

    query = "A fault-tolerant distributed system for leader election using consensus"

    results = engine.search(query, k=5)

    print("\nTop Matches:\n")
    for p, score in results:
        print(f"{p['id']} | score={score:.3f} | {p['claim']}")
