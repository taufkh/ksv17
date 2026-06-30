/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosPrinterService } from "@point_of_sale/app/printer/pos_printer_service";
import { BluetoothEscPosPrinter } from "./bluetooth_escpos_printer";

let bluetoothPrinter;

patch(PosPrinterService.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.config?.bluetooth_printer_enabled) {
            bluetoothPrinter = bluetoothPrinter || new BluetoothEscPosPrinter();
            bluetoothPrinter.configure(this.pos.config);
            this.bluetoothPrinter = bluetoothPrinter;
            this.setPrinter(this.bluetoothPrinter);
        }
    },

    async printHtml() {
        if (this.bluetoothPrinter && this.pos.config?.bluetooth_printer_enabled) {
            this.bluetoothPrinter.configure(this.pos.config);
            this.setPrinter(this.bluetoothPrinter);
        }
        return super.printHtml(...arguments);
    },

    isBluetoothPrinterEnabled() {
        return Boolean(this.bluetoothPrinter && this.pos.config?.bluetooth_printer_enabled);
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
