import os
from transformers import pipeline, AutoTokenizer
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

# Charger DistilBERT avec cache
@lru_cache(maxsize=3600)
def load_sentiment_analyzer():
    """Charge le modèle avec gestion de la troncature"""
    model_name = "nlptown/bert-base-multilingual-uncased-sentiment"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    return pipeline(
        "sentiment-analysis",
        model=model_name,
        tokenizer=tokenizer,
        truncation=True,
        max_length=512,
        device=0 if os.environ.get("USE_GPU", "false").lower() == "true" else -1
    )

def analyze_sentiments(reviews, batch_size=8):
    """Analyse les sentiments avec gestion des textes longs"""
    if not reviews:
        return []

    analyzer = load_sentiment_analyzer()
    texts = []

    for review in reviews:
        if not isinstance(review, dict) or 'text' not in review:
            continue

        text = review['text']
        if not text or not isinstance(text, str):
            continue

        # Troncature manuelle si nécessaire
        tokens = analyzer.tokenizer.tokenize(text)
        if len(tokens) > 512:
            tokens = tokens[:510]  # Garde 2 tokens pour [CLS] et [SEP]
            text = analyzer.tokenizer.convert_tokens_to_string(tokens)
        texts.append(text)

    if not texts:
        return []

    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            batch_results = analyzer(batch)
            results.extend(batch_results)
        except Exception as e:
            print(f"Erreur batch {i}: {e}")
            results.extend([{"label": "NEUTRAL", "score": 0.5}] * len(batch))

    return results
