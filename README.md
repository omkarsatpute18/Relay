# The Relay — Research Assistant Pipeline

The Relay is a small research assistant pipeline built to study how an LLM-based research system behaves under different retrieval settings, service conditions and rate limits.

It retrieves information from three research papers, sends relevant passages to a hosted language model through Groq, and returns answers with source citations. The project also includes a controllable stand-in model service for testing latency, concurrency, failures, refusals, streaming and quota exhaustion.

## 1. Project objectives

The project explores four main areas:

- **Retrieval:** Extract and search research papers using BM25.
- **Generation:** Generate answers using a hosted Groq model and retrieved evidence.
- **Service behaviour:** Simulate latency, concurrency, failures, rate limits, refusals and streaming.
- **Evaluation:** Compare retrieval settings and measure latency, token usage, retries and service outcomes.

## 2. Research papers

The retrieval library contains these three arXiv papers and versions:

| Research paper | arXiv ID | Version |
|---|---|---|
| Attention Is All You Need | 1706.03762 | v7 |
| Moshi: A Speech-Text Foundation Model for Real-Time Dialogue | 2410.00037 | v1 |
| Dynamic Chunking for End-to-End Hierarchical Sequence Modeling | 2507.07955 | v2 |

The PDFs are stored in the `papers/` directory.

## 3. System architecture

The pipeline follows these stages:

1. **Query analysis:** Validates the question and prepares it for retrieval.
2. **Evidence retrieval:** Searches the research-paper chunks using BM25.
3. **Evidence decision:** Checks whether the retrieved evidence meets the configured relevance threshold.
4. **Answer generation:** Sends the question and retrieved passages to the Groq model.
5. **Citation validation:** Checks that generated citations refer to retrieved chunks and match their metadata.
6. **Result logging:** Records request status, latency, retries, token usage and answer grades in a CSV file.

### Retrieval strategy

Four retrieval configurations are implemented:

- `bm25_top3` — retrieves up to 3 relevant chunks.
- `bm25_top5` — retrieves up to 5 relevant chunks.
- `bm25_top8` — retrieves up to 8 relevant chunks.
- `adaptive_top3_top8` — starts with 3 chunks and expands to 8 if the highest-ranked chunk does not meet the minimum relevance score.

The adaptive strategy currently checks the highest-ranked chunk's BM25 score. This is a simple threshold-based decision, not a semantic assessment of whether all required evidence has been retrieved.

## 4. Technology stack

- Python
- Groq API
- `openai/gpt-oss-20b`
- PyMuPDF for PDF text extraction
- `tiktoken` for token-based chunking
- `rank-bm25` for information retrieval
- `python-dotenv` for environment configuration
- CSV and JSON for experiment data and results

## 5. Repository structure

```text
Relay/
│
├── app/
│   ├── ingest.py
│   ├── query_analyzer.py
│   ├── retriever.py
│   ├── decision_engine.py
│   ├── generator.py
│   ├── validator.py
│   ├── pipeline.py
│   └── csv_logger.py
│
├── model_services/
│   ├── groq_service.py
│   └── standin_service.py
│
├── papers/
│   ├── attention_is_all_you_need.pdf
│   ├── moshi.pdf
│   └── dynamic_chunking.pdf
│
├── experiments/
│   ├── run_baseline.py
│   ├── run_standin.py
│   ├── run_evaluation.py
│   ├── run_retrieval_comparison.py
│   ├── analyze_results.py
│   ├── test_retrieval.py
│   ├── test_retrieval_settings.py
│   ├── test_standin_service.py
│   └── test_streaming.py
│
├── results/
│   ├── paper_chunks.json
│   ├── results.csv
│   ├── results_backup.csv
│   └── retrieval_comparison_progress.json
│
├── tests/
│   ├── test_rate_limit.py
│   ├── test_daily_limit.py
│   └── test_retry_policy.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

## 6. Installation and setup

### Prerequisites

- Python 3.10 or later
- Git
- A Groq API key
- Internet access for Groq API requests

### Clone the repository

```bash
git clone https://github.com/omkarsatpute18/Relay.git
cd Relay
```

### Create a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use:

```powershell
.\venv\Scripts\activate.bat
```

### Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install tiktoken
```

The final command installs `tiktoken`, which is imported by the ingestion script.

### Configure environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
MODEL_NAME=openai/gpt-oss-20b
```

Replace the placeholder with your own Groq API key.

**Security:** Never commit `.env` or expose your API key in source code, screenshots or submission files.

## 7. Running the project

Run commands from the root `Relay/` directory.

### Step 1: Ingest the research papers

```bash
python -m app.ingest
```

This extracts text from the three PDFs and creates token-based chunks using a chunk size of 500 tokens and an overlap of 75 tokens.

The output is saved to:

```text
results/paper_chunks.json
```

### Step 2: Test retrieval

```bash
python -m experiments.test_retrieval
```

This tests BM25 retrieval using sample research questions.

### Step 3: Test retrieval settings

```bash
python -m experiments.test_retrieval_settings
```

This compares the four retrieval configurations on a sample question.

### Step 4: Run the real Groq baseline

```bash
python -m experiments.run_baseline
```

This sends a sequence of research questions to the configured Groq model and records service outcomes and measurements.

### Step 5: Run the stand-in service experiments

```bash
python -m experiments.run_standin
```

The stand-in supports configurable latency, concurrency, failures, timeouts, rate limits, refusals, quota limits and streaming.

### Step 6: Run the retrieval quality evaluation

```bash
python -m experiments.run_retrieval_comparison
```

Choose one of the four retrieval settings when prompted. The experiment evaluates 15 questions, asks for a human answer grade, and saves progress so that completed questions are not unnecessarily repeated.

### Step 7: Run an individual evaluation

```bash
python -m experiments.run_evaluation
```

This allows an individual question and retrieval setting to be selected for evaluation.

### Step 8: Analyze recorded results

```bash
python -m experiments.analyze_results
```

This summarizes the recorded CSV measurements by scenario.

## 8. Stand-in model service

The stand-in service provides a controllable environment for testing service behaviour without relying on real model responses.

Its configurable parameters include:

- Base response latency
- Additional latency under load
- Maximum concurrent requests
- Internal failure probability
- Timeout probability
- Rate-limit probability
- Model refusal probability
- Streaming piece delay
- Per-minute request quota
- Daily request quota

It is intended to help explore how a client application behaves under different service conditions. Its measurements are simulated and should not be treated as actual Groq service performance.

## 9. Results and measurements

Experiment data is recorded in:

```text
results/results.csv
```

The CSV records:

- Request ID
- Experiment scenario
- Service source (real or stand-in)
- Request start time
- First-token latency, when measured
- Total pipeline latency
- Service status
- Retry count
- Input and output tokens
- Retrieval configuration
- Human-assigned answer grade

Service success and answer correctness are evaluated separately.

The `answer_grade` field supports:

- `correct`
- `wrong`
- `refused_correctly`
- `refused_wrongly`

The first-token measurement is unavailable for the regular Groq generation path because it uses non-streaming requests. The stand-in streaming experiment measures first-token latency separately.

## 10. Current limitations

- BM25 relies on lexical matching and may miss semantically relevant passages.
- The adaptive retrieval strategy checks only the highest-ranked chunk's score.
- Citation validation verifies citation references and metadata, but does not independently establish semantic support for every generated claim.
- The stand-in service approximates service behaviour and does not reproduce every detail of a hosted inference provider.
- Real service limits and recovery times can vary by model and account tier.
- The regular Groq generation path uses non-streaming responses, so first-token latency is not available for those requests.

## 11. Author

**Project:** The Relay — Research Assistant Pipeline  
**GitHub:** https://github.com/omkarsatpute18/Relay

Built as part of the ML Engineering Intern assignment for Vaani.
