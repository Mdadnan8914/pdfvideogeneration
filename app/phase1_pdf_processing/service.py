"""
PDF extraction service for processing PDF files and extracting structured content.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from .processor import PDFProcessor

logger = logging.getLogger(__name__)


class PDFExtractorService:
    """Service for extracting structured content from PDF files."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize PDF extractor service.
        
        Args:
            output_dir: Directory to save extraction results. If None, uses current directory.
        """
        self.output_dir = Path(output_dir) if output_dir else Path("./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_from_pdf(
        self,
        pdf_path: str,
        job_id: Optional[str] = None,
        extract_tables: bool = True,
        extract_index: bool = True,
        identify_first_page: bool = True
    ) -> Dict[str, any]:
        """
        Extract structured content from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            job_id: Optional job ID for organizing output files
            extract_tables: Whether to extract tables
            extract_index: Whether to extract index/table of contents
            identify_first_page: Whether to identify first content page
        
        Returns:
            Dictionary containing extracted content and metadata
        """
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Starting PDF extraction from {pdf_path}")
        
        # Generate job ID if not provided
        if not job_id:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            job_id = f"pdf_extract_{timestamp}"
        
        job_output_dir = self.output_dir / job_id
        job_output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Process PDF
            with PDFProcessor(pdf_path) as processor:
                # Extract all text
                text_data = processor.extract_all_text()
                
                # Identify first page
                first_page = None
                if identify_first_page:
                    first_page = processor.identify_first_page()
                
                # Extract index
                index_data = None
                if extract_index:
                    index_data = processor.extract_index()
                
                # Extract tables
                tables_data = []
                if extract_tables:
                    tables_data = processor.extract_tables()
                
                # Compile results
                result = {
                    "job_id": job_id,
                    "pdf_path": str(pdf_path_obj.resolve()),
                    "pdf_filename": pdf_path_obj.name,
                    "extraction_timestamp": datetime.now().isoformat(),
                    "total_pages": processor.total_pages,
                    "book_type": processor.book_type.value if processor.book_type else "unknown",
                    "first_content_page": first_page,
                    "text_extraction": {
                        "total_pages": text_data["total_pages"],
                        "pages": text_data["pages"],
                        "full_text": text_data["full_text"],
                        "total_characters": sum(p["char_count"] for p in text_data["pages"])
                    },
                    "index": index_data,
                    "tables": tables_data,
                    "summary": {
                        "total_pages": processor.total_pages,
                        "book_type": processor.book_type.value if processor.book_type else "unknown",
                        "first_content_page": first_page,
                        "total_text_pages": len([p for p in text_data["pages"] if p["text"]]),
                        "index_found": index_data is not None,
                        "index_entries_count": len(index_data["entries"]) if index_data else 0,
                        "tables_count": len(tables_data),
                        "total_characters": sum(p["char_count"] for p in text_data["pages"])
                    }
                }
                
                # Save results to JSON file
                json_output_path = job_output_dir / f"{job_id}_extraction.json"
                with open(json_output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False, default=str)
                
                logger.info(f"Extraction complete. Results saved to {json_output_path}")
                
                # Save full text to separate file
                text_output_path = job_output_dir / f"{job_id}_full_text.txt"
                with open(text_output_path, 'w', encoding='utf-8') as f:
                    f.write(text_data["full_text"])
                
                # Save index to separate file if found
                if index_data:
                    index_output_path = job_output_dir / f"{job_id}_index.txt"
                    with open(index_output_path, 'w', encoding='utf-8') as f:
                        f.write(f"Index (Page {index_data['page_number']}):\n\n")
                        for entry in index_data["entries"]:
                            entry_num = entry.get("entry_number", "")
                            title = entry.get("title", "")
                            page_ref = entry.get("page_reference", "")
                            f.write(f"{entry_num} {title} ... {page_ref}\n")
                
                # Save tables to CSV files if found
                if tables_data:
                    tables_dir = job_output_dir / "tables"
                    tables_dir.mkdir(exist_ok=True)
                    for table in tables_data:
                        table_filename = f"page_{table['page_number']}_table_{table['table_index']}.csv"
                        table_path = tables_dir / table_filename
                        if "csv" in table:
                            # Write CSV directly (already row-wise)
                            with open(table_path, 'w', encoding='utf-8', newline='') as f:
                                f.write(table["csv"])
                        else:
                            # Fallback: write raw data row-wise
                            with open(table_path, 'w', encoding='utf-8', newline='') as f:
                                import csv
                                writer = csv.writer(f)
                                # Write header row
                                if table.get("header"):
                                    writer.writerow([str(c) for c in table["header"]])
                                # Write data rows (each row is a horizontal row)
                                for row in table.get("data", []):
                                    writer.writerow([str(c) for c in row])
                
                # Add output file paths to result
                result["output_files"] = {
                    "json": str(json_output_path),
                    "full_text": str(text_output_path),
                    "index": str(index_output_path) if index_data else None,
                    "tables_directory": str(tables_dir) if tables_data else None
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}", exc_info=True)
            raise
    
    def extract_structured(self, pdf_path: str, job_id: Optional[str] = None) -> Dict[str, any]:
        """
        Convenience method to extract all structured content.
        
        Args:
            pdf_path: Path to the PDF file
            job_id: Optional job ID for organizing output files
        
        Returns:
            Dictionary containing all extracted content
        """
        return self.extract_from_pdf(
            pdf_path=pdf_path,
            job_id=job_id,
            extract_tables=True,
            extract_index=True,
            identify_first_page=True
        )

