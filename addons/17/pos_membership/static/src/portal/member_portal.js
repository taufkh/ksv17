/** @odoo-module */

import { renderSimpleBarcode } from "@pos_membership/lib/barcode_renderer";

function setupMemberPortal() {
    const container = document.getElementById("member_barcode_canvas");
    if (!container) {
        return;
    }
    renderSimpleBarcode(container, container.dataset.barcode);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupMemberPortal);
} else {
    setupMemberPortal();
}
