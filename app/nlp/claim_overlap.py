import spacy
import numpy as np
import faiss
import networkx as nx
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize
from typing import List, Dict
from app.logger import logger

# python -m spacy download en_core_web_sm
# Load English language model
nlp = spacy.load("en_core_web_sm")

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2" # 384 dim
sentence_transformer = SentenceTransformer(EMBED_MODEL)
def embed_text(texts: List[str]):
    vecs = sentence_transformer.encode(texts)
    return vecs

def preprocess_claim(text):
    """Clean patent claim text"""
    # Remove claim numbers
    text = re.sub(r'^\d+\.\s*', '', text)
    # Remove excessive whitespace
    text = ' '.join(text.split())
    return text

def extract_noun_verb_phrase(claim: str) -> List[str]:
    """
    NLP-based claim tech feature extraction using dependency + noun phrase parsing
    """
    doc = nlp(claim)  # full linguistic parse tree of the claim.
    # Extract noun chunks
    noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks]
    # Extract verbs (lemmatized form)
    verbs = [token.lemma_.lower() for token in doc if token.pos_ == "VERB"]

    # Combine for Jaccard
    features = set(noun_chunks + verbs)
    logger.info(f"Extracted features: {features}")
    return list(features)

def jaccard_similarity(set1, set2):
    """Calculate Jaccard similarity between two sets (or lists)"""
    s1 = set(set1)
    s2 = set(set2)
    intersection = len(s1.intersection(s2))
    union = len(s1.union(s2))
    return intersection / union if union > 0 else 0

if __name__ == "__main__":
    # Two patent claims
    claim1 = """
    A battery management system comprising an electric motor configured 
    to rotate a propeller and transmit power.
    """

    claim2 = """
    An electric propulsion system including a battery system and a motor 
    that rotates to generate thrust.
    """

    # Extract features
    features1 = extract_noun_verb_phrase(claim1)
    features2 = extract_noun_verb_phrase(claim2)

    # Calculate Jaccard similarity
    similarity = jaccard_similarity(features1, features2)

    print(f"Claim 1 features: {features1}")
    print(f"Claim 2 features: {features2}")
    print(f"Jaccard similarity: {similarity:.3f}")
