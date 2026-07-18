/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { PrinterService } from "@point_of_sale/app/printer/printer_service";
import { PosPrinterService } from "@point_of_sale/app/printer/pos_printer_service";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { loadAllImages } from "@point_of_sale/utils";
import { BluetoothEscPosPrinter } from "./bluetooth_escpos_printer";

let bluetoothPrinter;

patch(PosPrinterService.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.config?.bluetooth_printer_enabled) {
            bluetoothPrinter = bluetoothPrinter || new BluetoothEscPosPrinter();
            bluetoothPrinter.configure(this.pos.config);
            this.bluetoothPrinter = bluetoothPrinter;
            if (this.isAndroidBluetoothRuntime()) {
                this.setPrinter(this.bluetoothPrinter);
            }
        }
    },

    isAndroidBluetoothRuntime() {
        return Boolean(
            this.bluetoothPrinter &&
                this.pos.config?.bluetooth_printer_enabled &&
                this.bluetoothPrinter.isNativeBridgeSupported()
        );
    },

    isDesktopReceiptFallbackMode() {
        return Boolean(
            this.bluetoothPrinter &&
                this.pos.config?.bluetooth_printer_enabled &&
                !this.bluetoothPrinter.isNativeBridgeSupported()
        );
    },

    async printHtml(el, options = {}) {
        if (this.isAndroidBluetoothRuntime()) {
            this.bluetoothPrinter.configure(this.pos.config);
            this.setPrinter(this.bluetoothPrinter);
            try {
                return await PrinterService.prototype.printHtml.call(this, el, options);
            } catch (error) {
                return this.printHtmlAlternative(error, el, options);
            }
        }
        return super.printHtml(...arguments);
    },

    async print(component, props, options) {
        if (
            this.isAndroidBluetoothRuntime() &&
            component === OrderReceipt &&
            this.bluetoothPrinter.isNativeBridgeSupported()
        ) {
            this.bluetoothPrinter.configure(this.pos.config);
            this.setPrinter(this.bluetoothPrinter);
            const el = await this.renderer.toHtml(component, props);
            try {
                await loadAllImages(el);
            } catch (error) {
                console.error("Images could not be loaded correctly", error);
            }
            const result = await this.bluetoothPrinter.printStructuredReceipt(el, props?.data || {});
            if (result.successful) {
                return true;
            }
            throw {
                title: result.message?.title || _t("Bluetooth printer error"),
                body: result.message?.body || _t("Failed to print structured receipt to Bluetooth printer."),
            };
        }
        return super.print(...arguments);
    },

    printWeb() {
        if (this.isAndroidBluetoothRuntime()) {
            this.popup.add(ConfirmPopup, {
                title: _t("Web printer dinonaktifkan"),
                body: _t(
                    "POS ini diset untuk print lewat Bluetooth printer Android. Gunakan Connect Bluetooth Printer lalu print ulang."
                ),
                confirmText: _t("OK"),
                cancelText: null,
            });
            return false;
        }
        return super.printWeb(...arguments);
    },

    async printHtmlAlternative(error, ...args) {
        if (this.isAndroidBluetoothRuntime()) {
            if (error?.body === undefined) {
                console.error("Bluetooth print error:", error);
            }
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: error?.title || _t("Bluetooth printer error"),
                body:
                    (error?.body || _t("Gagal print ke Bluetooth printer.")) +
                    " " +
                    _t("Coba sambungkan ulang printer Panda lalu print ulang."),
                confirmText: _t("OK"),
                cancelText: null,
            });
            return Boolean(confirmed);
        }
        return super.printHtmlAlternative(...arguments);
    },

    isBluetoothPrinterEnabled() {
        return this.isAndroidBluetoothRuntime();
    },

    getBluetoothPrinterStatus() {
        if (!this.isBluetoothPrinterEnabled()) {
            return _t("Printer Bluetooth nonaktif.");
        }
        return this.bluetoothPrinter.getStatusLabel();
    },

    async connectBluetoothPrinter() {
        if (!this.isBluetoothPrinterEnabled()) {
            return false;
        }
        this.bluetoothPrinter.configure(this.pos.config);
        await this.bluetoothPrinter.connectInteractive();
        return true;
    },

    async tryAutoConnectBluetoothPrinter() {
        if (!this.isBluetoothPrinterEnabled()) {
            return false;
        }
        this.bluetoothPrinter.configure(this.pos.config);
        const hasAuthorizedPort = await this.bluetoothPrinter.hasAuthorizedPort();
        if (!hasAuthorizedPort) {
            return false;
        }
        await this.bluetoothPrinter.ensureConnection({ interactive: false });
        return true;
    },

    async printBluetoothCanvas(canvas, { interactive = true } = {}) {
        if (!this.isBluetoothPrinterEnabled()) {
            return false;
        }
        this.bluetoothPrinter.configure(this.pos.config);
        this.setPrinter(this.bluetoothPrinter);
        const result = await this.bluetoothPrinter.printCanvas(canvas, { interactive });
        if (!result.successful) {
            throw {
                title: result.message?.title || _t("Bluetooth printer error"),
                body: result.message?.body || _t("Failed to print to Bluetooth printer."),
            };
        }
        return true;
    },
});
