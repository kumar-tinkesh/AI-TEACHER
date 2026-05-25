# Chunk settings optimized for LLM context windows
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

TEXT_EXTENSIONS = {
    ".txt", ".md", ".json", ".csv", ".xml", ".yaml", ".yml",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".java", ".c", ".cpp", ".h", ".go", ".rs", ".rb", ".php",
    ".sh", ".bat", ".ps1", ".sql", ".r", ".swift", ".kt",
    ".scala", ".lua", ".pl", ".pm", ".erl", ".ex", ".exs",
    ".hs", ".lhs", ".clj", ".cljs", ".edn", ".coffee",
    ".vue", ".svelte", ".astro", ".sol", ".vy", ".cairo",
}


def extract_text_from_bytes(raw: bytes, filename: str | None = None) -> str:
    """
    Extract text content from raw bytes.
    Returns empty string for unsupported binary formats or decode failures.
    """
    if filename:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        # Only attempt text extraction for known text-like extensions
        known_exts = {e.lstrip(".") for e in TEXT_EXTENSIONS}
        if ext not in known_exts:
            return ""

    # Try multiple encodings
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return ""


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks for LLM context retrieval.
    Chunks are split at word boundaries when possible.
    """
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    step = chunk_size - overlap

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Try to break at a word boundary or newline
        if end < len(text):
            # Look for newline first
            nl_pos = text.rfind("\n", start, end)
            if nl_pos > start + chunk_size // 2:
                end = nl_pos + 1
            else:
                # Look for space
                space_pos = text.rfind(" ", start, end)
                if space_pos > start + chunk_size // 2:
                    end = space_pos + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start += step
        if end >= len(text):
            break

    return chunks


def chunk_bytes(raw: bytes, filename: str | None = None) -> list[str]:
    """
    Extract text from raw bytes and split into chunks.
    Returns a list of chunk strings.
    """
    text = extract_text_from_bytes(raw, filename)
    return split_into_chunks(text)
