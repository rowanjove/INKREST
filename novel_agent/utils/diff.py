import difflib
from typing import List, Dict

def compute_text_diff(text_a: str, text_b: str) -> List[Dict[str, str]]:
    """
    Compute a flat list of diff chunks between text_a and text_b.
    Each chunk is a dictionary: {"type": "equal" | "insert" | "delete", "text": "..."}.
    """
    a = text_a or ""
    b = text_b or ""
    
    matcher = difflib.SequenceMatcher(None, a, b)
    chunks = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            chunks.append({
                "type": "equal",
                "text": a[i1:i2]
            })
        elif tag == 'delete':
            chunks.append({
                "type": "delete",
                "text": a[i1:i2]
            })
        elif tag == 'insert':
            chunks.append({
                "type": "insert",
                "text": b[j1:j2]
            })
        elif tag == 'replace':
            chunks.append({
                "type": "delete",
                "text": a[i1:i2]
            })
            chunks.append({
                "type": "insert",
                "text": b[j1:j2]
            })
            
    # Clean up empty chunks and merge consecutive chunks of the same type
    merged_chunks = []
    for chunk in chunks:
        if not chunk["text"]:
            continue
        if merged_chunks and merged_chunks[-1]["type"] == chunk["type"]:
            merged_chunks[-1]["text"] += chunk["text"]
        else:
            merged_chunks.append(chunk)
            
    return merged_chunks
