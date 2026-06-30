/** @odoo-module */

import { Component } from "@odoo/owl";

export class MembershipBadge extends Component {
    static template = "pos_membership.MembershipBadge";
    static props = {
        badgeLabel: String,
        depositBalance: Number,
        totalPoints: Number,
        barcode: { type: String, optional: true },
    };
}
