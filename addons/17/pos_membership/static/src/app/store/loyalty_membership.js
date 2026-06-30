/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

const { DateTime } = luxon;

patch(Order.prototype, {
    _isMembershipOnlyProgram(program) {
        return !!program?.membership_only;
    },

    _canUseMembershipProgram(program) {
        if (!this._isMembershipOnlyProgram(program)) {
            return true;
        }
        return !!this.get_partner()?.is_custom_member;
    },

    _getMembershipAutoRuleIds() {
        return (this.pos.programs || [])
            .filter((program) => this._isMembershipOnlyProgram(program) && this._canUseMembershipProgram(program))
            .flatMap((program) => (program.rules || []).map((rule) => rule.id))
            .filter(Boolean);
    },

    async _updatePrograms() {
        const extraRuleIds = this._getMembershipAutoRuleIds().filter(
            (ruleId) => !this.codeActivatedProgramRules.includes(ruleId)
        );
        if (!extraRuleIds.length) {
            return await super._updatePrograms(...arguments);
        }
        this.codeActivatedProgramRules.push(...extraRuleIds);
        try {
            return await super._updatePrograms(...arguments);
        } finally {
            this.codeActivatedProgramRules = this.codeActivatedProgramRules.filter(
                (ruleId) => !extraRuleIds.includes(ruleId)
            );
        }
    },

    _programIsApplicable(program) {
        if (!this._canUseMembershipProgram(program)) {
            return false;
        }
        if (this._isMembershipOnlyProgram(program)) {
            if (program.date_from && program.date_from.startOf("day") > DateTime.now()) {
                return false;
            }
            if (program.date_to && program.date_to.endOf("day") < DateTime.now()) {
                return false;
            }
            if (program.limit_usage && program.total_order_count >= program.max_usage) {
                return false;
            }
            if (
                program.pricelist_ids.length > 0 &&
                (!this.pricelist || !program.pricelist_ids.includes(this.pricelist.id))
            ) {
                return false;
            }
            return true;
        }
        return super._programIsApplicable(...arguments);
    },
});
