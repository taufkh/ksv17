from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    whatsapp_message_ids = fields.One2many(
        "helpdesk.whatsapp.message",
        "ticket_id",
        string="WhatsApp Messages",
    )
    whatsapp_message_count = fields.Integer(compute="_compute_whatsapp_message_count")

    @api.depends("whatsapp_message_ids")
    def _compute_whatsapp_message_count(self):
        data = self.env["helpdesk.whatsapp.message"].read_group(
            [("ticket_id", "in", self.ids)],
            ["ticket_id"],
            ["ticket_id"],
        )
        counts = {item["ticket_id"][0]: item["ticket_id_count"] for item in data}
        for ticket in self:
            ticket.whatsapp_message_count = counts.get(ticket.id, 0)

    def action_view_whatsapp_messages(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "helpdesk_custom_whatsapp.action_helpdesk_whatsapp_message"
        )
        action["domain"] = [("ticket_id", "=", self.id)]
        action["context"] = {"default_ticket_id": self.id}
        return action

    def _queue_whatsapp_notifications(self, trigger, event=False, extra_context=None):
        queue_model = self.env["helpdesk.whatsapp.message"].sudo()
        template_model = self.env["helpdesk.whatsapp.template"].sudo()
        for ticket in self:
            templates = template_model._get_candidate_templates(ticket, trigger)
            for template in templates:
                if (
                    template.recipient_type == "customer"
                    and "public_portal_notify_whatsapp" in ticket._fields
                    and not ticket.public_portal_notify_whatsapp
                ):
                    continue
                recipients = template._get_recipient_partners(ticket, event=event)
                if not recipients:
                    continue
                for partner in recipients:
                    phone = queue_model._normalize_phone(partner.mobile or partner.phone)
                    if not phone:
                        queue_model.create(
                            {
                                "ticket_id": ticket.id,
                                "template_id": template.id,
                                "trigger": trigger,
                                "recipient_partner_id": partner.id,
                                "recipient_name": partner.name or _("Unknown"),
                                "recipient_phone": _("Missing phone"),
                                "body": template._render_message_body(
                                    ticket,
                                    event=event,
                                    recipient=partner,
                                    extra_context=extra_context,
                                ),
                                "state": "failed",
                                "max_attempts": queue_model._get_max_attempts(),
                                "error_message": _(
                                    "Recipient does not have a mobile or phone number."
                                ),
                                "source_model": event._name if event else False,
                                "source_res_id": event.id if event else False,
                            }
                        )
                        continue
                    queue_model.create(
                        queue_model._prepare_queue_values(
                            ticket,
                            template,
                            partner,
                            phone,
                            template._render_message_body(
                                ticket,
                                event=event,
                                recipient=partner,
                                extra_context=extra_context,
                            ),
                            trigger,
                            source_record=event,
                        )
                    )
        return True

    def write(self, vals):
        tracking = {}
        should_track = not self.env.context.get("skip_helpdesk_whatsapp")
        if should_track and "stage_id" in vals:
            for ticket in self:
                tracking[ticket.id] = {
                    "stage_id": ticket.stage_id.id,
                    "stage_name": ticket.stage_id.name,
                    "closed": ticket.closed,
                }
        result = super().write(vals)
        if should_track and "stage_id" in vals:
            for ticket in self:
                previous = tracking.get(ticket.id)
                if not previous or previous["stage_id"] == ticket.stage_id.id:
                    continue
                extra_context = {
                    "previous_stage_name": previous["stage_name"],
                    "changed_by_name": self.env.user.name,
                }
                ticket._queue_whatsapp_notifications(
                    "stage_update",
                    extra_context=extra_context,
                )
                if not previous["closed"] and ticket.closed:
                    ticket._queue_whatsapp_notifications(
                        "ticket_closed",
                        extra_context=extra_context,
                    )
        return result
