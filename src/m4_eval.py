from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


EVALUATOR_LLM_MODEL = "gpt-4o-mini"
EVALUATOR_EMBEDDING_MODEL = "text-embedding-3-small"
NAN_RETRIES = 2


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation.

    Returns {<metric>: mean, "per_question": [EvalResult...],
             "metadata": {"evaluator_models": [...]}}.
    Rows có metric NaN (judge LLM trả output không parse được) được chấm lại tối đa
    NAN_RETRIES lần; nếu vẫn NaN thì raise — không thay NaN bằng điểm giả.
    """
    import math
    from datasets import Dataset
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

    metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    n = len(questions)
    if not (len(answers) == len(contexts) == len(ground_truths) == n):
        raise ValueError("questions/answers/contexts/ground_truths phải cùng độ dài")

    # Chỉ định rõ evaluator model — mặc định của ragas 0.1 là gpt-3.5-turbo + ada-002
    llm = LangchainLLMWrapper(ChatOpenAI(model=EVALUATOR_LLM_MODEL, temperature=0))
    embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model=EVALUATOR_EMBEDDING_MODEL))
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    # answer_relevancy sinh câu hỏi từ câu trả lời rồi so cosine với câu hỏi gốc. Prompt mặc định
    # tiếng Anh hay sinh câu hỏi tiếng Anh → cosine cross-lingual thấp dù câu trả lời đúng
    # (đo được: 0.39 vs 0.88 cho cùng một câu trả lời). adapt() dịch prompt sang tiếng Việt,
    # cache trong .cache/ragas_prompts. 3 metric còn lại là LLM-judge, không so embedding → giữ nguyên.
    for m in metrics:
        m.llm = llm
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             ".cache", "ragas_prompts")
    _clean_prompt_cache(cache_dir)
    try:
        answer_relevancy.adapt(language="vietnamese", cache_dir=cache_dir)
        answer_relevancy.save(cache_dir=cache_dir)
        _clean_prompt_cache(cache_dir)
    except Exception as e:
        print(f"  ⚠️  answer_relevancy.adapt() failed, dùng prompt tiếng Anh: {e}")

    def _run(indices: list[int]) -> list[dict]:
        dataset = Dataset.from_dict({
            "question": [questions[i] for i in indices], "answer": [answers[i] for i in indices],
            "contexts": [contexts[i] for i in indices],
            "ground_truth": [ground_truths[i] for i in indices],
        })
        df = evaluate(dataset, metrics=metrics, llm=llm, embeddings=embeddings,
                      raise_exceptions=False).to_pandas()
        if len(df) != len(indices):
            raise ValueError(f"RAGAS trả {len(df)} rows cho {len(indices)} câu")
        rows = []
        for _, row in df.iterrows():
            rows.append({m: (math.nan if row.get(m) is None else float(row.get(m)))
                         for m in metric_names})
        return rows

    scores = _run(list(range(n)))
    for attempt in range(NAN_RETRIES):
        missing = [i for i, s in enumerate(scores) if any(math.isnan(s[m]) for m in metric_names)]
        if not missing:
            break
        print(f"  ⚠️  {len(missing)} câu có metric NaN → chấm lại (lần {attempt + 1})")
        for i, rescored in zip(missing, _run(missing)):
            for m in metric_names:
                if math.isnan(scores[i][m]):
                    scores[i][m] = rescored[m]
    bad = [i for i, s in enumerate(scores) if any(math.isnan(s[m]) for m in metric_names)]
    if bad:
        raise ValueError(f"RAGAS vẫn trả NaN cho các câu index {bad} sau {NAN_RETRIES} lần chấm lại")

    per_question = [
        EvalResult(question=questions[i], answer=answers[i], contexts=list(contexts[i]),
                   ground_truth=ground_truths[i], **scores[i])
        for i in range(n)
    ]
    aggregate = {m: sum(s[m] for s in scores) / n if n else 0.0 for m in metric_names}
    return {
        **aggregate,
        "per_question": per_question,
        "metadata": {"evaluator_models": [EVALUATOR_LLM_MODEL, EVALUATOR_EMBEDDING_MODEL]},
    }


def _clean_prompt_cache(cache_dir: str) -> None:
    """ragas lưu prompt đã dịch với output bọc trong ```json ... ``` → lần sau _load() báo
    "output in example is not in valid json format" và metric âm thầm quay về prompt tiếng Anh.
    Gỡ code fence để cache load lại được."""
    import glob
    import re

    for path in glob.glob(os.path.join(cache_dir, "*", "*.json")):
        with open(path, encoding="utf-8") as f:
            prompt = json.load(f)
        changed = False
        for example in prompt.get("examples", []):
            for key, value in example.items():
                if isinstance(value, str) and value.strip().startswith("```"):
                    example[key] = re.sub(r"^```(?:json)?\s*|\s*```$", "", value.strip())
                    changed = True
        if changed:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(prompt, f, ensure_ascii=False, indent=2)


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating", "Tighten prompt, lower temperature"),
        "context_recall": ("Missing relevant chunks", "Improve chunking or add BM25"),
        "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
        "answer_relevancy": ("Answer doesn't match question", "Improve prompt template"),
    }
    metric_names = list(diagnostic_tree)

    analyzed = []
    for r in eval_results:
        # Bỏ metric NaN (không chấm được) khỏi chẩn đoán
        scores = {m: getattr(r, m) for m in metric_names if getattr(r, m) == getattr(r, m)}
        if not scores:
            continue
        worst_metric = min(scores, key=scores.get)
        diagnosis, fix = diagnostic_tree[worst_metric]
        analyzed.append({
            "question": r.question,
            "expected": r.ground_truth,
            "answer": r.answer,
            "scores": scores,
            "avg_score": sum(scores.values()) / len(scores),
            "worst_metric": worst_metric,
            "score": scores[worst_metric],
            "diagnosis": diagnosis,
            "suggested_fix": fix,
        })

    analyzed.sort(key=lambda x: x["avg_score"])
    return analyzed[:bottom_n]



def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json",
                latency: dict | None = None):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    if latency:
        report["latency_breakdown"] = latency
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
