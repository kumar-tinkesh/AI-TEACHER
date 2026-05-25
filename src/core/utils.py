import json
import random
from datetime import datetime, timezone
from sqlmodel import Session, select


def generate_random_id(db: Session, model, min_val: int, max_val: int, max_attempts: int = 10) -> int:
    """Generate a random unique ID in the given range, checking for collisions."""
    for _ in range(max_attempts):
        new_id = random.randint(min_val, max_val)
        existing = db.exec(select(model).where(model.id == new_id)).first()
        if not existing:
            return new_id
    raise RuntimeError(f"Could not generate unique ID for {model.__name__} after {max_attempts} attempts")


def make_chunk_objects(chunks: list[str]) -> list[dict]:
    """Build chunk objects with random 7-digit IDs."""
    result = []
    for idx, content in enumerate(chunks):
        chunk_id = random.randint(1_000_000, 9_999_999)
        result.append({
            "id": chunk_id,
            "chunk_index": idx,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return result
