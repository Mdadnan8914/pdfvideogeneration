# scripts/test_pdf_only.py
import sys
import logging
from pathlib import Path
import time
from datetime import datetime
import argparse

# --- 1. Fix Python's Import Path ---
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.append(str(project_root))

# --- 2. Import Modules for Phase 1 ONLY ---
from app.config import settings
from app.logging_config import setup_logging

# Import Adnan's Full, Smart Services
from app.phase1_pdf_processing.service import PDFExtractorService
from app.phase1_pdf_processing.image_extractor import extract_images
from app.phase1_pdf_processing.text_cleaner import clean_text


def main(pdf_file_path: Path):
    start_time = time.time()
    
    # --- A. Setup ---
    job_id = f"pdf_test_{pdf_file_path.stem}_{datetime.now().strftime('%H%M%S')}"
    job_dir = settings.JOBS_OUTPUT_PATH / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    setup_logging(job_id=job_id, log_level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info(f"--- STARTING PDF-ONLY TEST FOR JOB: {job_id} ---")
    logger.info(f"Input PDF: {pdf_file_path}")
    logger.info(f"Job output will be in: {job_dir}")

    try:
        # ===== PHASE 1: PDF PROCESSING (Complete Logic) =====
        logger.info("--- PHASE 1: PDF Processing (with Adaptive Logic) ---")
        
        # 1.1: Run his full text/table/index service
        extractor_service = PDFExtractorService(output_dir=settings.JOBS_OUTPUT_PATH)
        extraction_result = extractor_service.extract_from_pdf(
            pdf_path=str(pdf_file_path),
            job_id=job_id
        )
        
        raw_text_path = Path(extraction_result["output_files"]["full_text"])
        tables_dir_path = extraction_result["output_files"].get("tables_directory")
        tables_dir = Path(tables_dir_path) if tables_dir_path else job_dir / "tables" # Handle if no tables
        
        # 1.2: image extraction logic
        images_dir = extract_images(pdf_file_path, job_dir)
        
        logger.info(f"Book type detected: {extraction_result['book_type']}")
        logger.info(f"Tables found: {extraction_result['summary']['tables_count']}")
        
        # ===== PHASE 1.5: TEXT CLEANING (The Dummy) =====
        logger.info("--- PHASE 1.5: Text Cleaning ---")
        cleaned_script_path = clean_text(
            raw_text_path=raw_text_path,
            tables_dir=tables_dir,
            images_dir=images_dir,
            job_dir=job_dir
        )
        logger.info(f"Dummy text cleaning complete. Output: {cleaned_script_path}")
        
        
        
        end_time = time.time()
        logger.info(f"--- PDF-ONLY TEST SUCCESS (Total time: {end_time - start_time:.2f}s) ---")
        logger.info(f"All Phase 1 outputs saved in {job_dir}")
        logger.info(f"Check the log file: {job_dir / (job_id + '_run.log')}")
        
    except Exception as e:
        logger.error(f"--- PDF-ONLY TEST FAILED {e}---", exc_info=True)
        end_time = time.time()
        logger.error(f"Failed after {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the PDF-Only (Phase 1) test.")
    parser.add_argument("pdf_path", type=str, help="Path to the input PDF file.")
    args = parser.parse_args()
    
    input_pdf = Path(args.pdf_path)
    if not input_pdf.exists():
        print(f"Error: PDF file not found at {input_pdf}")
        sys.exit(1)
        
    main(pdf_file_path=input_pdf)