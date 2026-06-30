/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { useErrorHandlers, useTrackedAsync } from "@point_of_sale/app/utils/hooks";
import { registry } from "@web/core/registry";
import { SessionReportCanvas } from "./session_report_canvas";
import { useState, Component, onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { epsonPrinterService } from "../../pos_session_report/epson_printer_service";

export class SessionReportPreviewScreen extends Component {
    static template = "pos_session_z_report_ext_omax.SessionReportPreviewScreen";
    static components = { SessionReportCanvas };
    static props = ["*"];

    setup() {
        super.setup();
        this.pos = usePos();
        useErrorHandlers();
        this.ui = useState(useService("ui"));
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.report = useService("report");
        this.printer = useService("printer");
        this.epsonPrinter = epsonPrinterService;
        
        this.state = useState({
            sessionData: null,
            canvasDataUrl: null,
            loading: true,
            error: null,
            bluetoothPrinterStatus: null,
        });
        
        this.doPrint = useTrackedAsync(this._printSessionReport.bind(this));
        this.doDownloadPdf = useTrackedAsync(this._downloadPdfReport.bind(this));
        
        onMounted(() => {
            this._loadSessionData();
        });
    }

    async _loadSessionData() {
        try {
            this.state.loading = true;
            this.state.error = null;
            
            const sessionId = this.pos.pos_session.id;
            const sessionData = await this._getSessionData(sessionId);

            this.epsonPrinter.initPrinter(this.pos.config);
            this.state.bluetoothPrinterStatus = this.printer.getBluetoothPrinterStatus?.();
            
            // Buat canvas data
            const canvas = await this.epsonPrinter.createSessionReportCanvas(sessionData);
            const canvasDataUrl = canvas.toDataURL("image/png");
            
            this.state.sessionData = sessionData;
            this.state.canvasDataUrl = canvasDataUrl;
            this.state.loading = false;
            
        } catch (error) {
            console.error("Error loading session data:", error);
            this.state.error = error.message;
            this.state.loading = false;
        }
    }

    async _getSessionData(sessionId) {
        // Ambil data session dari server dengan field yang tersedia
        const sessionData = await this.orm.call(
            'pos.session',
            'read',
            [sessionId],
            {
                fields: [
                    'name', 'start_at', 'stop_at', 'user_id', 'config_id',
                    'currency_id', 'company_id', 'state', 'cash_register_balance_start',
                    'cash_register_balance_end_real', 'cash_register_difference', 'statement_line_ids'
                ]
            }
        );
        
        if (sessionData && sessionData.length > 0) {
            const session = sessionData[0];
            
            // Ambil data config untuk mengetahui detail apa saja yang harus ditampilkan
            const configData = await this.orm.call(
                'pos.config',
                'read',
                [session.config_id[0]],
                {
                    fields: [
                        'show_product_wise_detail', 'product_or_variant', 'show_category_wise_sales',
                        'show_taxes_detail', 'show_pricelist_detail', 'show_payment_detail',
                        'show_cash_in_out_details', 'session_z_printer', 'use_session_z_printer_for_pos'
                    ]
                }
            );
            
            // Ambil data perusahaan untuk header
            const companyData = await this.orm.call(
                'res.company',
                'read',
                [session.company_id[0]],
                {
                    fields: ['name', 'street', 'street2', 'city', 'state_id', 'country_id', 'phone', 'email', 'website', 'logo']
                }
            );
            
            // Ambil info currency untuk format yang sama seperti PDF
            const currencyData = await this.orm.call(
                'res.currency',
                'read',
                [session.currency_id[0]],
                {
                    fields: ['name', 'symbol', 'position']
                }
            );
            
            // Ambil waktu server untuk "Report ON" seperti PDF
            const reportOnText = await this.orm.call(
                'pos.session',
                'get_current_datetime',
                [sessionId]
            );
            
            // Ambil data tambahan menggunakan method yang sudah ada
            const amountData = await this.orm.call(
                'pos.session',
                'get_session_amount_data',
                [sessionId]
            );
            
            const paymentData = await this.orm.call(
                'pos.session',
                'get_payment_data',
                [sessionId]
            );
            
            const productData = await this.orm.call(
                'pos.session',
                'get_product_variant_wise_sale',
                [sessionId]
            );
            
            // Convert dari items() ke object
            const productSalesObject = {};
            if (productData && Array.isArray(productData)) {
                productData.forEach(([product, qty]) => {
                    productSalesObject[product] = qty;
                });
            }
            
            const taxesData = await this.orm.call(
                'pos.session',
                'get_taxes_data',
                [sessionId]
            );
            
            const pricelistData = await this.orm.call(
                'pos.session',
                'get_pricelist',
                [sessionId]
            );
            
            // Ambil quantity untuk setiap pricelist
            const pricelistQtyData = {};
            if (pricelistData && Object.keys(pricelistData).length > 0) {
                for (const pricelist of Object.keys(pricelistData)) {
                    const qty = await this.orm.call(
                        'pos.session',
                        'get_pricelist_qty',
                        [sessionId, pricelist]
                    );
                    pricelistQtyData[pricelist] = qty;
                }
            }
            
            // Ambil cash in/out data jika diperlukan
            let cashInOutData = [];
            if (configData[0].show_cash_in_out_details && session.statement_line_ids.length > 0) {
                cashInOutData = await this.orm.call(
                    'account.bank.statement.line',
                    'read',
                    [session.statement_line_ids],
                    {
                        fields: ['payment_ref', 'amount']
                    }
                );
            }
            
            // Gabungkan semua data
            return {
                ...session,
                config: configData[0],
                company: companyData[0],
                currency: currencyData && currencyData[0] ? currencyData[0] : null,
                report_on: reportOnText,
                amount_data: amountData,
                payment_methods: paymentData || [],
                product_sales: productSalesObject || {},
                taxes_data: taxesData || {},
                pricelist_data: pricelistData || {},
                pricelist_qty_data: pricelistQtyData || {},
                cash_in_out_data: cashInOutData || []
            };
        }
        
        throw new Error("Tidak dapat mengambil data session");
    }

    async _printSessionReport() {
        try {
            if (!this.state.sessionData) {
                throw new Error("Session data tidak tersedia");
            }

            if (this.pos.config?.bluetooth_printer_enabled) {
                const canvas = await this.epsonPrinter.createSessionReportCanvas(this.state.sessionData);
                await this.printer.printBluetoothCanvas?.(canvas, { interactive: true });
                this.state.bluetoothPrinterStatus = this.printer.getBluetoothPrinterStatus?.();
                this.notification.add("Session report berhasil dicetak ke printer Bluetooth", {
                    type: "success",
                    sticky: false,
                });
                return;
            }

            console.log("=== _printSessionReport called ===");
            console.log("Session data config:", this.state.sessionData.config);
            
            // Cek apakah menggunakan Session Z Printer untuk POS
            const useSessionZPrinter = this.state.sessionData.config?.use_session_z_printer_for_pos;
            console.log("useSessionZPrinter:", useSessionZPrinter);
            
            if (useSessionZPrinter) {
                console.log("Using Session Z Printer for POS");
                // Cetak ke Session Z Printer (Imin printer)
                const result = await this.epsonPrinter.printSessionReport(this.state.sessionData);
                
                if (result.result) {
                    this.notification.add("Session report berhasil dicetak ke Session Z Printer", {
                        type: "success",
                        sticky: false,
                    });
                } else {
                    throw new Error(`Session Z Printer error: ${result.printerErrorCode}`);
                }
            } else {
                console.log("Using Epson printer");
                // Cetak ke Epson printer
                const result = await this.epsonPrinter.printSessionReport(this.state.sessionData);
                
                if (result.result) {
                    this.notification.add("Session report berhasil dicetak ke Epson printer", {
                        type: "success",
                        sticky: false,
                    });
                } else {
                    throw new Error(`Epson printer error: ${result.printerErrorCode}`);
                }
            }
        } catch (error) {
            console.error("Error printing session report:", error);
            if (this._isPrinterUnavailable(error)) {
                await this._downloadPdfReport();
                this.notification.add("Printer tidak tersedia. Report diunduh sebagai PDF.", {
                    type: "warning",
                    sticky: false,
                });
                return;
            }
            this.notification.add("Gagal mencetak session report: " + error.message, {
                type: "danger",
                sticky: false,
            });
        }
    }

    async connectBluetoothPrinter() {
        try {
            await this.printer.connectBluetoothPrinter?.();
            this.state.bluetoothPrinterStatus = this.printer.getBluetoothPrinterStatus?.();
            this.notification.add("Printer Bluetooth tersambung.", {
                type: "success",
                sticky: false,
            });
        } catch (error) {
            this.state.bluetoothPrinterStatus = this.printer.getBluetoothPrinterStatus?.();
            this.notification.add(error.body || error.message || "Tidak bisa tersambung ke printer Bluetooth.", {
                type: "danger",
                sticky: false,
            });
        }
    }

    _isPrinterUnavailable(error) {
        const message = error?.message || "";
        return message.includes("Printer Epson tidak tersedia") || message.includes("Session Z printer") || message.includes("Print error:");
    }

    async _downloadPdfReport() {
        await this.report.doAction("pos_session_z_report_ext_omax.action_report_session_z", [this.pos.pos_session.id]);
    }

    goBack() {
        this.pos.showScreen("ProductScreen");
    }

    get nextScreen() {
        return { name: "ProductScreen" };
    }
}

registry.category("pos_screens").add("SessionReportPreviewScreen", SessionReportPreviewScreen);
