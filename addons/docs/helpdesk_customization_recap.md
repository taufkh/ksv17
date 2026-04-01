# Helpdesk Customization Recap

Last updated: 2026-04-01  
Target database: `ksv17-dev`

## 1. Scope Summary

The Helpdesk implementation in this repository has been expanded from the OCA `helpdesk_mgmt` base into a broader support operations platform.

Delivered scope covers:

- baseline Helpdesk setup and demo dataset
- centralized feature management and modular config gating
- ticket calendar visibility
- escalation engine
- KPI and operational reporting
- public customer portal
- WhatsApp notification flow
- invoice generation from support work
- REST-style API layer
- support-centric sales handoff
- approval workflow
- knowledge base linkage
- customer-facing knowledge publication workflow
- support contract and entitlement tracking
- dispatch and field service reporting
- dispatch execution controls and evidence capture
- customer support overview
- asset coverage mapping
- problem management
- customer communication journal
- communication analytics dashboard
- release note tracking
- contract renewal monitoring
- contract renewal analytics
- CSAT recovery operational dashboard
- renewal forecast versus target and budget dashboard
- customer success playbooks and proactive tasks
- executive service review pack export
- scheduled executive pack distribution

## 2. Baseline Foundation

The custom stack is built on top of the OCA Helpdesk foundation and related business modules already enabled in the environment.

Important baseline modules used by the custom stack:

- `helpdesk_mgmt`
- `helpdesk_type`
- `helpdesk_mgmt_sla`
- `helpdesk_mgmt_template`
- `helpdesk_mgmt_assign_method`
- `helpdesk_mgmt_rating`
- `helpdesk_ticket_close_inactive`
- `helpdesk_mgmt_merge`
- `helpdesk_ticket_related`
- `helpdesk_mgmt_project`
- `helpdesk_mgmt_sale`
- `helpdesk_mgmt_crm`
- `helpdesk_mgmt_activity`
- `helpdesk_ticket_partner_response`
- `helpdesk_mgmt_stage_validation`
- `helpdesk_portal_restriction`
- `helpdesk_mgmt_timesheet`
- `helpdesk_timesheet_time_type`

Baseline demo data was also added so that the end-to-end feature set can be reviewed visually without manual setup.

## 3. Delivered Modules Overview

| Module | Primary Purpose | Main UI Exposure | Main Model(s) |
| --- | --- | --- | --- |
| `helpdesk_feature_hub` | Centralized feature registry and global modular config for custom Helpdesk features | `Settings > Helpdesk` | `helpdesk.feature.config`, `res.config.settings` |
| `helpdesk_custom_demo` | Demo dataset and showcase records | Existing Helpdesk menus populated with sample data | `helpdesk.ticket` and related base models |
| `helpdesk_custom_calendar` | Calendar overview of tickets and SLA windows | `Helpdesk > Calendar`, calendar switcher on ticket actions | `helpdesk.ticket` |
| `helpdesk_custom_escalation` | SLA and rule-based escalation engine | `Helpdesk > Configuration > Escalation Rules`, ticket smart button | `helpdesk.escalation.rule`, escalation event model, `helpdesk.ticket` |
| `helpdesk_custom_kpi` | KPI dashboard, analysis, trend, agent and customer reporting | `Helpdesk > Reporting` | KPI report and dashboard models |
| `helpdesk_custom_portal` | Public ticket tracking and customer interaction portal | public portal pages, ticket public-link actions, settings | `helpdesk.ticket`, portal controllers |
| `helpdesk_custom_whatsapp` | WhatsApp queue, templates, sending log, event notification | templates, logs, ticket smart button, settings | `helpdesk.whatsapp.template`, `helpdesk.whatsapp.message` |
| `helpdesk_custom_invoice` | Billing and invoicing from ticket effort | ticket form, invoice wizard, invoice views, team setup | invoice wizard and ticket billing fields |
| `helpdesk_custom_api` | External system integration through API | API endpoints, settings | API controller, `res.config.settings` |
| `helpdesk_custom_sales_handoff` | Separate pre-sales or upsell handoff from support flow | ticket action, reporting menu, CRM handoff review | `helpdesk.sales.handoff`, `helpdesk.ticket` |
| `helpdesk_custom_approval` | Approval requests for support exceptions and service actions | ticket action, reporting menu | `helpdesk.ticket.approval`, `helpdesk.ticket` |
| `helpdesk_custom_knowledge` | Ticket-linked knowledge articles | ticket action, article views, configuration | `document.page`, `helpdesk.ticket` |
| `helpdesk_custom_knowledge_portal` | Publish selected knowledge to customer portal and public ticket journey | portal home, public ticket page, knowledge article workflow | `document.page`, portal controllers |
| `helpdesk_custom_contract` | Support entitlement, SLA tier, retainer coverage | `Helpdesk > Configuration > Support Contracts`, ticket smart button | `helpdesk.support.contract`, `helpdesk.ticket` |
| `helpdesk_custom_dispatch` | Onsite visit and engineer scheduling | `Helpdesk > Reporting > Dispatch Board`, ticket action | `helpdesk.dispatch`, `helpdesk.ticket` |
| `helpdesk_custom_dispatch_execution` | Technician execution checklist, evidence, travel timing, and sign-off | dispatch form, evidence action, field service report summary | `helpdesk.dispatch`, `helpdesk.dispatch.evidence`, `helpdesk.field.service.report` |
| `helpdesk_custom_customer_360` | Customer-level support context view | `Helpdesk > Reporting > Customer Support Overview`, partner tab | `res.partner` extension |
| `helpdesk_custom_field_service_report` | Formal post-visit service report and acknowledgement | dispatch action, reporting menu | `helpdesk.field.service.report`, `helpdesk.dispatch` |
| `helpdesk_custom_asset_coverage` | Asset, branch, device, or process coverage map | `Helpdesk > Configuration > Support Assets`, ticket and contract linkage | `helpdesk.support.asset` |
| `helpdesk_custom_problem_management` | Problem, known error, RCA, and recurring issue tracking | `Helpdesk > Reporting > Problem Records`, ticket action | `helpdesk.problem`, `helpdesk.ticket` |
| `helpdesk_custom_customer_communication_log` | Structured cross-channel communication journal | `Helpdesk > Reporting > Customer Communication Log`, ticket smart button | `helpdesk.communication.log`, `helpdesk.ticket` |
| `helpdesk_custom_communication_analytics` | Communication responsiveness and channel analytics | `Helpdesk > Reporting > Communication Analytics` | `helpdesk.communication.analytics.report` |
| `helpdesk_custom_release_note_tracking` | Release, fix rollout, and customer update traceability | `Helpdesk > Reporting > Release Notes`, smart buttons on ticket/problem/knowledge | `helpdesk.release.note` and related extensions |
| `helpdesk_custom_contract_renewal` | Renewal watchlists and commercial follow-up for expiring support contracts | `Helpdesk > Reporting > Contract Renewals`, contract and customer views | `helpdesk.contract.renewal`, `helpdesk.support.contract` |
| `helpdesk_custom_contract_renewal_analytics` | Renewal pipeline dashboard and revenue-at-risk analytics | `Helpdesk > Reporting > Renewal Overview`, `Helpdesk > Reporting > Renewal Analytics` | renewal analytics dashboard/report models and `helpdesk.contract.renewal` |
| `helpdesk_custom_renewal_forecast` | Renewal forecast versus target and budget dashboard | `Helpdesk > Reporting > Renewal Forecast`, `Helpdesk > Configuration > Renewal Targets` | `helpdesk.renewal.target`, `helpdesk.renewal.forecast.dashboard` |
| `helpdesk_custom_customer_success_playbook` | Proactive customer success and renewal-readiness task management | `Helpdesk > Reporting > Customer Success Playbooks`, customer form smart button | `helpdesk.customer.success.playbook`, `res.partner` |
| `helpdesk_custom_service_review_pack` | Executive customer review pack and printable service summary export | `Helpdesk > Reporting > Service Review Packs`, customer form smart button | `helpdesk.service.review.pack`, `res.partner` |
| `helpdesk_custom_service_review_distribution` | Scheduled distribution of service review packs by email | `Helpdesk > Reporting > Service Review Distribution` | `helpdesk.service.review.distribution`, `helpdesk.service.review.pack` |

## 4. Detailed Module Notes

### 4.0 `helpdesk_feature_hub`

Feature purpose:

- centralizes feature-flag style configuration across custom Helpdesk addons

Key functions:

- registers canonical feature keys for custom Helpdesk domains
- exposes global toggles in `Settings > Helpdesk`
- provides helper methods to check whether a feature is enabled globally or for a team when applicable
- standardizes runtime gating for cron jobs, controllers, object actions, reporting menus, and printable report entry points

Menu and UI relation:

- `Settings > Helpdesk`
- feature blocks for foundation, channels, service delivery, commercial automation, analytics, and executive features

Main model relation:

- `helpdesk.feature.config`
- `res.config.settings`
- `ir.config_parameter`

Cross-module relation:

- acts as the control plane for the custom Helpdesk addon stack
- does not replace addon installation
- disables behavior safely through config without uninstalling dependent modules

### 4.1 `helpdesk_custom_demo`

Feature purpose:

- provides realistic demo records so every installed feature can be shown immediately

Key functions:

- seeds helpdesk teams, categories, ticket types, tickets, stages, ratings, timesheets, CRM lead links, sale order links, attachments, and portal users
- creates demo scenarios for overdue SLA, inactive close, related tickets, billing, project linkage, and portal activity

Menu and UI relation:

- no dedicated menu
- enriches the standard Helpdesk menus with visible sample records

Main model relation:

- centered on `helpdesk.ticket`
- links to CRM, Sales, Project, Portal, Rating, Timesheet, and Attachment records

### 4.2 `helpdesk_custom_calendar`

Feature purpose:

- adds calendar visibility for ticket submission date and SLA deadline range

Key functions:

- provides calendar view for all tickets and my tickets
- keeps ticket default action on Kanban while still exposing Calendar as an optional view
- helps supervisors see due dates and ticket timing at a glance

Menu and UI relation:

- `Helpdesk > Calendar`
- calendar tab on ticket actions such as All Tickets and My Tickets

Main model relation:

- `helpdesk.ticket`
- uses `create_date` and `sla_deadline` to render calendar spans

### 4.3 `helpdesk_custom_escalation`

Feature purpose:

- automates escalation when tickets breach defined conditions

Key functions:

- escalation rules with scope by team, stage, SLA, and timing
- cron-based evaluation
- escalation flagging on tickets
- chatter note and notification flow
- escalation event visibility from the ticket

Menu and UI relation:

- `Helpdesk > Configuration > Escalation Rules`
- ticket smart button for escalations
- additional escalation information in ticket form

Main model relation:

- `helpdesk.ticket`
- custom escalation rule model
- custom escalation event model

Cross-module relation:

- feeds KPI overdue and escalation metrics
- triggers WhatsApp notification scenarios
- appears in portal timeline
- used by problem management to measure impact

### 4.4 `helpdesk_custom_kpi`

Feature purpose:

- provides management and operations reporting across the helpdesk process

Key functions:

- KPI overview dashboard cards
- deep analysis in graph, pivot, and list views
- agent performance overview
- customer insight view
- trend monitoring
- aging, breach, backlog, same-day close, assignment speed, rating, and escalation metrics
- CSAT operational metrics: low-CSAT open queue, recovery SLA misses, and no-follow-up >24h counters

Menu and UI relation:

- `Helpdesk > Reporting > KPI Overview`
- `Helpdesk > Reporting > KPI Analysis`
- `Helpdesk > Reporting > Agent Performance`
- `Helpdesk > Reporting > Customer Insights`
- `Helpdesk > Reporting > Trend Monitor`

Main model relation:

- SQL-based KPI reporting models
- dashboard and trend reporting models
- reads from `helpdesk.ticket`, rating, SLA, escalation, team, assignee, and partner dimensions

Cross-module relation:

- consumes escalation state
- consumes SLA metrics
- consumes rating data
- forms the reporting layer used by managers to review all other modules

### 4.5 `helpdesk_custom_portal`

Feature purpose:

- exposes a public customer-facing tracking page for tickets

Key functions:

- tokenized public ticket tracking without back-office access
- public reply, close, reopen, and feedback actions
- public escalation request with preferred contact channel and callback time
- file upload validation
- portal timeline and attachment exposure
- SLA status badge and customer rating entry
- collaborator management and per-ticket notification preferences
- digest policy override by team, retry controls, and failure monitoring
- backend quick-share actions: copy link, send via email, send via WhatsApp, with team-level message templates
- CSAT improvement automation: low-score recovery tasking, customer follow-up reminder cron, and resolution summary tracking
- configurable public access behavior from settings

Menu and UI relation:

- backend ticket buttons: `Open Public Portal`, `Refresh Public Link`, `Revoke Public Link`
- website route for public ticket tracking
- configuration options in Helpdesk settings

Main model relation:

- `helpdesk.ticket`
- website controller routes
- settings extension in `res.config.settings`

Cross-module relation:

- logs communication into communication journal
- can trigger rating flow
- shows escalation milestones in timeline
- works with portal restriction and partner-response base modules

### 4.6 `helpdesk_custom_whatsapp`

Feature purpose:

- provides outbound WhatsApp messaging with queue and retry controls

Key functions:

- message template management
- queue and retry engine
- sandbox mode and live mode configuration
- event-driven messages for stage change, escalation, and close
- message logs and ticket-level visibility

Menu and UI relation:

- `Helpdesk > Configuration > WhatsApp Templates`
- `Helpdesk > Reporting > WhatsApp Logs`
- ticket smart button for WhatsApp
- settings in Helpdesk configuration

Main model relation:

- `helpdesk.whatsapp.template`
- `helpdesk.whatsapp.message`
- `helpdesk.ticket`

Cross-module relation:

- consumes escalation events
- consumes portal-related customer contact data
- writes into customer communication log when messages are sent or fail terminally

### 4.7 `helpdesk_custom_invoice`

Feature purpose:

- converts billable support effort into invoices

Key functions:

- ticket billing policy and invoice readiness
- linkage of time type and billable time
- wizard to create invoice from ticket effort
- invoice visibility back on the ticket

Menu and UI relation:

- invoice creation wizard from ticket
- support billing setup on team and time-type configuration
- invoice linkage in accounting views

Main model relation:

- `helpdesk.ticket`
- invoice creation wizard
- accounting move integration
- time type and timesheet data

Cross-module relation:

- consumes timesheet entries from baseline Helpdesk Timesheet stack
- contributes invoice visibility to Customer Support Overview
- contributes uninvoiced hours context for account review

### 4.8 `helpdesk_custom_api`

Feature purpose:

- exposes Helpdesk operations to external systems

Key functions:

- health and metadata endpoints
- ticket list and ticket detail endpoints
- create ticket endpoint
- reply to ticket endpoint
- close ticket endpoint
- KPI summary endpoint
- token-based access control

Menu and UI relation:

- configuration in Helpdesk settings
- no dedicated backend operational menu because it is service-facing

Main model relation:

- API controller endpoints
- settings extension in `res.config.settings`
- `helpdesk.ticket`

Cross-module relation:

- can expose portal URL in serialized ticket payload
- consumes KPI layer for summary endpoint
- writes structured communication log entries for ticket creation, reply, and close

### 4.9 `helpdesk_custom_sales_handoff`

Feature purpose:

- keeps Helpdesk support-centric and separates commercial follow-up from the support UI

Key functions:

- removes direct opportunity conversion from the support flow
- adds `Request Sales Follow-up` style handoff flow
- lets sales review and convert handoffs separately
- keeps ticket informed about handoff state without exposing CRM behavior as a default support action

Menu and UI relation:

- ticket action for sales follow-up
- ticket smart button for handoffs
- reporting list for Sales Handoffs

Main model relation:

- `helpdesk.sales.handoff`
- `helpdesk.ticket`
- CRM lead linkage when approved and converted

Cross-module relation:

- uses CRM as downstream destination, not as direct ticket behavior
- appears in Customer Support Overview

### 4.10 `helpdesk_custom_approval`

Feature purpose:

- manages approvals for exception-based support actions

Key functions:

- approval request lifecycle from draft to implemented or rejected
- approval types such as refund, onsite visit, replacement unit, billing exception, SLA waiver, and access exception
- ticket-level request submission and follow-up

Menu and UI relation:

- ticket action `Request Approval`
- ticket smart button `Approvals`
- `Helpdesk > Reporting > Approval Requests`

Main model relation:

- `helpdesk.ticket.approval`
- `helpdesk.ticket`

Cross-module relation:

- dispatch can reference onsite-related approvals
- Customer Support Overview surfaces pending approvals per customer
- contract and SLA exception governance can be reviewed through approvals

### 4.11 `helpdesk_custom_knowledge`

Feature purpose:

- turns recurring or resolved ticket knowledge into structured articles

Key functions:

- create article from ticket
- link one or multiple tickets to the same article
- classify article visibility and lifecycle
- keep support documentation close to ticket operations

Menu and UI relation:

- ticket button `Create Knowledge Article`
- ticket smart button `Knowledge`
- article and category views under Helpdesk reporting and configuration

Main model relation:

- `document.page`
- `helpdesk.ticket`

Cross-module relation:

- problem records can point to knowledge articles
- Customer Support Overview surfaces linked knowledge records

### 4.12 `helpdesk_custom_contract`

Feature purpose:

- manages support entitlement and contract-based coverage

Key functions:

- contract types such as retainer, block hours, incident bundle, and warranty
- contract state, SLA tier, remaining hours, and coverage visibility
- auto-match contract to tickets by customer and team
- track consumed hours through timesheets
- tooltip guidance for contract type definitions

Menu and UI relation:

- `Helpdesk > Configuration > Support Contracts`
- ticket smart button for support contract
- ticket fields for contract state, coverage status, and remaining hours

Main model relation:

- `helpdesk.support.contract`
- `helpdesk.ticket`

Cross-module relation:

- consumes timesheet data
- extended by asset coverage module
- surfaced in Customer Support Overview
- linked to invoice context and support commercial visibility

### 4.13 `helpdesk_custom_dispatch`

Feature purpose:

- schedules onsite work and engineer dispatch from Helpdesk

Key functions:

- dispatch lifecycle from draft through completed, no access, or cancelled
- engineer assignment
- schedule window and site contact
- findings and follow-up notes
- calendar, tree, form, and pivot visibility

Menu and UI relation:

- ticket action `Schedule Dispatch`
- ticket smart button `Dispatches`
- `Helpdesk > Reporting > Dispatch Board`

Main model relation:

- `helpdesk.dispatch`
- `helpdesk.ticket`

Cross-module relation:

- may reference approvals
- extended by field service report
- extended by asset coverage
- surfaced in Customer Support Overview

### 4.14 `helpdesk_custom_customer_360`

Feature purpose:

- centralizes support context per customer into one internal screen

Key functions:

- customer-level overview of open, closed, overdue, escalated, and unassigned tickets
- visibility of contracts, remaining hours, approvals, dispatches, invoices, handoffs, knowledge, portal views, and rating
- single operational view for account review and service management

Menu and UI relation:

- `Helpdesk > Reporting > Customer Support Overview`
- `Customer Support Overview` tab on partner form

Main model relation:

- extension of `res.partner`

Cross-module relation:

- aggregates information from contracts, invoices, dispatches, approvals, sales handoffs, knowledge, and portal usage

### 4.15 `helpdesk_custom_field_service_report`

Feature purpose:

- formalizes field visit reporting after dispatch execution

Key functions:

- create visit report from dispatch
- report summary, checklist, findings, parts used, recommendations, and next steps
- customer acknowledgement and service closure steps

Menu and UI relation:

- dispatch button `Create Service Report`
- dispatch smart button `Service Reports`
- `Helpdesk > Reporting > Field Service Reports`

Main model relation:

- `helpdesk.field.service.report`
- `helpdesk.dispatch`

Cross-module relation:

- extends dispatch process
- gives stronger service evidence for customer review and internal operations

### 4.16 `helpdesk_custom_asset_coverage`

Feature purpose:

- maps support coverage down to site, branch, device, workspace, or business process level

Key functions:

- maintain support asset master data
- link assets to contracts
- relate tickets and dispatches to assets
- mark covered versus uncovered support scope

Menu and UI relation:

- `Helpdesk > Configuration > Support Assets`
- contract asset tab and smart button
- asset fields on ticket and dispatch

Main model relation:

- `helpdesk.support.asset`
- `helpdesk.support.contract`
- `helpdesk.ticket`
- `helpdesk.dispatch`

Cross-module relation:

- extends contract coverage
- extends dispatch execution
- feeds problem analysis and customer overview

### 4.17 `helpdesk_custom_problem_management`

Feature purpose:

- manages recurring issues, root causes, known errors, and permanent fix tracking

Key functions:

- create problem from ticket
- track state from investigation to known error and resolution
- link multiple tickets to one problem
- store workaround, RCA, and permanent fix plan

Menu and UI relation:

- ticket action `Create Problem`
- ticket smart button `Problem`
- `Helpdesk > Reporting > Problem Records`

Main model relation:

- `helpdesk.problem`
- `helpdesk.ticket`

Cross-module relation:

- links recurring incidents together
- can reference knowledge article
- uses escalation and asset context to measure impact
- creates a natural bridge to pending release-note tracking

### 4.18 `helpdesk_custom_customer_communication_log`

Feature purpose:

- creates a structured customer communication journal across channels

Key functions:

- stores inbound and outbound communication entries
- tracks channel, direction, communication type, status, source model, and summary
- exposes ticket communication count and latest channel
- logs demo and live communication events from portal, WhatsApp, and API integrations

Menu and UI relation:

- ticket smart button `Comms`
- ticket tab `Communication Log`
- `Helpdesk > Reporting > Customer Communication Log`

Main model relation:

- `helpdesk.communication.log`
- `helpdesk.ticket`

Cross-module relation:

- receives portal reply, feedback, close, and reopen events
- receives WhatsApp send and terminal failure events
- receives API ticket creation, reply, and close events
- can support future customer experience analytics or audit history

### 4.19 `helpdesk_custom_communication_analytics`

Feature purpose:

- provides operational reporting on customer communication responsiveness and channel behavior

Key functions:

- ticket-level communication analytics report
- inbound versus outbound communication trend by ticket
- failed-delivery visibility
- response-due detection when the last customer update has not yet been answered
- stale communication detection for open tickets with no recent update
- response bucket and inactivity bucket segmentation

Menu and UI relation:

- `Helpdesk > Reporting > Communication Analytics`

Main model relation:

- `helpdesk.communication.analytics.report`

Cross-module relation:

- consumes the structured records from `helpdesk.communication.log`
- complements KPI reporting with communication-specific metrics
- benefits portal, WhatsApp, API, and manual communication auditability

### 4.20 `helpdesk_custom_release_note_tracking`

Feature purpose:

- tracks fix rollout, release communication, and ticket impact after root cause identification

Key functions:

- manage release note records with version, severity, type, rollout state, and customer message
- link release notes to problems, tickets, knowledge articles, and communication logs
- log customer update actions directly from the release note
- surface release-note traceability on ticket, problem, knowledge, and communication views

Menu and UI relation:

- `Helpdesk > Reporting > Release Notes`
- ticket smart button `Release Notes`
- problem smart button `Release Notes`
- knowledge article smart button `Release Notes`

Main model relation:

- `helpdesk.release.note`
- `helpdesk.problem`
- `helpdesk.ticket`
- `document.page`
- `helpdesk.communication.log`

Cross-module relation:

- closes the gap between known error tracking and customer-facing fix communication
- extends problem management with release and rollout governance
- enriches communication log auditability with release context
- links knowledge articles to actual production fixes

### 4.21 `helpdesk_custom_contract_renewal`

Feature purpose:

- automates renewal watchlists for support contracts that are approaching expiry or need commercial follow-up

Key functions:

- detects expiring contracts and renewal-risk conditions
- creates renewal watch records with trigger type, risk level, probability, and follow-up date
- links renewal follow-up to sales handoff flow
- surfaces renewal watch indicators inside support contract and customer overview screens

Menu and UI relation:

- `Helpdesk > Reporting > Contract Renewals`
- support contract smart button `Renewals`
- contract page `Renewal`
- customer smart button `Renewals`
- customer page `Renewals`

Main model relation:

- `helpdesk.contract.renewal`
- `helpdesk.support.contract`
- `helpdesk.sales.handoff`
- `res.partner`

Cross-module relation:

- extends support contract monitoring into commercial renewal readiness
- reuses sales handoff for renewal escalation to commercial teams
- enriches Customer Support Overview with contract-risk visibility
- complements invoicing and contract coverage reporting

### 4.22 `helpdesk_custom_knowledge_portal`

Feature purpose:

- publishes selected support knowledge articles to customer-facing portal and public ticket journeys

Key functions:

- knowledge publication lifecycle from draft, review, approval, publication, and retirement
- article visibility by selected customer or active support contract
- suggested knowledge on public ticket tracking pages
- portal article feedback and ticket-deflection tracking
- portal home entry for customer knowledge browsing

Menu and UI relation:

- portal home card `Knowledge`
- portal list and detail pages for helpdesk knowledge
- public ticket page section `Suggested Knowledge Articles`
- knowledge article backend workflow fields and actions

Main model relation:

- `document.page`
- portal controllers in `helpdesk_custom_knowledge_portal`

Cross-module relation:

- extends internal knowledge management into self-service support
- integrates with public portal token flow
- uses support contract visibility for controlled publication
- feeds deflection metrics for future portal analytics

### 4.23 `helpdesk_custom_dispatch_execution`

Feature purpose:

- adds technician execution governance on top of dispatch scheduling and field reporting

Key functions:

- pre-departure checklist before travel can start
- travel start, arrival, and departure checkpoint timestamps
- structured evidence capture with dispatch-linked files and proof types
- customer sign-off decision tracking
- completion guardrails before dispatch close and service report submission

Menu and UI relation:

- dispatch header buttons `Leave Site`, `Mark Signed`, and `Sign-off Declined`
- dispatch smart button `Evidence`
- dispatch pages `Execution Control` and `Execution Evidence`
- field service report execution summary fields

Main model relation:

- `helpdesk.dispatch`
- `helpdesk.dispatch.evidence`
- `helpdesk.field.service.report`

Cross-module relation:

- extends dispatch scheduling with execution checkpoints
- enforces field service report quality through execution readiness rules
- complements asset coverage and onsite approvals
- improves auditability of onsite work and customer acceptance

### 4.24 `helpdesk_custom_contract_renewal_analytics`

Feature purpose:

- turns renewal watchlists into a measurable commercial pipeline with follow-up risk visibility

Key functions:

- renewal overview dashboard by company, team, and salesperson scope
- weighted renewal revenue and revenue-at-risk calculation
- overdue follow-up tracking and follow-up aging visibility
- expiry bucket and probability bucket analytics
- renewal risk segment summary in Customer Support Overview

Menu and UI relation:

- `Helpdesk > Reporting > Renewal Overview`
- `Helpdesk > Reporting > Renewal Analytics`
- extended tree and form visibility inside `Contract Renewals`
- customer page renewal risk indicators inside `Customer Support Overview`

Main model relation:

- `helpdesk.contract.renewal`
- `helpdesk.contract.renewal.analytics.dashboard`
- `helpdesk.contract.renewal.analytics.report`
- `res.partner`

Cross-module relation:

- extends `helpdesk_custom_contract_renewal` with pipeline and risk analytics
- enriches Customer Support Overview with renewal risk segmentation
- complements sales handoff by showing handoff-stage renewal pipeline value
- gives management visibility into renewal revenue exposure beyond operational contract tracking

### 4.25 `helpdesk_custom_service_review_pack`

Feature purpose:

- creates exportable executive service review packs for each customer

Key functions:

- generates customer review snapshots for a selected date range
- summarizes ticket volume, open risk, communication, dispatch, billing, contract coverage, and renewal exposure
- stores an executive summary snapshot for reuse and auditability
- prints the pack as a PDF report for service review meetings

Menu and UI relation:

- `Helpdesk > Reporting > Service Review Packs`
- customer smart button `Service Reviews`
- customer smart button `Generate Review`
- report action `Service Review Pack` from the pack form

Main model relation:

- `helpdesk.service.review.pack`
- `res.partner`

Cross-module relation:

- consumes Customer Support Overview logic at customer level
- consumes communication log, dispatch, invoice, contract, and renewal analytics data
- gives account and service managers a printable review artifact for periodic customer meetings

### 4.26 `helpdesk_custom_renewal_forecast`

Feature purpose:

- compares weighted renewal forecast against explicit target and budget values

Key functions:

- monthly target definition by overall scope, team, and salesperson
- forecast dashboard with target, budget, weighted forecast, pipeline, won value, and revenue-at-risk
- gap-to-target and attainment-rate visibility
- management review of whether renewal pipeline is enough to cover target and budget

Menu and UI relation:

- `Helpdesk > Reporting > Renewal Forecast`
- `Helpdesk > Configuration > Renewal Targets`

Main model relation:

- `helpdesk.renewal.target`
- `helpdesk.renewal.forecast.dashboard`

Cross-module relation:

- consumes commercial values from `helpdesk_custom_contract_renewal_analytics`
- gives management a planning layer on top of renewal watchlists
- complements service review and customer success planning with target-versus-pipeline context

### 4.27 `helpdesk_custom_customer_success_playbook`

Feature purpose:

- formalizes proactive customer-success follow-up outside reactive ticket handling

Key functions:

- playbooks for quarterly review, adoption check, renewal readiness, and risk recovery
- owner assignment and due-date based cadence
- proactive activity scheduling for account or service owners
- customer-level health state and action-plan tracking

Menu and UI relation:

- `Helpdesk > Reporting > Customer Success Playbooks`
- customer smart button `Playbooks`
- customer smart button `New Playbook`

Main model relation:

- `helpdesk.customer.success.playbook`
- `res.partner`

Cross-module relation:

- links customer, contract, and renewal context in one proactive follow-up record
- complements Customer Support Overview with success and risk action planning
- creates activities that push the team to act before renewal or support risk becomes urgent

### 4.28 `helpdesk_custom_service_review_distribution`

Feature purpose:

- automates scheduled delivery of executive service review packs

Key functions:

- recurring distribution schedule by customer
- recipient list management
- automatic pack generation for the chosen period
- PDF attachment generation and email queue creation
- run-now action for manual distribution testing

Menu and UI relation:

- `Helpdesk > Reporting > Service Review Distribution`

Main model relation:

- `helpdesk.service.review.distribution`
- `helpdesk.service.review.pack`
- `mail.mail`

Cross-module relation:

- depends on `helpdesk_custom_service_review_pack` for the exported document
- turns executive review packs into a repeatable customer-communication process
- complements customer success and renewal reviews by making service-review delivery operational

## 5. Cross-Module Process Map

### 5.1 Incident-to-resolution operational chain

Main chain:

- Ticket intake through backend, portal, or API
- SLA monitoring and escalation
- Agent handling and update logging
- Optional approval, dispatch, field report, or contract validation
- Optional billing, customer communication, knowledge capture, and problem tracking

### 5.2 Major integration dependencies

- `helpdesk_custom_portal` depends on `helpdesk_custom_escalation` and rating-related base modules
- `helpdesk_custom_knowledge_portal` depends on internal knowledge, portal, and contract visibility
- `helpdesk_custom_whatsapp` depends on escalation and portal/customer context
- `helpdesk_custom_api` depends on portal and KPI layers
- `helpdesk_custom_customer_communication_log` depends on portal, WhatsApp, API, and demo data
- `helpdesk_custom_contract` depends on timesheet support
- `helpdesk_custom_contract_renewal` depends on contract, sales handoff, and customer overview
- `helpdesk_custom_contract_renewal_analytics` depends on contract renewal and customer overview
- `helpdesk_custom_renewal_forecast` depends on renewal analytics and target master data
- `helpdesk_custom_customer_success_playbook` depends on renewal analytics and customer overview
- `helpdesk_custom_service_review_pack` depends on customer overview, communication log, invoice, dispatch, and renewal analytics
- `helpdesk_custom_service_review_distribution` depends on service review pack and outgoing mail queue
- `helpdesk_custom_asset_coverage` depends on contract and dispatch
- `helpdesk_custom_dispatch_execution` depends on dispatch and field service report
- `helpdesk_custom_problem_management` depends on knowledge, escalation, and asset coverage
- `helpdesk_custom_release_note_tracking` depends on problem management, communication log, and knowledge
- `helpdesk_custom_customer_360` aggregates data from contract, invoice, knowledge, dispatch, portal, and sales handoff modules

## 6. Current Scope Boundary

The following repository module exists but is outside this implementation recap:

- `helpdesk_custom_claude_ai`

Reason:

- it was already present in the repository and was not part of the Helpdesk delivery stream documented here

## 7. Recommended Reading Order

For technical review:

1. Start with baseline and demo data
2. Review ticket-facing extensions: portal, escalation, contract, approval, dispatch
3. Review reporting layer: KPI and Customer Support Overview
4. Review support governance layers: knowledge, knowledge portal, problem management, release notes, communication log
5. Review field execution layers: dispatch, dispatch execution, service report, asset coverage
6. Review integration and commercial layers: WhatsApp, API, sales handoff, contract renewal, renewal analytics, renewal forecast, customer success playbooks, service review packs, scheduled distribution, invoicing

For business walkthrough:

1. Demo data
2. Ticket Kanban and Calendar
3. Portal and communication
4. Escalation and KPI
5. Contract, approval, dispatch, service report
6. Customer Support Overview
7. Problem, release note, and knowledge management
8. Customer self-service knowledge
9. Commercial follow-up and renewal monitoring
