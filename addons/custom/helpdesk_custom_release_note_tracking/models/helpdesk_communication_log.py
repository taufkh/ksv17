from odoo import fields, models


class HelpdeskCommunicationLog(models.Model):
    _inherit = "helpdesk.communication.log"

    release_note_id = fields.Many2one(
        "helpdesk.release.note",
        string="Release Note",
        ondelete="set null",
        index=True,
    )
