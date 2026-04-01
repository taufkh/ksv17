# Helpdesk Pending Backlog

Last updated: 2026-04-01  
Target database: `ksv17-dev`

This document lists items that are still pending and have not been developed yet in the current Helpdesk customization stream.

## 1. Recently Completed

### 1.1 Customer-facing knowledge publication workflow

Status:

- delivered

Delivered scope:

- publication state, review, approval, publication, and retirement workflow
- visibility by customer and support contract
- portal knowledge listing and article detail pages
- suggested knowledge on public ticket tracking pages
- helpful / not helpful feedback and deflection counters

### 1.2 Dispatch execution enhancement pack

Status:

- delivered

Delivered scope:

- pre-departure checklist enforcement before travel
- travel start, arrival, and departure execution timestamps
- evidence capture model with grouped dispatch proof records
- customer sign-off tracking
- service-report submission guardrails tied to dispatch execution readiness

### 1.3 Executive service review pack export

Status:

- delivered

Delivered scope:

- customer-level service review snapshot by selected period
- printable PDF service review pack for account and service-review meetings
- summary of operational, communication, dispatch, billing, contract, and renewal metrics
- customer smart buttons to generate and open historical review packs

### 1.4 Renewal forecast versus target and budget dashboard

Status:

- delivered

Delivered scope:

- monthly target master by overall scope and team
- forecast dashboard for target, budget, weighted pipeline, and revenue at risk
- target-versus-attainment visibility for renewal planning

### 1.5 Customer success playbooks and proactive renewal tasks

Status:

- delivered

Delivered scope:

- proactive customer-success playbook records by customer and contract
- quarterly review, adoption, renewal-readiness, and risk-recovery playbook types
- scheduled activities for owners when follow-up dates become due

### 1.6 Scheduled distribution for service review pack / executive export

Status:

- delivered

Delivered scope:

- recurring distribution setup by customer
- recipient list management
- automatic service-review PDF generation
- queued outbound email delivery with attachment linkage

## 2. Pending Items

### 2.1 Commercial renewal analytics enhancement

Status:

- delivered

Why it matters:

- renewal watchlist and sales handoff suggestion now exist
- commercial renewal health needs a dedicated view for pipeline value, revenue at risk, and follow-up aging

Delivered scope:

- renewal summary cards by risk and state
- expected renewal revenue and lost-renewal reporting
- aging analysis for overdue follow-up dates
- Customer Support Overview badge for renewal risk segmentation

Current pending state:

- no high-priority item remains in the original Helpdesk roadmap stream
- current backlog is now purely optional optimization or business-specific extension

### 2.2 Helpdesk modularization by centralized config

Status:

- delivered

Why it matters:

- custom Helpdesk scope is already broad and split across many addons
- runtime behavior is not yet consistently gated by config
- future maintenance will be safer if features can be controlled centrally and overridden per team where relevant

Current phase:

- Phase 1 audit completed in `addons/docs/helpdesk_modularization_phase1_audit.md`
- Phase 2 to Phase 5 implementation delivered for feature registry, centralized settings, runtime guards, menu/report entry-point gating, and database rollout in `ksv17-dev`
- detailed operational guide is available in `addons/docs/helpdesk_modular_config_guide.md`

Delivered scope:

- centralized Helpdesk feature registry via `helpdesk_feature_hub`
- global feature toggles exposed in `Settings > Helpdesk`
- runtime gating for cron, controller, API, business action, reporting menu, and review-pack PDF output
- initial team-level override support for features that already had stable team fields
- smoke test checklist documented in `addons/docs/helpdesk_modular_config_smoke_test_checklist.md`

Current pending state:

- no blocker remains for global feature enable/disable from config
- further team-level expansion is optional follow-up work, not part of the current blocker

## 3. Priority Recommendation

Recommended next implementation order if the stream continues:

1. executive service-review distribution tracking and delivery analytics
2. customer success scoring and health trend analytics
3. renewal target simulation and what-if planning

## 4. Reasoning for Prioritization

The current Helpdesk stack is already strong on intake, operation, governance, dispatch, field execution, reporting, self-service knowledge, release traceability, contract renewal monitoring, renewal planning, proactive customer success, and executive review automation.

What remains is no longer a missing core feature. Any next item is now an optimization layer.

That means future work should be chosen based on business preference rather than backlog urgency.
