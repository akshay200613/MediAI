"""
MediAI RAG Evaluation & Benchmark Suite
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.ai.llm.litellm_client import get_llm_client, LiteLLMClient
from core.ai.rag.pipeline import RAGPipeline

# ============================================================================
# Golden Benchmark Dataset
# ============================================================================

GOLDEN_DATASET: list[dict] = [
    {
        "question": "What are the contact numbers for BMH Kozhikode?",
        "expected_keywords": ["contact", "phone", "number", "BMH", "Kozhikode"],
        "expected_category": "hospital_info",
        "reference_answer": "Baby Memorial Hospital (BMH) Kozhikode contact numbers include emergency, reception, and outpatient consultation helpline desks.",
        "note": "Hospital contact information query",
        "answerable": True,
    },
    {
        "question": "What facilities are available at BMH Kozhikode?",
        "expected_keywords": ["facility", "facilities", "department", "service", "BMH"],
        "expected_category": "hospital_info",
        "reference_answer": "BMH Kozhikode provides advanced ICUs, multi-specialty surgical suites, diagnostic imaging, 24/7 emergency trauma care, and outpatient clinics.",
        "note": "Hospital facilities overview",
        "answerable": True,
    },
    {
        "question": "What insurance providers are associated with BMH?",
        "expected_keywords": ["insurance", "provider", "coverage", "policy"],
        "expected_category": "insurance",
        "reference_answer": "BMH Kozhikode is empanelled with major health insurance providers and TPAs for cashless hospitalization.",
        "note": "Insurance partnerships",
        "answerable": True,
    },
    {
        "question": "What medical specialties are available at BMH Kozhikode?",
        "expected_keywords": ["specialty", "specialties", "cardiology", "orthopedic", "department"],
        "expected_category": "hospital_info",
        "reference_answer": "Specialties include Cardiology, Neurology, Orthopedics, Gastroenterology, Oncology, Pediatrics, and General Surgery.",
        "note": "Available specializations",
        "answerable": True,
    },
    {
        "question": "What are the working hours for BMH Kozhikode?",
        "expected_keywords": ["hours", "timing", "open", "working", "schedule"],
        "expected_category": "hospital_info",
        "reference_answer": "BMH Emergency and ICU services operate 24/7. Outpatient consultation clinics operate during scheduled morning and evening hours.",
        "note": "Operating hours",
        "answerable": True,
    },
    {
        "question": "What are the drug interactions for ACE inhibitors?",
        "expected_keywords": ["ACE", "inhibitor", "interaction", "drug", "medication"],
        "expected_category": "clinical_guidelines",
        "reference_answer": "I don't have information about drug interactions.",
        "note": "Pharmacology knowledge - OOD",
        "answerable": False,
    },
    {
        "question": "What are the consultation fee details for doctors at BMH?",
        "expected_keywords": ["fee", "consultation", "cost", "charge", "payment"],
        "expected_category": "hospital_info",
        "reference_answer": "I don't have information about consultation fees.",
        "note": "Pricing information - OOD",
        "answerable": False,
    },
    {
        "question": "What are the room tariffs and charges for inpatient admission?",
        "expected_keywords": [],
        "expected_category": "uncollected",
        "reference_answer": "I don't have information about room tariffs.",
        "note": "Uncollected data - should refuse to answer",
        "answerable": False,
    },
    {
        "question": "What is the detailed patient discharge process?",
        "expected_keywords": [],
        "expected_category": "uncollected",
        "reference_answer": "I don't have information about the discharge process.",
        "note": "Uncollected data - should refuse to answer",
        "answerable": False,
    },
    {
        "question": "What are the standard patient intake protocols for emergency admissions?",
        "expected_keywords": ["intake", "triage", "emergency", "protocol", "admission"],
        "expected_category": "clinical_guidelines",
        "reference_answer": "I don't have information about the detailed emergency admission protocols.",
        "note": "Clinical workflow question - uncollected",
        "answerable": False,
    },
]

COLLECTION_NAME = "medai_knowledge"

# ============================================================================
# Math & Evaluation Metric Functions
# ============================================================================

def is_source_relevant(src: dict, expected_category: str, expected_keywords: list[str]) -> bool:
    cat = str(src.get("category", "")).lower()
    title = str(src.get("title", "")).lower()
    content = str(src.get("content", "")).lower()
    text_block = f"{cat} {title} {content}"
    cat_lower = expected_category.lower()
    kw_lowers = [kw.lower() for kw in expected_keywords]
    return (cat_lower and cat_lower in cat) or any(kw in text_block for kw in kw_lowers)

def calculate_recall_at_k(sources: list[dict], expected_category: str, expected_keywords: list[str], k: int) -> float:
    total_relevant = sum(1 for src in sources if is_source_relevant(src, expected_category, expected_keywords))
    if total_relevant == 0:
        return 0.0
    
    hits = sum(1 for src in sources[:k] if is_source_relevant(src, expected_category, expected_keywords))
    return hits / total_relevant

def calculate_mrr(sources: list[dict], expected_category: str, expected_keywords: list[str]) -> float:
    for rank, src in enumerate(sources, start=1):
        if is_source_relevant(src, expected_category, expected_keywords):
            return 1.0 / rank
    return 0.0

def calculate_ndcg_at_k(sources: list[dict], expected_category: str, expected_keywords: list[str], k: int) -> float:
    top_k = sources[:k]
    if not top_k:
        return 0.0

    rel_scores: list[int] = []
    for src in top_k:
        if is_source_relevant(src, expected_category, expected_keywords):
            rel_scores.append(1)
        else:
            rel_scores.append(0)

    dcg = sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(rel_scores))
    ideal_scores = sorted(rel_scores, reverse=True)
    idcg = sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(ideal_scores))

    if idcg == 0:
        return 0.0
    return dcg / idcg

async def evaluate_faithfulness(answer: str, sources: list[dict], mode: str, llm: "LiteLLMClient" = None) -> float:
    if not answer or not sources:
        return 0.0

    source_texts = " ".join([str(s.get("text") or s.get("content", "")) for s in sources])
    if not source_texts.strip():
        return 0.0

    if mode == "FULL" and llm:
        from core.ai.llm.client import Message
        prompt = f"Given the following sources:\n{source_texts}\n\nAnd the answer:\n{answer}\n\nRate the faithfulness of the answer to the sources on a scale from 0.0 to 1.0. Just output the number and nothing else."
        try:
            res = await llm.generate([Message(role="user", content=prompt)], temperature=0.0)
            score = float(res.content.strip())
            return min(1.0, max(0.0, score))
        except Exception:
            pass # fallback to FAST

    source_texts_lower = source_texts.lower()
    stopwords = {"the", "a", "an", "is", "are", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by", "this", "that", "it", "as", "from", "i", "don't", "know", "information"}
    ans_tokens = [w.strip(".,;:!?()[]\"'") for w in answer.lower().split()]
    ans_keywords = [w for w in ans_tokens if len(w) > 2 and w not in stopwords]

    if not ans_keywords:
        return 1.0

    grounded_count = sum(1 for kw in ans_keywords if kw in source_texts_lower)
    score = grounded_count / len(ans_keywords)
    if "[Source" in answer or "[source" in answer:
        score = min(1.0, score + 0.15)

    return min(1.0, max(0.0, score))

async def evaluate_answer_correctness(answer: str, reference_answer: str, expected_keywords: list[str] | None, answerable: bool, mode: str, llm: "LiteLLMClient" = None) -> float:
    if not answerable:
        return 0.0 # Correct refusal handled separately
        
    if not answer or not reference_answer:
        return 0.0

    if mode == "FULL" and llm:
        from core.ai.llm.client import Message
        prompt = f"Given the reference answer:\n{reference_answer}\n\nAnd the actual answer:\n{answer}\n\nRate the correctness and semantic alignment of the actual answer to the reference on a scale from 0.0 to 1.0. Just output the number and nothing else."
        try:
            res = await llm.generate([Message(role="user", content=prompt)], temperature=0.0)
            score = float(res.content.strip())
            return min(1.0, max(0.0, score))
        except Exception:
            pass # fallback to FAST

    stopwords = {"the", "a", "an", "is", "are", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by", "this", "that", "it", "as", "from"}
    ref_words = set(w.strip(".,;:!?()[]\"'") for w in reference_answer.lower().split() if len(w) > 2 and w not in stopwords)
    ans_words = set(w.strip(".,;:!?()[]\"'") for w in answer.lower().split() if len(w) > 2 and w not in stopwords)

    if not ref_words:
        return 0.0

    overlap = len(ref_words.intersection(ans_words)) / len(ref_words)

    kw_bonus = 0.0
    if expected_keywords:
        kw_lowers = [k.lower() for k in expected_keywords]
        ans_text = answer.lower()
        kw_hits = sum(1 for k in kw_lowers if k in ans_text)
        kw_bonus = 0.3 * (kw_hits / max(1, len(kw_lowers)))

    final_score = min(1.0, (overlap * 0.7) + kw_bonus + 0.15)
    return final_score

def evaluate_correct_refusal(answer: str) -> float:
    refusal_phrases = ["don't know", "do not have", "no information", "cannot answer", "unable to provide", "not provided", "i do not know", "i'm sorry", "does not contain", "cannot be confirmed"]
    ans_lower = answer.lower()
    if any(phrase in ans_lower for phrase in refusal_phrases) and len(answer.split()) < 40:
        return 1.0
    return 0.0

# ============================================================================
# Error Categorization
# ============================================================================

def categorize_error(exc: Exception) -> str:
    exc_type = type(exc).__name__
    exc_str = str(exc).lower()
    
    if "ratelimit" in exc_type.lower() or "429" in exc_str:
        return "RATE_LIMIT"
    if "timeout" in exc_type.lower():
        return "TIMEOUT"
    if "auth" in exc_type.lower() or "401" in exc_str or "403" in exc_str:
        return "AUTHENTICATION"
    if "serviceunavailable" in exc_type.lower() or "500" in exc_str or "502" in exc_str or "503" in exc_str or "apierror" in exc_type.lower():
        return "PROVIDER_5XX"
    if "aiserviceunavailable" in exc_type.lower():
        return "FALLBACK_FAILURE"
    
    return "UNKNOWN"

# ============================================================================
# Dataclasses
# ============================================================================

@dataclass
class QueryEvalMetrics:
    question: str
    answerable: bool
    expected_category: str
    recall_at_3: float | None
    recall_at_5: float | None
    recall_at_10: float | None
    mrr: float | None
    ndcg_at_3: float | None
    ndcg_at_5: float | None
    faithfulness: float | None
    answer_correctness: float | None
    correct_refusal: float | None
    latency_ms: float
    retrieved_chunks: int
    answer_excerpt: str
    is_error: bool = False
    error_category: str | None = None
    error_msg: str | None = None

@dataclass
class HybridRAGEvalReport:
    timestamp: str
    mode: str
    collection: str
    total_queries: int
    answerable_queries: int
    unanswerable_queries: int
    
    evaluated_answerable_queries: int
    mean_recall_at_3: float | None
    mean_recall_at_5: float | None
    mean_recall_at_10: float | None
    mean_mrr: float | None
    mean_ndcg_at_3: float | None
    mean_ndcg_at_5: float | None
    
    mean_faithfulness: float | None
    mean_answer_correctness: float | None
    
    correct_refusal_rate: float | None
    
    successful_queries: int
    system_errors: int
    system_error_rate: float
    rate_limit_errors: int
    timeout_errors: int
    provider_5xx_errors: int
    authentication_errors: int
    fallback_failures: int
    unknown_errors: int
    
    avg_latency_ms: float
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    
    results: list[QueryEvalMetrics]


# ============================================================================
# Unit Tests
# ============================================================================

def run_unit_tests():
    print(f"\n{'=' * 75}")
    print("  Running Unit Tests for Recall@K")
    print(f"{'=' * 75}")
    
    def _create_source(cat="cat", title="title", content="kw"):
        return {"category": cat, "title": title, "content": content}
    
    # Scenario A: Relevant item is at rank 7
    sources_a = [_create_source(cat="bad", content="bad") for _ in range(6)] + [_create_source()] + [_create_source(cat="bad", content="bad")] * 3
    r3 = calculate_recall_at_k(sources_a, "cat", ["kw"], 3)
    r5 = calculate_recall_at_k(sources_a, "cat", ["kw"], 5)
    r10 = calculate_recall_at_k(sources_a, "cat", ["kw"], 10)
    assert r3 == 0.0, f"Expected 0.0, got {r3}"
    assert r5 == 0.0, f"Expected 0.0, got {r5}"
    assert r10 == 1.0, f"Expected 1.0, got {r10}"
    print("  [Pass] Scenario A (Relevant item at rank 7)")

    # Scenario B: Relevant item is at rank 2
    sources_b = [_create_source(cat="bad", content="bad"), _create_source()] + [_create_source(cat="bad", content="bad")] * 8
    r3 = calculate_recall_at_k(sources_b, "cat", ["kw"], 3)
    r5 = calculate_recall_at_k(sources_b, "cat", ["kw"], 5)
    r10 = calculate_recall_at_k(sources_b, "cat", ["kw"], 10)
    assert r3 == 1.0
    assert r5 == 1.0
    assert r10 == 1.0
    print("  [Pass] Scenario B (Relevant item at rank 2)")

    # Scenario C: Two relevant items exist at ranks 2 and 8
    sources_c = [_create_source(cat="bad", content="bad"), _create_source(), _create_source(cat="bad", content="bad"), _create_source(cat="bad", content="bad"), _create_source(cat="bad", content="bad"), _create_source(cat="bad", content="bad"), _create_source(cat="bad", content="bad"), _create_source(), _create_source(cat="bad", content="bad"), _create_source(cat="bad", content="bad")]
    r3 = calculate_recall_at_k(sources_c, "cat", ["kw"], 3)
    r5 = calculate_recall_at_k(sources_c, "cat", ["kw"], 5)
    r10 = calculate_recall_at_k(sources_c, "cat", ["kw"], 10)
    assert r3 == 0.5
    assert r5 == 0.5
    assert r10 == 1.0
    print("  [Pass] Scenario C (Relevant items at ranks 2 and 8)")
    
    print("  All Unit Tests Passed!\n")

# ============================================================================
# Benchmark Runner
# ============================================================================

async def run_evaluation(mode: str = "FAST") -> HybridRAGEvalReport:
    # --- Rate Limiting Monkey Patch ---
    original_generate = LiteLLMClient.generate
    original_embed = LiteLLMClient.embed
    llm_semaphore = asyncio.Semaphore(1)

    async def rate_limited_generate(self, *args, **kwargs):
        async with llm_semaphore:
            res = await original_generate(self, *args, **kwargs)
            await asyncio.sleep(4.5)  # Enforce conservative 12 RPM ceiling for Gemini free tier
            return res

    async def rate_limited_embed(self, *args, **kwargs):
        async with llm_semaphore:
            res = await original_embed(self, *args, **kwargs)
            await asyncio.sleep(1.0)
            return res

    LiteLLMClient.generate = rate_limited_generate
    LiteLLMClient.embed = rate_limited_embed
    # ----------------------------------

    llm = get_llm_client()
    pipeline = RAGPipeline(
        llm_client=llm,
        collection_name=COLLECTION_NAME,
    )

    print(f"\n{'=' * 75}")
    print(f"  MediAI Hybrid RAG Benchmark Suite ({mode} Mode)")
    print(f"  Collection : {COLLECTION_NAME}")
    print(f"  Queries    : {len(GOLDEN_DATASET)}")
    print(f"  Timestamp  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 75}\n")

    results: list[QueryEvalMetrics] = []

    for i, entry in enumerate(GOLDEN_DATASET, start=1):
        q_text = entry["question"]
        print(f"[{i:02d}/{len(GOLDEN_DATASET)}] Evaluating: '{q_text}'")

        t0 = time.perf_counter()
        is_ans = entry.get("answerable", True)
        try:
            max_retries = 3
            rag_res = None
            for attempt in range(max_retries):
                try:
                    rag_res = await pipeline.query(q_text)
                    break
                except Exception as query_exc:
                    err_str = str(query_exc).lower()
                    is_rate_limit = (
                        "429" in err_str
                        or "ratelimit" in err_str
                        or "resource_exhausted" in err_str
                        or "temporarily unavailable" in err_str
                    )
                    if is_rate_limit and attempt < max_retries - 1:
                        backoff = (attempt + 1) * 6
                        print(f"       Rate limit / busy signal encountered. Backing off for {backoff}s (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(backoff)
                        continue
                    raise query_exc

            latency_ms = (time.perf_counter() - t0) * 1000

            sources = rag_res.sources
            exp_cat = entry.get("expected_category", "")
            exp_kws = entry.get("expected_keywords", [])
            ref_ans = entry.get("reference_answer", "")

            if not is_ans:
                r3 = r5 = r10 = mrr_val = ndcg3 = ndcg5 = None
                faith = correctness = None
                cor_ref = evaluate_correct_refusal(rag_res.answer)
            else:
                r3 = calculate_recall_at_k(sources, exp_cat, exp_kws, 3)
                r5 = calculate_recall_at_k(sources, exp_cat, exp_kws, 5)
                r10 = calculate_recall_at_k(sources, exp_cat, exp_kws, 10)
                mrr_val = calculate_mrr(sources, exp_cat, exp_kws)
                ndcg3 = calculate_ndcg_at_k(sources, exp_cat, exp_kws, 3)
                ndcg5 = calculate_ndcg_at_k(sources, exp_cat, exp_kws, 5)
                faith = await evaluate_faithfulness(rag_res.answer, sources, mode, llm)
                correctness = await evaluate_answer_correctness(rag_res.answer, ref_ans, exp_kws, True, mode, llm)
                cor_ref = None

            metrics = QueryEvalMetrics(
                question=q_text,
                answerable=is_ans,
                expected_category=exp_cat,
                recall_at_3=r3,
                recall_at_5=r5,
                recall_at_10=r10,
                mrr=mrr_val,
                ndcg_at_3=ndcg3,
                ndcg_at_5=ndcg5,
                faithfulness=faith,
                answer_correctness=correctness,
                correct_refusal=cor_ref,
                latency_ms=round(latency_ms, 1),
                retrieved_chunks=rag_res.retrieved_chunks,
                answer_excerpt=rag_res.answer[:120].replace("\n", " "),
                is_error=False,
            )

            if is_ans:
                print(f"       Recall@5: {r5:.2f} | MRR: {mrr_val:.2f} | NDCG@5: {ndcg5:.2f} | Faithfulness: {faith:.2f} | Correctness: {correctness:.2f} | ({latency_ms:.0f}ms)")
            else:
                print(f"       OOD Query | Correct Refusal: {cor_ref:.2f} | ({latency_ms:.0f}ms)")
            print()
            results.append(metrics)

        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            err_cat = categorize_error(exc)
            print(f"       ERROR ({err_cat}): {exc}\n")
            results.append(
                QueryEvalMetrics(
                    question=q_text,
                    answerable=is_ans,
                    expected_category=entry.get("expected_category", ""),
                    recall_at_3=None,
                    recall_at_5=None,
                    recall_at_10=None,
                    mrr=None,
                    ndcg_at_3=None,
                    ndcg_at_5=None,
                    faithfulness=None,
                    answer_correctness=None,
                    correct_refusal=None,
                    latency_ms=round(latency_ms, 1),
                    retrieved_chunks=0,
                    answer_excerpt="",
                    is_error=True,
                    error_category=err_cat,
                    error_msg=str(exc),
                )
            )

    # Revert monkey patch
    LiteLLMClient.generate = original_generate
    LiteLLMClient.embed = original_embed

    # --- Metrics Aggregation ---
    successful = [r for r in results if not r.is_error]
    ans_successful = [r for r in successful if r.answerable]
    ood_successful = [r for r in successful if not r.answerable]
    
    def _mean(items):
        clean = [x for x in items if x is not None]
        return round(sum(clean) / len(clean), 3) if clean else None

    report = HybridRAGEvalReport(
        timestamp=datetime.now().isoformat(),
        mode=mode,
        collection=COLLECTION_NAME,
        total_queries=len(results),
        answerable_queries=len([r for r in results if r.answerable]),
        unanswerable_queries=len([r for r in results if not r.answerable]),
        
        evaluated_answerable_queries=len(ans_successful),
        mean_recall_at_3=_mean([r.recall_at_3 for r in ans_successful]),
        mean_recall_at_5=_mean([r.recall_at_5 for r in ans_successful]),
        mean_recall_at_10=_mean([r.recall_at_10 for r in ans_successful]),
        mean_mrr=_mean([r.mrr for r in ans_successful]),
        mean_ndcg_at_3=_mean([r.ndcg_at_3 for r in ans_successful]),
        mean_ndcg_at_5=_mean([r.ndcg_at_5 for r in ans_successful]),
        
        mean_faithfulness=_mean([r.faithfulness for r in ans_successful]),
        mean_answer_correctness=_mean([r.answer_correctness for r in ans_successful]),
        
        correct_refusal_rate=_mean([r.correct_refusal for r in ood_successful]),
        
        successful_queries=len(successful),
        system_errors=len([r for r in results if r.is_error]),
        system_error_rate=round(len([r for r in results if r.is_error]) / max(1, len(results)), 3),
        rate_limit_errors=len([r for r in results if r.error_category == "RATE_LIMIT"]),
        timeout_errors=len([r for r in results if r.error_category == "TIMEOUT"]),
        provider_5xx_errors=len([r for r in results if r.error_category == "PROVIDER_5XX"]),
        authentication_errors=len([r for r in results if r.error_category == "AUTHENTICATION"]),
        fallback_failures=len([r for r in results if r.error_category == "FALLBACK_FAILURE"]),
        unknown_errors=len([r for r in results if r.error_category == "UNKNOWN"]),
        
        avg_latency_ms=round(sum(r.latency_ms for r in successful) / max(1, len(successful)), 1) if successful else 0.0,
        p50_latency_ms=round(statistics.quantiles([r.latency_ms for r in successful], n=100)[49], 1) if len(successful) > 1 else (successful[0].latency_ms if successful else None),
        p95_latency_ms=round(statistics.quantiles([r.latency_ms for r in successful], n=100)[94], 1) if len(successful) > 1 else (successful[0].latency_ms if successful else None),
        
        results=results,
    )

    def _fmt(val):
        return f"{val:.3f}" if val is not None else "null"

    print(f"{'=' * 75}")
    print(f"  BENCHMARK SUMMARY RESULTS ({mode})")
    print(f"{'=' * 75}")
    print("DATASET")
    print("-------")
    print(f"Total Queries                 : {report.total_queries}")
    print(f"Answerable Queries            : {report.answerable_queries}")
    print(f"Unanswerable/OOD Queries      : {report.unanswerable_queries}")
    print("\nRETRIEVAL")
    print("---------")
    print(f"Evaluated Answerable Queries  : {report.evaluated_answerable_queries}")
    print(f"Mean Recall@3                 : {_fmt(report.mean_recall_at_3)}")
    print(f"Mean Recall@5                 : {_fmt(report.mean_recall_at_5)}")
    print(f"Mean Recall@10                : {_fmt(report.mean_recall_at_10)}")
    print(f"Mean MRR                      : {_fmt(report.mean_mrr)}")
    print(f"Mean NDCG@3                   : {_fmt(report.mean_ndcg_at_3)}")
    print(f"Mean NDCG@5                   : {_fmt(report.mean_ndcg_at_5)}")
    print("\nANSWER QUALITY")
    print("--------------")
    print(f"Mean Faithfulness             : {_fmt(report.mean_faithfulness)}")
    print(f"Mean Answer Correctness       : {_fmt(report.mean_answer_correctness)}")
    print("\nOOD HANDLING")
    print("------------")
    print(f"Correct Refusal Rate          : {_fmt(report.correct_refusal_rate)}")
    print("\nSYSTEM RELIABILITY")
    print("-------------------")
    print(f"Successful Queries            : {report.successful_queries}")
    print(f"System Errors                 : {report.system_errors}")
    print(f"System Error Rate             : {report.system_error_rate * 100:.1f}%")
    print(f"Rate Limit Errors             : {report.rate_limit_errors}")
    print(f"Timeout Errors                : {report.timeout_errors}")
    print(f"Provider 5xx Errors           : {report.provider_5xx_errors}")
    print(f"Authentication Errors         : {report.authentication_errors}")
    print(f"Fallback Failures             : {report.fallback_failures}")
    print(f"Unknown Errors                : {report.unknown_errors}")
    print("\nLATENCY")
    print("-------")
    print(f"Average                       : {report.avg_latency_ms:.1f} ms")
    if report.p50_latency_ms:
        print(f"P50                           : {report.p50_latency_ms:.1f} ms")
        print(f"P95                           : {report.p95_latency_ms:.1f} ms")
    else:
        print(f"P50                           : null")
        print(f"P95                           : null")
    print(f"{'=' * 75}\n")

    eval_dir = PROJECT_ROOT / "data" / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = eval_dir / f"rag_eval_{mode.lower()}_{ts}.json"
    out_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Full benchmark report saved -> {out_path}\n")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MediAI RAG Evaluation")
    parser.add_argument("--mode", type=str, choices=["FAST", "FULL"], default="FAST", help="Evaluation mode (FAST=deterministic, FULL=LLM-as-a-judge)")
    args = parser.parse_args()
    
    run_unit_tests()
    asyncio.run(run_evaluation(mode=args.mode))
    