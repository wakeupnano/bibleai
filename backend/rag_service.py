"""
RAG Service — Retrieval-Augmented Generation for Bible AI Assistant

Handles:
- Vector similarity search against ChromaDB
- Context expansion (surrounding verses for narrative context)
- ESV API real-time fetch ("KJV Search, ESV Fetch" architecture)
- Cross-lingual retrieval (Korean query -> English results and vice versa)

Architecture Note — ESV Compliance:
  We NEVER store ESV text in ChromaDB (violates Crossway ToS).
  Instead we use "KJV Search, ESV Fetch":
    1. Search: KJV vectors find relevant verses
    2. Fetch: ESV API retrieves modern text in real-time
    3. Swap: ESV text replaces KJV in LLM context
"""

import os
import httpx
import chromadb
from sentence_transformers import SentenceTransformer
from typing import Optional


# ------------------------------------------------------------------
# ESV API Configuration
# ------------------------------------------------------------------
ESV_API_URL = "https://api.esv.org/v3/passage/text/"
ESV_API_KEY = os.getenv("ESV_API_KEY")  # Get free key at api.esv.org

# ESV Copyright Notice (REQUIRED by Crossway when displaying ESV text)
ESV_COPYRIGHT = (
    'Scripture quotations are from the ESV Bible (The Holy Bible, English '
    'Standard Version), copyright 2001 by Crossway, a publishing ministry of Good '
    'News Publishers. ESV Text Edition: 2025. Used by permission. All rights reserved.'
)


# ------------------------------------------------------------------
# Book Name Mappings (for reference detection)
# ------------------------------------------------------------------
BOOK_NAMES_KR = {
    "Genesis": "창세기", "Exodus": "출애굽기", "Leviticus": "레위기",
    "Numbers": "민수기", "Deuteronomy": "신명기", "Joshua": "여호수아",
    "Judges": "사사기", "Ruth": "룻기", "1 Samuel": "사무엘상",
    "2 Samuel": "사무엘하", "1 Kings": "열왕기상", "2 Kings": "열왕기하",
    "1 Chronicles": "역대상", "2 Chronicles": "역대하", "Ezra": "에스라",
    "Nehemiah": "느헤미야", "Esther": "에스더", "Job": "욥기",
    "Psalms": "시편", "Proverbs": "잠언", "Ecclesiastes": "전도서",
    "Song of Solomon": "아가", "Isaiah": "이사야", "Jeremiah": "예레미야",
    "Lamentations": "예레미야애가", "Ezekiel": "에스겔", "Daniel": "다니엘",
    "Hosea": "호세아", "Joel": "요엘", "Amos": "아모스",
    "Obadiah": "오바댜", "Jonah": "요나", "Micah": "미가",
    "Nahum": "나훔", "Habakkuk": "하박국", "Zephaniah": "스바냐",
    "Haggai": "학개", "Zechariah": "스가랴", "Malachi": "말라기",
    "Matthew": "마태복음", "Mark": "마가복음", "Luke": "누가복음",
    "John": "요한복음", "Acts": "사도행전", "Romans": "로마서",
    "1 Corinthians": "고린도전서", "2 Corinthians": "고린도후서",
    "Galatians": "갈라디아서", "Ephesians": "에베소서",
    "Philippians": "빌립보서", "Colossians": "골로새서",
    "1 Thessalonians": "데살로니가전서", "2 Thessalonians": "데살로니가후서",
    "1 Timothy": "디모데전서", "2 Timothy": "디모데후서",
    "Titus": "디도서", "Philemon": "빌레몬서", "Hebrews": "히브리서",
    "James": "야고보서", "1 Peter": "베드로전서", "2 Peter": "베드로후서",
    "1 John": "요한일서", "2 John": "요한이서", "3 John": "요한삼서",
    "Jude": "유다서", "Revelation": "요한계시록",
}


class BibleRAGService:
    """Manages retrieval of Bible verses from ChromaDB with context expansion."""

    def __init__(
        self,
        chroma_dir: str = "./chroma_db",
        collection_name: str = "bible_verses",
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ):
        self.model = SentenceTransformer(embedding_model)
        self.client = chromadb.PersistentClient(path=chroma_dir)
        self.collection = self.client.get_collection(name=collection_name)
        self._http_client = httpx.Client(timeout=10.0)
        print(f"RAG Service initialized. Collection has {self.collection.count()} documents.")
        if ESV_API_KEY:
            print("ESV API key detected - real-time ESV fetch enabled.")
        else:
            print("No ESV API key - English will use KJV only.")

    # ------------------------------------------------------------------
    # Reference Detection - Exact Lookup for Specific Verse Requests
    # ------------------------------------------------------------------
    def detect_and_lookup_reference(
        self,
        query: str,
        translation_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Detect if the query mentions a specific Bible reference (e.g.,
        "Romans 8:28", "로마서 8:28", "John 3:16") and do an exact
        metadata lookup instead of relying on vector similarity.

        Vector search is bad at this because "로마서 8:28의 의미" gets
        poorly embedded by English-optimized models, and the cosine
        similarity matches on superficial patterns (chapter numbers)
        rather than the actual book name.

        Returns matching verses if a reference was found, empty list otherwise.
        """
        import re

        # Pattern 1: English references like "Romans 8:28", "1 John 3:16"
        en_pattern = re.compile(
            r'(\d?\s?[A-Z][a-z]+(?:\s+of\s+[A-Z][a-z]+)?)\s+(\d+):(\d+)',
            re.IGNORECASE,
        )

        # Pattern 2: Korean references like "로마서 8:28", "요한복음 3:16"
        kr_pattern = re.compile(
            r'([가-힣]+)\s*(\d+):(\d+)'
        )

        # Build reverse Korean-to-English book name map
        kr_to_en = {v: k for k, v in BOOK_NAMES_KR.items()}

        matches = []

        # Try English pattern
        for m in en_pattern.finditer(query):
            raw_book = m.group(1).strip()
            chapter = int(m.group(2))
            verse = int(m.group(3))

            # Normalize book name (handle case variations)
            book = None
            for canonical in BOOK_NAMES_KR.keys():
                if canonical.lower() == raw_book.lower():
                    book = canonical
                    break
            if book:
                matches.append((book, chapter, verse))

        # Try Korean pattern
        for m in kr_pattern.finditer(query):
            raw_book_kr = m.group(1).strip()
            chapter = int(m.group(2))
            verse = int(m.group(3))

            book = kr_to_en.get(raw_book_kr)
            if book:
                matches.append((book, chapter, verse))

        if not matches:
            return []

        # Do exact metadata lookup for each detected reference
        found_verses = []
        for book, chapter, verse in matches:
            where_conditions = [
                {"book": {"$eq": book}},
                {"chapter": {"$eq": chapter}},
                {"verse": {"$eq": verse}},
            ]
            if translation_filter:
                where_conditions.append({"translation": {"$eq": translation_filter}})

            results = self.collection.get(
                where={"$and": where_conditions},
                include=["metadatas"],
            )

            if results and results["metadatas"]:
                for metadata in results["metadatas"]:
                    found_verses.append({
                        "text": metadata["text"],
                        "reference": metadata["reference"],
                        "reference_kr": metadata["reference_kr"],
                        "translation": metadata["translation"],
                        "book": metadata["book"],
                        "book_kr": metadata.get("book_kr", metadata["book"]),
                        "chapter": metadata["chapter"],
                        "verse": metadata["verse"],
                        "similarity": 1.0,  # Exact match = perfect relevance
                    })

        return found_verses

    # ------------------------------------------------------------------
    # Core Search (Hybrid: Exact Reference + Vector Similarity)
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        n_results: int = 8,
        translation_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Hybrid search: tries exact reference lookup first, then vector similarity.

        If the user says "로마서 8:28" or "Romans 8:28", we detect the reference
        and do a direct metadata lookup (guaranteed correct). Then we also run
        vector similarity to find thematically related verses. Results are merged
        with exact matches ranked highest (similarity=1.0).

        This fixes the problem where vector search confuses "Romans 8:28" with
        "John 8:32" because the embedding model latches onto the chapter number.
        """
        # Step 1: Try exact reference detection
        exact_matches = self.detect_and_lookup_reference(query, translation_filter)
        exact_refs = {v["reference"] for v in exact_matches}

        # Step 2: Vector similarity search
        where_filter = None
        if translation_filter:
            where_filter = {"translation": translation_filter}

        query_embedding = self.model.encode(query).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["metadatas", "distances", "documents"],
        )

        vector_verses = []
        if results and results["metadatas"]:
            for i, metadata in enumerate(results["metadatas"][0]):
                distance = results["distances"][0][i] if results["distances"] else None
                similarity = 1 - (distance / 2) if distance is not None else 0

                # Skip duplicates already found by exact match
                if metadata["reference"] in exact_refs:
                    continue

                vector_verses.append({
                    "text": metadata["text"],
                    "reference": metadata["reference"],
                    "reference_kr": metadata["reference_kr"],
                    "translation": metadata["translation"],
                    "book": metadata["book"],
                    "book_kr": metadata["book_kr"],
                    "chapter": metadata["chapter"],
                    "verse": metadata["verse"],
                    "similarity": round(similarity, 4),
                })

        # Step 3: Merge — exact matches first (similarity=1.0), then vector results
        merged = exact_matches + vector_verses
        merged.sort(key=lambda x: x["similarity"], reverse=True)
        return merged

    # ------------------------------------------------------------------
    # Context Expansion - Fetch Surrounding Verses
    # ------------------------------------------------------------------
    def get_surrounding_verses(
        self,
        book: str,
        chapter: int,
        verse: int,
        translation: str,
        window: int = 2,
    ) -> list[dict]:
        """
        Fetch neighboring verses for narrative context.

        Example: If John 3:16 is retrieved, this returns John 3:14-18 so the
        LLM can explain the full context (Nicodemus, the serpent in the wilderness).
        """
        start_v = max(1, verse - window)
        end_v = verse + window

        results = self.collection.get(
            where={
                "$and": [
                    {"book": {"$eq": book}},
                    {"chapter": {"$eq": chapter}},
                    {"verse": {"$gte": start_v}},
                    {"verse": {"$lte": end_v}},
                    {"translation": {"$eq": translation}},
                ]
            },
            include=["metadatas"],
        )

        verses = []
        if results and results["metadatas"]:
            for metadata in results["metadatas"]:
                verses.append({
                    "text": metadata["text"],
                    "reference": metadata["reference"],
                    "reference_kr": metadata["reference_kr"],
                    "translation": metadata["translation"],
                    "book": metadata["book"],
                    "book_kr": metadata.get("book_kr", metadata["book"]),
                    "chapter": metadata["chapter"],
                    "verse": metadata["verse"],
                })

        verses.sort(key=lambda v: v["verse"])
        return verses

    # ------------------------------------------------------------------
    # ESV API - Real-Time Fetch ("KJV Search, ESV Fetch")
    # ------------------------------------------------------------------
    def fetch_esv_passage(self, reference: str) -> Optional[str]:
        """
        Fetch passage from ESV API in real-time.
        We NEVER store ESV text in our database (violates Crossway ToS).
        """
        if not ESV_API_KEY:
            return None

        try:
            response = self._http_client.get(
                ESV_API_URL,
                headers={"Authorization": f"Token {ESV_API_KEY}"},
                params={
                    "q": reference,
                    "include-headings": "false",
                    "include-footnotes": "false",
                    "include-verse-numbers": "true",
                    "include-short-copyright": "false",
                    "include-passage-references": "false",
                    "indent-paragraphs": "0",
                },
            )
            response.raise_for_status()
            data = response.json()

            passages = data.get("passages", [])
            return passages[0].strip() if passages else None

        except Exception as e:
            print(f"ESV API error for '{reference}': {e}")
            return None

    def _build_reference_str(self, book: str, chapter: int, start_v: int, end_v: int) -> str:
        """Build 'John 3:14-18' style reference string."""
        if start_v == end_v:
            return f"{book} {chapter}:{start_v}"
        return f"{book} {chapter}:{start_v}-{end_v}"

    # ------------------------------------------------------------------
    # Build Context - The Main Pipeline
    # ------------------------------------------------------------------
    def build_context(
        self,
        initial_verses: list[dict],
        similarity_threshold: float = 0.3,
        expand_top_n: int = 2,
        context_window: int = 2,
        prefer_esv: bool = False,
    ) -> tuple[str, list[dict]]:
        """
        Build formatted context with expansion and optional ESV fetch.

        Accepts pre-fetched verses from search() to avoid redundant vector queries.

        Pipeline:
        1. Filter by similarity threshold
        2. Expand top N results with surrounding verses (+/- context_window)
        3. Optionally fetch ESV via API for English passages
        4. Sort by Bible order for LLM readability

        Args:
            initial_verses: Pre-fetched results from search() (sorted by similarity)
            similarity_threshold: Minimum similarity to include
            expand_top_n: How many top results to expand with neighbors
            context_window: Verses before/after to fetch for expansion
            prefer_esv: If True and ESV API key exists, fetch ESV for English

        Returns:
            (formatted_context_string, relevant_source_verses)
        """
        relevant_verses = [v for v in initial_verses if v["similarity"] >= similarity_threshold]

        if not relevant_verses:
            return (
                "No direct Bible text found via search. The user may be asking a "
                "general conversational question, requesting a QT recommendation, "
                "or discussing something not tied to a specific verse. Use your "
                "general biblical knowledge to guide them. You may suggest specific "
                "books or passages commonly relevant to their topic.",
                [],
            )

        # Step 2: Context Expansion
        expanded_context = []
        processed_refs = set()
        direct_match_refs = {v["reference"] for v in relevant_verses}

        # Expand top N results with surrounding verses
        for v in relevant_verses[:expand_top_n]:
            neighbors = self.get_surrounding_verses(
                book=v["book"],
                chapter=v["chapter"],
                verse=v["verse"],
                translation=v["translation"],
                window=context_window,
            )
            for n in neighbors:
                if n["reference"] not in processed_refs:
                    expanded_context.append(n)
                    processed_refs.add(n["reference"])

        # Add remaining results not already expanded
        for v in relevant_verses[expand_top_n:]:
            if v["reference"] not in processed_refs:
                expanded_context.append(v)
                processed_refs.add(v["reference"])

        # Sort by book/chapter/verse for readability
        expanded_context.sort(key=lambda x: (x["book"], x["chapter"], x["verse"]))

        # Step 3: Optional ESV Fetch
        esv_passages = {}
        if prefer_esv and ESV_API_KEY:
            chapter_groups: dict[tuple, list[int]] = {}
            for v in expanded_context:
                if v["translation"] == "KJV":
                    key = (v["book"], v["chapter"])
                    if key not in chapter_groups:
                        chapter_groups[key] = []
                    chapter_groups[key].append(v["verse"])

            for (book, chapter), verse_nums in chapter_groups.items():
                min_v, max_v = min(verse_nums), max(verse_nums)
                ref = self._build_reference_str(book, chapter, min_v, max_v)
                esv_text = self.fetch_esv_passage(ref)
                if esv_text:
                    esv_passages[(book, chapter, min_v, max_v)] = esv_text

        # Step 4: Format context string
        context_lines = [
            "=== RETRIEVED BIBLE PASSAGES (with surrounding context) ===",
            "",
        ]

        current_group = None
        for v in expanded_context:
            group_key = (v["book"], v["chapter"], v["translation"])

            if group_key != current_group:
                if current_group is not None:
                    context_lines.append("")
                current_group = group_key
                book_kr = v.get("book_kr", v["book"])
                context_lines.append(
                    f"--- {v['book']} {v['chapter']} / {book_kr} {v['chapter']}장 "
                    f"({v['translation']}) ---"
                )

            marker = "★" if v["reference"] in direct_match_refs else "·"
            context_lines.append(
                f"  {marker} v{v['verse']}: \"{v['text']}\""
                f"  [{v['reference']} / {v['reference_kr']}]"
            )

        # Append ESV passages if fetched (sorted by Bible order)
        if esv_passages:
            context_lines.append("")
            context_lines.append("--- ESV Translation (fetched via API for English display) ---")
            sorted_esv_keys = sorted(esv_passages.keys(), key=lambda x: (x[0], x[1], x[2]))
            for key in sorted_esv_keys:
                book, chapter, min_v, max_v = key
                text = esv_passages[key]
                ref = self._build_reference_str(book, chapter, min_v, max_v)
                context_lines.append(f"  {ref} (ESV):")
                context_lines.append(f"  \"{text}\"")
                context_lines.append("")
            context_lines.append(f"  [ESV Copyright: {ESV_COPYRIGHT}]")

        context_lines.extend([
            "",
            "=== END OF RETRIEVED PASSAGES ===",
            "",
            "INSTRUCTIONS:",
            "- Use the passages above to ground your response.",
            "- ★ = directly relevant verses; · = surrounding context for narrative understanding.",
            "- Cite using format: [Bible, Reference, Translation]",
            "- If ESV text is provided and the user speaks English, prefer quoting ESV.",
            "- If quoting ESV, include the copyright notice at the end of your response.",
            "- Use surrounding context to explain the passage's meaning, not just the single verse.",
            "- If no passage is relevant to the user's actual question, say so honestly.",
        ])

        return "\n".join(context_lines), relevant_verses

    # ------------------------------------------------------------------
    # Get Full Chapter (for QT reading)
    # ------------------------------------------------------------------
    def get_chapter(
        self,
        book: str,
        chapter: int,
        translation: str = "KJV",
    ) -> list[dict]:
        """Retrieve all verses from a specific chapter for QT reading."""
        results = self.collection.get(
            where={
                "$and": [
                    {"book": {"$eq": book}},
                    {"chapter": {"$eq": chapter}},
                    {"translation": {"$eq": translation}},
                ]
            },
            include=["metadatas"],
        )

        verses = []
        if results and results["metadatas"]:
            for metadata in results["metadatas"]:
                verses.append({
                    "text": metadata["text"],
                    "reference": metadata["reference"],
                    "reference_kr": metadata["reference_kr"],
                    "translation": metadata["translation"],
                    "book": metadata.get("book", book),
                    "book_kr": metadata.get("book_kr", book),
                    "chapter": metadata["chapter"],
                    "verse": metadata["verse"],
                })
            verses.sort(key=lambda v: v["verse"])

        return verses
