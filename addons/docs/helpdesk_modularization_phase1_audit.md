# Helpdesk Modularization Phase 1 Audit

Last updated: 2026-04-01  
Target database: `ksv17-dev`

## 1. Goal

This audit maps every custom Helpdesk addon into a modularization blueprint so the next implementation phase can make features:

- accessible from centralized settings
- overridable per team when needed
- safe to disable without uninstalling the addon
- consistent in cron, controller, hook, and UI behavior

This phase does not change code yet. It defines the target config contract.

## 2. Key Findings

- 30 Helpdesk-related custom addons were audited.
- 5 Helpdesk addons already expose `res.config.settings`: `helpdesk_mgmt_extended`, `helpdesk_custom_portal`, `helpdesk_custom_whatsapp`, `helpdesk_custom_api`, and `helpdesk_custom_claude_ai`.
- 23 Helpdesk addons define `post_init_hook`; most are demo/bootstrap oriented, but a few also set runtime defaults or create operational records.
- 7 Helpdesk addons define `ir.cron` schedules and therefore need hard runtime guards first.
- 4 addons already extend `helpdesk.ticket.team` and are natural candidates for team-level override: `helpdesk_mgmt_extended`, `helpdesk_custom_portal`, `helpdesk_custom_invoice`, and `helpdesk_custom_claude_ai`.
- The highest-risk runtime cluster is `portal -> whatsapp -> api -> communication log`, because these modules expose controllers, background jobs, or external integrations.

## 3. Config Model Target

Target control levels used in this audit:

- `G`: global feature toggle in centralized Helpdesk settings
- `GT`: global toggle plus team-level override on `helpdesk.ticket.team`
- `GR`: global toggle plus feature-record control in the module's own model
- `GI`: global toggle plus integration-specific parameters
- `Seed`: install/bootstrap only, not part of normal runtime feature toggling

Proposed naming convention for centralized feature keys:

- `helpdesk.core.extended`
- `helpdesk.channel.portal`
- `helpdesk.channel.whatsapp`
- `helpdesk.integration.api`
- `helpdesk.ai.claude`
- `helpdesk.ops.dispatch`
- `helpdesk.ops.dispatch_execution`
- `helpdesk.ops.field_service_report`
- `helpdesk.ops.escalation`
- `helpdesk.ops.approval`
- `helpdesk.billing.invoice`
- `helpdesk.knowledge.base`
- `helpdesk.knowledge.portal`
- `helpdesk.contract.base`
- `helpdesk.renewal.watch`
- `helpdesk.renewal.analytics`
- `helpdesk.renewal.forecast`
- `helpdesk.customer.overview`
- `helpdesk.customer.communication_log`
- `helpdesk.analytics.communication`
- `helpdesk.analytics.kpi`
- `helpdesk.problem.management`
- `helpdesk.release.notes`
- `helpdesk.sales.handoff`
- `helpdesk.success.playbook`
- `helpdesk.review.pack`
- `helpdesk.review.distribution`
- `helpdesk.asset.coverage`
- `helpdesk.calendar`
- `helpdesk.demo.seed`

## 4. Audit Matrix

| Module | Proposed feature key | Domain | Current control surface | Runtime coupling | Target config | Phase |
| --- | --- | --- | --- | --- | --- | --- |
| `helpdesk_mgmt_extended` | `helpdesk.core.extended` | Core foundation | settings, team fields | cron, controller, team, ticket, partner | `GT` | P1 |
| `helpdesk_custom_calendar` | `helpdesk.calendar` | Core ops | none | views only | `G` | P3 |
| `helpdesk_custom_escalation` | `helpdesk.ops.escalation` | Core ops | rule records | cron, ticket | `GR` | P1 |
| `helpdesk_custom_kpi` | `helpdesk.analytics.kpi` | Analytics | none | report models, views | `G` | P2 |
| `helpdesk_custom_portal` | `helpdesk.channel.portal` | Customer channel | settings, team fields | cron, controller, team, ticket | `GT` | P1 |
| `helpdesk_custom_whatsapp` | `helpdesk.channel.whatsapp` | Customer channel | settings | cron, ticket, outbound integration | `GI` | P1 |
| `helpdesk_custom_api` | `helpdesk.integration.api` | Integration | settings | controller, token auth | `GI` | P1 |
| `helpdesk_custom_claude_ai` | `helpdesk.ai.claude` | AI automation | settings, team fields | cron, team, ticket | `GT` | P1 |
| `helpdesk_custom_approval` | `helpdesk.ops.approval` | Governance | none | ticket, approval records | `GR` | P2 |
| `helpdesk_custom_invoice` | `helpdesk.billing.invoice` | Billing | team fields | ticket, invoice wizard, account models | `GT` | P1 |
| `helpdesk_custom_knowledge` | `helpdesk.knowledge.base` | Knowledge | none | ticket, document page | `GR` | P2 |
| `helpdesk_custom_knowledge_portal` | `helpdesk.knowledge.portal` | Knowledge channel | none | controller, document page, portal views | `GR` | P2 |
| `helpdesk_custom_contract` | `helpdesk.contract.base` | Commercial | none | ticket, contract records | `GR` | P2 |
| `helpdesk_custom_dispatch` | `helpdesk.ops.dispatch` | Service delivery | none | ticket, dispatch records | `GR` | P1 |
| `helpdesk_custom_dispatch_execution` | `helpdesk.ops.dispatch_execution` | Service delivery | none | dispatch, evidence, report dependency | `GR` | P1 |
| `helpdesk_custom_field_service_report` | `helpdesk.ops.field_service_report` | Service delivery | none | dispatch, report records | `GR` | P1 |
| `helpdesk_custom_customer_360` | `helpdesk.customer.overview` | Customer insight | none | partner views, cross-module reads | `G` | P2 |
| `helpdesk_custom_asset_coverage` | `helpdesk.asset.coverage` | Service delivery | none | ticket, contract, dispatch | `GR` | P2 |
| `helpdesk_custom_problem_management` | `helpdesk.problem.management` | Governance | none | ticket, knowledge, asset dependency | `GR` | P2 |
| `helpdesk_custom_customer_communication_log` | `helpdesk.customer.communication_log` | Customer insight | none | ticket, cross-channel write-ins | `G` | P2 |
| `helpdesk_custom_communication_analytics` | `helpdesk.analytics.communication` | Analytics | none | report models, communication log dependency | `G` | P2 |
| `helpdesk_custom_release_note_tracking` | `helpdesk.release.notes` | Governance | none | ticket, problem, knowledge, comm log | `GR` | P2 |
| `helpdesk_custom_sales_handoff` | `helpdesk.sales.handoff` | Commercial | none | ticket, CRM handoff records | `GR` | P2 |
| `helpdesk_custom_contract_renewal` | `helpdesk.renewal.watch` | Commercial | none | cron, contract, handoff, partner | `GR` | P1 |
| `helpdesk_custom_contract_renewal_analytics` | `helpdesk.renewal.analytics` | Analytics | none | report models, partner views | `G` | P2 |
| `helpdesk_custom_renewal_forecast` | `helpdesk.renewal.forecast` | Analytics | none | dashboard models, targets | `GR` | P3 |
| `helpdesk_custom_customer_success_playbook` | `helpdesk.success.playbook` | Customer success | none | cron, partner, task generation | `GR` | P1 |
| `helpdesk_custom_service_review_pack` | `helpdesk.review.pack` | Executive reporting | none | partner, snapshot, report | `GR` | P2 |
| `helpdesk_custom_service_review_distribution` | `helpdesk.review.distribution` | Executive automation | none | cron, outbound distribution | `GR` | P1 |
| `helpdesk_custom_demo` | `helpdesk.demo.seed` | Demo/bootstrap | hook only | seed data across all addons | `Seed` | P3 |

Phase meaning:

- `P1`: runtime-critical, must be retrofit first
- `P2`: functional/read-model features, retrofit after runtime-critical modules are safe
- `P3`: optional polish or bootstrap-only handling

## 5. Domain Clusters

### 5.1 Core and Channel Foundation

Modules:

- `helpdesk_mgmt_extended`
- `helpdesk_custom_calendar`
- `helpdesk_custom_escalation`
- `helpdesk_custom_portal`
- `helpdesk_custom_whatsapp`
- `helpdesk_custom_api`
- `helpdesk_custom_claude_ai`

Notes:

- This cluster owns most runtime entry points.
- It also contains the majority of current config surfaces.
- Phase 2 implementation should introduce a shared feature-gate helper here first.

### 5.2 Service Delivery and Billing

Modules:

- `helpdesk_custom_approval`
- `helpdesk_custom_invoice`
- `helpdesk_custom_dispatch`
- `helpdesk_custom_dispatch_execution`
- `helpdesk_custom_field_service_report`
- `helpdesk_custom_asset_coverage`

Notes:

- These features are process-driven and should remain available only where the business workflow uses them.
- Team-level override is useful for billing.
- Dispatch-related features should use record-level enablement because they are driven by dispatch/report records as much as by team policy.

### 5.3 Knowledge, Governance, and Customer Context

Modules:

- `helpdesk_custom_knowledge`
- `helpdesk_custom_knowledge_portal`
- `helpdesk_custom_problem_management`
- `helpdesk_custom_release_note_tracking`
- `helpdesk_custom_customer_360`
- `helpdesk_custom_customer_communication_log`

Notes:

- These modules are tightly linked by relational models and smart buttons.
- They should degrade gracefully in UI when disabled rather than trying to hide every inherited field.
- `knowledge_portal` must not serve portal routes when either portal publishing or the base knowledge feature is disabled.

### 5.4 Commercial, Renewal, and Executive Layers

Modules:

- `helpdesk_custom_contract`
- `helpdesk_custom_sales_handoff`
- `helpdesk_custom_contract_renewal`
- `helpdesk_custom_contract_renewal_analytics`
- `helpdesk_custom_renewal_forecast`
- `helpdesk_custom_customer_success_playbook`
- `helpdesk_custom_service_review_pack`
- `helpdesk_custom_service_review_distribution`

Notes:

- This cluster is deep in dependencies and should not be flattened into one mega feature flag.
- Renewal watch, playbooks, and distribution have real background automation and should be treated as runtime-active features.
- Analytics and executive reporting should depend on source features being present, but their own visibility can still be controlled globally.

## 6. Highest-Risk Coupling

### 6.1 Cron-bound features

These modules need runtime guard checks before anything else:

- `helpdesk_mgmt_extended`
- `helpdesk_custom_escalation`
- `helpdesk_custom_portal`
- `helpdesk_custom_whatsapp`
- `helpdesk_custom_claude_ai`
- `helpdesk_custom_customer_success_playbook`
- `helpdesk_custom_service_review_distribution`
- `helpdesk_custom_contract_renewal`

Requirement:

- each cron entry point must short-circuit when its feature is globally disabled
- if the feature supports team scoping, batch logic must skip teams or records where the feature is disabled

### 6.2 Controller and external-entry features

These modules need explicit feature gates at the request boundary:

- `helpdesk_custom_portal`
- `helpdesk_custom_knowledge_portal`
- `helpdesk_custom_api`
- `helpdesk_mgmt_extended` portal controller extension

Requirement:

- requests must be rejected early with a stable response when the feature is disabled
- disabled routes must not expose partial functionality or inconsistent public errors

### 6.3 Hook-heavy bootstrap modules

These modules currently create demo or setup data during installation:

- `helpdesk_custom_demo`
- most `helpdesk_custom_*` functional addons with `post_init_hook`

Requirement:

- bootstrap logic should be separated from runtime feature toggles
- demo seed should not be part of the normal feature management screen

## 7. Immediate Implementation Scope for Phase 2

The next coding phase should start with a new feature registry layer and retrofit these modules first:

1. `helpdesk_mgmt_extended`
2. `helpdesk_custom_portal`
3. `helpdesk_custom_whatsapp`
4. `helpdesk_custom_api`
5. `helpdesk_custom_claude_ai`
6. `helpdesk_custom_escalation`
7. `helpdesk_custom_invoice`
8. `helpdesk_custom_dispatch`
9. `helpdesk_custom_dispatch_execution`
10. `helpdesk_custom_field_service_report`
11. `helpdesk_custom_contract_renewal`
12. `helpdesk_custom_customer_success_playbook`
13. `helpdesk_custom_service_review_distribution`

Expected output of Phase 2:

- centralized feature registry
- unified global settings UI
- first-pass team override strategy
- runtime guards in cron and controllers
- no behavior change for enabled installations

## 8. Open Decisions

These still need explicit choice before implementation starts:

1. Whether team overrides should support `inherit`, `force_on`, and `force_off`, or only simple boolean overrides.
2. Whether read-only analytics features should be hidden from menus when disabled, or only show empty states.
3. Whether demo data should move into a separate non-production stream, or remain installable in the same addon tree.
4. Whether contract, approval, dispatch, and release-note modules need company-level overrides in addition to team-level control.
