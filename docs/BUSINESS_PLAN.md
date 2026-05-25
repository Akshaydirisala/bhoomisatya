# BhoomiSatya — Business Plan

## Executive Summary

**BhoomiSatya** answers the two most critical questions every Indian property buyer faces:

> *"Is this property safe?"* and *"Is it worth the price?"*

We deliver AI-powered property verification reports via WhatsApp, combining real-time data from 10+ government portals with market valuation analysis. A buyer sends a property description (text or voice note in Telugu/English), and receives a comprehensive report with two clear verdicts — **Safety** and **Valuation** — within minutes, not days.

Starting with Telangana and Andhra Pradesh, BhoomiSatya targets the massive gap between expensive manual lawyer verification (₹5,000-25,000, takes 2-4 weeks) and zero verification (the risky default for most buyers).

---

## 1. Problem Statement

### Problem 1: Property Safety Verification is Broken

Buying property in Telangana/AP is a minefield:

- **Forged documents**: Fake pattadar passbooks, fabricated sale deeds
- **Hidden encumbrances**: Existing mortgages, unpaid loans, undisclosed liens
- **Litigation traps**: Pending court cases the seller doesn't disclose
- **Government claims**: Land under acquisition, highway alignment, or environmental restriction
- **Missing RERA**: Apartments sold without mandatory RERA registration

The current solution — hiring a lawyer to do manual verification — costs ₹5,000-25,000, takes 2-4 weeks, and is unavailable in smaller towns. Most buyers skip verification entirely and hope for the best. This is especially dangerous for NRIs buying remotely.

### Problem 2: Fair Price Determination is Opaque

- Government guideline values are artificially low (30-50% of market value)
- "Market rates" are whatever the broker tells you
- No standardized comparable sales data available to buyers
- NRIs are routinely quoted 20-40% above local market rates
- No way to verify if a price is fair without extensive local knowledge

---

## 2. Solution

BhoomiSatya is an **AI-powered property verification agent** that:

1. **Accepts input via WhatsApp** — send a survey number, address, or voice note in Telugu/English
2. **Scrapes 10+ government portals in real-time** — Dharani, IGRS, RERA, eCourts, CERSAI, HMDA, and more
3. **Cross-references all data** to detect fraud, encumbrances, litigation, and regulatory violations
4. **Computes fair market value** using guideline values, comparable recent sales, and location adjustments
5. **Delivers two verdicts**:
   - **Safety Verdict**: SAFE / RISKY / DANGEROUS (with specific reasons)
   - **Valuation Verdict**: FAIR / OVERPRICED / UNDERPRICED (with price range)
6. **Generates a PDF report** with all evidence, sources, and explanations
7. **Sends the report via WhatsApp** — shareable with family, agent, or bank

---

## 3. Target Market

### Primary Segments

| Segment | Size Estimate | Pain Point | Willingness to Pay |
|---------|--------------|------------|-------------------|
| **NRI property buyers** (US, Gulf, UK) | ~500K Telangana/AP origin NRIs buying property annually | Cannot visit in person, rely on agents, fear of fraud | HIGH (₹2,000-5,000 is trivial vs. property cost) |
| **Local first-time buyers** | ~2M property registrations/year in TS+AP | Cannot afford ₹15K lawyer, don't know the process | MEDIUM (₹999-1,999 is attractive) |
| **Real estate agents** | ~50K active agents in TS+AP | Want to build trust with buyers, differentiate from competition | MEDIUM (bulk pricing for regular use) |
| **Banks/NBFCs** | ~200 bank branches doing property loans in Hyderabad | Need verification for loan approval, currently outsource | HIGH (replace ₹5K-10K manual verification) |

### Geographic Focus

- **Phase 1** (Months 1-6): Telangana — Hyderabad, Rangareddy, Medchal-Malkajgiri, Sangareddy
- **Phase 2** (Months 7-12): Full Telangana (33 districts) + Andhra Pradesh top 5 cities
- **Phase 3** (Year 2): Full AP + Karnataka (Bangalore) + Maharashtra (Pune)

---

## 4. Market Size Estimate

### Telangana
- Annual property registrations (2023-24): ~8.5 lakh (850,000)
- Estimated % that would pay for automated verification: 5-10%
- Serviceable market: 42,500 - 85,000 reports/year
- At avg ₹1,500/report: **₹6.4 - 12.8 crore/year**

### Andhra Pradesh
- Annual property registrations: ~7 lakh (700,000)
- Serviceable market: 35,000 - 70,000 reports/year
- At avg ₹1,500/report: **₹5.3 - 10.5 crore/year**

### Combined TAM (TS + AP)
- **₹11.7 - 23.3 crore/year** (~$1.4M - $2.8M)

### NRI Premium Segment
- ~50,000 NRI property transactions/year (TS+AP origin)
- 20% conversion at avg ₹2,500/report: **₹2.5 crore/year**

---

## 5. Competitive Analysis

| Competitor | What They Do | Weakness | BhoomiSatya Advantage |
|-----------|-------------|----------|----------------------|
| **Manual lawyers** | Physical document verification at SRO | Expensive (₹5K-25K), slow (2-4 weeks), unavailable in small towns | 100x cheaper, 100x faster, available everywhere |
| **Property verification startups** (e.g., SquareYards, PropCheck) | Semi-automated verification for metro cities | No Telugu state portal expertise, no real-time scraping, expensive (₹3K-10K) | Deep Dharani/IGRS integration, WhatsApp-native, affordable |
| **Legal tech platforms** (e.g., Vakil No. 1) | Connect buyers with lawyers | Still manual, still expensive, still slow | Fully automated, instant |
| **Doing nothing** (most buyers) | Skip verification, trust the broker | Huge risk of fraud and overpayment | Peace of mind for ₹999 |

**Unfair advantage**: Deep scraping integration with Telugu state government portals (Dharani, IGRS, RERA). These portals are notoriously difficult to automate — they use dynamic dropdowns, CAPTCHAs, and session-based workflows. Our Playwright-based scrapers handle all of this. Replicating this is a 3-6 month effort for any competitor.

---

## 6. Revenue Model

### Three Tiers

| Tier | Price | What's Included | Target Segment |
|------|-------|----------------|----------------|
| **Quick Check** | ₹999 | Ownership verification (Dharani/Meebhoomi) + encumbrance check + safety verdict only | Budget buyers, initial screening |
| **Full Report** | ₹1,999 | Everything in Quick + RERA check + litigation search + valuation verdict + PDF report | Most buyers (primary tier) |
| **Premium Report** | ₹2,999 | Everything in Full + comparable sales analysis + investment recommendation + priority support | NRIs, high-value properties, banks |

### Additional Revenue Streams (Phase 2+)

- **Bulk/subscription plans** for agents: ₹9,999/month for 10 reports
- **Bank API integration**: ₹500-1,000/report for loan verification
- **Title insurance referral**: Commission on title insurance policies (tie-up with insurers)
- **Legal service referral**: Commission on lawyer referrals for RISKY/DANGEROUS properties

---

## 7. Unit Economics

### Per Report (Full Report @ ₹1,999)

| Cost Component | Amount |
|---------------|--------|
| LLM API (GPT-4o, ~2K tokens input + 1K output per node, 8 nodes) | ₹15-25 |
| Bhashini ASR (if voice note) | ₹2-5 |
| Cloud infrastructure (per-report amortized) | ₹5-10 |
| WhatsApp Business API message cost | ₹1-2 |
| Razorpay payment gateway (2%) | ₹40 |
| **Total variable cost** | **₹63-82** |
| **Gross margin** | **₹1,917-1,936 (96%)** |

### Fixed Monthly Costs (Early Stage)

| Item | Monthly Cost |
|------|-------------|
| GCP infrastructure (Cloud Run + SQL + Redis) | ₹5,000 |
| WhatsApp Business API platform fee | ₹0 (free tier up to 1000 conversations) |
| OpenAI / Anthropic API (base) | ₹2,000 |
| Domain + miscellaneous | ₹500 |
| **Total fixed** | **₹7,500** |

### Breakeven

- Fixed costs: ₹7,500/month
- Gross margin per report: ~₹1,900
- **Breakeven: 4 reports/month**

---

## 8. Go-to-Market Strategy

### Phase 1: NRI-First (Months 1-3)

**Why NRIs first**: highest willingness to pay, largest pain point (can't visit in person), English-comfortable (easier initial UX), concentrated in searchable online communities.

**Channels**:

1. **Google Ads** — target keywords:
   - "Hyderabad property verification"
   - "Telangana land check online"
   - "Is my Hyderabad land safe to buy"
   - "NRI property buying Telangana"
   - Budget: ₹30,000/month, expected CPC: ₹15-30, conversions: 50-100/month

2. **YouTube** — create 5-minute explainer videos:
   - "How to check if your Telangana land is safe" (Telugu + English)
   - "5 things NRIs must verify before buying property in Hyderabad"
   - Target: 10K views/month organically + promoted

3. **NRI community groups** — WhatsApp groups, Facebook groups, Reddit (r/india, r/hyderabad):
   - Share case studies (anonymized) of properties flagged as DANGEROUS
   - Offer first report free or at ₹499

### Phase 2: WhatsApp Virality (Months 3-6)

The report is designed to be shared. Every BhoomiSatya report includes:
- A shareable summary card (image)
- "Share with your family" CTA
- "Verify another property" CTA with WhatsApp deep link

**Viral loop**: Buyer gets report → shares with spouse/parents/agent → they verify their own property → refer others.

**Target**: 1.5x viral coefficient (each buyer brings 0.5 new buyers).

### Phase 3: Agent Partnerships (Months 6-9)

Partner with real estate agents who want to differentiate:
- "BhoomiSatya Verified" badge for listings
- Bulk pricing: 10 reports/month for ₹9,999
- Agent dashboard to order reports and share with clients
- Target: 50 agents × 5 reports/month = 250 reports/month

### Phase 4: Bank Integration (Months 9-12)

- API integration with bank loan processing systems
- Replace manual verification (₹5,000-10,000) with BhoomiSatya (₹1,000-2,000)
- Pilot with 2-3 cooperative banks / NBFCs in Hyderabad
- Target: 100 reports/month per bank partner

---

## 9. Financial Projections (Monthly, 12 Months)

| Month | Reports | Revenue (₹) | Variable Cost (₹) | Fixed Cost (₹) | Net (₹) | Cumulative (₹) |
|-------|---------|-------------|-------------------|----------------|---------|----------------|
| 1 | 10 | 14,990 | 750 | 7,500 | 6,740 | 6,740 |
| 2 | 25 | 39,975 | 1,875 | 7,500 | 30,600 | 37,340 |
| 3 | 50 | 84,950 | 3,750 | 10,000 | 71,200 | 108,540 |
| 4 | 80 | 135,920 | 6,000 | 10,000 | 119,920 | 228,460 |
| 5 | 120 | 203,880 | 9,000 | 15,000 | 179,880 | 408,340 |
| 6 | 180 | 305,820 | 13,500 | 15,000 | 277,320 | 685,660 |
| 7 | 280 | 475,720 | 21,000 | 20,000 | 434,720 | 1,120,380 |
| 8 | 400 | 679,600 | 30,000 | 25,000 | 624,600 | 1,744,980 |
| 9 | 550 | 934,450 | 41,250 | 30,000 | 863,200 | 2,608,180 |
| 10 | 700 | 1,189,300 | 52,500 | 35,000 | 1,101,800 | 3,709,980 |
| 11 | 900 | 1,529,100 | 67,500 | 40,000 | 1,421,600 | 5,131,580 |
| 12 | 1,200 | 2,038,800 | 90,000 | 50,000 | 1,898,800 | 7,030,380 |

**Assumptions**:
- Avg revenue per report: ₹1,699 (mix of Quick ₹999 and Full ₹1,999)
- Variable cost per report: ₹75
- Fixed costs grow with scale (more infra, potentially part-time help)
- Growth driven by ads (months 1-3), virality (4-6), agents (7-9), banks (10-12)
- No external funding assumed

**Year 1 total**: ~₹70 lakh revenue, ~₹55 lakh profit (before tax and founder salary)

---

## 10. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Government portals block scraping** | MEDIUM | HIGH | Multiple IP rotation, residential proxies, Playwright stealth mode. If fully blocked, partner with data providers or apply for API access. |
| **Portal redesign breaks scrapers** | HIGH | MEDIUM | Automated monitoring of portal changes (hash page structure daily). Modular scraper design allows quick fixes. Budget 2-3 days/month for scraper maintenance. |
| **Low initial adoption** | MEDIUM | MEDIUM | NRI-first strategy reduces risk (higher intent). Free/discounted first report to build trust. Iterate on pricing. |
| **LLM accuracy issues** | LOW | HIGH | Human-in-the-loop review for first 100 reports. Structured output with explicit source links so user can verify. Conservative verdicts (flag as RISKY when uncertain rather than SAFE). |
| **Legal liability** (wrong verdict) | LOW | HIGH | Clear disclaimer: "This report is for informational purposes only and does not constitute legal advice." Recommend lawyer for RISKY/DANGEROUS properties. Consider E&O insurance at scale. |
| **Competitor with more resources** | LOW | MEDIUM | First-mover advantage on Telugu state portals. Deep scraper integration is a 3-6 month moat. Build brand trust through accuracy and speed. |
| **WhatsApp Business API policy change** | LOW | MEDIUM | Web app as backup channel. Telegram bot as alternative. API-first architecture allows any frontend. |
| **CAPTCHA / bot detection by portals** | MEDIUM | MEDIUM | CAPTCHA solving services (2Captcha, anti-captcha) as fallback. Playwright human-like interaction patterns. Reduce request frequency. |

---

## 11. Team Requirements

### Solo Founder Phase (Months 1-6)
- **Founder** (you): Full-stack development, scraper engineering, AI agent design, marketing
- Time commitment: Full-time
- Skills needed: Python, FastAPI, Playwright, LangChain/LangGraph, basic Telugu

### First Hire (Months 4-6)
- **Scraper Engineer** (part-time/contract): Maintain and extend portal scrapers
- Why: Portal maintenance is ongoing work; frees founder for product and growth
- Budget: ₹30,000-50,000/month (contract)

### Growth Phase (Months 6-12)
- **Telugu Content Person** (part-time): Telugu report templates, voice UX, marketing content
- Why: Core market speaks Telugu; report quality in Telugu is a differentiator
- Budget: ₹20,000-30,000/month (part-time)

### Year 2
- **Business Development**: Real estate agent partnerships, bank integrations
- **Customer Support**: Handle edge cases, escalations, report disputes
- **Data Engineer**: Scale scraping infrastructure, build data warehouse

---

## 12. Key Metrics to Track

| Metric | Target (Month 6) | Target (Month 12) |
|--------|------------------|-------------------|
| Monthly reports generated | 180 | 1,200 |
| Report accuracy (post-verification) | >95% | >98% |
| Avg report generation time | <10 min | <5 min |
| Customer satisfaction (WhatsApp rating) | 4.2/5 | 4.5/5 |
| Viral coefficient | 1.3x | 1.5x |
| Monthly revenue | ₹3 lakh | ₹20 lakh |
| Portal uptime (scraper success rate) | >90% | >95% |

---

## 13. Why Now?

1. **Dharani digitization is complete**: Telangana fully digitized land records in 2020-22. For the first time, all data is scrapeable.
2. **WhatsApp penetration**: 95%+ smartphone users in India have WhatsApp. No app download barrier.
3. **LLM capabilities**: GPT-4o / Claude can parse unstructured property descriptions in Telugu and English with high accuracy. This was not possible 2 years ago.
4. **Bhashini ASR maturity**: Indian government's speech-to-text for Telugu is now production-grade. Voice notes from farmers and non-tech-savvy buyers can be processed.
5. **UPI + Razorpay**: Instant payments via UPI make ₹999-2,999 micro-transactions frictionless.
6. **Telangana property boom**: Hyderabad is India's fastest-growing property market. Record registrations in 2023-24. Buyer anxiety about fraud is at an all-time high.

---

*BhoomiSatya — Bhoom ki Satya, Aapke Haath Mein (The truth about land, in your hands)*
