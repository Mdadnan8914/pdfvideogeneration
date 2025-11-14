import logging
from pathlib import Path
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

def extract_images(pdf_path: Path, job_dir: Path, min_width: int = 400, min_height: int = 300) -> Path:
    """
    Extracts images from a PDF, skipping small decorative ones.
    """
    logger.info(f"Starting image extraction from {pdf_path.name}...")
    images_dir = job_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    image_count = 0
    
    try:
        pdf = fitz.open(pdf_path)
        for page_index, page in enumerate(pdf):
            images = page.get_images(full=True)
            for count, img in enumerate(images):
                xref = img[0]
                width = img[2]
                height = img[3]

                # Filter out small images, based on Adnan's notebook
                if width < min_width or height < min_height:
                    continue  

                extracted = pdf.extract_image(xref)
                if not extracted or not extracted.get("image"):
                    continue

                img_bytes = extracted["image"]
                img_ext = extracted["ext"]
                
                filename = f"page_{page_index+1}_img_{count+1}.{img_ext}"
                img_path = images_dir / filename
                
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                image_count += 1

        pdf.close()
        logger.info(f"Extracted {image_count} images to: {images_dir}")
        return images_dir
    except Exception as e:
        logger.error(f"Failed to extract images: {e}", exc_info=True)
        pdf.close()
        raise