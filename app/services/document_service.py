from datetime import datetime
import hashlib
from pathlib import Path
import re
from typing import Dict, List

import nest_asyncio

nest_asyncio.apply()
from llama_index.core import Settings as llamaSettings, VectorStoreIndex, StorageContext
from app.schemas.document import DocumentStatus, HRPolicy
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
    TableStructureOptions,
)

from llama_index.core.schema import Document
from llama_index.core.node_parser import (
    SentenceSplitter,
    SemanticSplitterNodeParser,
    MarkdownNodeParser,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from pypdf import PdfReader

from app.core.config import settings
from app.core.logger import logger

llamaSettings.llm = None


class DocumentProcessor:
    """
    Advanced document processing with semantic chunking
    """

    def __init__(self, embed_model: HuggingFaceEmbedding, vector_store: PGVectorStore):
        table_options = TableStructureOptions(
            mode=TableFormerMode.ACCURATE,  # Can be "fast" or "accurate"
            do_cell_matching=False,  # This prevents splitting when headers are complex
        )

        pipeline_options = PdfPipelineOptions()
        pipeline_options.table_structure_options = table_options

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        self.splitter = MarkdownNodeParser()
        self.fallback_splitter = SentenceSplitter(
            chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP
        )
        self.embed_model = embed_model
        self.vector_store = vector_store

        self._init_vector_store()

    def _init_vector_store(self):
        """Initialize vector store"""
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )
        try:
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store, embed_model=self.embed_model
            )
        except Exception as e:
            logger.exception(
                f"DocumentProcessor error: {e}",
                stack_info=True,
                exc_info=True,
            )
            raise Exception("Error while init vector store at document processor.")

    def _extract_text(self, file_path: Path) -> str:
        """Extract text from PDF with layout preservation"""
        text_parts = []
        try:
            logger.info(f"🚀 Docling Page-by-Page Conversion: {file_path.name}")

            # 1. First, do a quick convert to get the total page count
            # (Docling needs to know how many pages exist before we loop)
            initial_result = self.converter.convert(file_path)
            total_pages = len(initial_result.document.pages)

            # 2. Iterate through each page number (starting from 1)
            for page_num in range(1, total_pages + 1):
                # Convert ONLY the current page
                page_result = self.converter.convert(
                    file_path, page_range=(page_num, page_num)
                )

                # Inject your marker
                text_parts.append(f"\n\n [PAGE_START_{page_num}] \n\n")

                # Export the single-page document to Markdown
                # This ensures tables stay intact on their respective pages
                page_md = page_result.document.export_to_markdown(
                    image_placeholder="", compact_tables=True
                )
                text_parts.append(page_md)

            return "".join(text_parts)
        except Exception as e:
            logger.warning(f"docling failed, falling back to pypdf: {e}")
            # pypdf Fallback
            reader = PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                marker = f" [PAGE_START_{i + 1}] "
                page_text = page.extract_text() or ""
                if "|" in page_text or "  " in page_text:
                    # Tables need their layout preserved exactly
                    pass
                else:
                    page_text = re.sub(r"\n{3,}", "\n\n", page_text)
                text_parts.append(marker + page_text)

        return "\n\n".join(text_parts)

    def _extract_metadata(
        self, file_path: Path, text: str, category: str | None
    ) -> Dict:
        """Extract metadata using heuristics"""
        filename = file_path.stem.lower()

        # Detect category from filename/content
        if category is None:
            if any(kw in filename for kw in ["leave", "vacation", "pto"]):
                category = "leave_policy"
            elif any(kw in filename for kw in ["conduct", "behavior", "ethics"]):
                category = "code_of_conduct"
            elif any(kw in filename for kw in ["benefit", "insurance", "health"]):
                category = "benefits"
            elif any(kw in filename for kw in ["payroll", "salary", "compensation"]):
                category = "compensation"
            else:
                category = "general"

        # Extract title (first line or filename)
        # lines = text.strip().split("\n")
        # title = lines[0][:100] if lines else filename.replace("_", " ").title()

        return {
            "category": category,
            "title": str(file_path.name).split(".")[0],
            "source": str(file_path.name),
            "file_size": file_path.stat().st_size,
            "extraction_date": datetime.now().isoformat(),
        }

    def _table_cleaner(self, text: str) -> str:
        text = re.sub(
            r"<!-- TABLE_START -->\n\|(\s*\|)+\s*(.*?)\s*(\|.*\2\s*)+\|",  # Detect tables with duplicate columns
            r"<!-- TABLE_START -->\n| \2 |",  # Replace with a single instance of the duplicate content
            text,
        )

        text = re.sub(
            r"<!-- TABLE_START -->\n\|([^|]+)(\|\s*\1)+\|",  # Match duplicate columns
            r"<!-- TABLE_START -->\n| \1 |",  # Replace with just one column
            text,
        )
        return text

    async def _process_document_v1(
        self,
        file_path: Path,
        doc_id: str,
        tenant_id: str,
        file_hash: str | None = None,
        category: str = None,
    ) -> List[Document]:
        text = self._extract_text(file_path)
        metadata = self._extract_metadata(file_path, text, category)
        metadata["doc_id"] = doc_id

        if file_hash is None:
            file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()

        text = re.sub(r"\n{2,}\|", r"\n<!-- TABLE_START -->\n|", text)
        text = re.sub(r"\|\n(?!\|)", r"|\n<!-- TABLE_END -->\n", text)

        text = self._table_cleaner(text)

        document = Document(text=text, metadata=metadata, id_=doc_id)

        # 🚀 Use the Element Parser logic
        try:
            # get_nodes_from_documents returns a list of base nodes
            # It internally identifies tables and creates summaries
            nodes = self.splitter.get_nodes_from_documents([document])
        except Exception as e:
            logger.warning(f"Element parsing failed, using fallback: {e}")
            nodes = self.fallback_splitter.get_nodes_from_documents([document])

        current_page_label = "1"
        last_seen_page = "1"

        for i, node in enumerate(nodes):
            # 1. Handle Page Tracking (Keep your existing regex logic)
            page_matches = re.findall(r"\[PAGE_START_(\d+)\]", node.text)
            if page_matches:
                start_of_chunk = page_matches[0]
                end_of_chunk = page_matches[-1]
                current_page_label = (
                    end_of_chunk
                    if start_of_chunk == last_seen_page
                    else f"{last_seen_page}-{end_of_chunk}"
                )
                last_seen_page = end_of_chunk
            else:
                current_page_label = last_seen_page

            # 2. Clean text and Update Metadata
            node.text = re.sub(r"\[PAGE_START_\d+\]", "", node.text).strip()

            node.metadata.update(
                {
                    "chunk_index": i,
                    "total_chunks": len(nodes),
                    "chunk_id": f"{doc_id}_chunk_{i}",
                    "page_label": str(current_page_label),
                    "file_hash": file_hash,
                    "tenant_id": tenant_id,
                    # Carry over initial metadata
                    **metadata,
                }
            )

            # 3. Add the Header for LLM grounding
            header = f"SOURCE: {metadata['source']} | PAGE: {current_page_label}\n---\n"
            node.text = header + node.text

        return nodes

    async def ingest_document(
        self, file_path: Path, doc_id: str, tenant_id: str, category: str | None = None
    ) -> HRPolicy:
        """
        Ingest document: chunk, embed, and store in vectore store
        """
        try:
            # Process document
            nodes = await self._process_document_v1(
                file_path, doc_id, tenant_id, category=category
            )

            # Create or update index
            self.index.insert_nodes(nodes)

            # Persist
            metadata = nodes[0].metadata if nodes else {}

            return True, HRPolicy(
                id=doc_id,
                filename=file_path.name,
                title=metadata.get("title", file_path.name),
                category=metadata.get("category", "general"),
                upload_date=datetime.now(),
                status=DocumentStatus.COMPLETED,
                chunk_count=len(nodes),
                metadata=metadata,
                file_hash=hashlib.md5(file_path.read_bytes()).hexdigest(),
            )

        except Exception as e:
            logger.exception(
                f"Document ingestion failed: {e}", stack_info=True, exc_info=True
            )
            raise
