/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { BasePrinter } from "@point_of_sale/app/printer/base_printer";

const DEFAULT_CONFIG = {
    baudRate: 9600,
    paperWidth: "58",
};

export class BluetoothEscPosPrinter extends BasePrinter {
    setup() {
        super.setup(...arguments);
        this.config = { ...DEFAULT_CONFIG };
        this.port = null;
        this.writer = null;
        this.connectionPromise = null;
        if (navigator.serial?.addEventListener) {
            navigator.serial.addEventListener("disconnect", this._handleDisconnect.bind(this));
        }
    }

    configure(posConfig = {}) {
        this.config = {
            baudRate: Number.parseInt(posConfig.bluetooth_printer_baud_rate || DEFAULT_CONFIG.baudRate, 10),
            paperWidth: posConfig.bluetooth_printer_paper_width || DEFAULT_CONFIG.paperWidth,
        };
    }

    isSupported() {
        return Boolean(navigator.serial);
    }

    getStatusLabel() {
        if (!this.isSupported()) {
            return _t("Browser ini belum mendukung Web Serial.");
        }
        if (this.writer) {
            return _t("Printer Bluetooth tersambung.");
        }
        return _t("Printer Bluetooth belum tersambung.");
    }

    async hasAuthorizedPort() {
        if (!this.isSupported()) {
            return false;
        }
        const ports = await navigator.serial.getPorts();
        if (!this.port && ports.length) {
            this.port = ports[0];
        }
        return Boolean(this.port || ports.length);
    }

    async connectInteractive() {
        await this.ensureConnection({ interactive: true });
        return true;
    }

    async ensureConnection({ interactive = false } = {}) {
        if (!this.isSupported()) {
            throw {
                title: _t("Web Serial tidak tersedia"),
                body: _t("Gunakan Google Chrome di Android dan buka POS lewat localhost atau HTTPS."),
            };
        }
        if (this.connectionPromise) {
            return this.connectionPromise;
        }
        this.connectionPromise = this._connect(interactive);
        try {
            return await this.connectionPromise;
        } finally {
            this.connectionPromise = null;
        }
    }

    async _connect(interactive) {
        if (this.writer && this.port?.writable) {
            return true;
        }

        if (!this.port) {
            const ports = await navigator.serial.getPorts();
            if (ports.length) {
                this.port = ports[0];
            }
        }

        if (!this.port && interactive) {
            this.port = await navigator.serial.requestPort({});
        }

        if (!this.port) {
            throw {
                title: _t("Printer Bluetooth belum dipilih"),
                body: _t("Tap Connect Printer sekali untuk memilih printer Panda yang sudah di-pair di tablet."),
            };
        }

        if (!this.port.readable || !this.port.writable) {
            await this.port.open({
                baudRate: this.config.baudRate,
                dataBits: 8,
                stopBits: 1,
                parity: "none",
                flowControl: "none",
                bufferSize: 8192,
            });
        }

        this.writer = this.port.writable.getWriter();
        return true;
    }

    async disconnect() {
        if (this.writer) {
            try {
                this.writer.releaseLock();
            } catch {
                // ignore lock release errors
            }
        }
        this.writer = null;
        if (this.port) {
            try {
                await this.port.close();
            } catch {
                // ignore close errors
            }
        }
        this.port = null;
    }

    _handleDisconnect(event) {
        if (event.target === this.port) {
            this.writer = null;
            this.port = null;
        }
    }

    async printReceipt(receipt) {
        await this.ensureConnection({ interactive: true });
        return super.printReceipt(receipt);
    }

    async printCanvas(canvas, { interactive = true } = {}) {
        await this.ensureConnection({ interactive });
        const payload = this.processCanvas(canvas);
        const result = await this.sendPrintingJob(payload);
        if (result?.result) {
            return { successful: true };
        }
        return this.getResultsError(result);
    }

    async sendPrintingJob(payload) {
        try {
            await this.ensureConnection();
            await this.writer.write(payload);
            return { result: true };
        } catch (error) {
            await this.disconnect();
            return {
                result: false,
                error,
            };
        }
    }

    openCashbox() {
        return false;
    }

    processCanvas(canvas) {
        const resizedCanvas = this._resizeCanvas(canvas);
        const raster = this._canvasToRaster(resizedCanvas);
        const commands = [
            Uint8Array.from([0x1b, 0x40]),
            Uint8Array.from([0x1b, 0x61, 0x01]),
            ...raster,
            Uint8Array.from([0x1b, 0x64, 0x04]),
            Uint8Array.from([0x1b, 0x61, 0x00]),
        ];
        return this._concatChunks(commands);
    }

    _resizeCanvas(sourceCanvas) {
        const targetWidth = this.config.paperWidth === "80" ? 576 : 384;
        const safeWidth = Math.max(8, Math.floor(targetWidth / 8) * 8);
        const ratio = safeWidth / sourceCanvas.width;
        const targetHeight = Math.max(1, Math.round(sourceCanvas.height * ratio));
        const canvas = document.createElement("canvas");
        canvas.width = safeWidth;
        canvas.height = targetHeight;
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        ctx.fillStyle = "#FFFFFF";
        ctx.fillRect(0, 0, safeWidth, targetHeight);
        ctx.drawImage(sourceCanvas, 0, 0, safeWidth, targetHeight);
        return canvas;
    }

    _canvasToRaster(canvas) {
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const bytesPerRow = canvas.width / 8;
        const maxChunkHeight = 255;
        const chunks = [];

        for (let startY = 0; startY < canvas.height; startY += maxChunkHeight) {
            const chunkHeight = Math.min(maxChunkHeight, canvas.height - startY);
            const rasterBytes = new Uint8Array(bytesPerRow * chunkHeight);

            for (let y = 0; y < chunkHeight; y++) {
                for (let xByte = 0; xByte < bytesPerRow; xByte++) {
                    let byte = 0;
                    for (let bit = 0; bit < 8; bit++) {
                        const x = xByte * 8 + bit;
                        const pixelIndex = ((startY + y) * canvas.width + x) * 4;
                        const alpha = data[pixelIndex + 3];
                        const luminance =
                            data[pixelIndex] * 0.299 +
                            data[pixelIndex + 1] * 0.587 +
                            data[pixelIndex + 2] * 0.114;
                        if (alpha > 0 && luminance < 180) {
                            byte |= 0x80 >> bit;
                        }
                    }
                    rasterBytes[y * bytesPerRow + xByte] = byte;
                }
            }

            chunks.push(
                this._concatChunks([
                    Uint8Array.from([
                        0x1d,
                        0x76,
                        0x30,
                        0x00,
                        bytesPerRow & 0xff,
                        (bytesPerRow >> 8) & 0xff,
                        chunkHeight & 0xff,
                        (chunkHeight >> 8) & 0xff,
                    ]),
                    rasterBytes,
                ])
            );
        }

        return chunks;
    }

    _concatChunks(chunks) {
        const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
        const result = new Uint8Array(totalLength);
        let offset = 0;
        for (const chunk of chunks) {
            result.set(chunk, offset);
            offset += chunk.length;
        }
        return result;
    }
}
