# Helpdesk Modular Config Smoke Test Checklist

Last updated: 2026-04-01  
Target database: `ksv17-dev`

## 1. Purpose

This checklist verifies that custom Helpdesk features can be safely enabled and disabled from centralized configuration.

Primary validation goals:

- the toggle is visible in `Settings > Helpdesk`
- disabling the feature blocks its main runtime entry points
- enabling the feature restores normal behavior
- no unrelated Helpdesk area regresses during the toggle cycle

## 2. General Test Rules

Before running feature-specific checks:

- use an admin user
- start from a stable database snapshot
- confirm `helpdesk_feature_hub` is installed
- keep one browser tab on `Settings > Helpdesk`
- after each save, refresh the target menu or form being tested

Recommended validation sequence per feature:

1. confirm feature works while enabled
2. disable the feature and save settings
3. verify blocked behavior or graceful degradation
4. re-enable the feature and save settings
5. confirm feature works again

## 3. Cross-Cutting Checks

Run these once after any batch of feature toggles:

- `Settings > Helpdesk` opens without JS or Owl errors
- Helpdesk main menu still opens normally
- saving settings does not raise unrelated warnings or tracebacks
- disabled feature does not break unrelated enabled feature menus
- re-enabled feature becomes available again without server restart

## 4. Feature Checklist

### 4.1 Helpdesk Extended Foundation

Toggle:

- `Helpdesk Extended Foundation`

Validate while enabled:

- `Settings > Helpdesk` opens normally
- extended Helpdesk settings still render
- Helpdesk portal-related extended flow still behaves normally

Validate while disabled:

- portal extension behavior from `helpdesk_mgmt_extended` no longer runs
- foundation cron methods short-circuit without error
- no crash when opening Helpdesk team or ticket forms

### 4.2 Escalation Engine

Toggle:

- `Escalation Engine`

Validate while enabled:

- `Helpdesk > Configuration > Escalation Rules` opens
- escalation cron can run without feature error
- escalated ticket logic behaves normally

Validate while disabled:

- escalation processing cron does not escalate tickets
- escalation-triggered actions do not proceed
- related reporting still opens only if its own feature is enabled

### 4.3 Public Tracking Portal

Toggle:

- `Public Tracking Portal`

Validate while enabled:

- public tracking link opens
- public reply and ticket status page work
- portal digest behavior remains normal

Validate while disabled:

- public tracking URL is rejected
- ticket public actions stop working
- portal digest cron or follow-up processing short-circuits

### 4.4 WhatsApp Notifications

Toggle:

- `WhatsApp Notifications`

Validate while enabled:

- WhatsApp configuration fields remain editable
- queue processing works in normal or sandbox mode

Validate while disabled:

- WhatsApp queue cron does not process records
- ticket actions that would enqueue WhatsApp messages do not send runtime flow forward

### 4.5 Helpdesk API

Toggle:

- `Helpdesk API`

Validate while enabled:

- API settings remain editable
- authenticated API request can still reach the controller

Validate while disabled:

- API request is rejected at the controller boundary
- no ticket create or update proceeds from the API path

### 4.6 Claude AI

Toggle:

- `Claude AI`

Validate while enabled:

- AI analysis action on ticket is available where team allows AI
- AI cron can process pending tickets

Validate while disabled:

- AI analysis action is blocked
- AI cron short-circuits
- team-level `ai_enabled` no longer matters when global toggle is off

### 4.7 Billing and Invoicing

Toggle:

- `Billing and Invoicing`

Validate while enabled:

- invoice wizard opens from eligible ticket
- invoice creation from ticket works for teams with `allow_billing`

Validate while disabled:

- invoice wizard cannot be opened from ticket
- invoice create action is blocked
- team-level `allow_billing` cannot override a disabled global toggle

### 4.8 Dispatch Workflow

Toggle:

- `Dispatch Workflow`

Validate while enabled:

- dispatch can be scheduled from ticket
- dispatch form actions can move state normally
- dispatch list/reporting menu opens

Validate while disabled:

- dispatch scheduling from ticket is blocked
- dispatch create and state actions are blocked
- dispatch-related object actions fail with controlled message

### 4.9 Dispatch Execution

Toggle:

- `Dispatch Execution`

Validate while enabled:

- execution-specific actions are available
- evidence capture works
- sign-off flow works

Validate while disabled:

- execution-only actions are blocked
- evidence create is blocked
- base dispatch flow still works where fallback to base dispatch is expected

### 4.10 Field Service Report

Toggle:

- `Field Service Report`

Validate while enabled:

- service report can be created from dispatch
- report submit and lifecycle actions work

Validate while disabled:

- report create from dispatch is blocked
- report lifecycle actions are blocked
- dispatch can still exist if dispatch feature itself stays enabled

### 4.11 Contract Renewal Watch

Toggle:

- `Contract Renewal Watch`

Validate while enabled:

- renewal watch records behave normally
- renewal sync cron can run

Validate while disabled:

- renewal sync cron does not create or update watch records
- operational renewal actions stop where guarded

### 4.12 Customer Success Playbooks

Toggle:

- `Customer Success Playbooks`

Validate while enabled:

- playbook records open normally
- due playbook cron can schedule activity

Validate while disabled:

- due playbook cron short-circuits
- playbook operational actions do not continue where guarded

### 4.13 Service Review Distribution

Toggle:

- `Service Review Distribution`

Validate while enabled:

- distribution setup opens normally
- due distribution cron can process queue

Validate while disabled:

- due distribution cron short-circuits
- distribution execution does not proceed

### 4.14 KPI Reporting

Toggle:

- `KPI Reporting`

Validate while enabled:

- `Helpdesk > Reporting > KPI Overview` opens
- `KPI Analysis`, `Agent Performance`, `Customer Insights`, and `Trend Monitor` open
- KPI object actions from dashboard cards work

Validate while disabled:

- KPI reporting menus are blocked through menu wrapper
- KPI object actions are blocked
- direct open from dashboard card or related action no longer proceeds

### 4.15 Communication Analytics

Toggle:

- `Communication Analytics`

Validate while enabled:

- `Helpdesk > Reporting > Communication Analytics` opens

Validate while disabled:

- communication analytics reporting menu is blocked
- direct reporting action no longer opens analytics view

### 4.16 Customer Support Overview

Toggle:

- `Customer Support Overview`

Validate while enabled:

- `Helpdesk > Reporting > Customer Support Overview` opens
- partner support overview tab and smart buttons behave normally

Validate while disabled:

- reporting menu is blocked
- partner smart buttons are blocked
- computed support overview metrics degrade safely instead of crashing

### 4.17 Renewal Analytics

Toggle:

- `Renewal Analytics`

Validate while enabled:

- `Helpdesk > Reporting > Renewal Overview` opens
- `Helpdesk > Reporting > Renewal Analytics` opens

Validate while disabled:

- both renewal analytics reporting menus are blocked
- analytics-related partner metrics degrade safely

### 4.18 Renewal Forecast

Toggle:

- `Renewal Forecast`

Validate while enabled:

- `Helpdesk > Reporting > Renewal Forecast` opens
- renewal target create and edit work

Validate while disabled:

- renewal forecast reporting menu is blocked
- renewal target create and edit are blocked

### 4.19 Service Review Pack

Toggle:

- `Service Review Pack`

Validate while enabled:

- `Helpdesk > Reporting > Service Review Packs` opens
- pack can be created
- snapshot generation works
- PDF print works

Validate while disabled:

- reporting menu is blocked
- pack create is blocked
- pack actions are blocked
- PDF print is blocked from both button flow and report binding flow

## 5. Team-Level Override Checks

Run these only for features that currently support team-level behavior.

### 5.1 Claude AI

- keep global `Claude AI` enabled
- set one team with `ai_enabled = False`
- confirm AI action is blocked for that team
- set another team with `ai_enabled = True`
- confirm AI action works for that team

### 5.2 Billing and Invoicing

- keep global `Billing and Invoicing` enabled
- set one team with `allow_billing = False`
- confirm invoice flow is blocked for that team
- set another team with `allow_billing = True`
- confirm invoice flow works for that team

## 6. Recommended Regression Log Format

For each feature tested, capture:

- feature name
- toggle state tested
- user used
- entry point tested
- actual result
- expected result
- pass or fail
- traceback or screenshot if failed

## 7. Documentation References

Related documents:

- `addons/docs/helpdesk_modular_config_guide.md`
- `addons/docs/helpdesk_modularization_phase1_audit.md`
- `addons/docs/helpdesk_customization_recap.md`
