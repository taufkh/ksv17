/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Order, Orderline } from "@point_of_sale/app/store/models";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(Orderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.membership_reward_line = this.membership_reward_line || false;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.membership_reward_line = !!json.membership_reward_line;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.membership_reward_line = !!this.membership_reward_line;
        return json;
    },
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.membership_claim_reward = this.membership_claim_reward || false;
        this.membership_claim_product_id = this.membership_claim_product_id || false;
        this.membership_claim_product_name = this.membership_claim_product_name || false;
        this.membership_points_earned_preview = this.membership_points_earned_preview || 0;
        this.membership_balance_after = this.membership_balance_after || 0;
        this.membership_points_total_after = this.membership_points_total_after || 0;
        this.membership_deposit_amount_used = this.membership_deposit_amount_used || 0;
        this.membership_topup_amount = this.membership_topup_amount || 0;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.membership_claim_reward = !!json.membership_claim_reward;
        this.membership_claim_product_id = json.membership_claim_product_id || false;
        this.membership_claim_product_name = json.membership_claim_product_name || false;
        this.membership_points_earned_preview = json.membership_points_earned_preview || json.membership_points_earned || 0;
        this.membership_balance_after = json.membership_balance_after || 0;
        this.membership_points_total_after = json.membership_points_total || 0;
        this.membership_deposit_amount_used = json.membership_deposit_amount_used || 0;
        this.membership_topup_amount = json.membership_topup_amount || 0;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.membership_claim_reward = !!this.membership_claim_reward;
        json.membership_claim_product_id = this.membership_claim_product_id || false;
        json.membership_points_earned_preview = this.getMembershipPointsPreview();
        json.membership_deposit_amount_used = this.getMembershipDepositPaymentAmount();
        json.membership_topup_amount = this.getMembershipTopupAmount();
        return json;
    },

    add_paymentline(paymentMethod) {
        if (paymentMethod?.is_membership_deposit) {
            const partner = this.get_partner();
            if (!partner?.is_custom_member) {
                this.pos.popup.add(ErrorPopup, {
                    title: "Membership Required",
                    body: "Select a member before using deposit payment.",
                });
                return false;
            }
        }
        const line = super.add_paymentline(...arguments);
        if (line && paymentMethod?.is_membership_deposit) {
            const availableBalance = this.get_partner()?.total_deposit_balance || 0;
            line.set_amount(Math.min(line.amount || 0, availableBalance));
        }
        return line;
    },

    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        const partner = this.get_partner();
        const memberInfo = this.pos.getMembershipPartnerInfo(partner);
        result.membership = {
            is_member: memberInfo.isMember,
            badge_label: memberInfo.badgeLabel,
            barcode: memberInfo.barcode,
            deposit_balance: this.membership_balance_after || partner?.total_deposit_balance || 0,
            total_points: this.membership_points_total_after || partner?.total_points || 0,
            points_earned: this.membership_points_earned_preview || 0,
            deposit_used: this.membership_deposit_amount_used || this.getMembershipDepositPaymentAmount(),
            topup_amount: this.membership_topup_amount || this.getMembershipTopupAmount(),
            claim_reward: this.membership_claim_reward,
            claim_product_name: this.membership_claim_product_name,
        };
        return result;
    },

    setMembershipReceiptData(data) {
        this.membership_balance_after = data.membership_balance_after || 0;
        this.membership_points_total_after = data.membership_points_total || 0;
        this.membership_points_earned_preview = data.membership_points_earned || 0;
        this.membership_deposit_amount_used = data.membership_deposit_amount_used || 0;
        this.membership_topup_amount = data.membership_topup_amount || 0;
        this.membership_claim_reward = !!data.membership_claim_reward;
        this.membership_claim_product_name = data.membership_claim_product_name || this.membership_claim_product_name;
    },

    getMembershipRewardLines() {
        return this.get_orderlines().filter((line) => line.membership_reward_line);
    },

    clearMembershipReward() {
        for (const line of [...this.getMembershipRewardLines()]) {
            this.removeOrderline(line);
        }
        this.membership_claim_reward = false;
        this.membership_claim_product_id = false;
        this.membership_claim_product_name = false;
    },

    async setMembershipRewardProduct(product) {
        this.assert_editable();
        this.clearMembershipReward();
        await this.add_product(product, { merge: false });
        const line = this.get_selected_orderline();
        if (line) {
            line.membership_reward_line = true;
            line.set_unit_price(0);
        }
        this.membership_claim_reward = true;
        this.membership_claim_product_id = product.id;
        this.membership_claim_product_name = product.display_name;
    },

    getMembershipTopupAmount() {
        return this.get_orderlines()
            .filter((line) => this.pos.isMembershipTopupProduct(line.get_product()))
            .reduce((sum, line) => sum + Math.max(0, line.get_price_with_tax()), 0);
    },

    getMembershipDepositPaymentAmount() {
        return this.get_paymentlines()
            .filter((line) => line.payment_method?.is_membership_deposit)
            .reduce((sum, line) => sum + Math.max(0, line.amount || 0), 0);
    },

    getMembershipPointsPreview() {
        const spendAmount = this.pos.membershipConfig?.pointSpendAmount || 0;
        const pointValue = this.pos.membershipConfig?.pointValue || 0;
        if (spendAmount <= 0 || pointValue <= 0) {
            return 0;
        }
        const totalEligible = this.get_orderlines()
            .filter(
                (line) =>
                    line.get_quantity() > 0 &&
                    !this.pos.isMembershipTopupProduct(line.get_product()) &&
                    !line.membership_reward_line
            )
            .reduce((sum, line) => sum + Math.max(0, line.get_price_with_tax()), 0);
        return Math.floor(totalEligible / spendAmount) * pointValue;
    },

    set_partner(partner) {
        const result = super.set_partner(...arguments);
        if (!partner?.is_custom_member) {
            this.clearMembershipReward();
            for (const line of [...this.get_paymentlines()]) {
                if (line.payment_method?.is_membership_deposit) {
                    this.remove_paymentline(line);
                }
            }
        } else {
            const availableBalance = partner.total_deposit_balance || 0;
            if (this.getMembershipDepositPaymentAmount() > availableBalance) {
                for (const line of [...this.get_paymentlines()]) {
                    if (line.payment_method?.is_membership_deposit) {
                        this.remove_paymentline(line);
                    }
                }
            }
        }
        return result;
    },
});

patch(PaymentScreen.prototype, {
    get membershipPartnerInfo() {
        return this.pos.getMembershipPartnerInfo(this.currentOrder.get_partner());
    },

    async _isOrderValid(isForceValidate) {
        const result = await super._isOrderValid(...arguments);
        if (!result) {
            return false;
        }
        const partner = this.currentOrder.get_partner();
        const depositAmount = this.currentOrder.getMembershipDepositPaymentAmount();
        if (!depositAmount) {
            return true;
        }
        if (!partner?.is_custom_member) {
            this.popup.add(ErrorPopup, {
                title: "Membership Required",
                body: "Deposit payment can only be used by a registered member.",
            });
            return false;
        }
        const availableBalance = partner.total_deposit_balance || 0;
        if (depositAmount - availableBalance > 0.00001) {
            this.popup.add(ErrorPopup, {
                title: "Insufficient Deposit",
                body: `Available deposit is ${this.env.utils.formatCurrency(availableBalance)}.`,
            });
            return false;
        }
        return true;
    },

    async _postPushOrderResolve(order, order_server_ids) {
        const result = await super._postPushOrderResolve(...arguments);
        const membershipData = await this.orm.call("pos.order", "read_membership_receipt_data", [order_server_ids]);
        if (membershipData?.[0]) {
            order.setMembershipReceiptData(membershipData[0]);
        }
        const partner = order.get_partner();
        if (partner) {
            await this.pos.refreshMembershipPartner(partner);
        }
        return result;
    },
});
