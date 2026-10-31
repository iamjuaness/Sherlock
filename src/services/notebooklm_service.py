"""
Servicio de integración con NotebookLM (via notebooklm-py).

Permite consultar notebooks de investigación, reglas cuantitativas y análisis
de partidos sin consumir tokens en APIs externas de pago (OpenRouter / OpenAI).
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Intentar importar notebooklm de forma segura
try:
    from notebooklm import NotebookLMClient
    _NOTEBOOKLM_AVAILABLE = True
except ImportError:
    _NOTEBOOKLM_AVAILABLE = False


class NotebookLMService:
    """Cliente y helper para orquestar consultas a NotebookLM."""

    def __init__(self, notebook_id: Optional[str] = None):
        self.notebook_id = notebook_id or os.environ.get("NOTEBOOKLM_NOTEBOOK_ID")
        self.enabled = os.environ.get("ENABLE_NOTEBOOKLM", "false").lower() in ("true", "1", "yes")

    def is_available(self) -> bool:
        """Verifica si la librería está instalada y las credenciales mínimas existen."""
        if not _NOTEBOOKLM_AVAILABLE:
            return False
        # Verificar si existe storage_state.json o master_token.json
        storage_path = os.environ.get("NOTEBOOKLM_STORAGE_PATH")
        if storage_path and os.path.exists(storage_path):
            return True
        default_dir = os.path.expanduser("~/.notebooklm/profiles/default")
        has_storage = os.path.exists(os.path.join(default_dir, "storage_state.json"))
        has_master = os.path.exists(os.path.join(default_dir, "master_token.json"))
        return has_storage or has_master

    async def ask_question(self, question: str, notebook_id: Optional[str] = None) -> Optional[str]:
        """Envía una pregunta a un notebook específico o al configurado por defecto."""
        target_nb = notebook_id or self.notebook_id
        if not target_nb:
            logger.warning("No se proporcionó notebook_id para NotebookLM.")
            return None

        if not self.is_available():
            logger.warning("NotebookLM no está autenticado o no disponible.")
            return None

        try:
            async with await NotebookLMClient.from_storage() as client:
                res = await client.chat.send(target_nb, question)
                if hasattr(res, "text") and res.text:
                    return res.text.strip()
                if hasattr(res, "answer") and res.answer:
                    return res.answer.strip()
                return str(res)
        except Exception as e:
            logger.error("Error consultando NotebookLM: %s", e)
            return None

    async def list_notebooks(self) -> List[Dict[str, Any]]:
        """Lista los notebooks disponibles en la cuenta."""
        if not self.is_available():
            return []
        try:
            async with await NotebookLMClient.from_storage() as client:
                items = await client.notebooks.list()
                return [{"id": getattr(n, "id", ""), "title": getattr(n, "title", "")} for n in items]
        except Exception as e:
            logger.error("Error listando notebooks: %s", e)
            return []

    async def add_source_text(self, title: str, content: str, notebook_id: Optional[str] = None) -> bool:
        """Sube un documento de texto o análisis al notebook para enriquecer la base de conocimiento."""
        target_nb = notebook_id or self.notebook_id
        if not target_nb or not self.is_available():
            return False
        try:
            async with await NotebookLMClient.from_storage() as client:
                await client.sources.add_text(target_nb, title=title, content=content)
                return True
        except Exception as e:
            logger.error("Error agregando texto a NotebookLM: %s", e)
            return False


# Singleton por defecto
notebooklm_service = NotebookLMService()
