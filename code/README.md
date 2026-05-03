# Multi-Domain Support Triage Agent

**HackerRank Orchestrate Hackathon Submission**  
**Date:** May 1, 2026  
**Development Time:** 8 hours  
**Sample Validation:** 100% accuracy (10/10 status, 10/10 request_type)

A production-ready, terminal-based Python agent that processes support tickets across three ecosystems (HackerRank, Claude, Visa) using a modular RAG pipeline with local LLM integration.

---

## 🎯 Approach Overview

### Core Philosophy
- **Safety First:** Conservative escalation - when in doubt, escalate to human
- **Corpus-Grounded:** All responses backed by retrieved articles, no hallucinations
- **Deterministic:** Same input → same output (temperature=0, stable sorting)
- **Local-First:** Uses Ollama for privacy and control, no external API dependencies

### Pipeline Architecture

```
Input Ticket
    ↓
Company Router (keyword-based)
    ↓
BM25 Retriever (789 articles, title-boosting)
    ↓
Safety Gate (13 escalation rules)
    ↓
Classifier (request_type + product_area)
    ↓
Response Generator (Ollama gemma4:e4b or templates)
    ↓
Output CSV (8 columns)
```

---

## 📁 Module Overview

| Module | Responsibility | Key Features |
|--------|---------------|--------------|
| **corpus_loader.py** | Load & parse markdown articles | YAML frontmatter parsing, 789 articles indexed |
| **router.py** | Company identification | Keyword scoring, fallback to "unknown" |
| **retriever.py** | Article retrieval | BM25Okapi + 1.8× title-match boosting |
| **safety_gate.py** | Escalation rules | 13 rules in priority order, context-aware |
| **classifier.py** | Request classification | Request type + product area taxonomy |
| **generator.py** | Response generation | Ollama API + deterministic templates |
| **main.py** | Pipeline orchestration | Error handling, progress tracking |
| **validate.py** | Accuracy validation | Compares against sample ground truth |
| **models.py** | Data structures | Dataclasses for type safety |
| **config.py** | Configuration | All constants centralized |
| **utils.py** | Utilities | Text processing, injection detection |

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** (or Conda)
- **Ollama** (optional, has deterministic fallback)

### Installation

```bash
# Option 1: Conda (recommended)
conda create -n orchestrate python=3.11 -y
conda activate orchestrate
pip install -r requirements.txt

# Option 2: venv
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### Configuration

```bash
# Create environment file
cp .env.example .env

# Edit .env (optional - defaults work without Ollama)
USE_OLLAMA=true   # Set to false for deterministic fallback
```

### Running

```bash
# Process all 29 tickets
python main.py

# Output written to: ../support_tickets/output.csv
```

### Validation

```bash
# Validate against sample tickets
python validate.py

# Expected: Status accuracy >= 70% (we achieve 100%)
```

---

## 🏗️ Technical Approach

### 1. Retrieval Strategy
- **Algorithm:** BM25Okapi (deterministic, fast, no embeddings needed)
- **Corpus:** 789 articles (446 HackerRank, 323 Claude, 20 Visa)
- **Enhancement:** 1.8× score boost for articles with >30% title token overlap
- **Caching:** BM25 models cached per company for performance

### 2. Safety Gate
**13 Escalation Rules (priority order):**
1. Prompt injection (multilingual detection)
2. Destructive code requests
3. Out-of-domain queries (celebrities, weather)
4. Chit-chat (thank you messages)
5. Identity theft
6. Refund requests
7. Payment failures
8. Security vulnerabilities
9. Service outages
10. Access restoration
11. Score manipulation
12. Certificate identity changes
13. Vague tickets with no company

**Context-Aware Detection:**
- Card keywords override prompt injection false positives
- Multi-threshold detection (strong vs weak patterns)

### 3. Response Generation
- **Primary:** Ollama gemma4:e4b (local, temperature=0)
- **Fallback:** Article excerpts (when Ollama unavailable)
- **Templates:** Escalation/invalid responses (no LLM needed)
- **Format:** JSON structured output with response + justification

### 4. Classification
- **Request Type:** product_issue, feature_request, bug, invalid
- **Product Area:** Company-specific taxonomies (e.g., HackerRank: screen, interviews, billing, account)
- **Logic:** Keyword matching + article-based inference

---

## 📊 Results

### Sample Validation (10 tickets)
- **Status Accuracy:** 100% (10/10)
- **Request Type Accuracy:** 100% (10/10)
- **Result:** PASS ✓

### Full Ticket Set (29 tickets)
- **Total Processed:** 29/29
- **Replied:** 12 (Ollama-generated, natural language)
- **Escalated:** 17 (template-based, deterministic)
- **Empty Responses:** 0
- **Distribution:** 18 product_issue, 8 bug, 2 invalid, 1 feature_request

### Quality Metrics
- ✅ No hallucinated phone numbers, URLs, or policies
- ✅ All responses grounded in corpus articles
- ✅ Conservative escalation (safety first)
- ✅ Natural language responses (not article dumps)
- ✅ Clear justifications with article references

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
USE_OLLAMA=true          # Enable Ollama (false = deterministic fallback)
```

### Key Constants (config.py)
```python
OLLAMA_MODEL = "gemma4:e4b"
TEMPERATURE = 0                    # Deterministic
MIN_RETRIEVAL_SCORE = 0.5         # Escalate if no good match
TOP_K_ARTICLES = 5                # Retrieve top 5 articles
```

---

## 📝 Output Format

**File:** `../support_tickets/output.csv`

**Columns:**
1. `issue` - Original ticket text
2. `subject` - Ticket subject line
3. `company` - HackerRank, Claude, Visa, or None
4. `response` - User-facing answer (corpus-grounded)
5. `product_area` - Support category (e.g., "screen", "billing")
6. `status` - "replied" or "escalated"
7. `request_type` - "product_issue", "feature_request", "bug", or "invalid"
8. `justification` - Concise explanation of decision

---

## 🎨 Design Decisions

### Why BM25 over Embeddings?
- **Deterministic:** Same query always returns same results
- **Fast:** No GPU needed, instant retrieval
- **Explainable:** Scores based on term frequency
- **Sufficient:** 789 articles is small enough for BM25 to excel

### Why Ollama over Claude/GPT?
- **Local Control:** No external API dependencies
- **Privacy:** Data never leaves local machine
- **Cost:** No API costs
- **Deterministic:** Temperature=0 ensures reproducibility

### Why Rule-Based Safety Gate?
- **Explicit:** All escalation logic is auditable
- **Fast:** No LLM call needed for dangerous cases
- **Reliable:** No black-box decisions
- **Maintainable:** Easy to add/modify rules

### Why Conservative Escalation?
- **Safety:** Better to over-escalate than hallucinate
- **Trust:** Users prefer "I'll escalate" over wrong info
- **Compliance:** Reduces liability for sensitive cases

---

## 🧪 Testing

### Corpus Loading Test
```bash
python corpus_loader.py
# Expected: Positive article counts for all companies
```

### Validation Test
```bash
python validate.py
# Expected: Status accuracy >= 70%
```

### Determinism Test
```bash
python main.py
cp ../support_tickets/output.csv output1.csv
python main.py
diff output1.csv ../support_tickets/output.csv
# Expected: No differences
```

---

## 📦 Dependencies

```
pandas>=2.0.0          # Data processing
python-dotenv>=1.0.0   # Environment variables
rank_bm25>=0.2.2       # BM25 retrieval (optional, has fallback)
openai>=1.0.0          # Ollama API client (optional)
pyyaml>=6.0            # YAML frontmatter parsing
```

**Optional Dependencies:**
- `rank_bm25` - Falls back to keyword matching if unavailable
- `openai` - Falls back to article excerpts if unavailable

---

## 🔍 Troubleshooting

### "No module named 'rank_bm25'"
```bash
pip install rank_bm25
# Or: Agent will use keyword matching fallback
```

### "Connection refused" (Ollama)
```bash
# Option 1: Start Ollama
ollama serve

# Option 2: Use deterministic fallback
# Set USE_OLLAMA=false in .env
```

### "Empty responses"
```bash
# Verify Ollama is running or fallback is enabled
python -c "from config import USE_OLLAMA; print(f'USE_OLLAMA={USE_OLLAMA}')"
```

---

## 📚 Project Structure

```
code/
├── main.py              # Entry point
├── config.py            # All configuration
├── models.py            # Data structures
├── corpus_loader.py     # Load support articles
├── router.py            # Company routing
├── retriever.py         # BM25 retrieval
├── safety_gate.py       # Escalation rules
├── classifier.py        # Request classification
├── generator.py         # Response generation
├── utils.py             # Utilities
├── validate.py          # Validation script
├── requirements.txt     # Dependencies
└── README.md            # This file
```

---

## 🏆 Key Achievements

- ✅ **100% sample validation accuracy**
- ✅ **0 empty responses** (robust fallback handling)
- ✅ **Corpus-grounded** (no hallucinations)
- ✅ **Deterministic** (reproducible results)
- ✅ **Local-first** (privacy-preserving)
- ✅ **Modular** (10 separate modules)
- ✅ **Production-ready** (error handling, logging)

---

## 👥 Development

**Total Time:** 8 hours  
**Iterations:** 12 refinement cycles  
**Tools Used:** Antigravity (initial build) + Kiro (refinement)  
**Approach:** Iterative development with continuous validation

---

## 📄 License

This project was developed for the HackerRank Orchestrate Hackathon (May 1-2, 2026).
