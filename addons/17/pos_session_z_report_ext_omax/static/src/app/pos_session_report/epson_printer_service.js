/** @odoo-module */

// Registry tidak diperlukan lagi karena service didaftarkan melalui start function

/**
 * Service untuk mencetak session report langsung ke printer Epson
 */
class EpsonPrinterService {
    constructor() {
        this.printer = null;
    }

    /**
     * Inisialisasi printer Epson dari konfigurasi POS
     */
    initPrinter(posConfig) {
        if (posConfig.epson_printer_ip) {
            this.printer = {
                ip: posConfig.epson_printer_ip,
                url: window.location.protocol + "//" + posConfig.epson_printer_ip,
                address: window.location.protocol + "//" + posConfig.epson_printer_ip + "/cgi-bin/epos/service.cgi?devid=local_printer"
            };
        }
        return this.printer;
    }

    /**
     * Mengirim data cetak ke printer Epson
     */
    async sendPrintingJob(printData) {
        if (!this.printer) {
            throw new Error("Printer Epson tidak tersedia");
        }

        try {
            const response = await fetch(this.printer.address, {
                method: "POST",
                body: printData,
                headers: {
                    'Content-Type': 'application/xml'
                }
            });

            const body = await response.text();
            const parser = new DOMParser();
            const parsedBody = parser.parseFromString(body, "application/xml");
            const responseElement = parsedBody.querySelector("response");

            return {
                result: responseElement.getAttribute("success") === "true",
                printerErrorCode: responseElement.getAttribute("code"),
                message: responseElement.textContent || ""
            };
        } catch (error) {
            console.error("Error sending print job:", error);
            throw new Error("Gagal mengirim data ke printer: " + error.message);
        }
    }

    /**
     * Membuat XML print data untuk Epson printer
     */
    createEpsonPrintData(imageData, width, height) {
        const eposPrintData = `<?xml version="1.0" encoding="UTF-8"?>
<epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
    <image width="${width}" height="${height}" align="center">${imageData}</image>
    <cut type="feed"/>
</epos-print>`;
        
        return eposPrintData;
    }

    /**
     * Mencetak session report ke printer Epson atau Session Z Printer
     */
    async printSessionReport(sessionData) {
        // Cek apakah menggunakan Session Z Printer
        if (sessionData.config && sessionData.config.use_session_z_printer_for_pos && sessionData.config.session_z_printer) {
            return await this.printToSessionZPrinter(sessionData);
        }
        
        // Default ke Epson printer
        if (!this.printer) {
            throw new Error("Printer Epson tidak tersedia");
        }

        try {
            // Buat canvas untuk session report
            const canvas = await this.createSessionReportCanvas(sessionData);
            
            // Konversi canvas ke raster image
            const rasterData = this.canvasToRaster(canvas);
            const encodedData = this.encodeRaster(rasterData);
            
            // Buat XML print data
            const printData = this.createEpsonPrintData(encodedData, canvas.width, canvas.height);
            
            // Kirim ke printer
            const result = await this.sendPrintingJob(printData);
            
            if (!result.result) {
                throw new Error(`Printer error: ${result.printerErrorCode}`);
            }
            
            return result;
        } catch (error) {
            console.error("Error printing session report:", error);
            throw error;
        }
    }

    /**
     * Membuat canvas untuk session report
     */
    async createSessionReportCanvas(sessionData) {
        // Debug logging untuk melihat struktur data
        console.log('Session data received:', sessionData);
        console.log('Product sales type:', typeof sessionData.product_sales);
        console.log('Product sales data:', sessionData.product_sales);
        console.log('Config show_product_wise_detail:', sessionData.config?.show_product_wise_detail);
        console.log('Config product_or_variant:', sessionData.config?.product_or_variant);
        console.log('Product sales keys count:', sessionData.product_sales ? Object.keys(sessionData.product_sales).length : 0);
        
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Set canvas size (sesuaikan dengan ukuran printer thermal 80mm)
        canvas.width = 576; // 72 DPI * 8 inch
        
        // Hitung estimasi height berdasarkan jumlah item
        let estimatedHeight = 800; // Base height untuk header dan footer
        
        // Tambahkan height untuk product sales jika ada
        if (sessionData.config?.show_product_wise_detail && sessionData.product_sales) {
            const productCount = Object.keys(sessionData.product_sales).length;
            estimatedHeight += productCount * 40; // 40px per product
        }
        
        // Tambahkan height untuk category wise sales jika ada
        if (sessionData.config?.show_category_wise_sales) {
            estimatedHeight += 200; // Estimasi untuk category sales
        }
        
        // Tambahkan height untuk taxes detail jika ada
        if (sessionData.config?.show_taxes_detail) {
            estimatedHeight += 150; // Estimasi untuk taxes
        }
        
        // Tambahkan height untuk pricelist detail jika ada
        if (sessionData.config?.show_pricelist_detail) {
            estimatedHeight += 200; // Estimasi untuk pricelist
        }
        
        // Tambahkan height untuk payment detail jika ada
        if (sessionData.config?.show_payment_detail) {
            estimatedHeight += 150; // Estimasi untuk payment
        }
        
        // Tambahkan height untuk cash in/out details jika ada
        if (sessionData.config?.show_cash_in_out_details) {
            estimatedHeight += 200; // Estimasi untuk cash in/out
        }
        
        // Pastikan minimum height dan maksimum height
        estimatedHeight = Math.max(estimatedHeight, 1200); // Minimum 1200px
        estimatedHeight = Math.min(estimatedHeight, 8000); // Maximum 8000px untuk performa
        
        canvas.height = estimatedHeight;
        
        // Background putih
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Text hitam
        ctx.fillStyle = 'black';
        ctx.font = '20px monospace'; // Sama dengan address, telp, email
        ctx.textAlign = 'left';
        
        let y = 40; // 20 * 2 = 40
        const lineHeight = 28; // Sesuaikan dengan font 20px
        const margin = 40; // 20 * 2 = 40
        const rightMargin = canvas.width - margin;
        
        // Helper functions
        const centerText = (text, yPos, font = '20px monospace') => { // Sama dengan address, telp, email
            ctx.font = font;
            ctx.textAlign = 'center';
            ctx.fillText(text, canvas.width / 2, yPos);
            ctx.textAlign = 'left';
            ctx.font = '20px monospace'; // Sama dengan address, telp, email
        };
        
        const rightAlignText = (text, yPos, font = '20px monospace') => { // Sama dengan address, telp, email
            ctx.font = font;
            ctx.textAlign = 'right';
            ctx.fillText(text, rightMargin, yPos);
            ctx.textAlign = 'left';
        };
        
        const formatCurrency = (amount) => {
            const cur = sessionData.currency || {};
            const symbol = cur.symbol;
            const position = cur.position; // 'before' or 'after'
            const value = new Intl.NumberFormat('id-ID', {
                style: symbol ? 'decimal' : 'currency',
                currency: symbol ? undefined : (cur.name || 'IDR'),
                minimumFractionDigits: 0
            }).format(amount || 0);
            if (!symbol) return value;
            return position === 'after' ? `${value} ${symbol}` : `${symbol} ${value}`;
        };
        
        const formatDateTime = (dateString) => {
            if (!dateString) return 'N/A';
            return new Date(dateString).toLocaleString('id-ID');
        };
        
        // Header profesional tanpa border
        centerText('SESSION Z REPORT', y, 'bold 24px monospace'); // Sedikit lebih besar dari font normal
        y += lineHeight + 10; // 5 * 2 = 10
        
        // Company info
        if (sessionData.company) {
            centerText(sessionData.company.name || 'COMPANY NAME', y, 'bold 20px monospace'); // Sama dengan font normal tapi bold
            y += lineHeight;
            
            if (sessionData.company.street) {
                centerText(sessionData.company.street, y, '20px monospace'); // 10px * 2 = 20px
                y += lineHeight;
            }
            
            if (sessionData.company.street2) {
                centerText(sessionData.company.street2, y, '20px monospace');
                y += lineHeight;
            }
            
            if (sessionData.company.city) {
                centerText(sessionData.company.city, y, '20px monospace');
                y += lineHeight;
            }
            
            if (sessionData.company.phone) {
                centerText(`Tel: ${sessionData.company.phone}`, y, '20px monospace');
                y += lineHeight;
            }
            
            if (sessionData.company.email) {
                centerText(`Email: ${sessionData.company.email}`, y, '20px monospace');
                y += lineHeight;
            }
        }
        
        y += 20; // 10 * 2 = 20
        
        // Report info (pakai server current datetime agar sama dengan PDF)
        ctx.fillText('Report ON', margin, y);
        rightAlignText(sessionData.report_on || formatDateTime(new Date().toISOString()), y);
        y += lineHeight;
        
        ctx.fillText('Salesperson', margin, y);
        rightAlignText(sessionData.user_id?.[1] || 'N/A', y);
        y += lineHeight;
        
        y += 20; // 10 * 2 = 20
        
        // Session details
        ctx.fillText('Session', margin, y);
        rightAlignText(sessionData.name || 'N/A', y);
        y += lineHeight;
        
        ctx.fillText('Opened Date', margin, y);
        rightAlignText(formatDateTime(sessionData.start_at), y);
        y += lineHeight;
        
        ctx.fillText('Closed Date', margin, y);
        rightAlignText(formatDateTime(sessionData.stop_at), y);
        y += lineHeight;
        
        ctx.fillText('Session Status', margin, y);
        rightAlignText(sessionData.state || 'N/A', y);
        y += lineHeight;
        
        y += 20; // 10 * 2 = 20
        
        // Financial summary
        if (sessionData.amount_data && typeof sessionData.amount_data === 'object') {
            const amountData = sessionData.amount_data;
            
            ctx.fillText('Opening Balance', margin, y);
            rightAlignText(formatCurrency(sessionData.cash_register_balance_start), y);
            y += lineHeight;
            
            ctx.fillText('Closing Balance', margin, y);
            rightAlignText(formatCurrency(sessionData.cash_register_balance_end_real), y);
            y += lineHeight;
            
            ctx.fillText('Difference', margin, y);
            rightAlignText(formatCurrency(sessionData.cash_register_difference), y);
            y += lineHeight;
            
            ctx.fillText('Gross Sales', margin, y);
            rightAlignText(formatCurrency(amountData.total_sale), y);
            y += lineHeight;
            
            ctx.fillText('Tax', margin, y);
            rightAlignText(formatCurrency(amountData.tax), y);
            y += lineHeight;
            
            ctx.fillText('Discount Amount', margin, y);
            rightAlignText(formatCurrency(amountData.discount), y);
            y += lineHeight;
            
            ctx.fillText('Total', margin, y);
            rightAlignText(formatCurrency(amountData.final_total), y);
            y += lineHeight;
        }
        
        y += 20; // 10 * 2 = 20
        
        // Product/Variant wise detail
        console.log('Checking product wise detail conditions:');
        console.log('- sessionData.config exists:', !!sessionData.config);
        console.log('- show_product_wise_detail:', sessionData.config?.show_product_wise_detail);
        console.log('- product_sales exists:', !!sessionData.product_sales);
        console.log('- product_sales has data:', sessionData.product_sales ? Object.keys(sessionData.product_sales).length > 0 : false);
        console.log('- product_sales content:', sessionData.product_sales);
        console.log('- product_sales keys:', sessionData.product_sales ? Object.keys(sessionData.product_sales) : 'N/A');
        
        // Kondisi yang lebih fleksibel - cek satu per satu
        const hasConfig = !!sessionData.config;
        const showProductDetail = sessionData.config?.show_product_wise_detail;
        const hasProductSales = !!sessionData.product_sales;
        const hasProductData = sessionData.product_sales ? Object.keys(sessionData.product_sales).length > 0 : false;
        
        console.log('Condition breakdown:');
        console.log('- hasConfig:', hasConfig);
        console.log('- showProductDetail:', showProductDetail);
        console.log('- hasProductSales:', hasProductSales);
        console.log('- hasProductData:', hasProductData);
        
        if (hasConfig && showProductDetail && hasProductSales && hasProductData) {
            const title = sessionData.config.product_or_variant === 'product' ? 
                'Product Wise Sales' : 'Product Variant Wise Sales';
            centerText(title, y, 'bold 20px monospace'); // Sama dengan font normal tapi bold
            y += lineHeight + 10; // 5 * 2 = 10
            
            // Header
            ctx.fillText(sessionData.config.product_or_variant === 'product' ? 'Product' : 'Product Variant', margin, y);
            rightAlignText('Qty', y);
            y += lineHeight;
            
            // Separator dihilangkan (tanpa garis putus-putus)
            
            let totalQty = 0;
            Object.entries(sessionData.product_sales).forEach(([product, qty]) => {
                ctx.fillText(product.substring(0, 30), margin, y); // Truncate long names
                rightAlignText(qty.toString(), y);
                totalQty += qty;
                y += lineHeight;
            });
            
            // Total line
            ctx.fillText('Total Items', margin, y);
            rightAlignText(totalQty.toString(), y);
            y += lineHeight + 20; // 10 * 2 = 20
        } else {
            console.log('Product wise detail NOT displayed because:');
            if (!hasConfig) console.log('- Config not available');
            if (!showProductDetail) console.log('- show_product_wise_detail is false');
            if (!hasProductSales) console.log('- product_sales object not available');
            if (!hasProductData) console.log('- product_sales has no data');
        }
        
        // Category wise sales
        if (sessionData.config && sessionData.config.show_category_wise_sales && sessionData.amount_data?.products_sold) {
            centerText('Category Wise Sales', y, 'bold 20px monospace'); // Sama dengan font normal tapi bold
            y += lineHeight + 10; // 5 * 2 = 10
            
            ctx.fillText('Category', margin, y);
            rightAlignText('Qty', y);
            y += lineHeight;
            
            // Separator dihilangkan (tanpa garis putus-putus)
            
            Object.entries(sessionData.amount_data.products_sold).forEach(([category, qty]) => {
                const displayCategory = category === 'undefine' ? 'Others' : category;
                ctx.fillText(displayCategory.substring(0, 30), margin, y);
                rightAlignText(qty.toString(), y);
                y += lineHeight;
            });
            
            ctx.fillText(`Total Items: ${sessionData.amount_data.total_sale_product}`, margin, y);
            y += lineHeight + 20; // 10 * 2 = 20
        }
        
        // Taxes detail
        if (sessionData.config && sessionData.config.show_taxes_detail && sessionData.taxes_data && Object.keys(sessionData.taxes_data).length > 0) {
            centerText('Taxes Detail', y, 'bold 20px monospace'); // Sama dengan font normal tapi bold
            y += lineHeight + 10; // 5 * 2 = 10
            
            ctx.fillText('Tax', margin, y);
            rightAlignText('Amount', y);
            y += lineHeight;
            
            // Separator dihilangkan (tanpa garis putus-putus)
            
            let taxTotal = 0;
            Object.entries(sessionData.taxes_data).forEach(([tax, amount]) => {
                const displayTax = tax === 'undefine' ? 'Others' : tax;
                ctx.fillText(displayTax.substring(0, 25), margin, y);
                rightAlignText(formatCurrency(amount), y);
                taxTotal += amount;
                y += lineHeight;
            });
            
            ctx.fillText('Total', margin, y);
            rightAlignText(formatCurrency(taxTotal), y);
            y += lineHeight + 20; // 10 * 2 = 20
        }
        
        // Pricelist detail
        if (sessionData.config && sessionData.config.show_pricelist_detail && sessionData.pricelist_data && Object.keys(sessionData.pricelist_data).length > 0) {
            centerText('Pricelist Detail', y, 'bold 20px monospace'); // Sama dengan font normal tapi bold
            y += lineHeight + 10; // 5 * 2 = 10
            
            ctx.fillText('Pricelist', margin, y);
            ctx.textAlign = 'center';
            ctx.fillText('Qty', canvas.width * 0.6, y); // Pindah ke 60% dari lebar canvas
            ctx.textAlign = 'right';
            ctx.fillText('Amount', rightMargin, y);
            ctx.textAlign = 'left';
            y += lineHeight;
            
            // Separator dihilangkan (tanpa garis putus-putus)
            
            let pricelistTotal = 0;
            let pricelistQtyTotal = 0;
            Object.entries(sessionData.pricelist_data).forEach(([pricelist, amount]) => {
                const displayPricelist = pricelist === 'undefine' ? 'Others' : pricelist;
                const qty = sessionData.pricelist_qty_data[pricelist] || 0;
                
                ctx.fillText(displayPricelist.substring(0, 20), margin, y);
                ctx.textAlign = 'center';
                ctx.fillText(qty.toString(), canvas.width * 0.6, y); // Pindah ke 60% dari lebar canvas
                ctx.textAlign = 'right';
                ctx.fillText(formatCurrency(amount), rightMargin, y);
                ctx.textAlign = 'left';
                
                pricelistTotal += amount;
                pricelistQtyTotal += qty;
                y += lineHeight;
            });
            
            ctx.fillText('Total', margin, y);
            ctx.textAlign = 'center';
            ctx.fillText(pricelistQtyTotal.toString(), canvas.width * 0.6, y); // Pindah ke 60% dari lebar canvas
            ctx.textAlign = 'right';
            ctx.fillText(formatCurrency(pricelistTotal), rightMargin, y);
            ctx.textAlign = 'left';
            y += lineHeight + 20; // 10 * 2 = 20
        }
        
        // Payment detail
        if (sessionData.config && sessionData.config.show_payment_detail && sessionData.payment_methods && sessionData.payment_methods.length > 0) {
            centerText('Payment Detail', y, 'bold 20px monospace'); // Sama dengan font normal tapi bold
            y += lineHeight + 10; // 5 * 2 = 10
            
            ctx.fillText('Method', margin, y);
            rightAlignText('Amount', y);
            y += lineHeight;
            
            // Separator dihilangkan (tanpa garis putus-putus)
            
            let paymentTotal = 0;
            sessionData.payment_methods.forEach(payment => {
                ctx.fillText(payment.name.substring(0, 25), margin, y);
                rightAlignText(formatCurrency(payment.total), y);
                paymentTotal += payment.total;
                y += lineHeight;
            });
            
            ctx.fillText('Total', margin, y);
            rightAlignText(formatCurrency(paymentTotal), y);
            y += lineHeight + 20; // 10 * 2 = 20
        }
        
        // Cash In Out Details
        if (sessionData.config && sessionData.config.show_cash_in_out_details && sessionData.cash_in_out_data && sessionData.cash_in_out_data.length > 0) {
            centerText('Cash In Out Details', y, 'bold 20px monospace'); // Sama dengan font normal tapi bold
            y += lineHeight + 10; // 5 * 2 = 10
            
            ctx.fillText('Label', margin, y);
            ctx.textAlign = 'center';
            ctx.fillText('Cash In', canvas.width * 0.6, y); // Pindah ke 60% dari lebar canvas
            ctx.fillText('Cash Out', canvas.width * 0.8, y); // Pindah ke 80% dari lebar canvas
            ctx.textAlign = 'left';
            y += lineHeight;
            
            // Separator dihilangkan (tanpa garis putus-putus)
            
            let totalCashIn = 0;
            let totalCashOut = 0;
            
            sessionData.cash_in_out_data.forEach(cashLine => {
                if (cashLine.payment_ref) {
                    ctx.fillText(cashLine.payment_ref.substring(0, 20), margin, y);
                    
                    if (cashLine.amount > 0) {
                        ctx.textAlign = 'center';
                        ctx.fillText(formatCurrency(Math.abs(cashLine.amount)), canvas.width * 0.6, y); // Pindah ke 60% dari lebar canvas
                        totalCashIn += Math.abs(cashLine.amount);
                        ctx.textAlign = 'left';
                    } else if (cashLine.amount < 0) {
                        ctx.textAlign = 'center';
                        ctx.fillText(formatCurrency(Math.abs(cashLine.amount)), canvas.width * 0.8, y); // Pindah ke 80% dari lebar canvas
                        totalCashOut += Math.abs(cashLine.amount);
                        ctx.textAlign = 'left';
                    }
                    y += lineHeight;
                }
            });
            
            ctx.fillText('Total', margin, y);
            ctx.textAlign = 'center';
            ctx.fillText(formatCurrency(totalCashIn), canvas.width * 0.6, y); // Pindah ke 60% dari lebar canvas
            ctx.fillText(formatCurrency(totalCashOut), canvas.width * 0.8, y); // Pindah ke 80% dari lebar canvas
            ctx.textAlign = 'left';
            y += lineHeight + 20; // 10 * 2 = 20
        }
        
        // Footer
        y += 40; // 20 * 2 = 40
        centerText('* * * * *', y);
        y += lineHeight;
        centerText('Thank you', y);
        
        // Adjust canvas height to actual content
        const actualHeight = y + 80; // 40 * 2 = 80
        console.log('Canvas height adjustment:', {
            estimatedHeight: canvas.height,
            actualHeight: actualHeight,
            difference: actualHeight - canvas.height
        });
        
        if (actualHeight > canvas.height) {
            console.log('Content exceeds canvas height, creating new canvas');
            const newCanvas = document.createElement('canvas');
            newCanvas.width = canvas.width;
            newCanvas.height = actualHeight;
            const newCtx = newCanvas.getContext('2d');
            newCtx.fillStyle = 'white';
            newCtx.fillRect(0, 0, newCanvas.width, newCanvas.height);
            newCtx.drawImage(canvas, 0, 0);
            return newCanvas;
        } else if (actualHeight < canvas.height - 100) {
            console.log('Content is much smaller than canvas, trimming canvas');
            const newCanvas = document.createElement('canvas');
            newCanvas.width = canvas.width;
            newCanvas.height = actualHeight;
            const newCtx = newCanvas.getContext('2d');
            newCtx.fillStyle = 'white';
            newCtx.fillRect(0, 0, newCanvas.width, newCanvas.height);
            newCtx.drawImage(canvas, 0, 0);
            return newCanvas;
        }
        
        return canvas;
    }

    /**
     * Transform canvas ke monochrome raster image menggunakan Floyd-Steinberg dithering
     */
    canvasToRaster(canvas) {
        const imageData = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height);
        const pixels = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        const errors = Array.from(Array(width), (_) => Array(height).fill(0));
        const rasterData = new Array(width * height).fill(0);

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                let oldColor, newColor;

                // Compute grayscale level
                const idx = (y * width + x) * 4;
                oldColor = pixels[idx] * 0.299 + pixels[idx + 1] * 0.587 + pixels[idx + 2] * 0.114;

                // Propagate the error from neighbor pixels
                oldColor += errors[x][y];
                oldColor = Math.min(255, Math.max(0, oldColor));

                if (oldColor < 128) {
                    // This pixel should be black
                    newColor = 0;
                    rasterData[y * width + x] = 1;
                } else {
                    // This pixel should be white
                    newColor = 255;
                    rasterData[y * width + x] = 0;
                }

                // Propagate the error to the following pixels using Floyd-Steinberg dithering
                const error = oldColor - newColor;
                if (error) {
                    if (x < width - 1) {
                        errors[x + 1][y] += (7 / 16) * error;
                    }
                    if (x > 0 && y < height - 1) {
                        errors[x - 1][y + 1] += (3 / 16) * error;
                    }
                    if (y < height - 1) {
                        errors[x][y + 1] += (5 / 16) * error;
                    }
                    if (x < width - 1 && y < height - 1) {
                        errors[x + 1][y + 1] += (1 / 16) * error;
                    }
                }
            }
        }

        return rasterData.join("");
    }

    /**
     * Base 64 encode raster image
     */
    encodeRaster(rasterData) {
        let encodedData = "";
        for (let i = 0; i < rasterData.length; i += 8) {
            const sub = rasterData.substr(i, 8);
            encodedData += String.fromCharCode(parseInt(sub, 2));
        }
        return btoa(encodedData);
    }

    /**
     * Mencetak ke Session Z Printer menggunakan format seperti session_z_report_button.js
     */
    async printToSessionZPrinter(sessionData) {
        try {
            const printerIP = sessionData.config.session_z_printer;
            const printerUrl = `http://${printerIP}:8088/print`;
            
            console.log("🖨️ Using Session Z Printer:", printerIP);
            console.log("🖨️ Full Printer URL:", printerUrl);
            
            // Format data ke format printer
            const printText = this.formatToSessionZPrinterText(sessionData);
            console.log("📝 Formatted Print Text:", printText);
            
            // Kirim ke printer
            const printResult = await this.sendToSessionZPrinter(printerUrl, printText);
            
            if (printResult.success) {
                console.log("✅ Session Z Printer print successful!");
                return { result: true, message: "Print successful with cut" };
            } else {
                throw new Error(printResult.message);
            }
        } catch (error) {
            console.error("Error printing to Session Z Printer:", error);
            throw error;
        }
    }

    /**
     * Format data ke format printer Session Z (seperti session_z_report_button.js)
     */
    formatToSessionZPrinterText(sessionData) {
        let printText = "";
        
        // Header
        printText += "[C]<b>SESSION Z REPORT</b>\n";
        if (sessionData.company) {
            printText += `[C]${sessionData.company.name || 'COMPANY NAME'}\n`;
            if (sessionData.company.street) printText += `[C]${sessionData.company.street}\n`;
            if (sessionData.company.street2) printText += `[C]${sessionData.company.street2}\n`;
            if (sessionData.company.city) printText += `[C]${sessionData.company.city}\n`;
            if (sessionData.company.phone) printText += `[C]Tel: ${sessionData.company.phone}\n`;
            if (sessionData.company.email) printText += `[C]Email: ${sessionData.company.email}\n`;
        }
        printText += "[C]===============================================\n";
        
        // Session Info
        printText += `[L]Session: ${sessionData.name || 'N/A'}\n`;
        printText += `[L]Report ON: ${sessionData.report_on || 'N/A'}\n`;
        printText += `[L]Salesperson: ${sessionData.user_id?.[1] || 'N/A'}\n`;
        printText += `[L]Status: ${sessionData.state || 'N/A'}\n`;
        if (sessionData.start_at) printText += `[L]Opened Date: ${new Date(sessionData.start_at).toLocaleString('id-ID')}\n`;
        if (sessionData.stop_at) printText += `[L]Closed Date: ${new Date(sessionData.stop_at).toLocaleString('id-ID')}\n`;
        printText += "[C]===============================================\n";
        
        // Financial Summary
        if (sessionData.amount_data && typeof sessionData.amount_data === 'object') {
            const amountData = sessionData.amount_data;
            const currencySymbol = sessionData.currency?.symbol || 'Rp';
            
            printText += "[L]<b>RINGKASAN KEUANGAN</b>\n";
            printText += "[C]------------------------------------------\n";
            printText += `[L]Opening Balance[R]${currencySymbol} ${(sessionData.cash_register_balance_start || 0).toLocaleString()}\n`;
            printText += `[L]Closing Balance[R]${currencySymbol} ${(sessionData.cash_register_balance_end_real || 0).toLocaleString()}\n`;
            printText += `[L]Difference[R]${currencySymbol} ${(sessionData.cash_register_difference || 0).toLocaleString()}\n`;
            printText += `[L]Gross Sales[R]${currencySymbol} ${(amountData.total_sale || 0).toLocaleString()}\n`;
            printText += `[L]Tax Amount[R]${currencySymbol} ${(amountData.tax || 0).toLocaleString()}\n`;
            printText += `[L]Discount Amount[R]${currencySymbol} ${(amountData.discount || 0).toLocaleString()}\n`;
            printText += "[C]------------------------------------------\n";
            printText += `[L]<b>TOTAL AMOUNT[R]${currencySymbol} ${(amountData.final_total || 0).toLocaleString()}</b>\n`;
            printText += "[C]===============================================\n";
        }
        
        // Product/Variant Wise Detail
        if (sessionData.config && sessionData.config.show_product_wise_detail && sessionData.product_sales && Object.keys(sessionData.product_sales).length > 0) {
            const titleText = sessionData.config.product_or_variant === 'product' ? 'Product Wise Sales' : 'Product Variant Wise Sales';
            const columnText = sessionData.config.product_or_variant === 'product' ? 'Product' : 'Product Variant';
            
            printText += `[C]<b>${titleText}</b>\n`;
            printText += "[C]-----------------------------------------------\n";
            printText += `[L]${columnText}[R]Qty\n`;
            printText += "[C]-----------------------------------------------\n";
            
            let totalItems = 0;
            for (const [product, qty] of Object.entries(sessionData.product_sales)) {
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
        
        // Category Wise Sales
        if (sessionData.config && sessionData.config.show_category_wise_sales && sessionData.amount_data?.products_sold) {
            printText += "[C]<b>Category Wise Sales</b>\n";
            printText += "[C]-----------------------------------------------\n";
            printText += "[L]Category[R]Qty\n";
            printText += "[C]-----------------------------------------------\n";
            
            for (const [category, qty] of Object.entries(sessionData.amount_data.products_sold)) {
                const displayCategory = category === 'undefine' ? 'Others' : category;
                printText += `[L]${displayCategory}[R]${qty}\n`;
            }
            printText += `[L]Total Items : ${sessionData.amount_data.total_sale_product || 0}\n`;
            printText += "[C]===============================================\n";
        }
        
        // Taxes Detail
        if (sessionData.config && sessionData.config.show_taxes_detail && sessionData.taxes_data && Object.keys(sessionData.taxes_data).length > 0) {
            printText += "[C]<b>Taxes Detail</b>\n";
            printText += "[C]-----------------------------------------------\n";
            printText += "[L]Tax[R]Amount\n";
            printText += "[C]-----------------------------------------------\n";
            
            let taxTotal = 0;
            const currencySymbol = sessionData.currency?.symbol || 'Rp';
            for (const [tax, amount] of Object.entries(sessionData.taxes_data)) {
                const displayTax = tax === 'undefine' ? 'Others' : tax;
                printText += `[L]${displayTax}[R]${currencySymbol} ${(amount || 0).toLocaleString()}\n`;
                taxTotal += parseFloat(amount || 0);
            }
            printText += "[C]-----------------------------------------------\n";
            printText += `[L]Total[R]${currencySymbol} ${taxTotal.toLocaleString()}\n`;
            printText += "[C]===============================================\n";
        }
        
        // Pricelist Detail
        if (sessionData.config && sessionData.config.show_pricelist_detail && sessionData.pricelist_data && Object.keys(sessionData.pricelist_data).length > 0) {
            printText += "[C]<b>Pricelist Detail</b>\n";
            printText += "[C]-----------------------------------------------\n";
            printText += "[L]Pricelist[C]Qty[R]Amount\n";
            printText += "[C]-----------------------------------------------\n";
            
            let pricelistTotal = 0;
            let pricelistQtyTotal = 0;
            const currencySymbol = sessionData.currency?.symbol || 'Rp';
            for (const [pricelist, amount] of Object.entries(sessionData.pricelist_data)) {
                const displayPricelist = pricelist === 'undefine' ? 'Others' : pricelist;
                const qty = sessionData.pricelist_qty_data && sessionData.pricelist_qty_data[pricelist] ? sessionData.pricelist_qty_data[pricelist] : 0;
                printText += `[L]${displayPricelist}[C]${qty}[R]${currencySymbol} ${(amount || 0).toLocaleString()}\n`;
                pricelistTotal += parseFloat(amount || 0);
                pricelistQtyTotal += parseInt(qty || 0);
            }
            printText += "[C]-----------------------------------------------\n";
            printText += `[L]Total[C]${pricelistQtyTotal}[R]${currencySymbol} ${pricelistTotal.toLocaleString()}\n`;
            printText += "[C]===============================================\n";
        }
        
        // Payment Detail
        if (sessionData.config && sessionData.config.show_payment_detail && sessionData.payment_methods && sessionData.payment_methods.length > 0) {
            printText += "[C]<b>Payment Detail</b>\n";
            printText += "[C]-----------------------------------------------\n";
            printText += "[L]Method[R]Amount\n";
            printText += "[C]-----------------------------------------------\n";
            
            let paymentTotal = 0;
            const currencySymbol = sessionData.currency?.symbol || 'Rp';
            sessionData.payment_methods.forEach(payment => {
                printText += `[L]${payment.name}[R]${currencySymbol} ${(payment.total || 0).toLocaleString()}\n`;
                paymentTotal += parseFloat(payment.total || 0);
            });
            printText += "[C]-----------------------------------------------\n";
            printText += `[L]Total[R]${currencySymbol} ${paymentTotal.toLocaleString()}\n`;
            printText += "[C]===============================================\n";
        }
        
        // Cash In Out Details
        if (sessionData.config && sessionData.config.show_cash_in_out_details && sessionData.cash_in_out_data && sessionData.cash_in_out_data.length > 0) {
            printText += "[C]<b>Cash In Out Details</b>\n";
            printText += "[C]-----------------------------------------------\n";
            printText += "[L]Label[C]Cash In[R]Cash Out\n";
            printText += "[C]-----------------------------------------------\n";
            
            let totalCashIn = 0;
            let totalCashOut = 0;
            const currencySymbol = sessionData.currency?.symbol || 'Rp';
            sessionData.cash_in_out_data.forEach(transaction => {
                const amount = parseFloat(transaction.amount || 0);
                const cashIn = amount > 0 ? amount.toLocaleString() : '';
                const cashOut = amount < 0 ? Math.abs(amount).toLocaleString() : '';
                
                printText += `[L]${transaction.payment_ref || ''}[C]${currencySymbol} ${cashIn}[R]${currencySymbol} ${cashOut}\n`;
                
                if (amount > 0) totalCashIn += amount;
                if (amount < 0) totalCashOut += Math.abs(amount);
            });
            printText += "[C]-----------------------------------------------\n";
            printText += `[L]Total[C]${currencySymbol} ${totalCashIn.toLocaleString()}[R]${currencySymbol} ${totalCashOut.toLocaleString()}\n`;
            printText += "[C]===============================================\n";
        }
        
        // Footer
        printText += "[C]Terima kasih\n";
        if (sessionData.company && sessionData.company.website) printText += `[C]${sessionData.company.website}\n`;
        printText += "[C]\n";
        printText += "[C]\n";
        
        // Add spacing before cut
        printText += "\n\n\n";
        
        return printText;
    }

    /**
     * Kirim ke Session Z Printer (seperti session_z_report_button.js)
     */
    async sendToSessionZPrinter(printerUrl, printText) {
        try {
            console.log("🖨️ Sending to Session Z printer:", printerUrl);
            console.log("📝 Print Text:", printText);
            
            // Payload untuk Session Z printer menggunakan tipe 'formatted'
            const payload = {
                type: "formatted",
                data: printText,
                dpi: 203,
                widthMm: 69.6,
                charsPerLine: 47
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
                await this.sendCutCommand(printerUrl);
                
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

    /**
     * Kirim perintah cut terpisah (seperti session_z_report_button.js)
     */
    async sendCutCommand(printerUrl) {
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
}

// Export service
export const epsonPrinterService = new EpsonPrinterService();

// Service akan didaftarkan melalui start function

// Module start function
export function start(env, { addCleanup }) {
    // Service sudah diinisialisasi di atas
    return epsonPrinterService;
}
