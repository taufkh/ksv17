from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseOrderSignatureWizard(models.TransientModel):
    _name = "purchase.order.signature.wizard"
    _description = "Purchase Order Signature Wizard"

    purchase_order_id = fields.Many2one("purchase.order", required=True, readonly=True)
    action_type = fields.Selection(
        [
            ("request", "Request Approval"),
            ("approve", "Approve Order"),
        ],
        required=True,
        readonly=True,
    )
    signer_name = fields.Char(required=True, readonly=True)
    signature = fields.Binary(required=True)

    def action_confirm_signature(self):
        self.ensure_one()
        if not self.signature:
            raise UserError(_("A signature is required."))
        if "sign_signature" in self.env.user._fields:
            self.env.user.sudo().write({"sign_signature": self.signature})
        if self.action_type == "request":
            self.purchase_order_id.action_sign_request_approval(self.signature)
        else:
            self.purchase_order_id.action_sign_approve_order(self.signature)
        return {"type": "ir.actions.act_window_close"}
