# Helpdesk Customization Docs

This folder contains the implementation recap and pending backlog for the custom Helpdesk stack developed in this repository for database `ksv17-dev`.

Available documents:

- `helpdesk_customization_recap.md`
  Complete recap of delivered features, module purpose, key functions, menu exposure, main models, and cross-module relations.
- `helpdesk_pending_backlog.md`
  Pending items that have not been developed yet, including recommended scope and implementation direction.
- `helpdesk_user_guide_end_to_end.md`
  Operational user guide with end-to-end business scenarios, role-based usage, and menu-by-menu execution flow.
- `helpdesk_quick_start.md`
  One-page quick start for non-technical users covering daily operational flow and key menus.
- `helpdesk_customer_portal_guide.md`
  Customer-side portal usage guide with end-to-end scenarios (update, attachment, close/reopen, and feedback flow).
- `scripts/helpdesk_functional_smoke_test.py`
  Repeatable functional smoke test for API and public portal flows.

Smoke test execution:

- Run inside the Odoo web container:
  `docker exec -i odoo17-docker-community-web-1 python3 /mnt/extra-addons/docs/scripts/helpdesk_functional_smoke_test.py`
- Optional parameters:
  `--base-url`, `--db`, `--api-token`, `--reference-ticket`, `--no-cleanup`
- Daily runner (host shell wrapper):
  `bash /Users/taufikhidayat/Documents/Projects/Odoo/odoo17-docker-community/addons/docs/scripts/run_helpdesk_smoke_daily.sh`
- Example crontab (daily 08:00 server time):
  `0 8 * * * bash /Users/taufikhidayat/Documents/Projects/Odoo/odoo17-docker-community/addons/docs/scripts/run_helpdesk_smoke_daily.sh`

Automated API test suite:

- Test file:
  `addons/custom/helpdesk_custom_api/tests/test_helpdesk_custom_api.py`
- Run tests:
  `docker exec -i odoo17-docker-community-web-1 /usr/bin/odoo -c /etc/odoo/odoo.conf --http-port=8071 -d ksv17-dev -u helpdesk_custom_api --test-enable --test-tags /helpdesk_custom_api --stop-after-init`

Scope note:

- This documentation focuses on the custom modules developed in the current Helpdesk implementation stream.
- Existing modules that were already present in the repository but not part of this implementation stream, such as `helpdesk_custom_claude_ai`, are not included as delivered scope.
