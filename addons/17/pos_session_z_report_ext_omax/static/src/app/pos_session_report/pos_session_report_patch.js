/** @odoo-module */

import { Component } from "@odoo/owl";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

export class SessionReportButton extends Component {
    static template = "pos_session_z_report_ext_omax.SessionReportButton";

    setup() {
        this.pos = usePos();
        this.report = useService("report");
    }

    async onClick() {
        try {
            this.pos.showScreen("SessionReportPreviewScreen");
        } catch (error) {
            console.error("Error opening SessionReportPreviewScreen:", error);
            await this.report.doAction("pos_session_z_report_ext_omax.action_report_session_z", {
                additionalContext: {
                    active_ids: [this.pos.pos_session.id],
                    active_id: this.pos.pos_session.id,
                    active_model: "pos.session",
                },
            });
        }
    }
}

ProductScreen.addControlButton({
    component: SessionReportButton,
    position: ["before", "CustomerButton"],
    condition() {
        return Boolean(this.pos.config?.omax_session_z_report);
    },
});

patch(ClosePosPopup.prototype, {
    async onClickSessionReport() {
        this.props.close();
        this.pos.showScreen("SessionReportPreviewScreen");
    },
});
