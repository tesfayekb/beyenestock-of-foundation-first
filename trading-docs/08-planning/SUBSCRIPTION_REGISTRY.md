# MarketMuse — Active Subscription Registry

**Owner:** tesfayekb
**Last verified:** 2026-04-30
**Verification source:** BeyeneQuant trading console Subscriptions UI (`beyene.io/trading/subscriptions`) + operator confirmation of paid-tier statuses + external provider dashboards (massive.com, databento.com, unusualwhales.com)
**Supersedes:** Master Forward Plan v1.2 Part 4 "Subscription decisions" framing (which treated Polygon Stocks Advanced + Databento Historical OPRA as forward-looking; both now confirmed active).

---

## 1. Active data subscriptions

| # | Service | Tier | Cost / mo | Renewal | What it covers |
|---|---|---|---|---|---|
| 1 | **Polygon.io — Options Developer** | Standard | $79 | monthly | Historical options chains (4 yr), Greeks / IV / OI, reference data, corporate actions, technical indicators, minute aggregates. 15-min delayed quotes. Acceptable — historical/reference layer, NOT in live decision path. |
| 2 | **Polygon.io — Stocks Advanced** | Advanced | $199 | monthly | Real-time equities (no delay), 20+ yr historical, 100% market coverage, **Polygon News** bundled, cross-asset (HYG / TLT / DXY) — covers Items 15A + 15D. **Restriction:** Individual Use — Non-pros only. **(2026-05-02 night audit — T-ACT-050)** Operator audit identified codebase consumes ONLY I:* indices (zero stocks/options/news API per Cursor's 10-callsite analysis). Optimal restructure: cancel this subscription + add Polygon Indices Advanced ($99/mo) = -$120/mo on this row alone (Stocks Advanced $199 → Indices Advanced $99; combined with Indices Starter $49/mo cancellation = -$149/mo total). **Pending Monday execution after T-ACT-045 closes** to avoid compounding capability changes. |
| 3 | **Databento OPRA Standard** | Standard | $199 | 2026-06-01 | Real-time live OPRA tick stream + historical OPRA archive (from 2013-04-01, 12+ yr depth) + 11 schemas. Covers Item 15B + Item 8 OPRA Flow Alpha + Item 4 replay harness substrate. Direct Equinix NY4 capture, FPGA, nanosecond timestamps. |
| 4 | **Unusual Whales** | (operator's tier) | $126 | monthly | Options flow alerts (large unusual trades). Auxiliary signal source for `flow_agent`. |
| 5 | **Finnhub** | annual | $125/yr (~$10.42/mo) | annually | Economic calendar (FOMC / CPI / NFP) with consensus data. |
| 6 | **NewsAPI** | Free tier | $0 | — | Financial headlines for sentiment scoring (100 req/day limit). Item 15A historical news backfill (in addition to Polygon News bundled in Stocks Advanced). |
| 7 | **Tradier sandbox** | brokerage paper account | $0 | — | Order execution + paper trading. Real-time SPX index-options quotes (per Tradier's index-options exception). General equities/options 15-min delayed in sandbox. Commission-only billing (~$0.35/contract). |
| 8 | **Polygon.io — Indices Starter** | Starter | $49 | monthly | 15-min delayed indices (`I:SPX`, `I:VIX`, `I:VVIX`, `I:VIX9D`). **(2026-05-02 night audit — T-ACT-050)** Redundant with Stocks Advanced row 2 real-time coverage. Original purpose was Item 15A historical news backfill (per T-ACT-048 partial closure); empirically not consumed; row added now closes T-ACT-048 acceptance criterion #2. Recency note: TBD pending T-ACT-045 Monday re-run; per Polygon published policy 15-min delayed for I:* indices, but `/v3/snapshot` may serve real-time despite policy. **Cancel Monday after T-ACT-045 closes** as part of T-ACT-050 restructure. |
| 9 | **Polygon.io — Indices Advanced (TARGET REPLACEMENT — pending Monday execution; NOT yet active)** | Advanced | $99 (target) | monthly (target) | **(T-ACT-050 target replacement; not yet subscribed)** Real-time per Polygon dashboard tier table. Covers all 10 codebase consumer sites (`I:SPX`, `I:VIX`, `I:VVIX`, `I:VIX9D` via `/v3/snapshot` + `/v2/aggs/ticker/I:.../range/...`). Net effect post-restructure: cancel Stocks Advanced + Indices Starter ($248/mo total) → subscribe Indices Advanced ($99/mo) = -$149/mo savings = -$1,788/yr. **Operator action Monday after T-ACT-045 closes.** |

**Total recurring data-subscription cost (pre-restructure 2026-05-02):** **~$662 / month** ($79 + $199 + $199 + $126 + $10.42 amortized + $0 + $0 + $49 + $0). **(2026-05-02 night T-ACT-050 audit — corrected from earlier ~$613/mo figure which omitted Polygon Indices Starter $49/mo line item; row 9 Indices Advanced is target replacement, NOT current charge.)** **Polygon line items pre-restructure:** $199 Stocks Advanced + $79 Options Developer + $49 Indices Starter = $327/mo on Polygon. **Post-restructure (Monday execution): cancel Stocks Advanced + Indices Starter, subscribe Indices Advanced = $79 Options Developer + $99 Indices Advanced = $178/mo on Polygon (net -$149/mo); total recurring data-subscription cost drops from ~$662/mo to ~$513/mo.**

---

## 2. Operational recurring costs (NOT data subscriptions, but part of monthly burn)

| Item | Cost / mo | Use |
|---|---|---|
| **Railway hosting** | ~$20 (variable) | Backend hosting (`diplomatic-mercy` service in `friendly-peace` project) + container runtime. |
| **Supabase** | $25 | Database (trading positions, sessions, predictions) + storage for `ml-models` bucket. |
| **Lovable** | $25 | Frontend hosting and deployment. |
| **Redis (Railway)** | $5 | Agent briefs, feature flags, GEX data, session state. Included in Railway plan. |
| **Anthropic Claude API** | usage-based (~$50-100) | Powers `synthesis_agent.py` AI synthesis layer (628 LOC, dual-provider, primary path). |
| **OpenAI API** | usage-based (~$20-50, low volume) | Dual-provider fallback for AI synthesis. Set `AI_PROVIDER=openai` to switch. |
| **GitHub** | $0-4 | Repo hosting. |

**Combined operational + AI usage:** ~$145-230 / mo.

**Full all-in monthly burn:** **~$760-845 / month**.

---

## 3. Coverage map — canonical data items vs. active subscriptions

Per `AI_BUILD_ROADMAP.md` §6 + §7 + Master ROI Plan §0 pointer table.

### Section 15 — Data improvements

| Item | Description | Phase home | Subscription that covers it | Status |
|---|---|---|---|---|
| **15A** | Real-time news headlines in prediction context | Phase 4B (Item 6 V0.2) + Phase 5C (Item 11) | Polygon News (in Stocks Advanced) **+ NewsAPI free tier** | ✅ COVERED — ⚠ **(2026-05-02 night T-ACT-050 audit)** Polygon News (bundled in Stocks Advanced) coverage will be SUSPENDED upon Monday subscription restructure. NewsAPI free tier remains primary; re-upgrade-to-Stocks-Advanced-or-Polygon-News pattern when Item 15A activates V0.2 (90+ days out per AI_BUILD_ROADMAP §6). |
| **15B** | Options flow signals (block trades, sweeps, OPRA) | Phase 4C (IS Item 8) | Databento OPRA Standard | ✅ COVERED |
| **15C** | VIX full term structure (9D / 3M / 6M) | Phase 3E (Item 5 — surface features) | CBOE-sourced via existing Polygon | ✅ COVERED |
| **15D** | Cross-asset signals (HYG, TLT, DXY) | DEFERRED V0.1; flag for un-defer in V0.2 | Polygon Stocks Advanced | ✅ COVERED — un-defer eligible at V0.2 — ⚠ **(2026-05-02 night T-ACT-050 audit)** Cross-asset (HYG/TLT/DXY) coverage will be SUSPENDED upon Monday subscription restructure. Re-upgrade-to-Stocks-Advanced pattern when Item 15D un-defer V0.2 eligibility opens (120+ days out per AI_BUILD_ROADMAP §6). |
| **15E** | Retail sentiment (Reddit / Twitter) | DEFERRED V2+ per Master Plan §6 | — | ⏸️ DEFERRED (not pursuing) |

**Auxiliary flow signal:** Unusual Whales is active and feeds `flow_agent`. Treated as supplementary to Databento OPRA (not a primary substrate per AI-SPEC-008).

### Section 17 — Infrastructure (NOT data subscriptions)

| Item | Description | Owner |
|---|---|---|
| **17A** | Resend SMTP migration | Master ROI Plan Action 11 |
| **17B** | Edge Function deploy for Learning Dashboard | Master ROI Plan Action 12 |
| **17C** | Phase A LightGBM training pipeline automation | Self-hosted on Railway / existing infra |

---

## 4. Under evaluation (no decision committed)

| Service | Recommendation | Trigger to revisit |
|---|---|---|
| **Benzinga (~$199/mo)** | **Stay deferred.** Polygon News + NewsAPI provides over-coverage. | Only if a specific curation/quality gap surfaces during Phase 5C Item 11 build. |

---

## 5. Forward-looking subscription decisions (NOT yet active; trigger-based)

| Trigger | Subscription | Notes |
|---|---|---|
| **Live-money cutover** (post Path Y activation + operator capital deployment decision) | **Tradier funded brokerage account** OR alternative broker (IBKR / TastyTrade) | Funded brokerage gets real-time on non-SPX symbols. Independent of data-subscription decisions. |
| **If MarketMuse expands beyond 0DTE SPX** | Re-evaluate execution broker + data-feed coverage | Future strategy decision; not imminent. |
| **If equity API call volumes outgrow Stocks Advanced limits** | Polygon Stocks Currencies (~$2,000/mo) | Plan flags as OVERKILL for current scale. Stay on Advanced unless concrete throttling surfaces. |
| **MarketMuse goes commercial / takes outside capital** | All "Non-pros only" subscriptions (Stocks Advanced) need re-licensing | Triggers entity-level review. Not imminent. |

---

## 6. Material implications for governance docs

This registry's existence reconciles three governance gaps:

1. **Master Forward Plan v1.2 Part 4 "Subscription decisions"** — listed Polygon Stocks Advanced + Databento Historical OPRA as forward-looking. Both already active. This registry supersedes; future v1.3 of the docx will reframe.
2. **`MASTER_ROI_PLAN.md` §0 pointer table** — references this registry as the source-of-truth for active subscriptions.
3. **`AI_BUILD_ROADMAP.md` §6 data-improvements table** — Item 15D status changes from "DEFERRED V0.1 per Master Plan §6 out-of-scope" to "DEFERRED V0.1; covered by Stocks Advanced; eligible for un-defer at V0.2".
4. **`AUDIT_DISPOSITION_PLAN.md` `C-AI-004-4`** — chain archive substrate prerequisite is in place via Databento OPRA Standard historical access. Default option 3 (V0.1 advisory-only) is no longer the constrained path; option 2 (calibration-grade replay) is unlocked. Ratify at Action 5a / Action 6.

---

## 7. Cluster B / Cluster C data dependencies — verified covered

| Spec | Substrate need | Coverage |
|---|---|---|
| AI-SPEC-005 (Item 5 Vol Fair-Value) | HAR-RV training data + VIX term structure | ✅ Polygon Stocks Advanced historical 5-min + VIX |
| AI-SPEC-006 (Item 6 Meta-Labeler) | Multi-feature substrate from Items 1/2/4/5/7/10 | ✅ Bundled into upstream specs |
| AI-SPEC-008 (Item 8 OPRA Flow Alpha) | Real-time OPRA + historical OPRA archive | ✅ Databento OPRA Standard |
| AI-SPEC-009 (Item 9 Exit Optimizer) | Closed-trade path metrics from Item 10 V0.2 | ✅ Self-generated; no external sub needed |
| AI-SPEC-004 (Item 4 Replay Harness) | Chain archive substrate per `C-AI-004-4` | ✅ Databento OPRA Standard historical access UNLOCKS option-2 (calibration-grade). Default option-3 superseded. |

**Implication:** `C-AI-004-4` operator decision can be ratified to **option 2 (calibration-grade replay)** during Action 5a / Action 6 governance. The chain archive substrate is in place via Databento; default option-3 (V0.1 advisory-only) is no longer the constrained path.

---

## 8. UI cross-reference

This registry is the documentary source-of-truth. The user-facing display lives at:

- **Page:** `beyene.io/trading/subscriptions`
- **Code:** `src/pages/trading/SubscriptionsPage.tsx` (hard-coded `SERVICES` array)
- **Backend:** `supabase/functions/subscription-key-status/index.ts` (reads API key configuration from Railway env vars)

When this registry changes, the UI must be updated in lockstep. When the UI changes, this registry must be updated in lockstep. Treat both as a single coherent governance surface.

---

## 9. Maintenance protocol

- Update this file at **every subscription change** (new sub, cancellation, tier change, cost change).
- Update `src/pages/trading/SubscriptionsPage.tsx` `SERVICES` array in lockstep.
- When a subscription moves between section 1 / section 4 / section 5, surface the move in the next governance reconciliation PR.
- Treat this file as **authoritative** over Master Forward Plan Part 4.

---

## 10. Summary — what's done, what's deferred, what's forward-looking

**ACTIVE (recurring):**
- Polygon Options Developer ($79)
- Polygon Stocks Advanced ($199)
- Databento OPRA Standard ($199, includes historical from 2013-04-01)
- Unusual Whales ($126)
- Finnhub ($125/yr)
- NewsAPI (free tier, $0)
- Tradier sandbox (commission-only, $0)

**DEFERRED (decision made, not pursuing):**
- Item 15E retail sentiment (V2+)
- Benzinga (Polygon News + NewsAPI covers)

**FORWARD-LOOKING (trigger-based):**
- Tradier funded brokerage account (live-money cutover)
- Re-evaluation of execution broker (if scope expands beyond 0DTE SPX)
- Re-licensing review (if MarketMuse goes commercial)

**No remaining "decisions pending" on the data-subscription side as of 2026-04-30.**

---

*End of Active Subscription Registry. Authoritative reference for in-repo agents (Cursor + Claude) and operator. Supersedes Master Forward Plan v1.2 Part 4 forward-framing. UI cross-reference: `src/pages/trading/SubscriptionsPage.tsx`.*
