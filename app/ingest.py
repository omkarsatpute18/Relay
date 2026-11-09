
import json
import re
from pathlib import Path

import fitz
import tiktoken


# Project directories
ROOT_DIR = Path(__file__).resolve().parent.parent
PAPERS_DIR = ROOT_DIR / "papers"
RESULTS_DIR = ROOT_DIR / "results"

OUTPUT_FILE = RESULTS_DIR / "paper_chunks.json"

# Consistent approximate tokenization for chunking
ENCODING = tiktoken.get_encoding("cl100k_base")

# Exact required paper versions
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


def clean_text(text):
    """Remove unnecessary whitespace from extracted PDF text."""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def create_chunks(text, chunk_size=500, overlap=75):
    """
    Divide text into token-based chunks.

    chunk_size: Maximum approximate tokens per chunk.
    overlap: Approximate tokens shared between chunks.
    """

    tokens = ENCODING.encode(text)

    chunks = []
    start = 0

    while start < len(tokens):

        end = min(start + chunk_size, len(tokens))

        chunk_tokens = tokens[start:end]
        chunk_text = ENCODING.decode(chunk_tokens)

        if chunk_text.strip():
            chunks.append(chunk_text.strip())

        if end == len(tokens):
            break

        start = end - overlap

    return chunks


def extract_papers(chunk_size=500, overlap=75):

    all_chunks = []
    chunk_id = 0

    for paper in PAPERS:

        pdf_path = PAPERS_DIR / paper["filename"]

        if not pdf_path.exists():
            raise FileNotFoundError(
                f"Missing PDF: {pdf_path}"
            )

        print(f"\nProcessing: {paper['title']}")

        document = fitz.open(pdf_path)

        for page_index, page in enumerate(document):

            page_text = clean_text(page.get_text("text"))

            if not page_text:
                print(
                    f"Skipping empty PDF page {page_index + 1}"
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
                    "text": chunk,
                    "approx_tokens": len(
                        ENCODING.encode(chunk)
                    )
                })

                chunk_id += 1

        document.close()

    return all_chunks


def main():

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    chunks = extract_papers()

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

    print("\n" + "=" * 50)
    print("PAPER INGESTION COMPLETED")
    print("=" * 50)

    print("Total chunks:", len(chunks))
    print("Output file:", OUTPUT_FILE)

    for paper in PAPERS:

        count = sum(
            1 for chunk in chunks
            if chunk["paper_id"] == paper["paper_id"]
        )

        print(f"{paper['title']}: {count} chunks")


if __name__ == "__main__":
    main()
