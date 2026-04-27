# Item 13: Realized-vs-Modeled Drift Detection — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-26
**Tier:** V0.4 Maturation (6-12 months after V0.3)
**Architectural Role:** Slow calibration immune system. Detects drift, demotes authority, triggers recalibration. The final architecture item.
**Sources:** GPT Round 2 + Items 1-12 dependencies + Claude verification + GPT verification accept

---

## Architectural Commitment

**Item 13 is the slow calibration immune system of the architecture.**

It is NOT:
- Another prediction model
- A trade selector
- An intraday veto layer
- A safety control that operates at fast timescales

It IS:
- A metric monitor
- A statistical drift detector
- An authority demotion controller
- A recalibration trigger
- An operator alerting layer

**Strongest commitment:**

> Item 13 protects authority, not trades. When modeled edge stops matching realized outcomes, the system must lose authority before it loses money. Restoration requires evidence, not optimism.

**Timescale separation:**

```
Items 1, 11, 12 = intraday / daily safety controls
Item 13         = daily / weekly / monthly calibration health control
```

**Asymmetric authority rule:**

```
Item 13 CAN auto-demote authority.
Item 13 CANNOT materially auto-promote authority.
Restoration requires Item 4 validation + operator approval.
```

This asymmetry is the architectural keystone. Demotion is conservative; promotion is aggressive. When in doubt, reduce authority — never expand it.

---

## 1. Drift Inventory

### 1.1 LightGBM Drift

**Metrics:**
```
feature_distribution_psi
prediction_brier_score
directional_hit_rate
ece_direction_probability
prediction_distribution_shift
```

**Healthy ranges:**
```
core feature PSI < 0.10
Brier not >10% worse than baseline
ECE <= 0.08–0.10
directional hit rate not below baseline by >5 percentage points
```

**Severity thresholds:**
```
WARNING:  any core feature PSI > 0.10
          OR Brier +10%
          OR ECE > 0.10

ACTION:   PSI > 0.20
          OR Brier +20%
          OR ECE > 0.15
          OR hit rate below baseline by >8 points

CRITICAL: PSI > 0.30
          OR Brier +35%
          OR ECE > 0.22
          OR model worse than naive baseline over rolling window
```

Use existing 12L scaffolding; Item 13 makes it authority-aware.

### 1.2 Item 5 Vol Fair-Value Drift

**Metrics:**
```
HAR_RV_QLIKE_vs_EWMA
rv_forecast_error
iv_rv_ratio_realized_correlation
strategy_ev_residual
top_ev_bucket_vs_bottom_ev_bucket
skew_z_distribution_shift
```

**Severity thresholds:**
```
WARNING:  HAR-RV underperforms EWMA by >5% over 20 sessions
          OR EV residual < -0.02R
          OR top-bottom EV separation weakens below 0.20σ

ACTION:   HAR-RV underperforms EWMA by >10%
          OR EV residual < -0.05R
          OR top EV bucket not better than bottom bucket

CRITICAL: HAR-RV underperforms EWMA by >20%
          OR EV residual < -0.10R
          OR EV ranking inverted and worsens P&L
```

**Authority effect:**
```
WARNING:  no authority change
ACTION:   production → reduced
          Item 12 calibration_cap = 0.50
CRITICAL: advisory-only for affected strategy class
          long-vol authority disabled
```

### 1.3 Item 6 Meta-Labeler Drift

**Metrics:**
```
Brier score
Expected Calibration Error (ECE)
Wilson high-confidence loss rate
top_bucket_realized_utility
bottom_vs_top_bucket separation
bootstrap CI coverage
feature PSI
```

**Severity thresholds:**
```
WARNING:  ECE > 0.12
          OR Brier worsens >10%
          OR top bucket utility weak but still positive

ACTION:   ECE > 0.18
          OR Brier worsens >20%
          OR top bucket cumulative utility <= 0
          OR Wilson lower bound on useful-take rate deteriorates 
             materially

CRITICAL: ECE > 0.25
          OR Brier worse than prior baseline
          OR top bucket negative for 2 windows
          OR high-confidence trades losing persistently
```

**Authority effect:**
```
ACTION:   skip/reduce production → reduce-only or advisory
CRITICAL: advisory-only for affected strategy/time bucket
```

### 1.4 Item 1 Governor Drift

**Metrics:**
```
rolling_veto_value_R
false_veto_cost
useful_veto_rate
catastrophic_loss_capture_rate
block_rate
rules_disagreement_rate
LightGBM_disagreement_rate
decision_sensitivity_flip_rate
parse_failure_rate
latency_p95
```

**Severity thresholds:**
```
WARNING:  veto_value < +0.5R over rolling window
          OR false_veto_cost >45%
          OR sensitivity flip rate >15%
          OR block_rate >35% without clear veto value

ACTION:   veto_value <= 0 over minimum sample
          OR false_veto_cost >60%
          OR useful_veto_rate Wilson_lower_95 < 0.30
          OR sensitivity flip rate >25%

CRITICAL: veto_value < -2R
          OR false_veto_cost >80%
          OR costly blocks dominate useful blocks
          OR parse/validation failures >2% in session
          OR catastrophic loss missed by Governor
```

**Authority effect:**
```
ACTION:   production veto → reduced / paper-binding only
CRITICAL: advisory-only except hard fallback:
            no new short-gamma
            no opportunity lean
```

### 1.5 Slippage Model Drift

**Metrics:**
```
estimated_vs_actual_slippage_error
median_absolute_error
slippage_bias
regime_conditional_error
slippage_as_pct_of_edge
```

**Severity thresholds:**
```
WARNING:  MAE > $0.12
          OR bias > $0.06

ACTION:   MAE > $0.20
          OR bias > $0.10
          OR slippage consumes >35% of modeled edge

CRITICAL: MAE > $0.35
          OR bias > $0.20
          OR repeated underestimation causing realized losses
```

**Authority cascade:** Slippage drift demotes anything dependent on EV:
```
Item 5 strategy EV authority
Item 6 utility labels
Item 12 allocation confidence
```

### 1.6 Item 12 Candidate Scoring Drift

**Metrics:**
```
top_score_bucket_vs_bottom_score_bucket
candidate_score_rank_correlation_with_realized_utility
ranking_sensitivity_flip_rate
capital_efficiency
false_underallocation_cost
loss_avoided_from_deallocation
```

**Severity thresholds:**
```
WARNING:  top-bottom gap < 0.20σ
          OR sensitivity flip >15%

ACTION:   top-bottom gap <= 0
          OR sensitivity flip >25%
          OR false_underallocation_cost > loss_avoided

CRITICAL: ranking inverted
          OR Item 12 worsens drawdown or worst day
```

**Authority effect:**
```
ACTION:   dynamic allocation production → reduced
CRITICAL: phase ladder only; Item 12 advisory
```

### 1.7 Item 10 / Attribution Drift

**Metrics:**
```
counterfactual_pnl_after_slippage_bias
counterfactual_vs_realized_correlation
calibration_eligible_error_rate
legacy_row_leakage_count
strategy_utility_label_failure_rate
```

**Severity thresholds:**
```
WARNING:  label failure rate >5%
          OR counterfactual bias >0.03R

ACTION:   label failure rate >10%
          OR counterfactual bias >0.05R
          OR correlation near zero

CRITICAL: any legacy_observability_only row enters training
          OR calibration_eligible filter bypassed
          OR counterfactual labels proven structurally wrong
```

**Critical attribution drift stops downstream training immediately.**

### 1.8 Operator Override Drift

**Metrics:**
```
override_rate
operator_outperformance_R
operator_vs_system_outcome_delta
override_reason_distribution
```

**Severity thresholds (with sample-size safeguards):**
```
WARNING:  override_rate_weekly > 8%
          OR operator_outperformance > 5%
          OR >= 3 overrides in week when eligible_decisions < 25

ACTION:   override_rate_weekly > 15%
          OR operator_outperformance > 10%
          OR overrides cluster around one failure mode
          OR overrides improve outcomes in 2 consecutive review windows

CRITICAL: override_rate_weekly > 25%
          OR operator_outperformance > 15%
          OR repeated manual session halts caused by system-context 
             failure
          OR operator prevents loss system would have taken despite 
             multiple active filters
```

**Sample-size minimums:**
```
For outperformance thresholds:
  WARNING:  require at least 5 overrides
  ACTION:   require at least 10 overrides
  CRITICAL: require at least 15 overrides

If sample smaller: classify as 'operator_signal_observed', not 
full drift
```

**Definitions:**
```
override_rate = operator_overrides / eligible_system_decisions

operator_outperformance = 
  outcome_after_operator_action 
  - counterfactual_outcome_of_system_recommendation

operator_edge_R = 
  operator_realized_R - system_counterfactual_R
```

**Critical principle:**

> operator_outperformance is more important than override count.

If the operator repeatedly improves outcomes, the system is missing something. That should trigger Item 4 review, NOT be dismissed as discretionary noise.

---

## 2. Detection Methods

### 2.1 Distribution Shifts

```
PSI:
  binned continuous features
  best for production monitoring

KS test:
  raw continuous distributions
  useful diagnostic, not authority trigger alone

Jensen-Shannon divergence:
  categorical distributions
  regime, event_class, strategy mix, time_bucket

KL divergence:
  research diagnostic only; too unstable for small samples
```

**Production default:**
```
PSI for numeric features
JS divergence for categorical features
```

### 2.2 Calibration Drift

```
ECE: probability calibration
Brier score: probability quality
Brier decomposition: reliability vs resolution
Wilson intervals: sparse event rates
Hosmer-Lemeshow: optional diagnostic, not binding authority trigger
```

### 2.3 Performance Drift (V0.4 Default: Z-Score)

V0.4 ships rolling z-score with regime-conditional comparison. NOT Page-Hinkley (too opaque).

**Formula:**
```
rolling_z = (current_metric - rolling_mean_60d) / rolling_std_60d
```

**Severity triggers:**
```
WARNING:  |z| > 2.0 for 3 observations

ACTION:   |z| > 2.5 for 5 observations
          OR current 20-trade window mean deviates by >1.5σ from 
             60-trade baseline

CRITICAL: |z| > 3.0 with realized P&L harm
          OR known data contamination
```

**Regime-conditional comparison:**
```
ordinary vs ordinary
event vs event
opex vs opex
high_vol vs high_vol
```

Do NOT compare FOMC-week volatility behavior to ordinary low-volatility weeks.

**V0.5+ research:**
```
Bayesian online change-point detection (BOCPD)
Only add if V0.4 z-score logic too slow or too noisy
```

### 2.4 Concept Drift

The most dangerous drift type:
```
prediction error worsens while feature distributions remain stable
```

The world changed; inputs look normal. Detected through prediction error analysis combined with stable feature distributions.

---

## 3. Severity Tiers and Authority Flips

### Three-Tier Model

#### WARNING

```
Condition:
  one metric crosses mild threshold
  sample size sufficient

Action:
  log drift_alert
  no authority change
  appears in daily/weekly digest
```

#### ACTION

```
Condition:
  same warning persists 2 windows
  OR two related metrics degrade in same item
  OR one action-level threshold crosses

Action:
  create new item_promotion_records row:
    authority_level: reduced or advisory
    is_current: true
    supersedes prior record
  
  Item 12 calibration_cap = 0.50
  Item 4 recalibration candidate scheduled
  operator notified within 24h
```

#### CRITICAL

```
Condition:
  severe threshold crossed
  OR realized P&L harm from drift
  OR data contamination / training leakage

Action:
  immediate demotion: production/reduced → advisory or disabled
  Item 12 calibration_cap = 0.25 or 0.00
  immediate operator alert
  Item 4 recalibration run triggered
```

### Auto-Demote / Never Auto-Promote

```
Item 13 CAN auto-demote authority.
Item 13 CANNOT auto-promote authority.

Restoration requires:
  Item 4 validation pass
  AND operator approval
```

---

## 4. Auto-Restoration Rules (Warning-Level Only)

### Strict Conditions

**No auto-restoration for ACTION or CRITICAL demotions.**

For WARNING-only states:

```
If WARNING produced dashboard warning only:
  auto-clear after 4 consecutive healthy windows

If WARNING produced temporary reduced authority:
  restore to PRIOR LEVEL ONLY if all conditions pass:
    - original demotion was WARNING only
    - metric healthy for 4 consecutive detection windows
    - no related drift signals fired
    - Item 4 baseline is current within 90 days
    - no realized P&L harm during warning period
    - operator receives restoration notice
```

### No Skipping Levels

```
reduced → prior production level only
advisory → reduced only if prior level was reduced
```

### Audit Trail

Every auto-restoration writes:
```
item_promotion_records (new is_current=true row)
drift_alerts.status = resolved_auto_warning
audit_reason = warning_cleared_4_windows
```

---

## 5. Detection Windows and Cadence

### Per-Item Specifications

```
LightGBM:
  window: rolling 50 predictions, 20 sessions preferred
  cadence: weekly + after model retrain
  minimum: 30 for warning, 50 for action

Item 5 Vol Engine:
  window: rolling 20 sessions for RV, 30 strategy EV candidates
  cadence: daily EOD metrics, weekly authority review
  minimum: 20 forecast observations

Item 6 Meta-Labeler:
  window: rolling 50 candidates or 30 actual trades minimum
  cadence: weekly
  minimum: 30 for warning, 50 for action

Item 1 Governor:
  window: rolling 50 decisions, minimum 10 veto/reduce
  cadence: weekly + immediate after catastrophic miss
  minimum: 30 for warning, 50 for action

Slippage:
  window: rolling 30 fills, strategy bucket minimum 10 fills
  cadence: daily EOD
  minimum: 20 fills global

Item 12 allocation:
  window: rolling 50 candidates, 20 sessions
  cadence: weekly

Attribution / counterfactual:
  window: rolling 30 calibration-grade counterfactuals
  cadence: weekly diagnostics, monthly authority review

Operator overrides:
  window: weekly + rolling 20 eligible decisions
  cadence: weekly
```

### Detection Latency Targets

Item 13 must detect drift within these latencies:

```
CRITICAL drift:
  detect within 24 hours of first confirmed occurrence
  Examples:
    training contamination: same day / next EOD
    slippage underestimating by >80% of edge: within 24h

ACTION drift:
  detect within 5–7 trading days of onset
  Example: meta-labeler top bucket turning unprofitable

WARNING drift:
  detect within 15–20 trading days of onset
  Example: feature PSI creeping above threshold
```

These targets become validation criteria for Item 13 itself in quarterly review.

---

## 6. Recalibration Workflow

### Warning

```
alert only
no automatic recalibration
review in weekly drift digest
```

### Action

```
1. Item 13 creates drift_alert
2. New item_promotion_records row demotes affected item
3. Item 12 sees authority degradation, reduces calibration_cap
4. Item 4 recalibration candidate scheduled
5. Operator reviews recalibration output
6. Restoration requires Item 4 pass + operator approval
```

### Critical

```
1. Immediate authority demotion
2. Operator alert immediately
3. Item 4 recalibration starts automatically if data available
4. NO auto-promotion even if recalibration passes
5. Operator must approve restoration
```

### Repeated Recalibration Failures

```
2 failed recalibrations in a row:
  demote one additional level

3 failed recalibrations within 90 days:
  disabled or diagnostic_only
  operator postmortem required
```

---

## 7. False Positive Mitigation

### Confirmation Requirements

```
WARNING:  one window enough

ACTION:   two consecutive warnings
          OR two related metrics degrade
          OR one action-level metric

CRITICAL: one severe metric with realized risk impact
          OR data contamination
          OR hard operational failure
```

### Sample Minimums

No authority change unless sample threshold met. If sample too small:
```
status = insufficient_sample
no demotion unless critical operational failure
```

### Event-Regime Separation

Compute drift separately for each regime:
```
ordinary
scheduled_event
unscheduled_event
opex
high_vol
low_vol
```

FOMC week may look like drift in ordinary metrics. That should be classified as event-regime behavior, NOT automatic model failure.

### Cooldowns

```
Same alert fingerprint:
  warning cooldown = 5 trading days
  action cooldown = 10 trading days
  critical = no cooldown but deduplicated
```

### Operator False-Positive Marking

```
Operator can mark:
  false_positive
  known_event_regime
  data_vendor_artifact
  expected_transition

Does NOT erase the alert. Becomes part of future review.
```

---

## 8. Drift Attribution and Dependency Graph

### Dependency Graph (V0.4)

```
LightGBM → Governor (Item 1)

Vol Engine (Item 5) → Meta-Labeler (Item 6)
Vol Engine (Item 5) → Item 12 candidate scoring

Meta-Labeler (Item 6) → Item 12 candidate scoring

Slippage → Vol Engine (Item 5)
Slippage → Meta-Labeler (Item 6)
Slippage → Counterfactual / Attribution (Item 10)
Slippage → Item 12 allocation

Attribution / Item 10 → Meta-Labeler training labels
Attribution / Item 10 → Governor veto-value measurement

OPRA Flow (Item 8) → Vol Engine
OPRA Flow (Item 8) → Meta-Labeler
OPRA Flow (Item 8) → Governor summaries
```

### Attribution Algorithm

When drift fires for item X:
```
1. Check active upstream drift alerts
2. If upstream alert exists:
     mark X drift as downstream_consequence
3. Prioritize upstream remediation
4. Demote downstream ONLY if it creates immediate trading risk
5. Suppress duplicate downstream alert spam
```

### Operator Notification Format

```
Root cause candidate:
  Vol Engine EV residual drift.

Downstream symptoms:
  Meta-Labeler top bucket utility deteriorating.
  Item 12 candidate ranking weakening.

Recommended action:
  Review Vol Engine first; keep downstream alerts linked.
```

### Schema Additions to drift_alerts

```sql
root_cause_candidate_item TEXT
downstream_consequence BOOLEAN NOT NULL DEFAULT false
upstream_alert_ids UUID[]
dependency_path TEXT[]
alert_group_id UUID
```

---

## 9. Meta-Drift Prevention

### No Item 14

Item 13 reviews itself through quarterly policy review, NOT automated threshold learning.

### drift_policy_versions Table

```sql
CREATE TABLE drift_policy_versions (
  policy_version TEXT PRIMARY KEY,
  thresholds_json JSONB NOT NULL,
  rationale TEXT NOT NULL,
  approved_by TEXT NOT NULL,
  effective_from TIMESTAMPTZ NOT NULL,
  retired_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Quarterly Meta-Review

Required metrics:
```
median_detection_latency_by_severity
missed_drift_count
late_detection_count
false_positive_count
authority_demotions_validated_by_Item4
demotions_later_reversed_as_false_positives
operator_alert_burden
```

### If Item 13 Misses Latency Targets

```
drift_policy_version must be reviewed
threshold adjustments documented
new policy_version created with rationale
```

---

## 10. Alert Fatigue Prevention

### Severity-Based Routing

```
WARNING:
  daily digest only
  dashboard badge
  no immediate interruption

ACTION:
  same-day notification
  operator review within 24h
  appears in weekly report

CRITICAL:
  immediate notification
  dashboard red state
  trading authority already demoted
  operator acknowledgement required
```

### Deduplication

```
Dedup key: item_id + metric_name + severity + regime_bucket
```

### Rate Limits

```
max 3 warning alerts per item per week
max 1 action alert per item per day
critical alerts grouped if same root cause
```

### Alert Lifecycle

```
open
acknowledged
recalibration_scheduled
resolved
false_positive
suppressed_known_regime
```

---

## 11. Schema: New Tables

### drift_metric_snapshots

```sql
CREATE TABLE drift_metric_snapshots (
  id UUID PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  item_id TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  metric_value NUMERIC NOT NULL,
  baseline_value NUMERIC NOT NULL,
  window_type TEXT NOT NULL,
  window_size INTEGER NOT NULL,
  sample_size INTEGER NOT NULL,
  regime_bucket TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN (
    'healthy', 'warning', 'action', 'critical'
  )),
  policy_version TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_drift_metrics_item_time 
  ON drift_metric_snapshots(item_id, timestamp);
CREATE INDEX idx_drift_metrics_severity 
  ON drift_metric_snapshots(severity, timestamp) 
  WHERE severity IN ('warning', 'action', 'critical');
```

### drift_alerts

```sql
CREATE TABLE drift_alerts (
  alert_id UUID PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  item_id TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN (
    'warning', 'action', 'critical'
  )),
  regime_bucket TEXT NOT NULL,
  observed_value NUMERIC NOT NULL,
  threshold_value NUMERIC NOT NULL,
  sample_size INTEGER NOT NULL,
  authority_action TEXT,
  promotion_record_id UUID NULL REFERENCES item_promotion_records(promotion_id),
  
  -- Dependency analysis
  root_cause_candidate_item TEXT,
  downstream_consequence BOOLEAN NOT NULL DEFAULT false,
  upstream_alert_ids UUID[],
  dependency_path TEXT[],
  alert_group_id UUID,
  
  -- Lifecycle
  status TEXT NOT NULL CHECK (status IN (
    'open',
    'acknowledged',
    'recalibration_scheduled',
    'resolved',
    'resolved_auto_warning',
    'false_positive',
    'suppressed_known_regime'
  )) DEFAULT 'open',
  operator_notes TEXT,
  audit_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_drift_alerts_open 
  ON drift_alerts(status, severity, timestamp DESC) 
  WHERE status IN ('open', 'acknowledged');
CREATE INDEX idx_drift_alerts_group 
  ON drift_alerts(alert_group_id);
```

### drift_policy_versions

```sql
CREATE TABLE drift_policy_versions (
  policy_version TEXT PRIMARY KEY,
  thresholds_json JSONB NOT NULL,
  rationale TEXT NOT NULL,
  approved_by TEXT NOT NULL,
  effective_from TIMESTAMPTZ NOT NULL,
  retired_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 12. V0.4 Ship Scope

### V0.4 Required

```
1. CREATE TABLE drift_metric_snapshots
2. CREATE TABLE drift_alerts (with dependency fields)
3. CREATE TABLE drift_policy_versions
4. backend/drift_detector.py (main orchestrator)
5. backend/drift_metric_collectors.py (8 per-item collectors)
6. backend/drift_severity_evaluator.py (three-tier classification)
7. backend/drift_attribution_engine.py (dependency graph traversal)
8. backend/drift_alert_router.py (severity-based notifications)
9. backend/drift_authority_demoter.py (writes item_promotion_records)
10. backend/drift_auto_restorer.py (warning-only auto-clear logic)
11. Quarterly meta-review dashboard
```

### Authority Automation in V0.4

```
Warning: no authority change (alerts only)
Action:  automated demotion to reduced
         operator notified
Critical: automated demotion to advisory/disabled
          immediate operator alert
Restoration: NEVER automatic for ACTION/CRITICAL
             auto-clear allowed for WARNING-only states
```

### V0.5+ Defers

```
- ML-based drift detector
- Cross-item causal drift analysis (beyond V0.4 dependency graph)
- Automatic retraining / deployment
- Bayesian online change-point detection
- Counterfactual attribution drift full automation
- Operator-behavior modeling
```

### Never Build

```
- Auto-promotion of demoted items (always operator-approved)
- Item 14 (meta-monitor of Item 13)
- Real-time drift detection that competes with intraday safety
- Drift detection that bypasses event-regime separation
- Threshold auto-tuning without operator review
```

---

## 13. Failure Mode Analysis

### Failure Mode 1: False Positives Demoting Healthy Items

```
Symptom: production items demoted unnecessarily, alert fatigue
Mitigation:
  confirmation requirements (multiple windows or metrics)
  sample-size minimums
  event-regime separation
  cooldowns on same alert fingerprint
```

### Failure Mode 2: Slow Detection of Real Drift

```
Symptom: drift exists but Item 13 doesn't catch it in time
Mitigation:
  detection latency targets (24h/5-7d/15-20d)
  quarterly meta-review tracks missed_drift_count
  policy versioning supports threshold tightening
```

### Failure Mode 3: Operator Alert Fatigue

```
Symptom: operator ignores alerts due to volume
Mitigation:
  severity-based routing (warning to digest, critical immediate)
  rate limits per item
  alert_group_id for related downstream symptoms
  operator can mark false_positive
```

### Failure Mode 4: Cascade of Demotions

```
Symptom: upstream drift demotes multiple downstream items
Mitigation:
  dependency graph attribution
  prioritize upstream remediation
  suppress downstream alerts when upstream is root cause
  demote downstream only if immediate trading risk
```

### Failure Mode 5: Operator Outperformance Dismissed as Noise

```
Symptom: operator consistently improves outcomes; system 
         dismisses as discretionary noise; real drift goes 
         unnoticed
Mitigation:
  operator_outperformance is first-class drift signal
  R-unit measurement of operator vs system counterfactual
  ACTION-level demotion when operator outperforms by >10%
```

---

## 14. Expected ROI Contribution

### Mature Direct Contribution

```
+1% to +3% annual full-account ROI
```

### Bull Case

```
+3% to +5% if catches one major regime/model degradation 
before bad trading stretch
```

### Mechanism

```
prevents silent calibration decay
reduces oversized trading during degraded model states
forces recalibration before drift compounds
preserves operator wisdom signal
```

### Negative Case

```
too many false positives
unnecessary demotions
missed profitable trades due to alert noise
operator override drift dismissed as noise
```

The confirmation logic, sample-size safeguards, dependency analysis, and quarterly meta-review are the safeguards.

---

## 15. Final Architectural Statement

**Item 13 protects authority, not trades.**

When modeled edge stops matching realized outcomes, the system must lose authority before it loses money. Restoration requires evidence, not optimism.

The architectural keystone is the asymmetric authority rule:
```
Auto-demote: yes (conservative)
Auto-promote: never materially (aggressive)
```

This asymmetry compounds correctly. Demotion errs toward safety; promotion errs toward caution. The system can never accelerate into trouble through automated authority changes — it can only decelerate. Restoration always requires human review of empirical evidence.

The eight monitored items (LightGBM, Vol Engine, Meta-Labeler, Governor, Slippage, Item 12, Attribution, Operator Overrides) cover every calibrated component. The dependency graph ensures alerts focus on root causes, not downstream symptoms. The quarterly meta-review prevents Item 13 from drifting itself.

**Item 13 is the slow immune system that protects the architecture from silent decay.** Items 1-12 build mechanisms; Item 13 ensures those mechanisms are still working as designed. Without Item 13, the architecture appears to operate normally while underlying signal quality degrades — exactly the failure mode that compounds losses before becoming visible.

---

*Spec produced through GPT-5.5 Pro Round 2 + Items 1-12 dependencies + Claude verification + GPT verification accept on 2026-04-26. Locked after one full audit round plus verification. Final architecture item — V0.4 architecture is now fully specified.*
