import base64
from datetime import timedelta

from odoo import _, api, fields, models


class HelpdeskServiceReviewDistribution(models.Model):
    _name = "helpdesk.service.review.distribution"
    _description = "Helpdesk Service Review Distribution"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "next_run_date asc, id desc"

    schedule_selection = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]
    period_selection = [
        ("current_month", "Current Month"),
        ("previous_month", "Previous Month"),
    ]
    state_selection = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("paused", "Paused"),
    ]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one("res.partner", required=True, domain=[("is_company", "=", True)], tracking=True)
    owner_id = fields.Many2one("res.users", default=lambda self: self.env.user, tracking=True, domain=[("share", "=", False)])
    recipient_ids = fields.Many2many("res.partner", string="Recipients", domain="[('parent_id', '=', partner_id)]")
    email_to = fields.Char(compute="_compute_email_to", store=True)
    schedule_type = fields.Selection(selection=schedule_selection, required=True, default="monthly", tracking=True)
    period_mode = fields.Selection(selection=period_selection, required=True, default="current_month", tracking=True)
    next_run_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    last_run_at = fields.Datetime(readonly=True, tracking=True)
    last_pack_id = fields.Many2one("helpdesk.service.review.pack", readonly=True, tracking=True)
    last_mail_id = fields.Many2one("mail.mail", readonly=True, tracking=True)
    state = fields.Selection(selection=state_selection, required=True, default="draft", tracking=True)
    note = fields.Html()

    @api.depends("recipient_ids.email")
    def _compute_email_to(self):
        for record in self:
            emails = [email for email in record.recipient_ids.mapped("email") if email]
            record.email_to = ",".join(emails)

    def _compute_period(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.period_mode == "previous_month":
            current_start = fields.Date.start_of(today, "month")
            end_date = current_start - timedelta(days=1)
            start_date = fields.Date.start_of(end_date, "month")
            return start_date, end_date
        return fields.Date.start_of(today, "month"), today

    def _compute_next_run_date(self):
        self.ensure_one()
        base = self.next_run_date or fields.Date.context_today(self)
        if self.schedule_type == "weekly":
            return base + timedelta(days=7)
        return fields.Date.add(base, months=1)

    def action_activate(self):
        self.write({"state": "active", "active": True})
        return True

    def action_pause(self):
        self.write({"state": "paused", "active": False})
        return True

    def _run_distribution(self):
        self.ensure_one()
        if not self.email_to:
            return False
        date_from, date_to = self._compute_period()
        pack = self.env["helpdesk.service.review.pack"].create(
            {
                "partner_id": self.partner_id.id,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        report_model = self.env["ir.actions.report"]
        pdf_bytes, report_format = report_model._render_qweb_pdf(
            "helpdesk_custom_service_review_pack.action_report_helpdesk_service_review_pack",
            pack.ids,
        )
        del report_format
        attachment = self.env["ir.attachment"].create(
            {
                "name": "%s.pdf" % pack.name,
                "type": "binary",
                "datas": base64.b64encode(pdf_bytes),
                "mimetype": "application/pdf",
                "res_model": "helpdesk.service.review.pack",
                "res_id": pack.id,
            }
        )
        mail = self.env["mail.mail"].create(
            {
                "subject": _("Service Review Pack - %(customer)s") % {"customer": self.partner_id.display_name},
                "body_html": _(
                    "<p>Please find the attached service review pack for %(customer)s.</p>"
                    "<p>Period: %(date_from)s to %(date_to)s.</p>"
                ) % {
                    "customer": self.partner_id.display_name,
                    "date_from": date_from,
                    "date_to": date_to,
                },
                "email_to": self.email_to,
                "attachment_ids": [(4, attachment.id)],
                "auto_delete": False,
            }
        )
        self.write(
            {
                "last_run_at": fields.Datetime.now(),
                "last_pack_id": pack.id,
                "last_mail_id": mail.id,
                "next_run_date": self._compute_next_run_date(),
                "state": "active",
                "active": True,
            }
        )
        self.message_post(body=_("Service review pack %(pack)s queued for distribution.") % {"pack": pack.display_name})
        return True

    def action_run_now(self):
        for record in self:
            record._run_distribution()
        return True

    @api.model
    def _cron_run_due_distributions(self):
        due = self.search(
            [
                ("active", "=", True),
                ("state", "=", "active"),
                ("next_run_date", "<=", fields.Date.context_today(self)),
            ]
        )
        for record in due:
            record._run_distribution()
        return True
