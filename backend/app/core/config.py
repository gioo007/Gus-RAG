from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-oss-120b"
    DATABASE_URL: str = ""
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    HF_TOKEN: str = ""
    COHERE_API_KEY: str = ""


    #v2 retrieval pipeline
    DEFAULT_K: int = 7
    RETRIEVAL_STRATEGY: Literal["v1", "v2"] = "v1"     #flip to "v2" once the eval rerun says it wins
    RETRIEVAL_FETCH_K_MULTIPLIER: int = 4              #v2 over-fetches k * this many candidates before reranking down to k
    BM25_WEIGHT: float = 0.4                           #vector side of the hybrid ensemble gets 1 - BM25_WEIGHT
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    MULTI_HOP_MAX_SUBQUESTIONS: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()