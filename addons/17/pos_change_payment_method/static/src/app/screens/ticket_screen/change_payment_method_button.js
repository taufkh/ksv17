/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.popup = useService("popup");
    },

    getSelectedOrderPaymentMethodLabel() {
        const order = this.getSelectedOrder?.();
        return order?.payment_method_label || _t("Tap button to load payment method");
    },

    getSelectedOrderSaleChannelLabel() {
        const order = this.getSelectedOrder?.();
        return order?.sale_channel_label || _t("Tap button to load sales channel");
    },

    selectedOrderCanChangePaymentMethod() {
        const order = this.getSelectedOrder?.();
        return !!order?.backendId;
    },

    selectedOrderCanChangeSaleChannel() {
        const order = this.getSelectedOrder?.();
        return !!order?.backendId;
    },

    async changeSelectedOrderPaymentMethod() {
        const order = this.getSelectedOrder?.();
        if (!order?.backendId) {
            return;
        }

        let changeData;
        try {
            changeData = await this.orm.call("pos.order", "get_payment_method_change_data", [
                order.backendId,
                this.pos.pos_session?.id || false,
            ]);
            Object.assign(order, changeData?.order || {});
            this.render(true);
        } catch (error) {
            const errorMessage =
                error?.data?.message ||
                error?.message ||
                error?.cause?.message ||
                _t("The selected order cannot be corrected.");
            await this.popup.add(ErrorPopup, {
                title: _t("Unable to Change Payment Method"),
                body: errorMessage,
            });
            return;
        }

        if (!changeData?.payment_methods?.length) {
            await this.popup.add(ErrorPopup, {
                title: _t("No Available Payment Method"),
                body: _t("There is no alternative payment method available for this order."),
            });
            return;
        }

        const { confirmed: pinConfirmed, payload: supervisorPin } = await this.popup.add(NumberPopup, {
            title: _t("Enter Supervisor PIN"),
            nbrDecimal: 0,
        });
        if (!pinConfirmed || !supervisorPin) {
            return;
        }

        const { confirmed: methodConfirmed, payload: paymentMethodId } = await this.popup.add(SelectionPopup, {
            title: _t("Select New Payment Method"),
            list: changeData.payment_methods.map((method) => ({
                id: method.id,
                label: method.name,
                item: method.id,
                isSelected: false,
            })),
        });
        if (!methodConfirmed || !paymentMethodId) {
            return;
        }

        try {
            const result = await this.orm.call("pos.order", "change_payment_method_from_pos", [
                order.backendId,
                paymentMethodId,
                String(supervisorPin),
                this.pos.pos_session?.id || false,
            ]);
            Object.assign(order, result?.order || {});
            this.render(true);
        } catch (error) {
            const errorMessage =
                error?.data?.message ||
                error?.message ||
                error?.cause?.message ||
                _t("The payment method could not be updated.");
            await this.popup.add(ErrorPopup, {
                title: _t("Payment Method Not Changed"),
                body: errorMessage,
            });
        }
    },

    async changeSelectedOrderSaleChannel() {
        const order = this.getSelectedOrder?.();
        if (!order?.backendId) {
            return;
        }

        let changeData;
        try {
            changeData = await this.orm.call("pos.order", "get_sale_channel_change_data", [
                order.backendId,
                this.pos.pos_session?.id || false,
            ]);
            Object.assign(order, changeData?.order || {});
            this.render(true);
        } catch (error) {
            const errorMessage =
                error?.data?.message ||
                error?.message ||
                error?.cause?.message ||
                _t("The selected order cannot be corrected.");
            await this.popup.add(ErrorPopup, {
                title: _t("Unable to Change Sales Channel"),
                body: errorMessage,
            });
            return;
        }

        if (!changeData?.sale_channels?.length) {
            await this.popup.add(ErrorPopup, {
                title: _t("No Available Sales Channel"),
                body: _t("There is no alternative sales channel available for this order."),
            });
            return;
        }

        const { confirmed: pinConfirmed, payload: supervisorPin } = await this.popup.add(NumberPopup, {
            title: _t("Enter Supervisor PIN"),
            nbrDecimal: 0,
        });
        if (!pinConfirmed || !supervisorPin) {
            return;
        }

        const { confirmed: channelConfirmed, payload: saleChannelId } = await this.popup.add(SelectionPopup, {
            title: _t("Select New Sales Channel"),
            list: changeData.sale_channels.map((channel) => ({
                id: channel.id,
                label: channel.name,
                item: channel.id,
                isSelected: false,
            })),
        });
        if (!channelConfirmed || !saleChannelId) {
            return;
        }

        try {
            const result = await this.orm.call("pos.order", "change_sale_channel_from_pos", [
                order.backendId,
                saleChannelId,
                String(supervisorPin),
                this.pos.pos_session?.id || false,
            ]);
            Object.assign(order, result?.order || {});
            this.render(true);
        } catch (error) {
            const errorMessage =
                error?.data?.message ||
                error?.message ||
                error?.cause?.message ||
                _t("The sales channel could not be updated.");
            await this.popup.add(ErrorPopup, {
                title: _t("Sales Channel Not Changed"),
                body: errorMessage,
            });
        }
    },
});
