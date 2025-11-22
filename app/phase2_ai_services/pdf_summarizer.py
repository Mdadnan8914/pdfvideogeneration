"""
PDF summarization service for generating extensive summaries of entire PDFs.
Uses GPT-4o-mini to create comprehensive summaries (minimum 10k words).
Handles large PDFs by chunking when necessary.
"""
import logging
import re
import time
from pathlib import Path
from typing import Dict, Tuple, List
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    """Estimate token count (roughly 1 token = 4 characters for English)."""
    return len(text) // 4


def _split_text_into_chunks(text: str, max_tokens: int) -> List[str]:
    """
    Split text into chunks that fit within token limit.
    Tries to split at paragraph boundaries to maintain context.
    """
    estimated_tokens = _estimate_tokens(text)
    if estimated_tokens <= max_tokens:
        return [text]
    
    chunks = []
    # Split by paragraphs (double newlines)
    paragraphs = re.split(r'\n\s*\n', text)
    current_chunk = []
    current_tokens = 0
    
    for paragraph in paragraphs:
        para_tokens = _estimate_tokens(paragraph)
        
        # If single paragraph is too large, split it by sentences
        if para_tokens > max_tokens:
            # Flush current chunk if it has content
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_tokens = 0
            
            # Split large paragraph by sentences
            sentences = re.split(r'([.!?]\s+)', paragraph)
            for i in range(0, len(sentences), 2):
                if i + 1 < len(sentences):
                    sentence = sentences[i] + sentences[i + 1]
                else:
                    sentence = sentences[i]
                
                sent_tokens = _estimate_tokens(sentence)
                if current_tokens + sent_tokens > max_tokens and current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = [sentence]
                    current_tokens = sent_tokens
                else:
                    current_chunk.append(sentence)
                    current_tokens += sent_tokens
        else:
            # Check if adding this paragraph would exceed limit
            if current_tokens + para_tokens > max_tokens and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_tokens = para_tokens
            else:
                current_chunk.append(paragraph)
                current_tokens += para_tokens
    
    # Add remaining chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks


def _generate_chunk_summary(
    client: OpenAI,
    model: str,
    chunk_text: str,
    chunk_index: int,
    total_chunks: int,
    pdf_filename: str,
    system_message: str
) -> str:
    """Generate a summary for a single chunk with rate limiting."""
    import time
    
    prompt = f"""You are summarizing part {chunk_index + 1} of {total_chunks} from the book "{pdf_filename}".

Create a detailed, comprehensive summary of this section. Include:
- Key plot points and events
- Character development and interactions
- Important themes and insights
- Significant details and descriptions

Write in a narrative style suitable for voice narration. Be thorough and detailed.

Section content:
{chunk_text}

Summary of this section:"""
    
    logger.info(f"Generating summary for chunk {chunk_index + 1}/{total_chunks}...")
    
    # Add delay between chunks to respect rate limits
    # With 30k TPM limit, we need to space out requests
    if chunk_index > 0:
        delay = 5  # 5 seconds delay between chunks to respect 30k TPM limit
        logger.info(f"Waiting {delay} seconds to respect rate limits...")
        time.sleep(delay)
    
    # Retry logic for rate limit errors
    max_retries = 3
    retry_delay = 10  # 10 seconds
    
    # For chunk summaries, use smaller output to stay under 30k TPM
    # Input ~10k + output ~8k = ~18k total (safe)
    chunk_max_output_tokens = 8000
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=chunk_max_output_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            error_str = str(e)
            if "rate_limit" in error_str.lower() or "429" in error_str:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                    logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Rate limit error after {max_retries} attempts")
                    raise
            else:
                # Not a rate limit error, re-raise immediately
                raise
    
    # Should never reach here, but just in case
    raise Exception("Failed to generate chunk summary after retries")


def generate_pdf_summary(
    pdf_text: str,
    pdf_filename: str,
    min_words: int = 10000
) -> Tuple[str, Dict[str, any]]:
    """
    Generate an extensive summary of the entire PDF using GPT-4o.
    Creates a "mini book" summary that is comprehensive and detailed.
    
    Args:
        pdf_text: Full text extracted from PDF
        pdf_filename: Name of the PDF file (for context)
        min_words: Minimum word count for the summary (default: 10,000)
    
    Returns:
        Tuple of (summary_text, stats_dict)
        stats_dict contains: word_count, estimated_minutes, model_used
    """
    if not pdf_text or not pdf_text.strip():
        raise ValueError("Cannot generate summary from empty PDF text.")
    
    if not settings.OPENAI_API_KEY:
        raise ValueError(
            "OpenAI API key not configured. "
            "Please set OPENAI_API_KEY in your .env file."
        )
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    # Use GPT-4o-mini which has better rate limits and is more cost-effective
    # It still has 128k context tokens, so it can handle large PDFs
    model = "gpt-4o-mini"
    
    logger.info(f"Generating PDF summary using {model} (minimum {min_words:,} words)...")
    logger.info(f"PDF text length: {len(pdf_text)} characters")
    
    # GPT-4o-mini has 128k context tokens
    # But we need to respect rate limits (TPM - tokens per minute)
    # If user has 30k TPM limit, we need to keep TOTAL tokens (input + output) under 30k
    # For chunk summaries: input ~10k + output ~8k = ~18k total (safe)
    # For final summary: input ~20k + output ~16k = ~36k (might exceed, so we'll reduce output)
    # Use smaller chunks to ensure we stay well under 30k TPM limit
    max_input_tokens = 10_000  # Very conservative limit to respect 30k TPM
    max_input_chars = max_input_tokens * 4  # ~40k characters per chunk
    
    estimated_tokens = _estimate_tokens(pdf_text)
    logger.info(f"Estimated tokens: {estimated_tokens:,}")
    
    system_message = (
        "You are an expert book summarizer and narrator. Your task is to create a comprehensive, "
        "engaging summary of the entire book that captures its essence, main themes, key characters, "
        "plot points, and important insights. The summary should be written in a narrative style "
        "suitable for voice narration, as if you're telling the story to a friend. "
        "Think of it as creating a 'mini book' - a complete, detailed retelling that preserves "
        "the full story, character arcs, and important details."
    )
    
    try:
        # Check if we need to chunk the PDF
        if estimated_tokens <= max_input_tokens:
            # PDF fits in one call - process the whole thing
            logger.info("PDF fits in single API call, processing entire document...")
            summary_text = _generate_single_summary(
                client, model, pdf_text, pdf_filename, min_words, system_message
            )
        else:
            # PDF is too large - need to chunk it
            logger.info(f"PDF is too large ({estimated_tokens:,} tokens), splitting into chunks...")
            chunks = _split_text_into_chunks(pdf_text, max_input_tokens)
            logger.info(f"Split PDF into {len(chunks)} chunks")
            
            # Generate summary for each chunk
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                try:
                    chunk_summary = _generate_chunk_summary(
                        client, model, chunk, i, len(chunks), pdf_filename, system_message
                    )
                    chunk_summaries.append(chunk_summary)
                    logger.info(f"Completed chunk {i + 1}/{len(chunks)}")
                except Exception as e:
                    logger.error(f"Error processing chunk {i + 1}: {e}")
                    # Continue with other chunks, but log the error
                    # We'll try to create a summary from the chunks we have
                    if "rate_limit" in str(e).lower():
                        logger.error("Rate limit exceeded. Please try again later or upgrade your OpenAI plan.")
                    raise
            
            # Combine chunk summaries and create final comprehensive summary
            logger.info("Combining chunk summaries into final comprehensive summary...")
            combined_summaries = "\n\n".join([
                f"=== Section {i+1} Summary ===\n{summary}"
                for i, summary in enumerate(chunk_summaries)
            ])
            
            summary_text = _generate_final_summary(
                client, model, combined_summaries, pdf_filename, min_words, system_message
            )
        
        word_count = len(summary_text.split())
        logger.info(f"Final summary generated: {word_count:,} words")
        
        # If summary is still too short, expand it iteratively until we reach minimum
        expansion_attempts = 0
        max_expansion_attempts = 5
        
        while word_count < min_words and expansion_attempts < max_expansion_attempts:
            expansion_attempts += 1
            logger.warning(
                f"Summary is {word_count:,} words, but minimum is {min_words:,}. "
                f"Expanding (attempt {expansion_attempts}/{max_expansion_attempts})..."
            )
            
            # Calculate how much more we need
            words_needed = min_words - word_count
            target_words = min_words + (words_needed * 0.2)  # Add 20% buffer
            
            summary_text = _expand_summary(
                client, model, summary_text, int(target_words), system_message
            )
            word_count = len(summary_text.split())
            logger.info(f"After expansion {expansion_attempts}: {word_count:,} words")
            
            # Add delay between expansion attempts to respect rate limits
            if expansion_attempts < max_expansion_attempts and word_count < min_words:
                time.sleep(3)  # 3 second delay
        
        if word_count < min_words:
            logger.warning(
                f"Summary is still {word_count:,} words after {max_expansion_attempts} expansion attempts. "
                f"Target was {min_words:,} words."
            )
        
        # Calculate estimated narration time (assuming ~150 words per minute)
        words_per_minute = 150
        estimated_minutes = word_count / words_per_minute
        
        stats = {
            "word_count": word_count,
            "estimated_minutes": round(estimated_minutes, 2),
            "model_used": model,
            "meets_minimum": word_count >= min_words
        }
        
        logger.info(f"Summary generation complete: {word_count:,} words, ~{estimated_minutes:.1f} minutes of narration")
        
        return summary_text, stats
        
    except Exception as e:
        logger.error(f"Error generating PDF summary: {e}", exc_info=True)
        raise


def _generate_single_summary(
    client: OpenAI,
    model: str,
    pdf_text: str,
    pdf_filename: str,
    min_words: int,
    system_message: str
) -> str:
    """Generate summary for a PDF that fits in a single API call."""
    prompt = f"""Create a comprehensive, extensive summary of the entire book from the PDF file "{pdf_filename}".

CRITICAL REQUIREMENTS - THESE ARE MANDATORY:
1. The summary MUST be AT LEAST {min_words:,} words long - this is an absolute minimum requirement, not a suggestion
2. Cover the ENTIRE book comprehensively - include ALL major plot points, themes, characters, and insights
3. Write in a narrative, engaging style suitable for voice narration
4. Maintain the book's tone and style as much as possible
5. Include extensive details, character development, and key events
6. Make it feel like a complete "mini book" - a full retelling of the story with rich detail
7. The summary should be so comprehensive that someone listening to it would understand the full book
8. Add descriptive passages, expand on dialogue, elaborate on character thoughts and emotions
9. Include more narrative detail, scene descriptions, and storytelling elements
10. Think of this as creating a condensed but detailed version that preserves the complete story

This summary will be used to create a video narration, so it needs to be extensive and detailed enough to fill significant narration time.

Here is the full text from the PDF:

{pdf_text}

Now create the extensive summary. It MUST be at least {min_words:,} words - be thorough and detailed:"""
    
    logger.info("Calling OpenAI API for summary generation...")
    # For single summary, reduce output tokens to stay under 30k TPM
    # Input ~10k + output ~12k = ~22k total (safe)
    single_summary_max_output = 12000
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=single_summary_max_output
    )
    
    return response.choices[0].message.content.strip()


def _generate_final_summary(
    client: OpenAI,
    model: str,
    combined_summaries: str,
    pdf_filename: str,
    min_words: int,
    system_message: str
) -> str:
    """Generate final comprehensive summary from combined chunk summaries."""
    prompt = f"""You have been given summaries of different sections of the book "{pdf_filename}". 
Your task is to combine these into a single, comprehensive, extensive summary of the ENTIRE book.

CRITICAL REQUIREMENTS - THESE ARE MANDATORY:
1. The final summary MUST be AT LEAST {min_words:,} words long - this is an absolute minimum requirement
2. Combine all sections seamlessly into a cohesive narrative
3. Ensure ALL major plot points, themes, characters, and insights from all sections are included
4. Write in a narrative, engaging style suitable for voice narration
5. Make it feel like a complete "mini book" - a full retelling of the entire story with rich detail
6. Maintain smooth transitions between sections
7. The summary should be so comprehensive that someone listening to it would understand the full book
8. Expand on the content from each section - add more detail, descriptions, and narrative elements
9. Include more character development, dialogue, and scene descriptions
10. Elaborate on themes, relationships, and social commentary
11. This summary will be used for video narration, so it needs to be extensive and detailed

Here are the section summaries:

{combined_summaries}

Now create the comprehensive final summary of the entire book. It MUST be at least {min_words:,} words - be thorough and detailed:"""
    
    logger.info("Calling OpenAI API to combine summaries into final comprehensive summary...")
    # For final summary, we might have larger input, so reduce output tokens
    # Try to keep total under 30k TPM
    final_summary_max_output = 12000
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=final_summary_max_output
    )
    
    return response.choices[0].message.content.strip()


def _expand_summary(
    client: OpenAI,
    model: str,
    summary_text: str,
    target_words: int,
    system_message: str
) -> str:
    """Expand a summary that is too short."""
    word_count = len(summary_text.split())
    words_needed = target_words - word_count
    
    expansion_prompt = f"""CRITICAL: The summary is currently {word_count:,} words, but it MUST be expanded to at least {target_words:,} words. 
This is a MINIMUM requirement - the summary should be comprehensive and detailed.

Please SIGNIFICANTLY expand the summary by:
1. Adding MUCH more detail to existing plot points and scenes
2. Expanding character descriptions and development
3. Adding more dialogue and interactions
4. Including more descriptive passages about settings and emotions
5. Elaborating on themes and social commentary
6. Adding more context and background information
7. Expanding on relationships and character dynamics
8. Including more narrative detail and storytelling elements

The expansion should be substantial - you need to add approximately {words_needed:,} more words. 
Make it feel like a complete "mini book" that thoroughly covers the entire story with rich detail.
This summary will be used for video narration, so it needs to be extensive.

Current summary ({word_count:,} words):
{summary_text}

Expanded summary (MUST be at least {target_words:,} words - this is critical):"""
    
    # Use higher max_tokens for expansion to allow for longer output
    expansion_max_output = 16000  # Use full 16k for expansion
    
    # Retry logic for rate limits
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": expansion_prompt}
                ],
                temperature=0.7,
                max_tokens=expansion_max_output
            )
            
            expanded_text = response.choices[0].message.content.strip()
            expanded_word_count = len(expanded_text.split())
            logger.info(f"Expansion generated {expanded_word_count:,} words (target: {target_words:,})")
            
            return expanded_text
            
        except Exception as e:
            error_str = str(e)
            if "rate_limit" in error_str.lower() or "429" in error_str:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"Rate limit during expansion, waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Rate limit error during expansion after {max_retries} attempts")
                    raise
            else:
                raise
    
    raise Exception("Failed to expand summary after retries")

