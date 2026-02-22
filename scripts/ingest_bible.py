"""
Bible Data Ingestion Script

Downloads public domain KJV (English) and attempts to fetch KRV (Korean)
automatically. Falls back to manual instructions if the Korean source
is unavailable.

Outputs a ChromaDB vector store with verse-level embeddings for RAG retrieval.

Usage:
    python ingest_bible.py
"""

import json
import os
import requests
import chromadb
from sentence_transformers import SentenceTransformer

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "../backend/chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
BIBLE_DATA_DIR = "../data"

# English-to-Korean book name mapping (standard Protestant canon, 66 books)
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

# Reverse mapping for parsing Korean-named source files
KR_TO_EN = {v: k for k, v in BOOK_NAMES_KR.items()}

# Known public sources for Korean Bible JSON (tried in order)
KRV_SOURCES = [
    "https://raw.githubusercontent.com/pjcone/bible-kr/master/krv.json",
    "https://raw.githubusercontent.com/thiagobodruk/bible/master/json/ko_krv.json",
    "https://raw.githubusercontent.com/antioch-church/bible-json/main/krv.json",
]


# ------------------------------------------------------------------
# Download Functions
# ------------------------------------------------------------------
def download_kjv():
    """Download the King James Version from a public domain JSON source."""
    kjv_path = os.path.join(BIBLE_DATA_DIR, "kjv.json")
    if os.path.exists(kjv_path):
        print("[OK] KJV data already cached locally.")
        with open(kjv_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print("[DOWNLOAD] Fetching KJV Bible data...")
    url = "https://raw.githubusercontent.com/thiagobodruk/bible/master/json/en_kjv.json"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    os.makedirs(BIBLE_DATA_DIR, exist_ok=True)
    with open(kjv_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] KJV saved to {kjv_path}")
    return data


def download_krv():
    """
    Attempt to download KRV (Korean Revised Version, 1961) from known
    public sources. Tries multiple URLs in order. If all fail, prints
    manual instructions.

    The KRV (1961) is public domain in Korea.
    """
    krv_path = os.path.join(BIBLE_DATA_DIR, "krv.json")
    if os.path.exists(krv_path):
        print("[OK] KRV data already cached locally.")
        with open(krv_path, "r", encoding="utf-8") as f:
            return json.load(f)

    os.makedirs(BIBLE_DATA_DIR, exist_ok=True)

    # Try each known source
    for url in KRV_SOURCES:
        print(f"[DOWNLOAD] Trying: {url}")
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                # Quick validation: should be a list of books with chapters
                if isinstance(data, list) and len(data) > 0:
                    first = data[0]
                    if "chapters" in first or "chapter" in first:
                        with open(krv_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False)
                        print(f"[OK] KRV downloaded and saved to {krv_path}")
                        return data
                print(f"[SKIP] Response from {url} didn't match expected structure.")
        except Exception as e:
            print(f"[SKIP] Failed: {e}")

    # All sources failed
    print()
    print("=" * 60)
    print("  COULD NOT AUTO-DOWNLOAD KRV (Korean Bible)")
    print("=" * 60)
    print()
    print("  The auto-fetch URLs may be down. To add Korean data manually:")
    print()
    print("  1. Search GitHub for 'Korean Bible JSON' or 'bible-kr json'")
    print("  2. Download a JSON file structured as:")
    print('     [{"name": "창세기", "chapters": [["태초에...", ...], ...]}, ...]')
    print(f"  3. Save it as: {os.path.abspath(krv_path)}")
    print("  4. Re-run this script.")
    print()
    print("  Continuing with KJV (English) only for now.")
    print("=" * 60)
    print()
    return None


# ------------------------------------------------------------------
# Parsing Functions
# ------------------------------------------------------------------
def parse_kjv_to_verses(kjv_data):
    """Flatten KJV JSON into a list of verse documents for ChromaDB."""
    verses = []
    for book in kjv_data:
        book_name = book.get("name", "Unknown")
        book_name_kr = BOOK_NAMES_KR.get(book_name, book_name)
        chapters = book.get("chapters", [])

        for ch_idx, chapter in enumerate(chapters):
            chapter_num = ch_idx + 1
            for v_idx, verse_text in enumerate(chapter):
                verse_num = v_idx + 1
                ref = f"{book_name} {chapter_num}:{verse_num}"
                ref_kr = f"{book_name_kr} {chapter_num}:{verse_num}"

                verses.append({
                    "id": f"kjv_{book_name}_{chapter_num}_{verse_num}",
                    "text": verse_text.strip(),
                    "translation": "KJV",
                    "book": book_name,
                    "book_kr": book_name_kr,
                    "chapter": chapter_num,
                    "verse": verse_num,
                    "reference": ref,
                    "reference_kr": ref_kr,
                    "search_text": f"{book_name} {book_name_kr} {chapter_num}:{verse_num} {verse_text.strip()}",
                })
    return verses


def parse_krv_to_verses(krv_data):
    """Flatten KRV JSON into a list of verse documents for ChromaDB.

    Handles two formats:
    1. Flat dictionary with abbreviations: {"창1:14": "하나님이...", ...}
    2. List-of-books with chapters: [{"name": "창세기", "chapters": [...]}, ...]
    """
    import re
    verses = []

    # Korean abbreviation to English book name mapping
    KR_ABBREV = {
        "창": "Genesis", "출": "Exodus", "레": "Leviticus", "민": "Numbers",
        "신": "Deuteronomy", "수": "Joshua", "삿": "Judges", "룻": "Ruth",
        "삼상": "1 Samuel", "삼하": "2 Samuel", "왕상": "1 Kings", "왕하": "2 Kings",
        "대상": "1 Chronicles", "대하": "2 Chronicles", "스": "Ezra",
        "느": "Nehemiah", "에": "Esther", "욥": "Job", "시": "Psalms",
        "잠": "Proverbs", "전": "Ecclesiastes", "아": "Song of Solomon",
        "사": "Isaiah", "렘": "Jeremiah", "애": "Lamentations", "겔": "Ezekiel",
        "단": "Daniel", "호": "Hosea", "욜": "Joel", "암": "Amos", "옵": "Obadiah",
        "욘": "Jonah", "미": "Micah", "나": "Nahum", "합": "Habakkuk",
        "습": "Zephaniah", "학": "Haggai", "슥": "Zechariah", "말": "Malachi",
        "마": "Matthew", "막": "Mark", "눅": "Luke", "요": "John", "행": "Acts",
        "롬": "Romans", "고전": "1 Corinthians", "고후": "2 Corinthians",
        "갈": "Galatians", "엡": "Ephesians", "빌": "Philippians", "골": "Colossians",
        "살전": "1 Thessalonians", "살후": "2 Thessalonians",
        "딤전": "1 Timothy", "딤후": "2 Timothy", "딛": "Titus", "몬": "Philemon",
        "히": "Hebrews", "약": "James", "벧전": "1 Peter", "벧후": "2 Peter",
        "요일": "1 John", "요이": "2 John", "요삼": "3 John", "유": "Jude",
        "계": "Revelation",
    }

    # Format 1: Flat dictionary with abbreviations (e.g., {"창1:14": "..."})
    if isinstance(krv_data, dict):
        for key, text in krv_data.items():
            match = re.match(r"([가-힣]+)\s*(\d+):(\d+)", key)
            if not match:
                continue

            abbrev, chapter_str, verse_str = match.groups()
            chapter_num = int(chapter_str)
            verse_num = int(verse_str)

            book_name_en = KR_ABBREV.get(abbrev, "Unknown")
            book_name_kr = BOOK_NAMES_KR.get(book_name_en, abbrev)

            ref = f"{book_name_en} {chapter_num}:{verse_num}"
            ref_kr = f"{book_name_kr} {chapter_num}:{verse_num}"

            verses.append({
                "id": f"krv_{book_name_en}_{chapter_num}_{verse_num}",
                "text": text.strip(),
                "translation": "개역한글",
                "book": book_name_en,
                "book_kr": book_name_kr,
                "chapter": chapter_num,
                "verse": verse_num,
                "reference": ref,
                "reference_kr": ref_kr,
                "search_text": f"{book_name_en} {book_name_kr} {chapter_num}:{verse_num} {text.strip()}",
            })
        return verses

    # Format 2: List-of-books with chapters (fallback for older JSON sources)
    for book in krv_data:
        raw_name = book.get("name", "Unknown")

        if raw_name in BOOK_NAMES_KR:
            book_name_en = raw_name
            book_name_kr = BOOK_NAMES_KR[raw_name]
        elif raw_name in KR_TO_EN:
            book_name_kr = raw_name
            book_name_en = KR_TO_EN[raw_name]
        else:
            book_name_en = raw_name
            book_name_kr = raw_name

        chapters = book.get("chapters", [])
        for ch_idx, chapter in enumerate(chapters):
            chapter_num = ch_idx + 1
            for v_idx, verse_text in enumerate(chapter):
                verse_num = v_idx + 1
                ref = f"{book_name_en} {chapter_num}:{verse_num}"
                ref_kr = f"{book_name_kr} {chapter_num}:{verse_num}"

                verses.append({
                    "id": f"krv_{book_name_en}_{chapter_num}_{verse_num}",
                    "text": verse_text.strip(),
                    "translation": "개역한글",
                    "book": book_name_en,
                    "book_kr": book_name_kr,
                    "chapter": chapter_num,
                    "verse": verse_num,
                    "reference": ref,
                    "reference_kr": ref_kr,
                    "search_text": f"{book_name_en} {book_name_kr} {chapter_num}:{verse_num} {verse_text.strip()}",
                })
    return verses


# ------------------------------------------------------------------
# ChromaDB Ingestion
# ------------------------------------------------------------------
def ingest_to_chroma(verses, collection_name="bible_verses"):
    """Embed all verses and write them into a persistent ChromaDB collection."""
    print(f"\n[MODEL] Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    print(f"[DB] Initializing ChromaDB at: {CHROMA_PERSIST_DIR}")
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    # Drop and recreate to ensure clean state on re-runs
    try:
        client.delete_collection(collection_name)
        print(f"[DB] Dropped existing collection: {collection_name}")
    except Exception:
        pass

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 500
    total = len(verses)
    print(f"\n[INGEST] Writing {total} verses into ChromaDB...\n")

    for i in range(0, total, batch_size):
        batch = verses[i : i + batch_size]

        ids = [v["id"] for v in batch]
        documents = [v["search_text"] for v in batch]
        metadatas = [
            {
                "text": v["text"],
                "translation": v["translation"],
                "book": v["book"],
                "book_kr": v["book_kr"],
                "chapter": v["chapter"],
                "verse": v["verse"],
                "reference": v["reference"],
                "reference_kr": v["reference_kr"],
            }
            for v in batch
        ]
        embeddings = model.encode(documents).tolist()

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        progress = min(i + batch_size, total)
        pct = progress / total * 100
        print(f"  {progress}/{total} ({pct:.0f}%)")

    print(f"\n[DONE] {total} verses ingested into '{collection_name}'")
    print(f"       ChromaDB path: {os.path.abspath(CHROMA_PERSIST_DIR)}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  Bible Data Ingestion - Phase 1")
    print("=" * 60)

    all_verses = []

    # KJV (English)
    kjv_data = download_kjv()
    kjv_verses = parse_kjv_to_verses(kjv_data)
    print(f"[PARSE] {len(kjv_verses)} KJV verses")
    all_verses.extend(kjv_verses)

    # KRV (Korean)
    krv_data = download_krv()
    if krv_data:
        krv_verses = parse_krv_to_verses(krv_data)
        print(f"[PARSE] {len(krv_verses)} KRV verses")
        all_verses.extend(krv_verses)

    if not all_verses:
        print("[ERROR] No verses to ingest. Check your data sources.")
        return

    ingest_to_chroma(all_verses)

    print("\n" + "=" * 60)
    print("  Ingestion complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
