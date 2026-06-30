/** @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

export class OnlineCheckerRecapButton extends Component {
    static template = "pos_sale_channel.OnlineCheckerRecapButton";
    static props = {};

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("pos_notification");
    }

    async onClick() {
        const configId = this.pos.config?.id;
        if (!configId) {
            return;
        }
        const reportWindow = window.open("", "_blank");
        const url = await this.orm.call("pos.config", "get_online_checker_recap_url", [[configId]]);
        if (!url) {
            reportWindow?.close();
            this.notification.add(_t("Online checker recap URL is not available."));
            return;
        }
        if (reportWindow) {
            reportWindow.location = url;
        } else {
            window.location = url;
        }
    }
}

ProductScreen.addControlButton({
    component: OnlineCheckerRecapButton,
    position: ["before", "CustomerButton"],
    condition: function () {
        return (this.pos.config?.online_checker_channel_ids || []).length > 0;
    },
});
