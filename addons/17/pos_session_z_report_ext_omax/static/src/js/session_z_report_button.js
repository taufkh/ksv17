/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";

// Patch FormController untuk menambahkan console log pada tombol Session Z Report
patch(FormController.prototype, {
    
    setup() {
        super.setup();
        // Console log saat form controller diinisialisasi
        if (this.props.resModel === 'pos.session') {
            console.log("Hello World! POS Session form loaded");
        }
    },
    
    async onButtonClicked(clickParams) {
        // Cek jika ini adalah tombol Laporan Closing Harian
        if (clickParams.name === 'action_hello') {
            console.log("📊 Laporan Closing Harian button clicked!");
            console.log("Calling action_hello method...");
            console.log("This will trigger custom client action to show JSON data and print...");
        }
        
        // Panggil method asli untuk tombol lainnya
        return super.onButtonClicked(clickParams);
    }
});

// Fungsi untuk format data JSON ke format printer
function formatToPrinterText(data) {
    let printText = "";
    
    // Header
    printText += "[C]<b>LAPORAN CLOSING HARIAN</b>\n";
    printText += `[C]${data.company.name}\n`;
    if (data.company.street) printText += `[C]${data.company.street}\n`;
    if (data.company.street2) printText += `[C]${data.company.street2}\n`;
    if (data.company.city) printText += `[C]${data.company.city}\n`;
    if (data.company.phone) printText += `[C]Tel: ${data.company.phone}\n`;
    if (data.company.email) printText += `[C]Email: ${data.company.email}\n`;
    if (data.company.website) printText += `[C]Website: ${data.company.website}\n`;
    printText += "[C]===============================================\n";
    
    // Session Info
    printText += `[L]Session: ${data.session.name}\n`;
    printText += `[L]Tanggal: ${data.report_on}\n`;
    printText += `[L]Salesperson: ${data.session.salesperson}\n`;
    printText += `[L]Status: ${data.session.status}\n`;
    printText += `[L]Config: ${data.session.config_name}\n`;
    if (data.session.opened_date) printText += `[L]Opened Date: ${data.session.opened_date}\n`;
    if (data.session.closed_date) printText += `[L]Closed Date: ${data.session.closed_date}\n`;
    printText += "[C]===============================================\n";
    
    // Financial Summary
    printText += "[L]<b>RINGKASAN KEUANGAN</b>\n";
    printText += "[C]------------------------------------------\n";
    printText += `[L]Opening Balance[R]${data.financials.currency_symbol} ${data.financials.opening_balance.toLocaleString()}\n`;
    printText += `[L]Closing Balance[R]${data.financials.currency_symbol} ${data.financials.closing_balance.toLocaleString()}\n`;
    printText += `[L]Difference[R]${data.financials.currency_symbol} ${data.financials.difference.toLocaleString()}\n`;
    printText += `[L]Gross Sales[R]${data.financials.currency_symbol} ${data.financials.gross_sales.toLocaleString()}\n`;
    printText += `[L]Tax Amount[R]${data.financials.currency_symbol} ${data.financials.tax.toLocaleString()}\n`;
    printText += `[L]Discount Amount[R]${data.financials.currency_symbol} ${data.financials.discount_amount.toLocaleString()}\n`;
    printText += "[C]------------------------------------------\n";
    printText += `[L]<b>TOTAL AMOUNT[R]${data.financials.currency_symbol} ${data.financials.total.toLocaleString()}</b>\n`;
    printText += "[C]===============================================\n";
    
    // Product Or Variant Wise Detail - kondisional seperti PDF
    if (data.config.show_product_wise_detail && Object.keys(data.product_details.products).length > 0) {
        const titleText = data.config.product_or_variant === 'product' ? 'Product Wise Sales' : 'Product Variant Wise Sales';
        const columnText = data.config.product_or_variant === 'product' ? 'Product' : 'Product Variant';
        
        printText += `[C]<b>${titleText}</b>\n`;
        printText += "[C]-----------------------------------------------\n";
        printText += `[L]${columnText}[R]Qty\n`;
        printText += "[C]-----------------------------------------------\n";
        
        let totalItems = 0;
        for (const [product, qty] of Object.entries(data.product_details.products)) {
            // Potong nama produk jika terlalu panjang, maksimal 35 karakter
            const maxProductNameLength = 35;
            const truncatedProduct = product.length > maxProductNameLength 
                ? product.substring(0, maxProductNameLength - 3) + "..." 
                : product;
            printText += `[L]${truncatedProduct}[R]${qty}\n`;
            totalItems += parseFloat(qty);
        }
        printText += "[C]-----------------------------------------------\n";
        printText += `[L]Total Items[R]${totalItems}\n`;
        printText += "[C]===============================================\n";
    }
    
    // Category Wise Sales - kondisional seperti PDF
    if (data.config.show_category_wise_sales && Object.keys(data.category_sales.categories).length > 0) {
        printText += "[C]<b>Category Wise Sales</b>\n";
        printText += "[C]-----------------------------------------------\n";
        printText += "[L]Category[R]Qty\n";
        printText += "[C]-----------------------------------------------\n";
        
        for (const [category, qty] of Object.entries(data.category_sales.categories)) {
            const displayCategory = category === 'undefine' ? 'Others' : category;
            printText += `[L]${displayCategory}[R]${qty}\n`;
        }
        printText += `[L]Total Items : ${data.category_sales.total_category_qty}\n`;
        printText += "[C]===============================================\n";
    }
    
    // Taxes Detail - kondisional seperti PDF
    if (data.config.show_taxes_detail && Object.keys(data.tax_details.taxes).length > 0) {
        printText += "[C]<b>Taxes Detail</b>\n";
        printText += "[C]-----------------------------------------------\n";
        printText += "[L]Tax[R]Amount\n";
        printText += "[C]-----------------------------------------------\n";
        
        let taxTotal = 0;
        for (const [tax, amount] of Object.entries(data.tax_details.taxes)) {
            const displayTax = tax === 'undefine' ? 'Others' : tax;
            printText += `[L]${displayTax}[R]${data.financials.currency_symbol} ${amount.toLocaleString()}\n`;
            taxTotal += parseFloat(amount);
        }
        printText += "[C]-----------------------------------------------\n";
        printText += `[L]Total[R]${data.financials.currency_symbol} ${taxTotal.toLocaleString()}\n`;
        printText += "[C]===============================================\n";
    }
    
    // Pricelist Detail - kondisional seperti PDF
    if (data.config.show_pricelist_detail && Object.keys(data.pricelist_details.pricelists).length > 0) {
        printText += "[C]<b>Pricelist Detail</b>\n";
        printText += "[C]-----------------------------------------------\n";
        printText += "[L]Pricelist[C]Qty[R]Amount\n";
        printText += "[C]-----------------------------------------------\n";
        
        let pricelistTotal = 0;
        let pricelistQtyTotal = 0;
        for (const [pricelist, amount] of Object.entries(data.pricelist_details.pricelists)) {
            const displayPricelist = pricelist === 'undefine' ? 'Others' : pricelist;
            const qty = data.pricelist_qty_data && data.pricelist_qty_data[pricelist] ? data.pricelist_qty_data[pricelist] : 0;
            printText += `[L]${displayPricelist}[C]${qty}[R]${data.financials.currency_symbol} ${amount.toLocaleString()}\n`;
            pricelistTotal += parseFloat(amount);
            pricelistQtyTotal += parseInt(qty);
        }
        printText += "[C]-----------------------------------------------\n";
        printText += `[L]Total[C]${pricelistQtyTotal}[R]${data.financials.currency_symbol} ${pricelistTotal.toLocaleString()}\n`;
        printText += "[C]===============================================\n";
    }
    
    // Payment Detail - kondisional seperti PDF
    if (data.config.show_payment_detail && data.payment_details.payments.length > 0) {
        printText += "[C]<b>Payment Detail</b>\n";
        printText += "[C]-----------------------------------------------\n";
        printText += "[L]Method[R]Amount\n";
        printText += "[C]-----------------------------------------------\n";
        
        let paymentTotal = 0;
        data.payment_details.payments.forEach(payment => {
            printText += `[L]${payment.name}[R]${data.financials.currency_symbol} ${payment.total.toLocaleString()}\n`;
            paymentTotal += parseFloat(payment.total);
        });
        printText += "[C]-----------------------------------------------\n";
        printText += `[L]Total[R]${data.financials.currency_symbol} ${paymentTotal.toLocaleString()}\n`;
        printText += "[C]===============================================\n";
    }
    
    // Cash In Out Details - kondisional seperti PDF
    if (data.config.show_cash_in_out_details && data.cash_in_out_details.transactions.length > 0) {
        printText += "[C]<b>Cash In Out Details</b>\n";
        printText += "[C]-----------------------------------------------\n";
        printText += "[L]Label[C]Cash In[R]Cash Out\n";
        printText += "[C]-----------------------------------------------\n";
        
        let totalCashIn = 0;
        let totalCashOut = 0;
        data.cash_in_out_details.transactions.forEach(transaction => {
            const amount = parseFloat(transaction.amount);
            const cashIn = amount > 0 ? amount.toLocaleString() : '';
            const cashOut = amount < 0 ? Math.abs(amount).toLocaleString() : '';
            
            printText += `[L]${transaction.payment_ref || ''}[C]${data.financials.currency_symbol} ${cashIn}[R]${data.financials.currency_symbol} ${cashOut}\n`;
            
            if (amount > 0) totalCashIn += amount;
            if (amount < 0) totalCashOut += Math.abs(amount);
        });
        printText += "[C]-----------------------------------------------\n";
        printText += `[L]Total[C]${data.financials.currency_symbol} ${totalCashIn.toLocaleString()}[R]${data.financials.currency_symbol} ${totalCashOut.toLocaleString()}\n`;
        printText += "[C]===============================================\n";
    }
    
    // Footer
    printText += "[C]Terima kasih\n";
    if (data.company.website) printText += `[C]${data.company.website}\n`;
    printText += "[C]\n";
    printText += "[C]\n";
    
    // Add spacing before cut
    printText += "\n\n\n";
    
    return printText;
}

// Fungsi untuk kirim ke printer imin
async function sendToPrinter(printerUrl, printText) {
    try {
        console.log("🖨️ Sending to imin printer:", printerUrl);
        console.log("📝 Print Text:", printText);
        
        // Payload untuk imin printer menggunakan tipe 'formatted' - lebarkan +3 char lagi
        const payload = {
            type: "formatted",
            data: printText,
            dpi: 203,
            widthMm: 69.6,  // dari 65.1mm ke 69.6mm (+3 char)
            charsPerLine: 47  // dari 44 ke 47 karakter (+3 char)
        };
        
        console.log("📦 Payload:", payload);
        
        const response = await fetch(printerUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log("✅ Print successful! Response:", result);
            
            // Setelah print berhasil, kirim perintah cut terpisah
            console.log("✂️ Sending cut command...");
            await sendCutCommand(printerUrl);
            
            return { success: true, message: "Print successful with cut", response: result };
        } else {
            const errorText = await response.text();
            console.error("❌ Print failed:", response.status, response.statusText, errorText);
            return { success: false, message: `Print failed: ${response.status} ${response.statusText}` };
        }
    } catch (error) {
        console.error("❌ Print error:", error);
        return { success: false, message: `Print error: ${error.message}` };
    }
}

// Fungsi untuk kirim perintah cut terpisah
async function sendCutCommand(printerUrl) {
    try {
        // ESC/POS cut command: GS V 0 (full cut)
        const cutCommand = new Uint8Array([0x1D, 0x56, 0x00]);
        const base64CutCommand = btoa(String.fromCharCode(...cutCommand));
        
        const cutPayload = {
            type: "raw",
            data: base64CutCommand,
            base64: true
        };
        
        console.log("✂️ Cut Command Payload:", cutPayload);
        
        const response = await fetch(printerUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(cutPayload)
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log("✅ Cut command successful! Response:", result);
        } else {
            console.error("❌ Cut command failed:", response.status, response.statusText);
        }
    } catch (error) {
        console.error("❌ Cut command error:", error);
    }
}

// Register custom client action untuk menangkap data dari tombol Laporan Closing Harian
async function helloWorldAction(env, action) {
    console.log("📊 Laporan Closing Harian! Custom client action triggered!");
    
    if (action.params && action.params.closing_report_data) {
        const data = action.params.closing_report_data;
        const sessionName = action.params.session_name;
        
        console.log("=== CLOSING REPORT JSON DATA ===");
        console.log(JSON.stringify(data, null, 2));
        console.log("=== END OF CLOSING REPORT DATA ===");
        
        // Tampilkan struktur data di console dengan emoji
        console.log("📊 Report Title:", data.report_title);
        console.log("🏢 Company:", data.company.name);
        console.log("📋 Session:", data.session.name);
        console.log("💰 Total Sales:", data.financials.total, data.financials.currency_symbol);
        console.log("📈 Tax Amount:", data.financials.tax, data.financials.currency_symbol);
        console.log("💳 Payment Methods:", data.payment_details.payments);
        
        if (data.product_details.enabled) {
            console.log("📦 Products Sold:", data.product_details.products);
            console.log("📊 Total Items:", data.product_details.total_items);
        }
        
        if (data.category_sales.enabled) {
            console.log("🏷️ Category Sales:", data.category_sales.categories);
        }
        
        // Format dan kirim ke printer jika IP printer tersedia
        const printerIP = data.config.session_z_printer;
        if (printerIP) {
            // Buat URL lengkap dari IP address untuk imin printer
            const printerUrl = `http://${printerIP}:8088/print`;
            console.log("🖨️ Printer IP found:", printerIP);
            console.log("🖨️ Full Printer URL:", printerUrl);
            
            // Format data ke format printer
            const printText = formatToPrinterText(data);
            console.log("📝 Formatted Print Text:");
            console.log(printText);
            
            // Kirim ke printer
            const printResult = await sendToPrinter(printerUrl, printText);
            
            if (printResult.success) {
                env.services.notification.add(`Laporan Closing Harian berhasil dikirim ke printer!`, {
                    title: "Print Success! 🖨️",
                    type: "success",
                    sticky: true,
                });
            } else {
                env.services.notification.add(`Gagal mengirim ke printer: ${printResult.message}`, {
                    title: "Print Failed ❌",
                    type: "danger",
                    sticky: true,
                });
            }
        } else {
            console.log("⚠️ No printer IP configured");
            env.services.notification.add(`JSON Data Generated for Session: ${sessionName}. No printer IP configured.`, {
                title: "Laporan Closing Harian - Data Ready! 📊",
                type: "info",
                sticky: true,
            });
        }
    }
}

// Register the client action
registry.category("actions").add("hello_world_action", helloWorldAction);
