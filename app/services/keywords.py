import json
import re
from collections import Counter

from sqlmodel import Session, select

from app.models import Keyword, Video


def extract_keywords_from_videos(session: Session, channel_id: int) -> int:
    """Extract keywords from a channel's video titles, tags, and descriptions.
    Returns the number of new keywords added."""
    videos = session.exec(select(Video).where(Video.channel_id == channel_id)).all()

    word_freq = Counter()

    for video in videos:
        # Extract from title
        words = _clean_and_split(video.title)
        word_freq.update(words)

        # Extract from tags
        if video.tags:
            try:
                tags = json.loads(video.tags)
                for tag in tags:
                    tag_words = _clean_and_split(tag)
                    word_freq.update(tag_words)
                    # Also keep full multi-word tags as phrases
                    cleaned_tag = tag.strip().lower()
                    if len(cleaned_tag) > 2 and " " in cleaned_tag:
                        word_freq[cleaned_tag] += 2  # Boost phrases from tags

            except (json.JSONDecodeError, TypeError):
                pass

        # Extract from description (first 500 chars — rest is usually links/boilerplate)
        if video.description:
            desc_words = _clean_and_split(video.description[:500])
            word_freq.update(desc_words)

    # Filter: keep terms that appear 2+ times or are multi-word phrases
    count = 0
    for term, freq in word_freq.most_common(200):
        if freq < 2 and " " not in term:
            continue
        if len(term) < 3:
            continue

        # Skip if already exists
        existing = session.exec(select(Keyword).where(Keyword.term == term)).first()
        if existing:
            continue

        keyword = Keyword(
            term=term,
            source="extraction",
            volume_proxy=float(freq),
        )
        session.add(keyword)
        count += 1

    session.commit()
    return count


# Common stopwords to filter out
_STOPWORDS = {
    "the", "and", "for", "with", "you", "that", "this", "from", "your",
    "are", "was", "were", "been", "have", "has", "had", "will", "would",
    "can", "could", "may", "might", "shall", "should", "not", "but",
    "into", "about", "than", "then", "when", "where", "which", "who",
    "how", "what", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "too", "very",
    "just", "because", "through", "during", "before", "after", "above",
    "below", "between", "under", "again", "further", "once", "here",
    "there", "also", "does", "did", "doing", "being", "while",
    "https", "http", "www", "com", "org",
}


def _clean_and_split(text: str) -> list[str]:
    """Clean text and split into meaningful terms."""
    text = text.lower()
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove special chars but keep spaces and hyphens
    text = re.sub(r"[^\w\s-]", " ", text)
    # Split
    words = text.split()
    # Filter stopwords and short words
    words = [w for w in words if w not in _STOPWORDS and len(w) > 2]

    # Also generate bigrams (two-word phrases)
    bigrams = []
    for i in range(len(words) - 1):
        bigram = f"{words[i]} {words[i+1]}"
        bigrams.append(bigram)

    return words + bigrams
