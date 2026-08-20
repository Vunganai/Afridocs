# AfriDocs AI — MVP Scope

**Document:** 02-mvp-scope.md  
**Phase:** 1 — Product Discovery & Requirements  
**Status:** Final  
**Date:** 2026-08-20  

---

## 1. MVP Philosophy

The MVP answers one question for one user in one workflow:

> **"Can a finance clerk upload an invoice and have the key fields extracted, validated, and routed for approval — without touching a keyboard?"**

Everything in scope serves that question. Everything else is explicitly out of scope.

This discipline protects against the most common SaaS failure mode: building a feature-complete product that no one has validated actually solves the problem.

---

## 2. MVP Boundary — In Scope

### 2.1 Document Type
**Invoices only.** This means:
- Tax invoices (SARS-compliant, South African format)
- Standard supplier invoices (any format, any currency)
- PDF, scanned PDF, and image files (JPG, PNG, TIFF)

Not in scope: contracts, purchase orders, delivery notes, bank statements, ID documents.

### 2.2 Ingestion Channels
| Channel | MVP | Post-MVP |
|---------|-----|----------|
| Manual upload (drag & drop, file picker) | ✅ | — |
| Email ingestion (dedicated inbox) | ✅ | — |
| API upload | ✅ | — |
| WhatsApp document forwarding | ❌ | Phase 2 |
| ERP push integration | ❌ | Phase 2 |

Email ingestion is included because pilot users receive most invoices via email and manual re-upload would break adoption.

### 2.3 AI Processing Pipeline
| Step | MVP | Notes |
|------|-----|-------|
| File validation (MIME, size, malware) | ✅ | Security gate — non-negotiable |
| OCR (text extraction from PDF/image) | ✅ | Azure AI Document Intelligence |
| Document classification (is this an invoice?) | ✅ | Reject non-invoices with explanation |
| Structured field extraction | ✅ | See field list in §2.4 |
| Extraction confidence scoring | ✅ | Per-field confidence 0.0–1.0 |
| Business rule validation | ✅ | See §2.5 |
| Duplicate detection | ✅ | Hash + invoice number + supplier |
| Anomaly flagging | ✅ | Basic: missing fields, zero amounts |
| Summarisation (LLM) | ❌ | Phase 2 |
| Semantic search / RAG | ❌ | Phase 2 |
| Multi-document correlation (PO matching) | ❌ | Phase 2 |

### 2.4 Extracted Invoice Fields

These are the fields extracted in the MVP. Each field has a confidence score. Fields below threshold go to human review.

| Field | Required | Validation |
|-------|----------|-----------|
| `invoice_number` | Yes | Non-empty; unique per supplier per tenant |
| `invoice_date` | Yes | Valid date; not future-dated beyond 7 days |
| `due_date` | No | If present, must be ≥ invoice_date |
| `supplier_name` | Yes | Non-empty |
| `supplier_vat_number` | No | If present, format: ZA + 10 digits (SARS) |
| `supplier_email` | No | If present, valid email format |
| `supplier_bank_account` | No | Stored but not validated in MVP |
| `line_items` | No | Array of {description, qty, unit_price, total} |
| `subtotal` | No | If present, must match sum of line items ±0.05 |
| `vat_amount` | No | If present, must equal subtotal × VAT rate ±0.05 |
| `total_amount` | Yes | Non-empty; > 0 |
| `currency` | Yes | ISO 4217 code; defaults to ZAR |
| `payment_terms` | No | Free text; e.g., "30 days" |
| `purchase_order_ref` | No | Cross-reference only; no PO matching in MVP |

### 2.5 Business Rule Validations (MVP)

| Rule | Action on Failure |
|------|------------------|
| Total amount > 0 | Reject extraction; route to human review |
| Invoice number not blank | Route to human review |
| Duplicate: same invoice_number + supplier for this tenant | Flag as DUPLICATE; block approval; notify reviewer |
| Extraction confidence < 0.80 on any required field | Route entire document to human review |
| VAT amount inconsistency > 5% | Flag as WARNING; still route to approval |
| File size > 20 MB | Reject at upload |
| MIME type not PDF/JPG/PNG/TIFF | Reject at upload |

### 2.6 Workflow Engine (MVP)

The MVP supports a **single fixed approval workflow**:

```
Upload → Process → [Auto-approved if confidence ≥ 0.95 and no flags]
                 → [Human review queue if flags or low confidence]
                        ↓
               Reviewer approves / rejects / corrects
                        ↓
               Manager approves (if amount > tenant threshold)
                        ↓
               APPROVED → ready for export
```

MVP workflow constraints:
- Maximum 2 approval levels
- Approval threshold (amount requiring manager sign-off) is configurable per tenant
- No custom routing rules — those are Phase 2
- No escalation timers — those are Phase 2

### 2.7 Human Review Interface
| Feature | MVP |
|---------|-----|
| Review queue with document list | ✅ |
| Side-by-side: original PDF + extracted fields | ✅ |
| Edit any extracted field inline | ✅ |
| Approve / Reject / Request correction | ✅ |
| Add reviewer comment | ✅ |
| Bulk actions | ❌ Phase 2 |
| Mobile-optimised review | ❌ Phase 2 |

### 2.8 Search
| Feature | MVP |
|---------|-----|
| Search by invoice number | ✅ |
| Search by supplier name | ✅ |
| Filter by date range | ✅ |
| Filter by status (pending, approved, rejected) | ✅ |
| Filter by amount range | ✅ |
| Full-text search (document content) | ❌ Phase 2 |
| Semantic / AI search | ❌ Phase 2 |

### 2.9 Export & Integration
| Feature | MVP |
|---------|-----|
| Export to CSV | ✅ |
| Export to JSON | ✅ |
| Webhook on approval event | ✅ |
| Xero integration | ❌ Phase 2 |
| QuickBooks integration | ❌ Phase 2 |
| Sage integration | ❌ Phase 2 |

### 2.10 Multi-Tenancy & Auth
| Feature | MVP |
|---------|-----|
| Multiple organisations (tenants) | ✅ |
| Row-level security (data isolation) | ✅ |
| Email + password auth | ✅ |
| Google OAuth | ✅ |
| MFA | ❌ Phase 2 |
| SSO / SAML | ❌ Phase 2 |
| Roles: Admin, Reviewer, Approver, Viewer | ✅ |
| Custom roles | ❌ Phase 2 |

### 2.11 Reporting & Dashboard
| Feature | MVP |
|---------|-----|
| Invoices processed count (7d, 30d) | ✅ |
| Processing pipeline status | ✅ |
| Pending review queue depth | ✅ |
| AI extraction accuracy (self-reported) | ✅ |
| Cost per document estimate | ❌ Phase 2 |
| SLA metrics | ❌ Phase 2 |
| Custom reports | ❌ Phase 2 |

---

## 3. Explicit Out-of-Scope (MVP)

The following are **confirmed out of scope for the MVP**. Any request to include them must go through a scope change decision.

| Feature | Rationale |
|---------|-----------|
| Contract processing | Different extraction schema; different workflow |
| Purchase order processing | Requires 3-way match logic |
| Delivery note processing | Requires PO linkage |
| Bank statement reconciliation | High complexity; separate product line |
| WhatsApp ingestion | Meta API approval delay; adds mobile complexity |
| Xero / QuickBooks push | Integration testing extends timeline significantly |
| Kubernetes deployment | Premature; Docker Compose + Azure Container Apps is sufficient |
| RAG / document Q&A | No corpus at launch; requires embeddings pipeline |
| Mobile app | Web-responsive is sufficient for pilot |
| Advanced analytics | No data yet; analytics improve with usage volume |
| Multi-language UI | English only for SA pilot |
| Multi-currency VAT rules | ZAR/SARS rules only for MVP |

---

## 4. MVP Success Criteria

The MVP is considered **successful** when all of the following are true:

| Criterion | Threshold | How Measured |
|-----------|-----------|-------------|
| At least 3 pilot organisations onboarded | 3 tenants | Platform database |
| Invoice extraction field accuracy | ≥ 95% average across all required fields | Evaluation dataset (see §5) |
| End-to-end processing time | < 60 seconds from upload to extracted+validated | Timing logs |
| Human review rate | < 20% of processed invoices | Platform metrics |
| Zero data leakage between tenants | 0 incidents | Security audit + pen test |
| Approval workflow completes successfully | 100% of approved invoices have audit trail | Database audit log |
| Pilot user retention after 2 weeks | ≥ 2 of 3 pilots still active | Login logs |

---

## 5. AI Evaluation Dataset (MVP)

Before launch, a ground-truth evaluation dataset must be assembled:

| Dataset | Size | Source |
|---------|------|--------|
| South African tax invoices (varied suppliers) | 50 documents | Synthetic + real (anonymised) |
| Scanned invoices (low quality) | 20 documents | Camera-captured tests |
| Handwritten/hybrid invoices | 10 documents | Edge case tests |
| Non-invoice documents (should be rejected) | 20 documents | Receipts, statements, contracts |
| **Total** | **100 documents** | — |

Each document has a ground-truth JSON file with the correct field values. Extraction results are scored against this ground truth before any production traffic.

**Minimum bar:** ≥ 95% field-level accuracy on the 50 SA tax invoice set before go-live.

---

## 6. MVP Timeline (Target)

| Week | Focus | Exit Criteria |
|------|-------|--------------|
| **Week 1** | Infrastructure setup, auth, file upload, AI pipeline | Invoice can be uploaded and extracted end-to-end in dev |
| **Week 2** | Review UI, approval workflow, search, export, evaluation | All MVP success criteria met; 1 pilot org live |

**Critical path items** (any of these slipping delays the whole timeline):
1. Azure AI Document Intelligence provisioning and quota approval
2. Azure OpenAI GPT-4o model deployment and quota
3. Supabase project setup and RLS policies
4. Pilot organisation recruitment (need at least 1 committed before Week 2)

---

## 7. Decisions Required Before Development Starts

| Decision | Owner | Deadline | Options |
|----------|-------|----------|---------|
| Azure vs AWS for AI services | Tech lead | Before Phase 3 | Azure (preferred), AWS, both |
| Supabase vs self-hosted Postgres | Tech lead | Before Phase 3 | Supabase (preferred), Azure PostgreSQL |
| Celery+Redis vs Supabase background jobs | Tech lead | Before Phase 3 | Celery (preferred for visibility), Supabase |
| Pricing model for pilot | Product/business | Before pilot outreach | Free pilot, usage-based, flat fee |
| Data residency for SA pilot | Legal/tech | Before onboarding | Azure South Africa North region |

---

*Previous: [01-vision.md](./01-vision.md) | Next: [03-user-personas.md](./03-user-personas.md)*
