# AfriDocs AI — Vision & Problem Statement

**Document:** 01-vision.md  
**Phase:** 1 — Product Discovery & Requirements  
**Status:** Final  
**Date:** 2026-08-20  
**Author:** AfriDocs AI Project Team  

---

## 1. Vision Statement

> **AfriDocs AI** is an AI-powered Intelligent Business Document Operations Platform that automates the ingestion, classification, extraction, validation, routing, and approval of business documents — starting with invoices — for African SMEs, accounting firms, and procurement teams that still operate on paper, PDFs, and email.

The platform turns a manual, error-prone, 3–5 day document processing cycle into a sub-60-second automated pipeline with a human-in-the-loop review layer for exceptions.

---

## 2. The Problem

### 2.1 Current Reality for African Businesses

African businesses — SMEs, accounting firms, logistics companies, insurers — receive hundreds to thousands of business documents every month: invoices, purchase orders, delivery notes, contracts, bank statements, and compliance records.

The dominant processing method is still **manual**:

| Step | Current Reality |
|------|----------------|
| Receipt | Email attachment, WhatsApp PDF, physical scan |
| Data entry | Finance clerk types fields into spreadsheet or accounting system |
| Validation | Manager eyeballs the numbers and signs a printed copy |
| Filing | Saved in a folder on someone's laptop or Google Drive |
| Retrieval | "Can you send me that invoice from last month?" — takes 20 minutes |
| Audit | Reconstructed from email threads and file shares |

### 2.2 Why This Is a Problem

- **Cost** — A finance clerk processing 200 invoices per month spends roughly 40–60 hours on data entry alone.
- **Errors** — Manual data entry produces an average 1–4% error rate per field. On a ZAR 500,000 invoice, a misplaced decimal is catastrophic.
- **Speed** — Invoice approval cycles of 3–10 business days cause cash flow friction with suppliers.
- **Fraud** — Duplicate invoices, phantom suppliers, and inflated amounts go undetected without automated checks.
- **Compliance** — POPIA and SARS e-invoice mandates require structured retention and audit trails — impossible with file folders.
- **Scale** — As a business grows, document volume grows linearly. Manual processing does not scale.

### 2.3 Why Now

Three forces have converged to make this solvable today at low cost:

1. **AI OCR maturity** — Azure AI Document Intelligence and AWS Textract can extract structured fields from scanned invoices with 90–98% accuracy out of the box.
2. **LLM availability** — GPT-4o can classify ambiguous documents, fill gaps in extraction, and explain anomalies in plain language.
3. **Cloud cost reduction** — Processing 1,000 invoices end-to-end costs under $5 on Azure or AWS today.

---

## 3. The Solution

AfriDocs AI provides a **multi-tenant SaaS platform** with four core capabilities:

```
INGEST → PROCESS → REVIEW → ACTION
```

| Layer | What It Does |
|-------|-------------|
| **Ingest** | Accept documents via upload, email, WhatsApp, or API |
| **Process** | OCR, classify, extract fields, validate against rules |
| **Review** | Route exceptions to human reviewers; flag anomalies |
| **Action** | Trigger approval workflows, push to accounting systems, archive |

### 3.1 MVP Constraint

The MVP processes **invoices only**. This is a deliberate product decision:

- Invoices are the highest-volume, highest-value document type for the target users.
- The extraction schema is well-defined and measurable.
- The approval workflow maps cleanly to a 2-level approval pattern (clerk → manager).
- Success can be demonstrated in a 2-week pilot with a real organisation.

All other document types (contracts, POs, delivery notes) are post-MVP.

---

## 4. Target Market

### 4.1 Primary Market (MVP)

| Segment | Description | Why They Buy |
|---------|-------------|-------------|
| **Accounting firms** | 5–50 person firms processing client invoices | Reduce time per client; take on more clients without hiring |
| **SME finance teams** | 10–200 employee companies with 50–500 invoices/month | Reduce clerk hours; close books faster |
| **Procurement teams** | Mid-market companies with 3-way match requirements | Automate PO → invoice → delivery note matching |

### 4.2 Expansion Markets (Post-MVP)

- Logistics companies (delivery notes, PODs)
- Insurance companies (claims documents)
- Banks and fintechs (KYC, bank statements)
- Government procurement (Phase 3)

### 4.3 Geographic Focus

- **Primary:** South Africa (ZAR, SARS compliance, POPIA)
- **Secondary:** Kenya, Nigeria, Ghana (Phase 2 localisation)
- **Tertiary:** Rest of Sub-Saharan Africa (Phase 3)

---

## 5. Value Proposition

### For Accounting Firms
> "Process your clients' invoices 10× faster with AI extraction and a one-click approval queue — no more copy-pasting into Xero."

### For SME Finance Teams
> "Stop paying your finance clerk to type invoice numbers. AfriDocs AI extracts, validates, and routes every invoice automatically, with a full audit trail."

### For Procurement Teams
> "Catch duplicate invoices, flag mismatched amounts, and close your month-end in days instead of weeks."

---

## 6. Success Metrics (Platform Level)

These are the platform-level outcomes that define success. Phase-specific metrics are defined in later documents.

| Metric | Target |
|--------|--------|
| Invoice extraction accuracy (field level) | ≥ 95% |
| End-to-end processing time (upload → extracted) | < 60 seconds |
| Human review rate (exceptions only) | < 20% of invoices |
| Approval cycle time reduction vs. baseline | ≥ 50% |
| Pilot organisation satisfaction (NPS) | ≥ 40 |
| Duplicate invoice detection rate | ≥ 98% |

---

## 7. What AfriDocs AI Is NOT

Clarifying scope prevents scope creep and investor confusion:

| Not This | Why |
|----------|-----|
| A general document management system (SharePoint replacement) | We process documents, not store them as a filing cabinet |
| An accounting/ERP system | We extract and route; the accounting system is the destination |
| A contract lifecycle management tool | Contracts are a Phase 2 document type |
| An RPA/bot-based scraper | We use structured AI extraction, not brittle screen scraping |
| A WhatsApp chatbot | WhatsApp is an ingestion channel, not the UI |

---

## 8. Competitive Landscape

| Competitor | Strength | Weakness | AfriDocs Advantage |
|------------|----------|----------|-------------------|
| Dext (Receipt Bank) | Mature, established | UK/EU focused; expensive for ZAR market | African-first pricing, POPIA compliance |
| AutoEntry | Good OCR | No workflow engine | Built-in approval flows |
| Microsoft Syntex | Deep M365 integration | Expensive; requires Azure licensing | No M365 lock-in |
| Docsumo | Strong extraction API | Developer tool, not end-user product | Full workflow + UI |
| Manual process | Free | Everything else | 10× speed, audit trail, fraud detection |

**Key differentiator:** AfriDocs AI is the only platform designed ground-up for African document types, currencies, tax codes (VAT/SARS), and compliance requirements (POPIA), with WhatsApp ingestion and ZAR/multi-currency support.

---

## 9. Assumptions Challenged

The following assumptions from the master brief were challenged during discovery:

| Assumption | Challenge | Decision |
|------------|-----------|----------|
| "Start with all document types" | Too broad for an MVP; validation metrics become meaningless | **Invoice-only MVP** |
| "WhatsApp ingestion from day one" | WhatsApp Business API requires Meta approval (2–4 weeks); blocks launch | **Email + upload first; WhatsApp Phase 2** |
| "Both Azure and AWS simultaneously" | Dual-cloud from day one doubles infrastructure complexity | **Azure primary; AWS documented for comparison** |
| "RAG from day one" | RAG requires a document corpus; no corpus exists at launch | **RAG is a Phase 2 feature** |
| "Kubernetes from day one" | Premature for a 2-week MVP; adds ops overhead with no benefit | **Docker Compose locally; Azure Container Apps for pilot** |

---

*Next document: [02-mvp-scope.md](./02-mvp-scope.md)*
