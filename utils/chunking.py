from typing import List

def split_text_into_chunks(text: str, max_words: int = 1000) -> List[str]:
    words = text.split()
    return [' '.join(words[i:i + max_words]) for i in range(0, len(words), max_words)]