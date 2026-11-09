
import json
import re
from pathlib import Path

import pymupdf
import tiktoken


# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

ROOT_DIR = Path(__file__).resolve().parent.parent

PAPERS_DIR = ROOT_DIR / "papers"
RESULTS_DIR = ROOT_DIR / "results"

OUTPUT_FILE = RESULTS_DIR / "paper_chunks.json"

# Tokenizer used for consistent chunk sizing
ENCODING = tiktoken.get_encoding("cl100k_base")


# ==========================================
# 2. RESEARCH PAPER INFORMATION
# ==========================================

PAPERS = [
    {
        "filename": "attention_is_all_you_need.pdf",
        "paper_id": "1706.03762",
        "title": "Attention Is All You Need",
        "version": 7,
    },
    {
        "filename": "moshi.pdf",
        "paper_id": "2410.00037",
        "title": "Moshi: A Speech-Text Foundation Model for Real-Time Dialogue",
        "version": 1,
    },
    {
        "filename": "dynamic_chunking.pdf",
        "paper_id": "2507.07955",
        "title": "Dynamic Chunking for End-to-End Hierarchical Sequence Modeling",
        "version": 2,
    },
]


# ==========================================
# 3. TEXT CLEANING
# ==========================================

def clean_text(text):
    """
    Remove unnecessary whitespace from extracted PDF text.
    """

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ==========================================
# 4. TEXT CHUNKING
# ==========================================

def create_chunks(text, chunk_size=500, overlap=75):
    """
    Divide extracted text into token-based chunks.

    chunk_size: Maximum approximate tokens per chunk.
    overlap: Number of overlapping tokens.

    Special-token-looking strings in PDFs are
    treated as ordinary document text.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative "
            "and smaller than chunk_size."
        )

    tokens = ENCODING.encode(
        text,
        disallowed_special=()
    )

    chunks = []

    start = 0

    while start < len(tokens):

        end = min(
            start + chunk_size,
            len(tokens)
        )

        chunk_tokens = tokens[start:end]

        chunk_text = ENCODING.decode(
            chunk_tokens
        )

        if chunk_text.strip():

            chunks.append({
                "text": chunk_text.strip(),
                "approx_tokens": len(chunk_tokens)
            })

        if end == len(tokens):
            break

        start = end - overlap

    return chunks


# ==========================================
# 5. PDF EXTRACTION AND PROCESSING
# ==========================================

def extract_papers(chunk_size=500, overlap=75):
    """
    Extract text from all research papers.

    Preserve:
    - Paper ID
    - Paper title
    - Paper version
    - PDF page number
    - Chunk ID
    - Extracted text
    - Approximate token count
    """

    all_chunks = []

    chunk_id = 0

    for paper in PAPERS:

        pdf_path = PAPERS_DIR / paper["filename"]

        if not pdf_path.exists():

            raise FileNotFoundError(
                f"Missing research paper: {pdf_path}"
            )

        print(
            f"\nProcessing: {paper['title']}"
        )

        document = pymupdf.open(pdf_path)

        try:

            print(
                f"Total PDF pages: {len(document)}"
            )

            for page_index, page in enumerate(document):

                page_text = clean_text(
                    page.get_text("text")
                )

                # Skip pages without extractable text
                if not page_text:

                    print(
                        f"Skipping empty PDF page "
                        f"{page_index + 1}"
                    )

                    continue

                page_chunks = create_chunks(
                    page_text,
                    chunk_size=chunk_size,
                    overlap=overlap
                )

                for chunk in page_chunks:

                    all_chunks.append({

                        "chunk_id": chunk_id,

                        "paper_id": paper["paper_id"],

                        "title": paper["title"],

                        "version": paper["version"],

                        "pdf_page": page_index + 1,

                        "text": chunk["text"],

                        "approx_tokens": chunk["approx_tokens"]

                    })

                    chunk_id += 1

        finally:

            document.close()

    return all_chunks


# ==========================================
# 6. SAVE EXTRACTED CHUNKS
# ==========================================

def save_chunks(chunks):

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            chunks,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"\nChunks saved successfully: {OUTPUT_FILE}"
    )


# ==========================================
# 7. MAIN EXECUTION
# ==========================================

def main():

    print("=" * 55)
    print("THE RELAY - RESEARCH PAPER INGESTION")
    print("=" * 55)

    chunks = extract_papers(
        chunk_size=500,
        overlap=75
    )

    save_chunks(chunks)

    print("\n" + "=" * 55)
    print("PAPER INGESTION COMPLETED")
    print("=" * 55)

    print(
        f"\nTotal chunks generated: {len(chunks)}"
    )

    print("\nPaper-wise chunk summary:")

    for paper in PAPERS:

        count = sum(
            1
            for chunk in chunks
            if chunk["paper_id"] == paper["paper_id"]
        )

        print(
            f"{paper['title']}: {count} chunks"
        )

    print("\nOutput file:")

    print(OUTPUT_FILE)

    print("\nNext step: Run the retrieval tests.")


# ==========================================
# 8. PROGRAM ENTRY POINT
# ==========================================

if __name__ == "__main__":

    main()
