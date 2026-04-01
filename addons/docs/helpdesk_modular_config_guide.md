# Helpdesk Modular Config Guide

Last updated: 2026-04-01  
Target database: `ksv17-dev`

## 1. Status Summary

The Helpdesk modularization stream is now delivered for centralized configuration.

What is already available:

- a centralized feature registry in `helpdesk_feature_hub`
- global feature toggles in `Settings > Helpdesk`
- runtime guards for cron, controller, API, business actions, reporting menus, and service review PDF output
- database rollout completed in `ksv17-dev`

What this means operationally:

- custom Helpdesk features can now be enabled or disabled from configuration without uninstalling their addons
- disabling a feature blocks its main runtime entry points and reporting entry points
- feature visibility is controlled by configuration, while addon installation stays intact

## 2. Configuration Entry Point

UI location:

- `Settings > Helpdesk`

Main settings blocks added by the modularization stream:

- `Feature Management`
- `Channels and Integrations`
- `Service Delivery`
- `Commercial and Automation`
- `Analytics and Executive`

Technical owner:

- addon: `helpdesk_feature_hub`
- registry model: `helpdesk.feature.config`
- settings model extension: `res.config.settings`

## 3. Current Feature Toggles

### 3.1 Feature Management

- `Helpdesk Extended Foundation`
- `Escalation Engine`

### 3.2 Channels and Integrations

- `Public Tracking Portal`
- `WhatsApp Notifications`
- `Helpdesk API`
- `Claude AI`

### 3.3 Service Delivery

- `Billing and Invoicing`
- `Dispatch Workflow`
- `Dispatch Execution`
- `Field Service Report`

### 3.4 Commercial and Automation

- `Contract Renewal Watch`
- `Customer Success Playbooks`
- `Service Review Distribution`

### 3.5 Analytics and Executive

- `KPI Reporting`
- `Communication Analytics`
- `Customer Support Overview`
- `Renewal Analytics`
- `Renewal Forecast`
- `Service Review Pack`

## 4. What Each Toggle Actually Controls

### 4.1 Runtime entry points already guarded

- scheduled jobs and cron methods
- public and authenticated controllers
- API endpoints
- main create and action methods for operational flows
- reporting menu entry points
- service review PDF generation

### 4.2 Examples

- turning off `Public Tracking Portal` disables public ticket routes and portal digest processing
- turning off `Helpdesk API` blocks external API access
- turning off `Dispatch Workflow` blocks dispatch creation and dispatch state actions
- turning off `Dispatch Execution` disables execution-only enhancements while preserving the base dispatch flow where designed
- turning off `KPI Reporting` blocks KPI overview, analysis, agent, customer, and trend reporting menus
- turning off `Service Review Pack` blocks pack creation, pack actions, menu access, and PDF output

## 5. Current Team-Level Override Scope

Global config is the primary control plane.

Team-level override is currently implemented only where a real team field already exists and is meaningful:

- `Claude AI`
  team field: `ai_enabled`
- `Billing and Invoicing`
  team field: `allow_billing`

Operational meaning:

- global toggle must be enabled first
- if a feature also has team override, the related team must allow it

## 6. Feature Key Map

| Feature key | Settings label | Main modules |
| --- | --- | --- |
| `helpdesk.core.extended` | Helpdesk Extended Foundation | `helpdesk_mgmt_extended` |
| `helpdesk.ops.escalation` | Escalation Engine | `helpdesk_custom_escalation` |
| `helpdesk.channel.portal` | Public Tracking Portal | `helpdesk_custom_portal` |
| `helpdesk.channel.whatsapp` | WhatsApp Notifications | `helpdesk_custom_whatsapp` |
| `helpdesk.integration.api` | Helpdesk API | `helpdesk_custom_api` |
| `helpdesk.ai.claude` | Claude AI | `helpdesk_custom_claude_ai` |
| `helpdesk.billing.invoice` | Billing and Invoicing | `helpdesk_custom_invoice` |
| `helpdesk.ops.dispatch` | Dispatch Workflow | `helpdesk_custom_dispatch` |
| `helpdesk.ops.dispatch_execution` | Dispatch Execution | `helpdesk_custom_dispatch_execution` |
| `helpdesk.ops.field_service_report` | Field Service Report | `helpdesk_custom_field_service_report` |
| `helpdesk.renewal.watch` | Contract Renewal Watch | `helpdesk_custom_contract_renewal` |
| `helpdesk.success.playbook` | Customer Success Playbooks | `helpdesk_custom_customer_success_playbook` |
| `helpdesk.review.distribution` | Service Review Distribution | `helpdesk_custom_service_review_distribution` |
| `helpdesk.analytics.kpi` | KPI Reporting | `helpdesk_custom_kpi` |
| `helpdesk.analytics.communication` | Communication Analytics | `helpdesk_custom_communication_analytics` |
| `helpdesk.customer.overview` | Customer Support Overview | `helpdesk_custom_customer_360` |
| `helpdesk.renewal.analytics` | Renewal Analytics | `helpdesk_custom_contract_renewal_analytics` |
| `helpdesk.renewal.forecast` | Renewal Forecast | `helpdesk_custom_renewal_forecast` |
| `helpdesk.review.pack` | Service Review Pack | `helpdesk_custom_service_review_pack` |

## 7. Design Boundaries

This implementation is modular by configuration, not by addon uninstall.

That distinction matters because:

- inherited views remain part of the installed system
- extended fields still exist on models
- access rules and menus may still exist physically in the database
- operational safety must therefore be enforced through feature gating, not through install state changes

The result is:

- safe runtime disablement
- lower risk during upgrades
- predictable behavior across dependent addons

## 8. Operational Notes

### 8.1 When a feature is disabled

- background processing should short-circuit
- controller or API entry should reject access
- menu wrappers should block direct reporting access
- object actions should stop with a controlled user-facing error

### 8.2 When a feature is enabled

- existing workflows should behave as before
- no uninstall or data migration is required for normal use

### 8.3 If configuration changes do not appear

Check these first:

- the addon `helpdesk_feature_hub` is installed
- the target addon has been upgraded in the current database
- the Odoo `web` service has been restarted after module installation when the running registry is stale

## 9. Delivered Documentation Set

The modularization stream is documented in:

- `addons/docs/helpdesk_modularization_phase1_audit.md`
- `addons/docs/helpdesk_modular_config_guide.md`
- `addons/docs/helpdesk_modular_config_smoke_test_checklist.md`
- `addons/docs/helpdesk_customization_recap.md`
- `addons/docs/helpdesk_pending_backlog.md`

## 10. Remaining Optional Work

The centralized config stream is complete for global toggles.

Optional follow-up items, not blockers for current usage:

- broader team-level override coverage for more features
- optional UI hiding strategy for inherited read-only fields that are currently only degraded at runtime
