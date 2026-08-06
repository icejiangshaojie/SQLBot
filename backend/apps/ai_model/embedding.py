import os
import os.path
import threading
from typing import Optional

from langchain_core.embeddings import Embeddings
from pydantic import BaseModel

from common.core.config import settings
from common.utils.utils import SQLBotLogUtil

os.environ["TOKENIZERS_PARALLELISM"] = "false"


class EmbeddingModelInfo(BaseModel):
    folder: str
    name: str
    device: str = 'cpu'


local_embedding_model = EmbeddingModelInfo(folder=settings.LOCAL_MODEL_PATH,
                                           name=os.path.join(settings.LOCAL_MODEL_PATH, 'embedding',
                                                             "shibing624_text2vec-base-chinese"))

_lock = threading.Lock()
locks = {}

_embedding_model: dict[str, Optional[Embeddings]] = {}

# Track whether local model path exists to avoid repeated checks
_model_path_available: Optional[bool] = None


def is_embedding_available() -> bool:
    """Check if the local embedding model path exists (e.g. not available on Windows dev)."""
    global _model_path_available
    if _model_path_available is None:
        _model_path_available = os.path.exists(settings.LOCAL_MODEL_PATH)
        if not _model_path_available:
            SQLBotLogUtil.info(
                f"[Embedding] LOCAL_MODEL_PATH '{settings.LOCAL_MODEL_PATH}' does not exist — "
                "embedding features disabled. Set LOCAL_MODEL_PATH to a valid path to enable."
            )
    return _model_path_available


class EmbeddingModelCache:

    @staticmethod
    def _new_instance(config: EmbeddingModelInfo = local_embedding_model):
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=config.name, cache_folder=config.folder,
                                     model_kwargs={'device': config.device},
                                     encode_kwargs={'normalize_embeddings': True}
                                     )

    @staticmethod
    def _get_lock(key: str = settings.DEFAULT_EMBEDDING_MODEL):
        lock = locks.get(key)
        if lock is None:
            with _lock:
                lock = locks.get(key)
                if lock is None:
                    lock = threading.Lock()
                    locks[key] = lock

        return lock

    @staticmethod
    def get_model(key: str = settings.DEFAULT_EMBEDDING_MODEL,
                  config: EmbeddingModelInfo = local_embedding_model) -> Optional[Embeddings]:
        """Get embedding model. Returns None if local model path doesn't exist."""
        if not is_embedding_available():
            return None

        model_instance = _embedding_model.get(key)
        if model_instance is None:
            lock = EmbeddingModelCache._get_lock(key)
            with lock:
                model_instance = _embedding_model.get(key)
                if model_instance is None:
                    model_instance = EmbeddingModelCache._new_instance(config)
                    _embedding_model[key] = model_instance

        return model_instance
