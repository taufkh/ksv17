/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { BarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_service";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(BarcodeReader.prototype, {
    async scan(barcode) {
        if (this.membershipPos?.isMembershipBarcode(barcode)) {
            let partner = this.membershipPos.getMembershipPartnerByBarcode(barcode);
            if (!partner) {
                const payload = await this.membershipPos.orm.call(
                    "pos.session",
                    "resolve_membership_barcode",
                    [this.membershipPos.pos_session.id, barcode]
                );
                if (payload?.id) {
                    partner = this.membershipPos.db.partner_by_id[payload.id];
                    if (partner) {
                        Object.assign(partner, payload);
                        this.membershipPos.db.update_partners([partner]);
                    }
                }
            }
            if (!partner) {
                this.membershipPos.popup.add(ErrorPopup, {
                    title: "Member Not Found",
                    body: `No member is registered with barcode ${barcode}.`,
                });
                return;
            }
            const order = this.membershipPos.get_order();
            if (order) {
                order.set_partner(partner);
            }
            return;
        }
        return super.scan(...arguments);
    },
});
