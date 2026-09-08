"""Keyword extraction logic for the preprocessing stage."""

import re
from typing import Dict, List

from sklearn.feature_extraction.text import TfidfVectorizer

FRENCH_STOP_WORDS = {
    # Articles / déterminants
    "le", "la", "les", "un", "une", "des", "du", "de",
    "ce", "cet", "cette", "ces", "mon", "ma", "mes",
    "ton", "ta", "tes", "son", "sa", "ses",
    "notre", "nos", "votre", "vos", "leur", "leurs",

    # Conjonctions
    "et", "ou", "mais", "donc", "or", "ni", "car",
    "puisque", "comme", "lorsque", "quand", "si",
    "bien", "que",

    # Prépositions
    "à", "au", "aux", "de", "du", "des", "en", "dans",
    "sur", "sous", "avec", "sans", "pour", "par",
    "entre", "vers", "chez", "contre", "depuis",
    "pendant", "avant", "après", "selon", "parmi",
    "derrière", "devant", "près", "autour",

    # Pronoms
    "je", "tu", "il", "elle", "on", "nous", "vous",
    "ils", "elles", "me", "te", "se", "moi", "toi",
    "lui", "eux", "leur", "y", "en",

    # Auxiliaires / verbes très fréquents
    "être", "est", "sont", "était", "étaient", "été",
    "avoir", "a", "ont", "avait", "avaient", "eu",
    "faire", "fait", "font", "faisait",
    "peut", "peuvent", "pouvait",
    "doit", "doivent", "devait",
    "va", "vont", "allait",
    "sera", "seront", "serait",
    "sont",

    # Pronoms / mots interrogatifs et relatifs
    "qui", "que", "quoi", "dont", "où", "lequel",
    "laquelle", "lesquels", "lesquelles",
    "quel", "quelle", "quels", "quelles",

    # Quantificateurs / mots génériques
    "tout", "toute", "tous", "toutes",
    "aucun", "aucune", "chaque",
    "certains", "certaines", "plusieurs",
    "quelque", "quelques",
    "autre", "autres",
    "même", "mêmes",
    "plus", "moins", "très", "trop",
    "assez", "aussi", "seulement",

    # Adverbes / connecteurs génériques
    "ainsi", "alors", "donc", "cependant",
    "toutefois", "également", "notamment",
    "ensuite", "enfin", "déjà", "encore",
    "souvent", "toujours", "jamais",
    "ici", "là", "ainsi",

    # Mots académiques trop génériques
    "article", "document", "étude", "travail",
    "résultat", "résultats", "méthode", "méthodes",
    "section", "partie", "figure", "tableau",
    "exemple", "cas",

    # Éléments structurels du document
    "résumé", "introduction", "conclusion",
    "références", "bibliographie",
    "annexe", "annexes",
}
ENGLISH_STOP_WORDS = {
    # Articles / determiners
    "the", "a", "an", "this", "that", "these", "those",

    # Conjunctions
    "and", "or", "but", "nor", "yet",

    # Prepositions
    "of", "in", "on", "at", "by", "for", "from", "to",
    "with", "without", "within", "between", "among",
    "through", "during", "before", "after", "over", "under",
    "into", "onto", "upon", "about", "against",

    # Pronouns
    "i", "we", "you", "he", "she", "it", "they",
    "me", "us", "him", "her", "them",
    "our", "your", "their", "its", "his", "hers",

    # Auxiliary / common verbs
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having",
    "do", "does", "did",
    "can", "could", "may", "might", "must",
    "shall", "should", "will", "would",

    # Relative / interrogative words
    "who", "whom", "whose", "which", "what", "where",
    "when", "why", "how",

    # Common generic words
    "all", "any", "both", "each", "every", "few",
    "more", "most", "other", "some", "such",
    "same", "only", "own", "than", "too", "very",

    # Common academic filler
    "also", "however", "therefore", "thus", "then",
    "furthermore", "moreover", "already", "often",
    "still", "well", "rather", "much", "many",

    # Generic document words
    "figure", "fig", "table", "tab",
}

SECTION_TITLES = {
    "abstract",
    "résumé",
    "introduction",
    "background",
    "contexte",
    "related work",
    "travaux connexes",
    "method",
    "methods",
    "methodology",
    "méthode",
    "méthodes",
    "méthodologie",
    "materials and methods",
    "results",
    "résultats",
    "discussion",
    "conclusion",
    "conclusions",
    "limitations",
    "limites",
    "future work",
    "perspectives",
    "references",
    "références",
}
GENERIC_KEYWORD_TERMS = {
    # Document/contact artifacts
    "com",
    "www",
    "http",
    "https",
    "org",
    "edu",
    "email",
    "mail",
    "correspondence",
    "outlook",

    # Generic metadata/contact terms
    "author",
    "authors",
    "address",
    "university",
    "department",
    "institute",
    "laboratory",
    "lab",

    

    # Document structure
    "figure",
    "fig",
    "table",
    "tab",
    "page",
    "pages",
    "section",
    "sections",

    # Obvious benchmark fragments
    "max",
}
GENERIC_SINGLE_KEYWORDS = {
    "open",
    "additional",
    "available",
    "based",
    "different",
    "general",
    "important",
    "new",
    "possible",
    "related",
    "specific",
    "various",
}

def normalize_keyword(keyword: str) -> str:
    """Normalize a keyword string."""
    keyword = re.sub(r"\s+", " ", keyword.strip())
    return keyword.lower()


def is_valid_keyword(
    keyword: str,
    stop_words: set[str],
) -> bool:
    """Filter generic, structural, and low-information keywords."""

    keyword = normalize_keyword(keyword)

    if not keyword:
        return False

    words = keyword.split()

    # Avoid excessively long n-grams.
    if len(words) > 5:
        return False

    # Reject stop words anywhere in the candidate.
    if any(word in stop_words for word in words):
        return False
    if any(
        word in GENERIC_KEYWORD_TERMS
        for word in words
    ):
        return False
    # Reject candidates that are entirely numeric.
    if all(word.isdigit() for word in words):
        return False

    # Reject very short tokens.
    if any(len(word) < 3 for word in words):
        return False

    if len(words) == 1 and keyword in GENERIC_SINGLE_KEYWORDS:
        return False

    # Reject section/document structure labels.
    if keyword in SECTION_TITLES:
        return False

    return True


def extract_provided_keywords(text: str) -> List[str]:
    """Extract author-provided keywords from the text."""
    match = re.search(r"(?:keywords?|key\s*words?|index\s+terms?|mots[\s-]*clés)\s*[:—-]\s*(.+)", text, flags=re.IGNORECASE)
    if not match:
        return []
    keyword_line = match.group(1)
    return [normalize_keyword(item) for item in re.split(r"\s*[;,•|]\s*", keyword_line) if normalize_keyword(item)]


def create_text_chunks(text: str, minimum_length: int = 80) -> List[str]:
    """Split text into usable chunks for TF-IDF."""
    text = re.sub(r"\b(?:references|références)\b.*$", " ", text, flags=re.IGNORECASE | re.DOTALL)
    raw_chunks = re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-ZÀ-Ö])", text)
    chunks = [re.sub(r"\s+", " ", chunk).strip() for chunk in raw_chunks if len(re.sub(r"\s+", " ", chunk).strip()) >= minimum_length]
    if len(chunks) < 2:
        words = text.split()
        chunk_size = 150
        chunks = [" ".join(words[index:index + chunk_size]) for index in range(0, len(words), chunk_size) if len(words[index:index + chunk_size]) >= 20]
    return chunks


def generate_tfidf_keywords(text: str, language: str = "en", top_n: int = 15) -> List[Dict[str, object]]:
    """Generate TF-IDF keywords from the provided text."""
    chunks = create_text_chunks(text)
    if not chunks:
        return []
    stop_words = FRENCH_STOP_WORDS if language == "fr" else ENGLISH_STOP_WORDS
    vectorizer = TfidfVectorizer(lowercase=True, stop_words=list(stop_words), ngram_range=(1, 3), min_df=1, max_df=0.95 if len(chunks) >= 5 else 1.0, token_pattern=r"(?u)\b[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ0-9\-]{2,}\b", sublinear_tf=True, max_features=5000)
    try:
        matrix = vectorizer.fit_transform(chunks)
    except ValueError:
        return []
    terms = vectorizer.get_feature_names_out()
    raw_scores = matrix.mean(axis=0).A1
    candidates = []
    for term, score in zip(terms, raw_scores):
        term = normalize_keyword(term)
        if is_valid_keyword(term, stop_words):
            candidates.append({"keyword": term, "score": float(score), "method": "tfidf"})
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:top_n * 3]

def normalize_keyword_for_comparison(keyword: str) -> str:
    """Normalize simple morphological variants for comparison."""

    keyword = normalize_keyword(keyword)

    if keyword.endswith("ies") and len(keyword) > 4:
        return keyword[:-3] + "y"

    if keyword.endswith("ses") and len(keyword) > 5:
        return keyword[:-2]

    if keyword.endswith("s") and not keyword.endswith("ss"):
        return keyword[:-1]

    return keyword

def remove_redundant_keywords(
    candidates: List[Dict[str, object]],
    top_n: int = 15,
) -> List[Dict[str, object]]:
    """Remove duplicate and less-informative nested keywords."""

    normalized_candidates = []

    for candidate in candidates:
        term = normalize_keyword(
            str(candidate.get("keyword", ""))
        )

        if not term:
            continue

        normalized_candidates.append(
            {
                **candidate,
                "keyword": term,
            }
        )

    # Prefer multi-word phrases over their shorter components.
    # Keep TF-IDF score as the secondary ranking criterion.
    normalized_candidates.sort(
        key=lambda item: (
            len(str(item["keyword"]).split()),
            float(item.get("score", 0)),
        ),
        reverse=True,
    )

    selected: List[Dict[str, object]] = []
    selected_terms: List[str] = []

    for candidate in normalized_candidates:
        term = str(candidate["keyword"])

        if term in selected_terms:
            continue

        term_words = set(term.split())

        redundant = False

        for selected_term in selected_terms:
            selected_words = set(
                selected_term.split()
            )

            # Same words.
            if term_words == selected_words:
                redundant = True
                break

            # Shorter keyword is already covered by
            # a more informative multi-word keyword.
            if term_words.issubset(selected_words):
                redundant = True
                break

        if redundant:
            continue

        selected.append(candidate)
        selected_terms.append(term)

        if len(selected) >= top_n:
            break

    # Restore final ranking by score.
    selected.sort(
        key=lambda item: float(
            item.get("score", 0)
        ),
        reverse=True,
    )

    return selected[:top_n]


def combine_keyword_sources(provided_keywords: List[str], tfidf_keywords: List[Dict[str, object]], language: str = "en", top_n: int = 15) -> List[Dict[str, object]]:
    """Combine author-provided and TF-IDF keywords."""
    stop_words = FRENCH_STOP_WORDS if language == "fr" else ENGLISH_STOP_WORDS
    combined: Dict[str, Dict[str, object]] = {}
    number_of_provided = max(len(provided_keywords), 1)
    for index, keyword in enumerate(provided_keywords):
        keyword = normalize_keyword(keyword)
        if not is_valid_keyword(keyword, stop_words):
            continue
        score = max(0.90, 1.00 - (index / number_of_provided) * 0.10)
        combined[keyword] = {"keyword": keyword, "score": round(score, 4), "method": "provided_keywords"}
    maximum_tfidf = max([item.get("score", 0) for item in tfidf_keywords], default=0)
    for item in tfidf_keywords:
        keyword = normalize_keyword(str(item.get("keyword", "")))
        if keyword in combined:
            continue
        normalized_score = (float(item.get("score", 0)) / maximum_tfidf * 0.89) if maximum_tfidf > 0 else 0
        combined[keyword] = {"keyword": keyword, "score": round(float(normalized_score), 4), "method": "tfidf"}
    ranked_keywords = sorted(combined.values(), key=lambda item: item["score"], reverse=True)
    return remove_redundant_keywords(ranked_keywords, top_n=top_n)


def _looks_like_generic_heading(
    line: str,
    cleaned_line: str,
) -> bool:
    """Detect a likely scientific section heading without hard-coded titles."""

    # Markdown headings are strong structural evidence.
    if re.match(r"^#{1,6}\s+", cleaned_line):
        return True

    # Detect numbered headings such as:
    # 1 Introduction
    # 2. Methodology
    # 3 Design and Architecture
    # 4.1 AI Models
    # 5.3 Benchmarking Methodology
    numbered_match = re.match(
        r"^\s*\d+(?:\.\d+)*[\.\)\s\-:]+(.+?)\s*$",
        cleaned_line,
    )

    if not numbered_match:
        return False

    title = numbered_match.group(1).strip()

    if not title:
        return False

    # Headings should be reasonably short.
    words = title.split()

    if len(words) > 12:
        return False

    # Avoid treating normal sentences as headings.
    if len(words) < 1:
        return False

    # Normal sentences / bibliography entries usually contain
    # strong sentence punctuation.
    if re.search(r"[.!?;]$", title):
        return False

    # Commas are uncommon in scientific section titles.
    if "," in title:
        return False

    # A numbered heading should generally look like a title:
    # "Design and Architecture"
    # "PDF Conversion Pipeline"
    # "AI Models"
    #
    # We accept:
    # - Title Case
    # - ALL CAPS
    # - short technical headings containing uppercase terms
    alpha_chars = [
        char
        for char in title
        if char.isalpha()
    ]

    if not alpha_chars:
        return False

    uppercase_ratio = sum(
        1
        for char in alpha_chars
        if char.isupper()
    ) / len(alpha_chars)

    # Accept conventional title-like capitalization.
    if uppercase_ratio >= 0.15:
        return True

    # Also accept very short headings such as:
    # "3 Results"
    # "4 Discussion"
    # "5 Conclusion"
    if len(words) <= 4:
        return True

    return False


def split_text_into_sections(text: str) -> Dict[str, str]:
    """Split a cleaned scientific document into semantic sections.

    Section detection is generic and does not depend exclusively on a
    predefined list of scientific section names.

    Supported structural signals include:
    - Markdown headings (#, ##, ###, ...)
    - Numbered scientific headings (1 Introduction, 2.1 Methods, ...)
    - Known scientific section titles from SECTION_TITLES

    Content before the first recognized scientific section is ignored
    because it commonly contains metadata, affiliations, correspondence,
    or other non-scientific information.
    """

    sections: Dict[str, str] = {}

    current_section: str | None = None
    current_content: List[str] = []

    for line in text.splitlines():
        cleaned_line = line.strip()

        # Preserve blank lines only after a section has started.
        if not cleaned_line:
            if current_section is not None:
                current_content.append("")
            continue

        # Remove Markdown heading markers.
        possible_title = re.sub(
            r"^#{1,6}\s*",
            "",
            cleaned_line,
        )

        # Remove scientific section numbering.
        possible_title = re.sub(
            r"^\s*\d+(?:\.\d+)*[\.\)\s\-:]*",
            "",
            possible_title,
        )

        # Normalize whitespace.
        possible_title = re.sub(
            r"\s+",
            " ",
            possible_title,
        ).strip()

        normalized_title = possible_title.lower()

        is_short_line = len(cleaned_line) <= 100

        # ---------------------------------------------------------
        # 1. Known scientific title
        # ---------------------------------------------------------
        recognized_title = any(
            normalized_title == title
            or normalized_title.startswith(title + " ")
            for title in SECTION_TITLES
        )

        # ---------------------------------------------------------
        # 2. Generic structural heading
        # ---------------------------------------------------------
        generic_heading = _looks_like_generic_heading(
            line,
            cleaned_line,
        )

        # A section heading must be short.
        is_heading = (
            is_short_line
            and (
                recognized_title
                or generic_heading
            )
        )

        if is_heading:
            # Save previous section.
            if current_section is not None:
                previous_text = "\n".join(
                    current_content
                ).strip()

                if len(previous_text) >= 100:
                    sections[current_section] = previous_text

            # Use normalized title as the section name.
            current_section = normalized_title
            current_content = []

        elif current_section is not None:
            current_content.append(line)

    # -------------------------------------------------------------
    # Save final section
    # -------------------------------------------------------------
    if current_section is not None:
        final_text = "\n".join(
            current_content
        ).strip()

        if len(final_text) >= 100:
            sections[current_section] = final_text

    # -------------------------------------------------------------
    # Safety fallback
    # -------------------------------------------------------------
    if not sections:
        sections = {
            "document": text,
        }

    return sections


def extract_article_keywords(cleaned_text: str, language: str = "en", top_n: int = 15, keywords_per_section: int = 5) -> Dict[str, object]:
    """Main keyword extraction function matching the notebook's return structure."""
    provided_keywords = extract_provided_keywords(cleaned_text)
    tfidf_keywords = generate_tfidf_keywords(text=cleaned_text, language=language, top_n=top_n)
    global_keywords = combine_keyword_sources(provided_keywords=provided_keywords, tfidf_keywords=tfidf_keywords, language=language, top_n=top_n)
    sections = split_text_into_sections(cleaned_text)
    section_keywords = {}
    for section_name, section_text in sections.items():
        if section_name in {"references", "références"}:
            continue
        generated = generate_tfidf_keywords(text=section_text, language=language, top_n=keywords_per_section)
        generated = remove_redundant_keywords(generated, top_n=keywords_per_section)
        maximum_score = max([item.get("score", 0) for item in generated], default=0)
        normalized_results = []
        for item in generated:
            normalized_score = (float(item.get("score", 0)) / maximum_score if maximum_score > 0 else 0)
            normalized_results.append({"keyword": item.get("keyword"), "score": round(float(normalized_score), 4), "method": "tfidf"})
        if normalized_results:
            section_keywords[section_name] = normalized_results
    return {
        "provided_keywords": provided_keywords,
        "global_keywords": global_keywords,
        "keywords_by_section": section_keywords,
        "configuration": {
            "global_keyword_limit": top_n,
            "keywords_per_section": keywords_per_section,
            "ngram_range": [1, 3],
            "generic_term_filtering": True,
        },
        "status": "keywords_generated" if global_keywords else "no_keywords_generated",
    }
