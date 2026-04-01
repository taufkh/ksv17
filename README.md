# Odoo 17 Docker Community Workspace

This repository is the workspace wrapper for the local Odoo 17 stack in `odoo17-docker-community`.

## Layout

- `Dockerfile`, `docker-compose.yml`, `config/`
  Runtime and container configuration for the local Odoo stack.
- `addons/custom/`
  Project-owned custom modules and local extensions that should be versioned in this repository.
- `addons/docs/`
  Functional documentation, runbooks, and smoke-test helpers.
- `addons/v17/`
  Upstream addon repositories kept locally as separate git repositories.
- `enterprise/`
  Odoo Enterprise checkout, kept as its own git repository and excluded from this repo.
- `helpdesk_mcp_server/`
  Local MCP helper service for Helpdesk workflows.

## Git Scope

This root repository intentionally tracks only workspace-level files and custom addons.

Ignored from this repository:

- `enterprise/`
- `addons/server-tools/`
- upstream repos under `addons/v17/`:
  `helpdesk`, `knowledge`, `management-system`, `project`, `timesheet`, `web`, `website`
- runtime outputs such as `logs/`, `.DS_Store`, and temporary HTML files

## Odoo Addons Path

Custom modules now live in `addons/custom/` and are loaded first by `config/odoo.conf`.

## Recommended Workflow

1. Manage project-owned modules in `addons/custom/`.
2. Keep upstream repositories updated inside `addons/v17/` and `enterprise/` using their own git remotes.
3. Use this root repository to version Docker/config/docs/customizations that define the overall workspace.
