# BhoomiSatya — Architecture Document

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BhoomiSatya System                          │
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────────────┐ │
│  │ WhatsApp │───▶│  FastAPI App  │───▶│   AI Agent Orchestrator   │ │
│  │  (User)  │◀───│  (Gateway)   │◀───│     (LangGraph)           │ │
│  └──────────┘    └──────┬───────┘    └─────────┬─────────────────┘ │
│                         │                       │                   │
│  ┌──────────┐    ┌──────▼───────┐    ┌─────────▼─────────────────┐ │
│  │ Razorpay │───▶│  PostgreSQL  │    │     Scraper Fleet          │ │
│  │ Payments │    │  (Reports,   │    │  ┌─────────┐ ┌─────────┐  │ │
│  └──────────┘    │   Cache)     │    │  │ Dharani │ │  IGRS   │  │ │
│                  └──────────────┘    │  │ Scraper │ │ Scraper │  │ │
│  ┌──────────┐    ┌──────────────┐    │  └─────────┘ └─────────┘  │ │
│  │ Bhashini │───▶│    Redis     │    │  ┌─────────┐ ┌─────────┐  │ │
│  │   ASR    │    │  (Queue,     │    │  │  RERA   │ │ Revenue │  │ │
│  └──────────┘    │   Sessions)  │    │  │ Checker │ │  Court  │  │ │
│                  └──────────────┘    │  └─────────┘ └─────────┘  │ │
│                                      └───────────────────────────┘ │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   Valuation Engine                             │ │
│  │  Guideline Values + Comparable Sales + Fair Market Estimate   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                  Report Generator (WeasyPrint)                │ │
│  │  Safety Verdict + Valuation Verdict + PDF with evidence       │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. Data Flow

```
User sends WhatsApp message (text or voice)
        │
        ▼
[WhatsApp Cloud API Webhook]
        │
        ▼
[Parse message] ──── voice? ──▶ [Bhashini ASR] ──▶ Telugu/Hindi → Text
        │                                              │
        ▼◀─────────────────────────────────────────────┘
[Create Report in DB, status=processing]
        │
        ▼
[Background Task: AI Orchestrator]
        │
        ├──▶ [Parse Input Node] — LLM extracts survey no, district, mandal
        │         │
        │         ▼
        ├──▶ [Scrape Dharani] — Land ownership, pattadar, extent, nature
        ├──▶ [Scrape IGRS] — Encumbrance certificate, recent transactions
        ├──▶ [Check RERA] — RERA registration for apartment projects
        ├──▶ [Check Litigation] — eCourts / revenue court cases
        │         │
        │         ▼
        ├──▶ [Compute Valuation] — Guideline values + comparable sales
        │         │
        │         ▼
        ├──▶ [Generate Verdicts]
        │    ├── Safety Verdict: SAFE / RISKY / DANGEROUS
        │    └── Valuation Verdict: FAIR / OVERPRICED / UNDERPRICED
        │         │
        │         ▼
        └──▶ [Generate PDF Report]
                  │
                  ▼
        [Update DB, status=completed]
                  │
                  ▼
        [Send WhatsApp reply with PDF link]
```

## 3. Scraper Architecture

### 3.1 Base Class

All scrapers inherit from `BaseScraper`, which provides:

- **HTTP client management** — shared `httpx.AsyncClient` with connection pooling
- **Playwright browser pool** — for JavaScript-rendered portals (Dharani, RERA)
- **Retry logic** — exponential backoff with jitter (1s, 2s, 4s base delays)
- **Rate limiting** — per-portal request throttling to avoid IP bans
- **Response caching** — Redis-backed TTL cache (survey data cached 24h, RERA 7d)
- **Error classification** — distinguishes transient errors (retry) from permanent (fail)
- **Structured logging** — every request/response logged with portal, duration, status

```python
class BaseScraper:
    base_url: str
    max_retries: int = 3
    retry_delay: float = 1.0
    cache_ttl: int = 86400  # seconds

    async def _get(url, params) -> Response
    async def _post_form(url, data) -> dict
    async def _browser_fetch(url, actions) -> str  # Playwright
    async def _cached(key, fetcher) -> Any
```

### 3.2 Portal-Specific Scrapers

| Scraper | Portal | Method | Data Extracted |
|---------|--------|--------|----------------|
| `DharaniScraper` | dharani.telangana.gov.in | Playwright (JS-rendered dropdowns) | Ownership, pattadar, extent, land nature, mutations |
| `IGRSScraper` | registration.telangana.gov.in | HTTP POST + HTML parse | Encumbrance certificates, transaction history |
| `RERAScraper` | rera.telangana.gov.in | HTTP + Playwright | RERA registration, project details, promoter info |
| `MeeBhoomiScraper` | meebhoomi.ap.gov.in | HTTP POST | AP land records (1-B, Adangal) |
| `APRegistrationScraper` | registration.ap.gov.in | HTTP POST | AP encumbrance, registration data |
| `CERSAIScraper` | cersai.org.in | HTTP | Central mortgage/charge registry |
| `CourtScraper` | ecourts.gov.in | HTTP | Pending litigation on property |

### 3.3 Retry & Caching Strategy

- **Retry**: 3 attempts with exponential backoff + jitter. On HTTP 429, respect `Retry-After` header. On 5xx, retry. On 4xx (except 429), fail immediately.
- **Caching**: Redis with key pattern `scraper:{portal}:{hash(params)}`. TTLs vary by data volatility:
  - Land records (Dharani): 24 hours
  - Encumbrance: 12 hours (can change with new transactions)
  - RERA project data: 7 days (changes infrequently)
  - Guideline values: 30 days (updated annually)
- **Circuit breaker**: If a portal returns 5 consecutive failures, mark it as degraded for 10 minutes. Report includes a note that portal data is temporarily unavailable.

## 4. AI Agent Architecture

### 4.1 LangGraph State Graph

The orchestrator uses LangGraph to define a directed acyclic graph of processing nodes. Each node receives the shared state, performs its task, and returns state updates.

```
                    ┌─────────────┐
                    │ parse_input │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
     ┌────────────┐ ┌────────────┐ ┌──────────┐
     │scrape_land │ │scrape_enc  │ │check_rera│
     │  _records  │ │ _umbrance  │ │          │
     └─────┬──────┘ └─────┬──────┘ └────┬─────┘
           │               │              │
           └───────────────┼──────────────┘
                           ▼
                  ┌────────────────┐
                  │check_litigation│
                  └───────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │compute_valuation│
                 └───────┬─────────┘
                         ▼
                ┌──────────────────┐
                │generate_verdicts │
                └───────┬──────────┘
                        ▼
                ┌───────────────┐
                │generate_report│
                └───────────────┘
```

### 4.2 State Schema

```python
class VerificationState(TypedDict):
    # Input
    property_input: str
    report_type: str  # quick | full | premium

    # Parsed
    parsed: dict  # survey_number, district, mandal, village, etc.
    needs_clarification: bool

    # Scraped data
    land_records: dict | None
    encumbrance: dict | None
    rera_data: dict | None
    litigation: list[dict]

    # Valuation
    guideline_value: float | None
    comparable_sales: list[dict]
    estimated_market_value: float | None

    # Verdicts
    safety_verdict: str  # SAFE | RISKY | DANGEROUS
    safety_reasons: list[str]
    valuation_verdict: str  # FAIR | OVERPRICED | UNDERPRICED
    valuation_analysis: str

    # Output
    report_html: str
    pdf_url: str
    summary: str
```

### 4.3 Tool Binding

Each scraper node binds LangChain tools so the LLM can decide which specific queries to make:

- `search_dharani(district, mandal, village, survey_number)` — fetch land ownership
- `get_encumbrance(document_number, year_range)` — fetch EC
- `search_rera(project_name_or_promoter)` — check RERA registration
- `search_ecourts(party_name, district)` — check litigation
- `get_guideline_value(district, mandal, village, land_type)` — fetch SRO rates

The LLM (GPT-4o / Claude) orchestrates the tool calls based on the parsed input.

## 5. Valuation Engine Design

### 5.1 Guideline Values

Government-published minimum registration values (SRO guideline values). Scraped from IGRS portals. Provides the floor price for any transaction.

### 5.2 Comparable Sales Aggregation

Recent sale deeds from the same village/locality within the last 2 years. Data sourced from IGRS transaction records. Aggregated as:
- Median price per sq. yard / sq. ft.
- Price trend (increasing / decreasing / stable)
- Number of comparable transactions found

### 5.3 Fair Market Value Algorithm

```
fair_market_value = weighted_average(
    guideline_value * 1.0,        # weight: 0.2
    comparable_median * 1.0,      # weight: 0.5
    online_listing_avg * 1.0,     # weight: 0.3 (if available)
)

valuation_verdict:
    if asking_price > fair_market_value * 1.15 → OVERPRICED
    if asking_price < fair_market_value * 0.85 → UNDERPRICED (or suspicious)
    else → FAIR
```

Additional adjustments:
- **Location premium**: main road frontage (+10-15%), corner plot (+5-10%)
- **Negative factors**: litigation (-20-30%), encumbrance (-15-25%), no RERA (-10%)
- **Land nature**: agricultural land in urban zone (conversion cost factored in)

## 6. Database Schema Overview

```sql
-- Core tables
reports           -- Each verification request
users             -- WhatsApp phone number based identity
payments          -- Razorpay transaction records

-- Geographic hierarchy
districts         -- State > District
mandals           -- District > Mandal
villages          -- Mandal > Village

-- Cached portal data
land_records      -- Dharani / Meebhoomi scrape cache
encumbrances      -- IGRS EC data cache
rera_projects     -- Pre-scraped RERA project index
guideline_values  -- SRO guideline values per village/locality
comparable_sales  -- Recent transactions from IGRS

-- Report output
report_documents  -- Generated PDF storage metadata
```

Key design decisions:
- UUIDs for all primary keys (no sequential IDs exposed to users)
- `created_at` / `updated_at` on all tables with timezone
- Soft deletes where appropriate
- JSONB columns for semi-structured scraped data (portal responses vary)

## 7. Deployment Architecture

### Target: GCP (Google Cloud Platform)

```
┌─────────────────────────────────────────────────┐
│                  GCP Project                     │
│                                                   │
│  ┌───────────────┐     ┌──────────────────────┐  │
│  │  Cloud Run     │────▶│  Cloud SQL           │  │
│  │  (FastAPI app) │     │  (PostgreSQL 16)     │  │
│  │  min: 0        │     │  db-f1-micro → db-g1 │  │
│  │  max: 10       │     └──────────────────────┘  │
│  └───────┬───────┘                                │
│          │            ┌──────────────────────┐    │
│          ├───────────▶│  Memorystore (Redis)  │    │
│          │            │  Basic tier, 1GB      │    │
│          │            └──────────────────────┘    │
│          │                                        │
│          │            ┌──────────────────────┐    │
│          ├───────────▶│  Cloud Storage        │    │
│          │            │  (PDF reports)        │    │
│          │            └──────────────────────┘    │
│          │                                        │
│          │            ┌──────────────────────┐    │
│          └───────────▶│  Secret Manager       │    │
│                       │  (API keys, tokens)   │    │
│                       └──────────────────────┘    │
│                                                   │
│  ┌──────────────────────────────────────────────┐ │
│  │  Cloud Scheduler (cron)                       │ │
│  │  - Refresh guideline values (monthly)         │ │
│  │  - Re-scrape RERA index (weekly)              │ │
│  │  - Clean expired cache (daily)                │ │
│  └──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Cost Estimate (Early Stage)

| Service | Spec | Monthly Cost |
|---------|------|-------------|
| Cloud Run | 0-2 instances, 1 vCPU, 512MB | ~$5-15 |
| Cloud SQL | db-f1-micro, 10GB | ~$10 |
| Memorystore | Basic 1GB | ~$35 |
| Cloud Storage | <1GB PDFs | ~$1 |
| Secret Manager | 5 secrets | ~$0 |
| **Total** | | **~$50-60/mo** |

## 8. Security Considerations

### 8.1 Webhook Security
- **WhatsApp**: Verify `hub.verify_token` on GET, validate payload signature on POST
- **Razorpay**: HMAC-SHA256 signature verification using webhook secret
- All webhook endpoints reject unsigned/invalid requests with 400/403

### 8.2 Credential Management
- No API keys or secrets in code or environment files in production
- All secrets stored in GCP Secret Manager
- Local development uses `.env` file (git-ignored)

### 8.3 Data Security
- No user Aadhaar or PAN numbers stored
- Phone numbers hashed for analytics, stored plain only for WhatsApp delivery
- Report PDFs served via signed URLs with 24-hour expiry
- Database connections use SSL in production

### 8.4 Rate Limiting
- WhatsApp webhook: rely on Meta's built-in rate limiting
- API endpoints: 100 requests/minute per IP (configurable)
- Portal scraping: per-portal rate limits to avoid IP blocking

### 8.5 Scraper Ethics
- Respect `robots.txt` where present
- No credential stuffing or login bypass
- Only access publicly available data
- Add delays between requests to reduce portal load
- User-Agent header identifies BhoomiSatya (not spoofed)
