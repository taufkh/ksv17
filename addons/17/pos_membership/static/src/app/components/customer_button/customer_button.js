/** @odoo-module */

import { CustomerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/customer_button/customer_button";
import { patch } from "@web/core/utils/patch";

patch(CustomerButton.prototype, {
    get membershipPartnerInfo() {
        return this.pos.getMembershipPartnerInfo(this.partner);
    },
});
