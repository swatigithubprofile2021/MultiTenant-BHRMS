import logging
from typing import List
import ollama
from langchain_ollama import ChatOllama
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
from app.core.config import settings
from app.core.logger import logger
import base64


class LLMManager:
    def __init__(self):
        self._models = {}
        self._base_option = {
            "num_predict": settings.LLM_MAX_TOKEN_LIMIT,
            "temperature": settings.LLM_TEMPERATURE,
            "num_thread": settings.LLM_MAX_NUM_THREAD,
            "disable_streaming": False,
            "repeat_penalty": 1.2,
            "top_k": 5,
            "stop": ["Human:", "User:", "SOURCE:"],
            "keep_alive": -1,
        }
        self._initialize_llm()

    def _initialize_llm(self):
        """
        Initializes the LLM with default model via Ollama,
        falling back to HuggingFace if Ollama is unavailable.
        """
        try:
            logger.info(f"Initializing Ollama with default model: {settings.LLM_MODEL}")
            # self._models[settings.LLM_MODEL] = ChatOllama(
            #     model=settings.LLM_MODEL, **self._base_option
            # )
            
            self._models[settings.LLM_MODEL] = ChatOllama(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            headers=self._get_auth_headers(),
            **self._base_option
                    )

        except Exception as e:
            logger.error(
                f"Failed to initialize Ollama: {e}. Attempting HuggingFace fallback..."
            )
            return self._get_hf_fallback()


    def _get_auth_headers(self):
        credentials = f"{settings.OLLAMA_USERNAME}:{settings.OLLAMA_PASSWORD}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}"
        }
    def _get_hf_fallback(self):
        try:
            from langchain_community.llms.huggingface_pipeline import (
                HuggingFacePipeline,
            )
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            import torch

            # Using Qwen 0.5B as a better fallback for an Agent system.
            model_id = "Qwen/Qwen2.5-0.5B-Instruct"

            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                device_map="auto",
                torch_dtype=(
                    torch.float16 if torch.cuda.is_available() else torch.float32
                ),
            )

            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=settings.LLM_MAX_TOKEN_LIMIT,
                temperature=settings.LLM_TEMPERATURE,
                trust_remote_code=True,
            )
            return HuggingFacePipeline(pipeline=pipe)

        except Exception as hf_e:
            logger.critical(f"All LLM initializations failed: {hf_e}")
            raise hf_e

    def get_available_models(self) -> List[str]:
        response = ollama.list()
        return [
            model["model"]
            for model in response.get("models", [])
            if "embed" not in model["model"].lower()
        ]

    def get(self, model: str) -> ChatOllama | None:
        if model in self._models:
            return self._models[model]

        is_model_available = self.get_available_models()
        if model in is_model_available:
            self._models[model] = ChatOllama(model=model, **self._base_option)
            return self._models[model]

        return None
