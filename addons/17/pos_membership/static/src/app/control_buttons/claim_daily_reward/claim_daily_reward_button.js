/** @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { useService } from "@web/core/utils/hooks";

export class ClaimDailyRewardButton extends Component {
    static template = "pos_membership.ClaimDailyRewardButton";

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.popup = useService("popup");
    }

    async onClick() {
        const order = this.pos.get_order();
        const partner = order?.get_partner();
        if (!order || !partner?.is_custom_member) {
            await this.popup.add(ErrorPopup, {
                title: "Member Required",
                body: "Select a member before claiming the daily reward.",
            });
            return;
        }
        const rewardStatus = await this.orm.call(
            "pos.session",
            "get_membership_reward_status",
            [this.pos.pos_session.id, partner.id]
        );
        if (!rewardStatus?.reward_product_id) {
            await this.popup.add(ErrorPopup, {
                title: "No Reward Configured",
                body: "There is no active daily reward for today.",
            });
            return;
        }
        if (rewardStatus.already_claimed || !rewardStatus.eligible) {
            await this.popup.add(ErrorPopup, {
                title: "Daily Reward Sudah Diklaim",
                body: "Daily reward hanya dapat diklaim 1 kali per hari.",
            });
            return;
        }
        const rewardProducts = (rewardStatus.reward_products || [])
            .map((reward) => this.pos.db.product_by_id[reward.id])
            .filter(Boolean);
        if (!rewardProducts.length) {
            await this.popup.add(ErrorPopup, {
                title: "Reward Product Missing",
                body: "Produk reward tidak tersedia di sesi POS ini.",
            });
            return;
        }
        let selectedProduct = rewardProducts[0];
        if (rewardProducts.length > 1) {
            const { confirmed, payload } = await this.popup.add(SelectionPopup, {
                title: _t("Pilih Daily Reward"),
                list: rewardProducts.map((product) => ({
                    id: product.id,
                    label: product.display_name,
                    item: product.id,
                    isSelected: product.id === order.membership_claim_product_id,
                })),
            });
            if (!confirmed || !payload) {
                return;
            }
            selectedProduct = this.pos.db.product_by_id[payload];
        }
        if (!selectedProduct) {
            return;
        }
        await order.setMembershipRewardProduct(selectedProduct);
    }
}

ProductScreen.addControlButton({
    component: ClaimDailyRewardButton,
    position: ["before", "CustomerButton"],
    condition() {
        return !!this.pos.getMembershipRewardConfig();
    },
});
