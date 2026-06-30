/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Navbar } from "@point_of_sale/app/navbar/navbar";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    shouldShowOnlineCheckerRecap() {
        return (this.pos.config?.online_checker_channel_ids || []).length > 0;
    },

    async onOnlineCheckerRecapClick() {
        this.closeMenu();
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
    },
});
