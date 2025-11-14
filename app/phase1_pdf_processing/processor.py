"""
PDF processing utilities for structured text extraction.
Handles first page detection, index extraction, and table extraction.
Uses adaptive strategies to handle different book types.
"""
import re
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pdfplumber
import pandas as pd

from .utils.pdf_extraction_strategies import (
    BookStructureAnalyzer,
    BookType,
    ExtractionConfig,
    AdaptiveIndexExtractor,
    AdaptiveTableExtractor
)

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Process PDF files to extract structured content."""
    
    def __init__(self, pdf_path: str, config: Optional[ExtractionConfig] = None):
        """
        Initialize PDF processor.
        
        Args:
            pdf_path: Path to the PDF file
            config: Optional extraction configuration. If None, will auto-detect.
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.pdf = None
        self.total_pages = 0
        self.config = config
        self.book_type = None
        self.index_extractor = None
        self.table_extractor = None
        
    def __enter__(self):
        """Context manager entry."""
        self.pdf = pdfplumber.open(self.pdf_path)
        self.total_pages = len(self.pdf.pages)
        
        # Auto-detect book type and configure if not provided
        if self.config is None:
            self._auto_configure()
        else:
            self.index_extractor = AdaptiveIndexExtractor(self.config)
            self.table_extractor = AdaptiveTableExtractor(self.config)
        
        return self
    
    def _auto_configure(self):
        """Auto-detect book type and configure extraction."""
        try:
            # Sample pages for analysis (first, middle, last)
            sample_pages = []
            sample_indices = [
                0,  # First page
                min(5, self.total_pages - 1),  # Early page
                min(10, self.total_pages - 1),  # Mid-early page
                self.total_pages // 2,  # Middle page
                max(0, self.total_pages - 5),  # Near end
            ]
            
            for idx in sample_indices:
                if idx < self.total_pages:
                    try:
                        text = self.pdf.pages[idx].extract_text()
                        if text:
                            sample_pages.append(text[:1000])  # First 1000 chars
                    except:
                        pass
            
            if sample_pages:
                # Analyze book type
                self.book_type = BookStructureAnalyzer.analyze_book_type(
                    sample_pages, self.total_pages
                )
                logger.info(f"Detected book type: {self.book_type.value}")
                
                # Get configuration for book type
                self.config = BookStructureAnalyzer.get_config_for_type(self.book_type)
            else:
                # Fallback to default config
                self.config = ExtractionConfig()
                self.book_type = BookType.UNKNOWN
                logger.warning("Could not analyze book type, using default configuration")
            
            # Initialize extractors
            self.index_extractor = AdaptiveIndexExtractor(self.config)
            self.table_extractor = AdaptiveTableExtractor(self.config)
            
        except Exception as e:
            logger.warning(f"Error in auto-configuration: {e}, using defaults")
            self.config = ExtractionConfig()
            self.book_type = BookType.UNKNOWN
            self.index_extractor = AdaptiveIndexExtractor(self.config)
            self.table_extractor = AdaptiveTableExtractor(self.config)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.pdf:
            self.pdf.close()
    
    def extract_all_text(self) -> Dict[str, any]:
        """
        Extract all text from PDF in structured format.
        
        Returns:
            Dictionary containing structured text data
        """
        if not self.pdf:
            raise RuntimeError("PDF not opened. Use context manager or call open() first.")
        
        pages_text = []
        for page_num, page in enumerate(self.pdf.pages, start=1):
            try:
                text = page.extract_text()
                if text:
                    pages_text.append({
                        "page_number": page_num,
                        "text": text.strip(),
                        "char_count": len(text)
                    })
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {e}")
                pages_text.append({
                    "page_number": page_num,
                    "text": "",
                    "char_count": 0
                })
        
        return {
            "total_pages": self.total_pages,
            "pages": pages_text,
            "full_text": "\n\n".join([p["text"] for p in pages_text])
        }
    
    def identify_first_page(self) -> Optional[int]:
        """
        Identify the first content page (after cover/title pages).
        
        Uses adaptive heuristics based on book type:
        - Looks for pages with substantial text content
        - Checks for common first page indicators (introduction, chapter 1, etc.)
        - Skips pages with very little text (likely covers)
        - Adapts thresholds based on detected book type
        
        Returns:
            Page number of first content page (1-indexed), or None if not found
        """
        if not self.pdf:
            raise RuntimeError("PDF not opened. Use context manager or call open() first.")
        
        # Use config-based content indicators and thresholds
        content_indicators = self.config.content_indicators if self.config else [
            r'\bintroduction\b',
            r'\bchapter\s+[1i]',
            r'\bpreface\b',
            r'\bforeword\b',
            r'\bprologue\b',
            r'\bpart\s+[1i]',
        ]
        
        min_text_length = self.config.min_content_length if self.config else 200
        skip_pages = self.config.skip_initial_pages if self.config else 0
        
        # Start checking after skip pages
        start_page = skip_pages + 1
        
        for page_num, page in enumerate(self.pdf.pages[start_page-1:], start=start_page):
            try:
                text = page.extract_text()
                if not text:
                    continue
                
                text_lower = text.lower().strip()
                text_length = len(text_lower)
                
                # Check if page has substantial content
                if text_length < min_text_length:
                    continue
                
                # Check for content indicators
                for pattern in content_indicators:
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        logger.info(f"First content page identified at page {page_num} (matched: {pattern})")
                        return page_num
                
                # If we have substantial text and we're past initial pages, likely content
                if page_num > skip_pages + 2 and text_length > min_text_length * 1.5:
                    logger.info(f"First content page identified at page {page_num} (substantial content)")
                    return page_num
                    
            except Exception as e:
                logger.warning(f"Error processing page {page_num} for first page detection: {e}")
                continue
        
        # Fallback: return first page with substantial content
        for page_num, page in enumerate(self.pdf.pages[start_page-1:], start=start_page):
            try:
                text = page.extract_text()
                if text and len(text.strip()) > min_text_length:
                    logger.info(f"First content page identified at page {page_num} (fallback)")
                    return page_num
            except Exception as e:
                continue
        
        return start_page  # Default to first page after skip
    
    def extract_index(self, max_pages_to_check: Optional[int] = None) -> Optional[Dict[str, any]]:
        """
        Extract table of contents/index from PDF using adaptive strategies.
        
        Uses multiple strategies:
        1. Keyword-based detection
        2. Pattern-based detection
        3. Statistical analysis
        
        Args:
            max_pages_to_check: Maximum number of pages to check for index
            
        Returns:
            Dictionary containing index data, or None if not found
        """
        if not self.pdf:
            raise RuntimeError("PDF not opened. Use context manager or call open() first.")
        
        if not self.index_extractor:
            # Fallback: create extractor with default config
            self.index_extractor = AdaptiveIndexExtractor(ExtractionConfig())
        
        # Prepare page data for adaptive extractor
        max_pages = max_pages_to_check or self.config.max_index_pages
        pages_data = []
        
        for page_num in range(1, min(max_pages + 1, self.total_pages + 1)):
            try:
                page = self.pdf.pages[page_num - 1]
                text = page.extract_text()
                if text:
                    pages_data.append({
                        "page_number": page_num,
                        "text": text
                    })
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {e}")
                continue
        
        # Use adaptive extractor
        return self.index_extractor.extract(pages_data, max_pages)
    
    def extract_tables(self, page_range: Optional[Tuple[int, int]] = None) -> List[Dict[str, any]]:
        """
        Extract all tables from PDF pages using adaptive strategies.
        
        Args:
            page_range: Optional tuple (start_page, end_page) to limit extraction.
                       If None, extracts from all pages.
        
        Returns:
            List of dictionaries containing table data (row-wise format)
        """
        if not self.pdf:
            raise RuntimeError("PDF not opened. Use context manager or call open() first.")
        
        if not self.table_extractor:
            # Fallback: create extractor with default config
            self.table_extractor = AdaptiveTableExtractor(ExtractionConfig())
        
        start_page = page_range[0] if page_range else 1
        end_page = page_range[1] if page_range else self.total_pages
        
        all_tables = []
        
        for page_num in range(start_page, min(end_page + 1, self.total_pages + 1)):
            try:
                page = self.pdf.pages[page_num - 1]
                # Use adaptive table extractor
                tables = self.table_extractor.extract(page, page_num)
                all_tables.extend(tables)
            except Exception as e:
                logger.warning(f"Error extracting tables from page {page_num}: {e}")
                continue
        
        logger.info(f"Extracted {len(all_tables)} tables from pages {start_page}-{end_page}")
        return all_tables
    
    def extract_structured_content(self) -> Dict[str, any]:
        """
        Extract all structured content from PDF in one call.
        
        Returns:
            Dictionary containing all extracted content
        """
        if not self.pdf:
            raise RuntimeError("PDF not opened. Use context manager or call open() first.")
        
        logger.info(f"Starting structured content extraction from {self.pdf_path}")
        
        # Extract all text
        text_data = self.extract_all_text()
        
        # Identify first page
        first_page = self.identify_first_page()
        
        # Extract index
        index_data = self.extract_index()
        
        # Extract tables
        tables_data = self.extract_tables()
        
        return {
            "pdf_path": str(self.pdf_path),
            "total_pages": self.total_pages,
            "book_type": self.book_type.value if self.book_type else "unknown",
            "first_content_page": first_page,
            "text_extraction": text_data,
            "index": index_data,
            "tables": tables_data,
            "summary": {
                "total_pages": self.total_pages,
                "book_type": self.book_type.value if self.book_type else "unknown",
                "first_content_page": first_page,
                "total_text_pages": len([p for p in text_data["pages"] if p["text"]]),
                "index_found": index_data is not None,
                "index_entries_count": len(index_data["entries"]) if index_data else 0,
                "tables_count": len(tables_data),
                "total_characters": sum(p["char_count"] for p in text_data["pages"])
            }
        }

