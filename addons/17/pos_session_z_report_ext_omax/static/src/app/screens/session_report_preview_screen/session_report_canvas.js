/** @odoo-module */

import { Component } from "@odoo/owl";

export class SessionReportCanvas extends Component {
    static template = "pos_session_z_report_ext_omax.SessionReportCanvas";
    static props = {
        canvasDataUrl: String,
    };
}
