import unicodedata

def normalize_text(text: str) -> str:
    """Normalizes text by removing accents, lowercasing, and stripping whitespace."""
    if not text:
        return ""
    # Remove accents/diacritics
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return text.strip().lower()
