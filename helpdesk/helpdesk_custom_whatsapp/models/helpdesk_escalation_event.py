from odoo import api, models


class HelpdeskEscalationEvent(models.Model):
    _inherit = "helpdesk.escalation.event"

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        if not self.env.context.get("skip_helpdesk_whatsapp"):
            for event in events:
                event.ticket_id.with_context(
                    skip_helpdesk_whatsapp=True
                )._queue_whatsapp_notifications("escalation", event=event)
        return events
