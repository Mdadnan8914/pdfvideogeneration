"""
Dynamic extraction strategies for different PDF book formats.
Uses multiple strategies and auto-detection to handle various book types.
"""
import re
import logging
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import pandas as pd

logger = logging.getLogger(__name__)


class BookType(Enum):
    """Types of books that require different extraction strategies."""
    ACADEMIC = "academic"
    NOVEL = "novel"
    TEXTBOOK = "textbook"
    MANUAL = "manual"
    UNKNOWN = "unknown"


@dataclass
class ExtractionConfig:
    """Configuration for extraction strategies."""
    # Index extraction
    index_keywords: List[str] = None
    index_patterns: List[str] = None
    max_index_pages: int = 15
    min_index_entries: int = 3
    
    # First page detection
    content_indicators: List[str] = None
    min_content_length: int = 200
    skip_initial_pages: int = 0
    
    # Table extraction
    min_table_rows: int = 2
    min_table_cols: int = 2
    min_table_cell_fill: float = 0.3
    max_cell_length: int = 500
    
    def __post_init__(self):
        """Set defaults if not provided."""
        if self.index_keywords is None:
            self.index_keywords = [
                r'\btable\s+of\s+contents\b',
                r'\bcontents\b',
                r'\bindex\b',
                r'\btoc\b',
                r'\boverview\b',
                r'\bchapters?\b',
            ]
        
        if self.index_patterns is None:
            self.index_patterns = [
                r'^[\s]*([IVX]+[\.\)]?|\d+[\.\)]?|chapter\s+\d+|part\s+\d+)[\s]+(.+?)(?:[\s]*\.{2,}[\s]*(\d+))?[\s]*$',
                r'^[\s]*([IVX]+[\.\)]?|\d+[\.\)]?)[\s]+(.+?)[\s]*$',
                r'^[\s]*([A-Z][^\.]{3,50})(?:[\s]*\.{2,}[\s]*(\d+))?[\s]*$',
            ]
        
        if self.content_indicators is None:
            self.content_indicators = [
                r'\bintroduction\b',
                r'\bchapter\s+[1i]',
                r'\bpreface\b',
                r'\bforeword\b',
                r'\bprologue\b',
                r'\bpart\s+[1i]',
                r'\bchapter\s+one\b',
                r'\bchapter\s+first\b',
            ]


class BookStructureAnalyzer:
    """Analyzes PDF structure to determine book type and best extraction strategy."""
    
    @staticmethod
    def analyze_book_type(text_samples: List[str], total_pages: int) -> BookType:
        """
        Analyze text samples to determine book type.
        
        Args:
            text_samples: Sample text from different pages
            total_pages: Total number of pages
            
        Returns:
            Detected book type
        """
        combined_text = " ".join(text_samples).lower()
        
        # Academic/Textbook indicators
        academic_indicators = [
            r'\breferences\b', r'\bbibliography\b', r'\bcitation\b',
            r'\babstract\b', r'\bintroduction\b', r'\bconclusion\b',
            r'\bfigure\s+\d+', r'\btable\s+\d+', r'\bequation\b'
        ]
        academic_score = sum(1 for pattern in academic_indicators 
                            if re.search(pattern, combined_text, re.IGNORECASE))
        
        # Novel indicators
        novel_indicators = [
            r'\bchapter\s+\d+', r'\bpart\s+\d+', r'\bepilogue\b',
            r'"[^"]{20,}"', r'\bhe\s+said\b', r'\bshe\s+said\b'
        ]
        novel_score = sum(1 for pattern in novel_indicators 
                         if re.search(pattern, combined_text, re.IGNORECASE))
        
        # Manual indicators
        manual_indicators = [
            r'\bstep\s+\d+', r'\bprocedure\b', r'\binstruction\b',
            r'\bhow\s+to\b', r'\btutorial\b', r'\bguide\b'
        ]
        manual_score = sum(1 for pattern in manual_indicators 
                          if re.search(pattern, combined_text, re.IGNORECASE))
        
        # Determine type
        if academic_score >= 3:
            return BookType.ACADEMIC
        elif novel_score >= 2 and total_pages > 100:
            return BookType.NOVEL
        elif manual_score >= 2:
            return BookType.MANUAL
        elif academic_score >= 2:
            return BookType.TEXTBOOK
        else:
            return BookType.UNKNOWN
    
    @staticmethod
    def get_config_for_type(book_type: BookType) -> ExtractionConfig:
        """Get extraction configuration for a specific book type."""
        configs = {
            BookType.ACADEMIC: ExtractionConfig(
                max_index_pages=20,
                min_index_entries=5,
                min_content_length=300,
                min_table_cell_fill=0.4,
            ),
            BookType.TEXTBOOK: ExtractionConfig(
                max_index_pages=25,
                min_index_entries=10,
                min_content_length=250,
                min_table_cell_fill=0.35,
            ),
            BookType.NOVEL: ExtractionConfig(
                max_index_pages=5,
                min_index_entries=1,
                min_content_length=100,
                skip_initial_pages=3,
            ),
            BookType.MANUAL: ExtractionConfig(
                max_index_pages=15,
                min_index_entries=3,
                min_content_length=150,
                min_table_cell_fill=0.3,
            ),
            BookType.UNKNOWN: ExtractionConfig(),  # Use defaults
        }
        return configs.get(book_type, ExtractionConfig())


class AdaptiveIndexExtractor:
    """Adaptive index extraction using multiple strategies."""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
    
    def extract(self, pages: List[Dict], max_pages: Optional[int] = None) -> Optional[Dict]:
        """
        Extract index using multiple strategies.
        
        Args:
            pages: List of page dictionaries with 'page_number' and 'text'
            max_pages: Maximum pages to check
            
        Returns:
            Index data or None
        """
        max_pages = max_pages or self.config.max_index_pages
        pages_to_check = min(max_pages, len(pages))
        
        # Strategy 1: Keyword-based detection
        index_pages = self._find_index_pages_by_keywords(pages[:pages_to_check])
        
        # Strategy 2: Pattern-based detection
        if not index_pages:
            index_pages = self._find_index_pages_by_patterns(pages[:pages_to_check])
        
        # Strategy 3: Statistical detection (look for pages with many short lines)
        if not index_pages:
            index_pages = self._find_index_pages_by_statistics(pages[:pages_to_check])
        
        if not index_pages:
            logger.info("No index pages found using any strategy")
            return None
        
        # Extract entries using multiple methods
        entries = self._extract_entries_adaptive(index_pages)
        
        if len(entries) < self.config.min_index_entries:
            logger.warning(f"Only found {len(entries)} index entries, minimum is {self.config.min_index_entries}")
            return None
        
        return {
            "page_number": index_pages[0]["page_number"],
            "pages": [p["page_number"] for p in index_pages],
            "has_index_keyword": True,
            "entries": entries,
            "raw_text": "\n".join([p["text"] for p in index_pages])
        }
    
    def _find_index_pages_by_keywords(self, pages: List[Dict]) -> List[Dict]:
        """Find index pages using keyword matching."""
        index_pages = []
        for page in pages:
            text_lower = page["text"].lower()
            if any(re.search(pattern, text_lower, re.IGNORECASE) 
                   for pattern in self.config.index_keywords):
                index_pages.append(page)
                # Check next few pages for continuation
                page_idx = pages.index(page)
                for next_page in pages[page_idx + 1:page_idx + 3]:
                    if self._looks_like_index_continuation(next_page["text"]):
                        if next_page not in index_pages:
                            index_pages.append(next_page)
                    else:
                        break
                break
        return index_pages
    
    def _find_index_pages_by_patterns(self, pages: List[Dict]) -> List[Dict]:
        """Find index pages using pattern matching."""
        index_pages = []
        for page in pages:
            text = page["text"]
            # Look for pages with many numbered entries
            numbered_lines = sum(1 for line in text.split('\n') 
                               if re.search(r'[IVX]+[\.\)]|\d+[\.\)]', line, re.IGNORECASE))
            if numbered_lines >= 3:
                index_pages.append(page)
                # Check continuation
                page_idx = pages.index(page)
                for next_page in pages[page_idx + 1:page_idx + 2]:
                    if self._looks_like_index_continuation(next_page["text"]):
                        if next_page not in index_pages:
                            index_pages.append(next_page)
                break
        return index_pages
    
    def _find_index_pages_by_statistics(self, pages: List[Dict]) -> List[Dict]:
        """Find index pages using statistical analysis."""
        index_pages = []
        for page in pages[:10]:  # Check first 10 pages
            text = page["text"]
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            if len(lines) < 5:
                continue
            
            # Index pages typically have:
            # - Many short lines (entry titles)
            # - Consistent line length
            # - Few very long lines
            avg_line_length = sum(len(l) for l in lines) / len(lines)
            short_lines = sum(1 for l in lines if 10 < len(l) < 80)
            long_lines = sum(1 for l in lines if len(l) > 150)
            
            # Heuristic: index pages have many short lines, few long lines
            if (short_lines > len(lines) * 0.5 and 
                long_lines < len(lines) * 0.2 and
                avg_line_length < 60):
                index_pages.append(page)
                break
        
        return index_pages
    
    def _looks_like_index_continuation(self, text: str) -> bool:
        """Check if text looks like continuation of index."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) < 3:
            return False
        
        # Check for numbered entries or short lines
        numbered = sum(1 for l in lines if re.search(r'[IVX]+[\.\)]|\d+[\.\)]', l))
        short_lines = sum(1 for l in lines if 5 < len(l) < 100)
        
        # Don't continue if we see actual content
        content_indicators = ['this', 'the', 'we', 'it', 'in', 'on', 'at']
        content_lines = sum(1 for l in lines 
                          if any(l.lower().startswith(ind + ' ') for ind in content_indicators))
        
        return (numbered >= 2 or short_lines > len(lines) * 0.6) and content_lines < 2
    
    def _extract_entries_adaptive(self, index_pages: List[Dict]) -> List[Dict]:
        """Extract index entries using adaptive pattern matching."""
        combined_text = "\n".join([p["text"] for p in index_pages])
        lines = combined_text.split('\n')
        
        entries = []
        current_entry = None
        start_collecting = False
        seen_titles = set()  # Track seen titles to avoid duplicates
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_entry:
                    # Save current entry
                    title_key = current_entry["title"].lower().strip()
                    if title_key not in seen_titles and len(title_key) > 2:
                        entries.append(current_entry)
                        seen_titles.add(title_key)
                    current_entry = None
                continue
            
            # Start collecting after finding index keyword
            if not start_collecting:
                if any(re.search(pattern, line, re.IGNORECASE) 
                      for pattern in self.config.index_keywords):
                    start_collecting = True
                continue
            
            # Stop if we hit actual content (but be lenient)
            if self._is_content_line(line, entries):
                # Only stop if we have enough entries and this really looks like content
                if len(entries) >= self.config.min_index_entries:
                    break
                continue
            
            # Skip common header/footer text
            if any(skip in line.lower() for skip in ['copyright', 'penguin', 'title page', 'dedication', 'epigraph']):
                # But allow if it's part of an entry
                if not current_entry:
                    continue
            
            # Try each pattern
            matched = False
            for pattern in self.config.index_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    if current_entry:
                        # Save previous entry
                        title_key = current_entry["title"].lower().strip()
                        if title_key not in seen_titles and len(title_key) > 2:
                            entries.append(current_entry)
                            seen_titles.add(title_key)
                    
                    groups = match.groups()
                    entry_num = groups[0] if len(groups) > 0 and groups[0] else None
                    title = groups[1] if len(groups) > 1 and groups[1] else line
                    page_ref = groups[2] if len(groups) > 2 and groups[2] else None
                    
                    # Clean title (remove duplicates if present)
                    if title:
                        title = str(title).strip()
                        # Remove duplicate words (e.g., "Title Page Title Page" -> "Title Page")
                        words = title.split()
                        if len(words) > 1 and words[:len(words)//2] == words[len(words)//2:]:
                            title = " ".join(words[:len(words)//2])
                    
                    # Validate entry
                    if title and 2 < len(str(title)) < 300:
                        title_key = title.lower().strip()
                        # Skip if we've seen this title
                        if title_key not in seen_titles:
                            current_entry = {
                                "entry_number": entry_num,
                                "title": title,
                                "page_reference": int(page_ref) if page_ref and page_ref.isdigit() else None
                            }
                            matched = True
                            break
                    else:
                        current_entry = None
                        matched = False
            
            # Handle continuation lines or unnumbered entries
            if not matched:
                if current_entry:
                    # This might be a continuation line
                    if len(line) < 150 and len(current_entry["title"]) + len(line) < 300:
                        # Check if it's not a duplicate
                        if line.lower().strip() != current_entry["title"].lower().strip():
                            current_entry["title"] += " " + line
                    else:
                        # Save current entry
                        title_key = current_entry["title"].lower().strip()
                        if title_key not in seen_titles:
                            entries.append(current_entry)
                            seen_titles.add(title_key)
                        current_entry = None
                else:
                    # Try to match as unnumbered entry (like "Epilogue", "Notes")
                    if (2 < len(line) < 80 and 
                        line[0].isupper() and
                        not line.isupper() and
                        not re.search(r'^[IVX]+[\.\)]|\d+[\.\)]', line)):
                        # Check if it's a known index entry type
                        known_entries = ['epilogue', 'notes', 'suggestions', 'about', 'appendix', 
                                       'bibliography', 'references', 'prologue', 'preface']
                        line_lower = line.lower()
                        if (any(line_lower.startswith(k) for k in known_entries) or 
                            (len(line.split()) <= 4 and not re.search(r'^(this|the|we|it|in|on|at|as|to|for|of|a|an)\s+[a-z]', line))):
                            title_key = line.lower().strip()
                            if title_key not in seen_titles:
                                entries.append({
                                    "entry_number": None,
                                    "title": line,
                                    "page_reference": None
                                })
                                seen_titles.add(title_key)
        
        # Save last entry
        if current_entry:
            title_key = current_entry["title"].lower().strip()
            if title_key not in seen_titles and len(title_key) > 2:
                entries.append(current_entry)
        
        # Filter and deduplicate
        filtered_entries = []
        seen = set()
        for entry in entries:
            title = entry.get("title", "").lower().strip()
            if title and title not in seen and 2 < len(title) < 300:
                # Skip if it's clearly not an index entry
                if not re.search(r'^(this|the|we|it|in|on|at|as|to|for|of|a|an)\s+[a-z]{10,}', title):
                    filtered_entries.append(entry)
                    seen.add(title)
        
        return filtered_entries
    
    def _is_content_line(self, line: str, entries: List[Dict]) -> bool:
        """Check if line looks like actual content (not index entry)."""
        # Very long lines (>250 chars) are likely content
        if len(line) > 250:
            return True
        
        # Lines starting with common content words followed by lowercase
        # This indicates actual prose content, not index entries
        content_starters = r'^(this|the|we|it|in|on|at|as|to|for|of|a|an)\s+[a-z]'
        if re.search(content_starters, line, re.IGNORECASE):
            # But allow if we have few entries (might still be collecting)
            if len(entries) < self.config.min_index_entries:
                return False
            # Also check if line is very long (definitely content)
            if len(line) > 150:
                return True
        
        # Check for PROLOGUE as standalone (but allow if it's an index entry)
        if re.match(r'^PROLOGUE$', line, re.IGNORECASE):
            # Only stop if we have entries and next line looks like content
            if len(entries) >= self.config.min_index_entries:
                return True
        
        return False


class AdaptiveTableExtractor:
    """Adaptive table extraction with multiple validation strategies."""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
    
    def extract(self, page, page_num: int) -> List[Dict]:
        """Extract tables from a page with adaptive validation."""
        try:
            tables = page.extract_tables()
            valid_tables = []
            
            for idx, table in enumerate(tables):
                if not table:
                    continue
                
                # Apply multiple validation strategies
                if self._validate_table(table):
                    structured = self._structure_table(table, page_num, idx + 1)
                    if structured:
                        valid_tables.append(structured)
            
            return valid_tables
        except Exception as e:
            logger.warning(f"Error extracting tables from page {page_num}: {e}")
            return []
    
    def _validate_table(self, table: List[List]) -> bool:
        """Validate if table structure is legitimate."""
        if not table:
            return False
        
        # Get non-empty rows
        non_empty_rows = [row for row in table 
                         if row and any(str(cell).strip() for cell in row if cell)]
        
        if len(non_empty_rows) < self.config.min_table_rows:
            return False
        
        # Check column count
        max_cols = max(len(row) for row in non_empty_rows if row)
        if max_cols < self.config.min_table_cols:
            return False
        
        # Check cell fill ratio
        total_cells = sum(len(row) for row in non_empty_rows)
        filled_cells = sum(1 for row in non_empty_rows 
                          for cell in row if cell and str(cell).strip())
        
        if total_cells == 0:
            return False
        
        fill_ratio = filled_cells / total_cells
        if fill_ratio < self.config.min_table_cell_fill:
            return False
        
        # Check for too many very long cells (likely formatted text, not table)
        long_cells = sum(1 for row in non_empty_rows 
                        for cell in row 
                        if cell and len(str(cell).strip()) > self.config.max_cell_length)
        
        if long_cells > len(non_empty_rows) * 0.5:
            return False
        
        return True
    
    def _structure_table(self, table: List[List], page_num: int, table_idx: int) -> Optional[Dict]:
        """Structure table data."""
        try:
            non_empty_rows = [row for row in table 
                            if row and any(str(cell).strip() for cell in row if cell)]
            
            if not non_empty_rows:
                return None
            
            # Identify header (first substantial row)
            header_row = None
            data_rows = []
            
            for row in non_empty_rows:
                cleaned = [str(cell).strip() if cell else "" for cell in row]
                if not any(cleaned):
                    continue
                
                if header_row is None:
                    header_row = cleaned
                else:
                    data_rows.append(cleaned)
            
            if not data_rows:
                return None
            
            # Normalize rows to header length
            header_len = len(header_row)
            normalized_data = []
            for row in data_rows:
                if len(row) < header_len:
                    row = row + [""] * (header_len - len(row))
                elif len(row) > header_len:
                    row = row[:header_len]
                normalized_data.append(row)
            
            # Create DataFrame
            try:
                df = pd.DataFrame(normalized_data, columns=header_row)
                return {
                    "page_number": page_num,
                    "table_index": table_idx,
                    "header": header_row,
                    "data": normalized_data,
                    "row_count": len(normalized_data),
                    "column_count": header_len,
                    "dataframe": df.to_dict('records'),
                    "csv": df.to_csv(index=False, lineterminator='\n')
                }
            except Exception as e:
                logger.warning(f"Error creating DataFrame: {e}")
                return {
                    "page_number": page_num,
                    "table_index": table_idx,
                    "header": header_row,
                    "data": normalized_data,
                    "row_count": len(normalized_data),
                    "column_count": header_len,
                    "raw_table": table
                }
        except Exception as e:
            logger.warning(f"Error structuring table: {e}")
            return None

