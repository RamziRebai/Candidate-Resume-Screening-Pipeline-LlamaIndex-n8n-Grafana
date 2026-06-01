import logging
import re
import time

from llama_index.core.schema import TransformComponent

logger = logging.getLogger(__name__)
CURRENT_RESUME_FILE = None
def group_resume_sections(text: str) -> list[str]:
    """
    Parses a markdown-formatted resume text and groups content under their
    respective headers/sub-headers independently.
    
    Returns a list of strings like:
    ["EDUCATION: **ESPRIT - Cycle Ingénieur, Data Science** **2021 – 2024**", ...]
    """
    lines = text.split('\n')
    result = []
    
    current_header = None
    current_content = []
    preamble_lines = []
    in_preamble = True

    def flush_content(header, content_lines):
        content = ' '.join(
            line.strip() for line in content_lines
            if line.strip() and line.strip() != '---'
        )
        if content:
            if header:
                result.append(f"{header}: {content}")
            else:
                result.append(f"preamble: {content}")

    def get_header(line: str):
        match = re.match(r'^(#{1,6})\s+(.*)', line)
        if match:
            text = match.group(2).strip()
            text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
            return text
        return None

    for line in lines:
        header = get_header(line)

        if header:
            in_preamble = False
            flush_content(current_header, current_content)
            current_header = header
            current_content = []
        elif in_preamble:
            if line.strip():
                preamble_lines.append(line.strip())
        else:
            current_content.append(line)

    # Flush last section
    flush_content(current_header, current_content)

    # Add preamble at the beginning
    if preamble_lines:
        result.insert(0, f"preamble: {' '.join(preamble_lines)}")

    return result

# ================================================================================
# CUSTOM TRANSFORM COMPONENTS
# ================================================================================

class ResumeTextProcessor(TransformComponent):
    """Custom processor for cleaning and enriching resume text"""
    
    def __call__(self, nodes, **kwargs):
        """Process nodes by cleaning text and adding metadata"""
        global CURRENT_RESUME_FILE
        processed_nodes = []
        
        for node in nodes:
            # Clean text - remove excessive special characters but keep important ones
            node.metadata.update({
                "resume_file": CURRENT_RESUME_FILE,
                "text_length": len(node.text),
                "processing_timestamp": str(int(time.time()))
            })
            processed_nodes.append(node)
            
        logger.info(f"Processed {len(processed_nodes)} nodes for resume: {CURRENT_RESUME_FILE}")
        return processed_nodes

# ================================================================================
# MAIN WORKFLOW IMPLEMENTATION

