# metrics/metrics.py
import time
from typing import Dict, Any, List
from rouge_score import rouge_scorer
from bert_score import score as bert_score
import textstat
import spacy

# Load NLP & scorers once
_NLP = spacy.load("it_core_news_md")
_ROUGE = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeLsum"], use_stemmer=True)

def length_metrics(original: str, summary: str, modo: int) -> Dict[str, float]:
    ow = max(1, len(original.split()))
    sw = len(summary.split())
    target_ratio = max(1e-9, modo / 100.0)
    ratio = sw / ow
    dev_pct = abs(ratio - target_ratio) / target_ratio * 100.0
    return {
        "words_original": ow,
        "words_summary": sw,
        "compression_ratio": ratio,
        "length_deviation_pct": dev_pct,
    }

def rouge_metrics(reference: str, summary: str) -> Dict[str, float]:
    # If you don't have a reference, you could (weakly) use original text as reference.
    scores = _ROUGE.score(reference, summary)
    return {
        "rouge1_f": scores["rouge1"].fmeasure,
        "rouge2_f": scores["rouge2"].fmeasure,
        "rougeL_f": scores["rougeLsum"].fmeasure,
    }

def bertscore_metrics(reference: str, summary: str) -> Dict[str, float]:
    # BERTScore supports 'it'; requires internet on first run to download weights.
    P, R, F1 = bert_score([summary], [reference], lang="it", rescale_with_baseline=True)
    return {
        "bertscore_precision": float(P.mean()),
        "bertscore_recall": float(R.mean()),
        "bertscore_f1": float(F1.mean()),
    }

def readability_metrics(summary: str) -> Dict[str, float]:
    # Note: textstat formulas are English-oriented; use for trend monitoring.
    sentences = max(1, summary.count(".") + summary.count("?") + summary.count("!"))
    return {
        "reading_ease": textstat.flesch_reading_ease(summary),
        "smog_index": textstat.smog_index(summary),
        "avg_sentence_length": len(summary.split()) / sentences,
    }

def entity_consistency(original: str, summary: str) -> Dict[str, float]:
    def ents(text: str):
        return set((e.text.strip(), e.label_) for e in _NLP(text).ents)
    o = ents(original)
    s = ents(summary)
    if not (o or s):
        return {"entity_jaccard": 1.0, "entities_src": 0, "entities_sum": 0}
    inter = len(o & s)
    union = len(o | s) if (o | s) else 1
    return {"entity_jaccard": inter / union, "entities_src": len(o), "entities_sum": len(s)}
