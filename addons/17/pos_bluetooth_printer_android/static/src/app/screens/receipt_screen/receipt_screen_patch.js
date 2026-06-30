/** @odoo-module **/

import { onMounted } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.popup = useService("popup");
        this.notification = useService("notification");

        if (this.pos.config?.bluetooth_printer_enabled) {
            this.orderUiState.bluetoothPrinterStatus = this.printer.getBluetoothPrinterStatus?.();
            onMounted(async () => {
                await this._autoPrintToBluetoothPrinter();
            });
        }
    },

    async connectBluetoothPrinter() {
        try {
            await this.printer.connectBluetoothPrinter?.();
            this.orderUiState.bluetoothPrinterStatus = this.printer.getBluetoothPrinterStatus?.();
            this.notification.add("Printer Bluetooth tersambung.", {
                type: "success",
            });
        } catch (error) {
            this.orderUiState.bluetoothPrinterStatus = this.printer.getBluetoothPrinterStatus?.();
            this.popup.add(ErrorPopup, {
                title: error.title || "Bluetooth printer error",
                body: error.body || error.message || "Tidak bisa tersambung ke printer Bluetooth.",
            });
        }
    },

    async _autoPrintToBluetoothPrinter() {
        if (
            !this.pos.config?.bluetooth_printer_enabled ||
            !this.pos.config?.bluetooth_printer_auto_print ||
            this.currentOrder._printed ||
            this.currentOrder._bluetoothAutoPrintAttempted
        ) {
            return;
        }
        this.currentOrder._bluetoothAutoPrintAttempted = true;
        try {
            const connected = await this.printer.tryAutoConnectBluetoothPrinter?.();
            this.orderUiState.bluetoothPrinterStatus = this.printer.getBluetoothPrinterStatus?.();
            if (connected) {
                await this.printReceipt();
            }
        } catch {
            this.orderUiState.bluetoothPrinterStatus = this.printer.getBluetoothPrinterStatus?.();
        }
    },
});
