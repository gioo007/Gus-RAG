#Usage:
#   python eval/run_eval.py v1 --k 4
#   python eval/run_eval.py v2 --k 4

#type ignores to silence pylance resolving issues (all code and imports run fine)

import sys
from unittest.mock import MagicMock
sys.modules["langchain_community.chat_models.vertexai"] = MagicMock()

import argparse
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from app.core.config import settings #type: ignore
from app.services import generation, retrieval #type: ignore

from dataset import EVAL_QUESTIONS
from langchain_groq import ChatGroq
from ragas import EvaluationDataset, evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import Faithfulness, LLMContextPrecisionWithReference
from ragas.run_config import RunConfig

RESULTS_DIR = Path(__file__).resolve().parent / "results"

def build_rows(label: str, k: int) -> list[dict]:
    rows = []
    for item in EVAL_QUESTIONS:
        question = item["question"]
        chunks = retrieval.retrieve(question, version=label, k=k)
        contexts = [chunk.page_content for chunk in chunks]
        answer = generation.generate(question, chunks)
        rows.append({
            "user_input": question,
            "retrieved_contexts": contexts,
            "response": answer,
            "reference": item["reference"]
        })
    return rows

def run(label: str, k: int) -> None:
    rows = build_rows(label, k)
    dataset = EvaluationDataset.from_list(rows)

    #using same model as judge is known to have a bias
    api_key = settings.GROQ_API_KEY
    judge = ChatGroq(temperature=0, model=settings.LLM_MODEL, api_key=api_key)
    evaluator_llm = LangchainLLMWrapper(judge)

    result = evaluate(
        dataset=dataset,

        metrics=[Faithfulness(llm=evaluator_llm), LLMContextPrecisionWithReference(llm=evaluator_llm)], #type: ignore
        #metrics = [LLMContextPrecisionWithReference(llm=evaluator_llm)],   #when doing micro precision runs
        #metrics = [Faithfulness(llm=evaluator_llm)],                       #when doing micro faithfulness runs

        llm=evaluator_llm,
        run_config=RunConfig(max_workers=1, max_retries=5, timeout=300)
    )

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outfile = RESULTS_DIR / f"{label}_k{k}_{timestamp}.json"
    result.to_pandas().to_json(outfile, orient="records", indent=2) #type: ignore

    print(f"{label}: {len(rows)} questions, k={k}")
    print(result)
    print(f"saved to {outfile}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("label", choices=["v1", "v2"])
    parser.add_argument("--k", type=int, default=4)
    args = parser.parse_args()
    run(args.label, args.k)