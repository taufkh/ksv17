/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup(env, services) {
        await super.setup(...arguments);
        if (services?.barcode_reader) {
            services.barcode_reader.membershipPos = this;
        }
    },

    async _processData(loadedData) {
        await super._processData(...arguments);
        this.membershipRewardConfigs = loadedData["daily.free.product.config"] || [];
        this.membershipConfig = {
            barcodePrefix: this.company.membership_barcode_prefix || "MBR",
            pointSpendAmount: this.company.membership_point_spend_amount || 0,
            pointValue: this.company.membership_point_value || 0,
            topupProductId: this.company.membership_topup_product_id?.[0] || false,
            depositPaymentMethodId: this.company.membership_deposit_payment_method_id?.[0] || false,
            autoLoadMembers: this.company.membership_auto_load_members,
        };
    },

    isMembershipBarcode(barcode) {
        const prefix = (this.membershipConfig?.barcodePrefix || "MBR").toUpperCase();
        return typeof barcode === "string" && barcode.toUpperCase().startsWith(`${prefix}-`);
    },

    getMembershipPartnerByBarcode(barcode) {
        return (this.partners || []).find(
            (partner) => partner.is_custom_member && partner.custom_member_barcode === barcode
        );
    },

    getMembershipRewardConfig() {
        return (this.membershipRewardConfigs || [])[0] || false;
    },

    getMembershipDepositPaymentMethod() {
        const methodId = this.membershipConfig?.depositPaymentMethodId;
        return (this.payment_methods || []).find(
            (paymentMethod) => paymentMethod.id === methodId || paymentMethod.is_membership_deposit
        );
    },

    isMembershipTopupProduct(product) {
        return !!product && product.id === this.membershipConfig?.topupProductId;
    },

    getMembershipPartnerInfo(partner) {
        if (!partner || !partner.is_custom_member) {
            return {
                isMember: false,
                badgeLabel: _t("Guest"),
                depositBalance: 0,
                totalPoints: 0,
            };
        }
        return {
            isMember: true,
            badgeLabel: partner.custom_member_type === "paid" ? _t("Paid") : _t("Free"),
            depositBalance: partner.total_deposit_balance || 0,
            totalPoints: partner.total_points || 0,
            barcode: partner.custom_member_barcode || "",
        };
    },

    async refreshMembershipPartner(partner) {
        if (!partner?.id) {
            return partner;
        }
        const payload = await this.orm.call("res.partner", "get_membership_snapshot", [partner.id]);
        Object.assign(partner, payload || {});
        this.db.update_partners([partner]);
        return partner;
    },
});
