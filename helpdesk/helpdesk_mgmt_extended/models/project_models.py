# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ProjectProject(models.Model):
    _inherit = "project.project"

    ticket_ids = fields.One2many(
        "helpdesk.ticket",
        "project_id",
        string="Helpdesk Tickets",
    )
    ticket_count = fields.Integer(
        string="Tickets",
        compute="_compute_ticket_count",
    )

    def _compute_ticket_count(self):
        data = self.env["helpdesk.ticket"].read_group(
            [("project_id", "in", self.ids)],
            ["project_id"],
            ["project_id"],
        )
        mapping = {d["project_id"][0]: d["project_id_count"] for d in data}
        for project in self:
            project.ticket_count = mapping.get(project.id, 0)

    def action_open_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tickets"),
            "res_model": "helpdesk.ticket",
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
        }


class ProjectTask(models.Model):
    _inherit = "project.task"

    ticket_ids = fields.Many2many(
        "helpdesk.ticket",
        "helpdesk_ticket_task_rel",
        "task_id",
        "ticket_id",
        string="Helpdesk Tickets",
    )
    ticket_count = fields.Integer(
        string="Tickets",
        compute="_compute_ticket_count",
    )

    def _compute_ticket_count(self):
        for task in self:
            task.ticket_count = len(task.ticket_ids)

    def action_open_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tickets"),
            "res_model": "helpdesk.ticket",
            "view_mode": "list,form",
            "domain": [("task_id", "=", self.id)],
        }
