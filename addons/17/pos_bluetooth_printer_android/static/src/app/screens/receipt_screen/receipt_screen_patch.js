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

        if (this.isAndroidBluetoothMode()) {
            this.orderUiState.bluetoothPrinterStatus = this.printer.getBluetoothPrinterStatus?.();
        }
        onMounted(async () => {
            await this._autoHandleReceiptOutput();
        });
    },

    isAndroidBluetoothMode() {
        return Boolean(this.printer.isAndroidBluetoothRuntime?.());
    },

    isDesktopPdfMode() {
        return Boolean(this.printer.isDesktopReceiptFallbackMode?.());
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

    async _autoHandleReceiptOutput() {
        if (
            !this.pos.config?.bluetooth_printer_enabled ||
            !this.pos.config?.bluetooth_printer_auto_print ||
            this.currentOrder._receiptOutputAutoHandled
        ) {
            return;
        }
        this.currentOrder._receiptOutputAutoHandled = true;

        if (this.isAndroidBluetoothMode()) {
            return this._autoPrintToBluetoothPrinter();
        }

        if (this.isDesktopPdfMode()) {
            return this._autoPrintToDesktopPdf();
        }
    },

    async _autoPrintToBluetoothPrinter() {
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

    async _autoPrintToDesktopPdf() {
        if (this.pos.config?.iface_print_auto) {
            return;
        }
        try {
            await this.printReceipt();
        } catch (error) {
            this.popup.add(ErrorPopup, {
                title: error?.title || "Receipt print error",
                body:
                    error?.body ||
                    error?.message ||
                    "Tidak bisa membuka print dialog browser untuk simpan PDF receipt.",
            });
        }
    },
});
