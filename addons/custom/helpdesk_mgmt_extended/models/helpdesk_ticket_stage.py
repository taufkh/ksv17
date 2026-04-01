# -*- coding: utf-8 -*-
from odoo import fields, models


class HelpdeskTicketStage(models.Model):
    """Extend the base stage with rating template and stage-validation fields."""
    _inherit = "helpdesk.ticket.stage"

    # ── Rating (helpdesk_mgmt_rating) ─────────────────────────────────────────
    rating_mail_template_id = fields.Many2one(
        "mail.template",
        string="Rating Email Template",
        domain=[("model", "=", "helpdesk.ticket")],
        help="When a ticket reaches this stage an email is sent to the customer "
             "asking them to rate the support they received.",
    )

    # ── Stage Validation (helpdesk_mgmt_stage_validation) ────────────────────
    validate_field_ids = fields.Many2many(
        "ir.model.fields",
        "helpdesk_stage_validate_field_rel",
        "stage_id",
        "field_id",
        string="Required Fields",
        domain=[("model", "=", "helpdesk.ticket"), ("ttype", "not in", ["one2many", "many2many"])],
        help="Fields that must be filled before a ticket can move to this stage.",
    )
