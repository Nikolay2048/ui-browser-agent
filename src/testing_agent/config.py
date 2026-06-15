from __future__ import annotations

import os

from langchain_ollama import ChatOllama

PLANNING_MODEL = os.getenv("PLANNING_MODEL", "qwen3.5:35b")
EXECUTION_MODEL = os.getenv("EXECUTION_MODEL", "qwen3.5:35b")
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "qwen2.5-coder:14b-instruct")

NUM_CTX = int(os.getenv("NUM_CTX", "8192"))
MAX_STEP_ITERATIONS = int(os.getenv("MAX_STEP_ITERATIONS", "40"))


def get_planning_llm() -> ChatOllama:
    return ChatOllama(
        model=PLANNING_MODEL,
        temperature=0,
        num_ctx=NUM_CTX,
        num_predict=4096,
        reasoning=False,
    )


def get_execution_llm() -> ChatOllama:
    return ChatOllama(
        model=EXECUTION_MODEL,
        temperature=0,
        num_ctx=NUM_CTX,
        num_predict=2048,
        reasoning=False,
    )


def get_generation_llm() -> ChatOllama:
    return ChatOllama(
        model=GENERATION_MODEL,
        temperature=0,
        num_ctx=NUM_CTX,
        num_predict=4096,
        reasoning=False,
    )
