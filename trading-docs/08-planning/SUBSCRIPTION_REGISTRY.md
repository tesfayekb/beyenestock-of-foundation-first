# MarketMuse — Active Subscription Registry

**Owner:** tesfayekb
**Last verified:** 2026-05-04 evening (Polygon Indices Starter→Advanced upgrade post-incident closure; per `trading-docs/06-tracking/HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md`)
**Verification source:** BeyeneQuant trading console Subscriptions UI (`beyene.io/trading/subscriptions`) + operator confirmation of paid-tier statuses + external provider dashboards (massive.com, databento.com, unusualwhales.com) + Polygon dashboard tier-comparison view (screenshots dated 2026-05-04 evening, captured during Indices subscription upgrade)
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
| 8 | **Polygon.io — Indices Starter (CANCELLED 2026-05-04 evening)** | Starter | $49 (was monthly) | — (cancelled) | 15-min delayed indices (`I:SPX`, `I:VIX`, `I:VVIX`, `I:VIX9D`). **(CANCELLED 2026-05-04 evening — incident closure T-ACT-061; replaced by row 9 Indices Advanced.)** The 15-min delay was the structural cause of the 2026-05-01 → 2026-05-04 prediction outage (76 hours zero predictions). Outage trigger was PR #92 (T-ACT-046, 2026-05-02) flipping `polygon:spx:current.fetched_at` from wall-clock-now to upstream Polygon timestamp, exposing the tier-mandated 15-min delay to the 330s freshness guard at `prediction_engine.py:1366/1373`. Row preserved as historical record per registry §9 maintenance protocol. See `HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` for full diagnosis and `HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md` Appendix A.8 for the lessons-learned entry. |
| 9 | **Polygon.io — Indices Advanced** | Advanced | $99 | monthly | **ACTIVE 2026-05-04 evening** (subscribed by operator post-incident; replaced row 8 Indices Starter). **Real-time entitlement** per Polygon dashboard tier-comparison view ("Real-time Data" vs Starter's "15-min Delayed Data"). Covers all 10 codebase consumer sites (`I:SPX`, `I:VIX`, `I:VVIX`, `I:VIX9D` via `/v3/snapshot` + `/v2/aggs/ticker/I:.../range/...`). **Usage restriction: "Non-pros only"** — Polygon professional/non-professional exchange-licensing distinction. Operator currently qualifies as non-professional. **THIS CONSTRAINT MUST BE REVISITED IF THE SYSTEM:** (a) registers as a professional trader anywhere, (b) takes external capital, (c) runs on behalf of any entity beyond the individual operator, (d) is commercialized in any form (including paid SaaS, signal redistribution, etc.). In any of those cases, exchange fees apply and a different tier/agreement is required. Cross-reference §5 row "MarketMuse goes commercial / takes outside capital" — Indices Advanced now joins Stocks Advanced as a "Non-pros only" subscription requiring re-licensing review under that trigger. **Verification gate:** §7.1 manual API probe in `HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` (expected `age_seconds < 60s` during RTH); operator action pending — see TASK_REGISTER T-ACT-061 closure criteria. **Net cost change (this row only):** +$50/mo (Starter $49 cancelled → Advanced $99 subscribed). **Net cost change vs. T-ACT-050 full restructure target:** the full T-ACT-050 -$149/mo restructure ALSO required cancelling Stocks Advanced ($199/mo, row 2) — that step is **NOT yet executed**; Stocks Advanced remains active per operator's current state. Pending separate operator decision. |

**Total recurring data-subscription cost (current state 2026-05-04 evening, post-Indices-upgrade):** **~$712.42 / month** ($79 Options Developer + $199 Stocks Advanced + $199 Databento + $126 Unusual Whales + $10.42 Finnhub amortized + $0 NewsAPI + $0 Tradier sandbox + ~$0 Indices Starter cancelled + $99 Indices Advanced active). **Net change vs. pre-2026-05-04-evening state:** **+$50/mo** (Indices Starter $49 cancelled → Indices Advanced $99 subscribed; Stocks Advanced $199 unchanged). **Polygon line items current:** $79 Options Developer + $199 Stocks Advanced + $99 Indices Advanced = $377/mo on Polygon.

**Pending T-ACT-050 full-restructure target (NOT yet executed; separate operator decision):** Cancel row 2 Stocks Advanced ($199/mo) when Indices Advanced sufficiency is confirmed. Result: $79 Options Developer + $99 Indices Advanced = $178/mo on Polygon; total recurring data-subscription drops to ~$513.42/mo (net -$149/mo from 2026-05-04-evening current state, or net -$199/mo from pre-2026-05-04 state). **Gating:** operator's current state still consumes Stocks Advanced for Polygon News (15A) and cross-asset HYG/TLT/DXY (15D); cancellation requires re-confirming codebase usage post the 2026-05-02 night T-ACT-050 audit (10-callsite analysis showed I:* indices only, no News/cross-asset consumption — those features are deferred per AI_BUILD_ROADMAP §6 V0.2/V0.2 timing).

---

## 1A. Polygon Indices tier comparison matrix (added 2026-05-04 evening)

Source: operator's Polygon dashboard tier-comparison view, screenshots dated 2026-05-04 evening. This matrix is preserved here so that the entitlement question is answerable from this file alone, without re-loading Polygon's pricing page. Future Cursor/Claude sessions reasoning about Indices subscription sufficiency must verify against this matrix (or the live tier-description text on Polygon's pricing page if newer than this snapshot) — **NOT from memory or prior-session assumption** (per Appendix A.8 lessons-learned: subscription/entitlement claims about external services are present-day factual questions that require checking current tier-description language).

| Feature              | Basic ($0/m)      | Starter ($49/m)         | Advanced ($99/m)         |
|----------------------|-------------------|-------------------------|--------------------------|
| Tickers              | Limited           | All Index Tickers       | All Index Tickers        |
| API Calls            | 5/min             | Unlimited               | Unlimited                |
| Historical Data      | 1+ Year           | 1+ Year                 | 1+ Year                  |
| Timeframe            | End of Day        | 15-min Delayed          | **Real-time**            |
| Reference Data       | Yes               | Yes                     | Yes                      |
| Technical Indicators | Yes               | Yes                     | Yes                      |
| Minute Aggregates    | Yes               | Yes                     | Yes                      |
| Flat Files           | No                | Yes                     | Yes                      |
| WebSockets           | No                | Yes                     | Yes                      |
| — Min Aggregates     | No                | Yes                     | Yes                      |
| — Values             | No                | No                      | Yes                      |
| Snapshot             | No                | Yes                     | Yes                      |
| Usage Restrictions   | Individual Use    | Individual Use          | Individual Use, **Non-pros only** |

**Note:** Polygon Indices does not currently offer a "Developer" middle tier between Starter and Advanced; only the three paid options shown above (Basic / Starter / Advanced) appear in the dashboard comparison view as of 2026-05-04 evening. Earlier `HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` §7.3 Path A description ("Indices Developer / Advanced — ~$150-199/m incremental") referenced a Developer tier that does not exist; superseded by this matrix.

**Active selection (post-2026-05-04 evening):** Advanced — provides real-time entitlement required by the codebase's 330s freshness guard at `prediction_engine.py:1366/1373`. Starter cancellation removes the 15-min-delay structural mismatch that caused the 2026-05-01 → 2026-05-04 prediction outage (see Appendix A.8).

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
| **MarketMuse goes commercial / takes outside capital** | All "Non-pros only" subscriptions (Stocks Advanced row 2 **AND Indices Advanced row 9**) need re-licensing | Triggers entity-level review. Not imminent. **(2026-05-04 evening: Indices Advanced added to this trigger list — operator currently qualifies as non-professional; status change events in §1 row 9 description must surface this row.)** |

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

**ACTIVE (recurring) — current state 2026-05-04 evening:**
- Polygon Options Developer ($79)
- Polygon Stocks Advanced ($199) — **(pending T-ACT-050 cancellation gate; see §1 total-row commentary)**
- **Polygon Indices Advanced ($99)** — **NEW 2026-05-04 evening**, replaced Indices Starter $49 row 8; "Non-pros only" usage restriction
- Databento OPRA Standard ($199, includes historical from 2013-04-01)
- Unusual Whales ($126)
- Finnhub ($125/yr)
- NewsAPI (free tier, $0)
- Tradier sandbox (commission-only, $0)

**CANCELLED (preserved as historical record per §9 maintenance protocol):**
- Polygon Indices Starter ($49) — cancelled 2026-05-04 evening; row 8 retained for incident reconstruction (76-hour outage 2026-05-01 → 2026-05-04 traceable to this tier's 15-min delay structurally mismatched with codebase real-time assumption)

**DEFERRED (decision made, not pursuing):**
- Item 15E retail sentiment (V2+)
- Benzinga (Polygon News + NewsAPI covers)

**FORWARD-LOOKING (trigger-based):**
- Tradier funded brokerage account (live-money cutover)
- Re-evaluation of execution broker (if scope expands beyond 0DTE SPX)
- Re-licensing review (if MarketMuse goes commercial — now applies to **both** Stocks Advanced AND Indices Advanced "Non-pros only" tiers)
- T-ACT-050 full restructure (cancel Stocks Advanced once Indices Advanced sufficiency is confirmed; net -$149/mo from current state) — pending operator decision after §7.1 probe + first post-upgrade prediction cycle confirm Indices Advanced is delivering real-time

**Open decision pending on the data-subscription side as of 2026-05-04 evening:**
1. Whether to execute the T-ACT-050 full restructure (cancel Stocks Advanced) once Indices Advanced sufficiency is empirically confirmed. Gating: §7.1 probe + first successful post-upgrade RTH prediction cycle write to `trading_prediction_outputs`.

---

*End of Active Subscription Registry. Authoritative reference for in-repo agents (Cursor + Claude) and operator. Supersedes Master Forward Plan v1.2 Part 4 forward-framing. UI cross-reference: `src/pages/trading/SubscriptionsPage.tsx`.*
