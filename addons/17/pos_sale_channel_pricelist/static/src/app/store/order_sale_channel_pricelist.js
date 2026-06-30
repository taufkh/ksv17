/** @odoo-module */

import { Order, Orderline } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    getPricelistById(pricelistId) {
        return (this.pricelists || []).find((pricelist) => pricelist.id === pricelistId) || null;
    },

    getDefaultSaleChannelPricelist() {
        return this.default_pricelist || null;
    },

    getSaleChannelPricelist(channelId) {
        const channel = this.getSaleChannelById ? this.getSaleChannelById(channelId) : null;
        const pricelistId = Array.isArray(channel?.pricelist_id)
            ? channel.pricelist_id[0]
            : channel?.pricelist_id;

        return this.getPricelistById(pricelistId) || this.getDefaultSaleChannelPricelist();
    },
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        if (!this.pricelist) {
            this.pricelist = this.getSaleChannelMappedPricelist();
        }
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if (json.sale_channel_id || !this.pricelist) {
            this.pricelist = this.getSaleChannelMappedPricelist();
        }
    },

    getFallbackPricelist() {
        return this.pos.getDefaultSaleChannelPricelist();
    },

    getSaleChannelMappedPricelist(channelId = null) {
        return this.pos.getSaleChannelPricelist(channelId || this.getSaleChannelId());
    },

    getEffectivePricelistForLine(line) {
        if (line?.hasSaleChannelOverride?.()) {
            return this.getSaleChannelMappedPricelist(line.sale_channel_id);
        }
        return this.pricelist || this.getSaleChannelMappedPricelist() || this.getFallbackPricelist();
    },

    setSaleChannelId(channelId) {
        this.assert_editable();
        this.sale_channel_id = channelId || this.pos.getDefaultSaleChannelId();
        this._applyOrderChannelPricing();
        this.save_to_db();
    },

    _applyOrderChannelPricing() {
        const orderPricelist = this.getSaleChannelMappedPricelist();
        this.set_pricelist(orderPricelist);

        const overriddenLines = this.get_orderlines().filter(
            (line) => line.hasSaleChannelOverride?.() && !line.comboLines?.length
        );
        overriddenLines.forEach((line) => this.repriceLineForSaleChannel(line, { force: false }));
    },

    repriceLineForSaleChannel(line, { force = false } = {}) {
        if (!line) {
            return;
        }
        const pricelist = this.getEffectivePricelistForLine(line);
        if (!pricelist) {
            return;
        }
        if (!force && line.price_type !== "original") {
            return;
        }
        if (force) {
            line.price_type = "original";
        }

        if (line.comboLines?.length) {
            this._repriceComboChildren(line, pricelist, force);
            return;
        }

        if (line.comboParent) {
            this._repriceComboChild(line, pricelist, force);
            return;
        }

        if (line.is_lot_tracked()) {
            const relatedLines = [];
            const price = line.product.get_price(
                pricelist,
                line.get_quantity(),
                line.get_price_extra(),
                false,
                line,
                relatedLines
            );
            relatedLines.forEach((relatedLine) => {
                if (force) {
                    relatedLine.price_type = "original";
                }
                relatedLine.set_unit_price(price);
                this.fix_tax_included_price(relatedLine);
            });
            return;
        }

        line.set_unit_price(
            line.product.get_price(pricelist, line.get_quantity(), line.get_price_extra(), false)
        );
        this.fix_tax_included_price(line);
    },

    _getComboLinePricing(parentLine, pricelist) {
        return this.compute_child_lines(
            parentLine.product,
            parentLine.comboLines.map((childLine) => {
                const comboLineCopy = { ...childLine.comboLine };
                if (childLine.attribute_value_ids) {
                    comboLineCopy.configuration = {
                        attribute_value_ids: childLine.attribute_value_ids,
                    };
                }
                return comboLineCopy;
            }),
            pricelist
        );
    },

    _repriceComboChildren(parentLine, pricelist, force) {
        const attributePrices = this._getComboLinePricing(parentLine, pricelist);
        parentLine.comboLines.forEach((childLine) => {
            const comboPrice = attributePrices.find(
                (item) => item.comboLine.id === childLine.comboLine.id
            );
            if (!comboPrice) {
                return;
            }
            if (!force && childLine.price_type !== "original") {
                return;
            }
            if (force) {
                childLine.price_type = "original";
            }
            childLine.set_unit_price(comboPrice.price);
            this.fix_tax_included_price(childLine);
        });
    },

    _repriceComboChild(line, pricelist, force) {
        const parentLine = line.comboParent;
        if (!parentLine) {
            return;
        }
        const comboPrice = this._getComboLinePricing(parentLine, pricelist).find(
            (item) => item.comboLine.id === line.comboLine.id
        );
        if (!comboPrice) {
            return;
        }
        if (!force && line.price_type !== "original") {
            return;
        }
        if (force) {
            line.price_type = "original";
        }
        line.set_unit_price(comboPrice.price);
        this.fix_tax_included_price(line);
    },
});

patch(Orderline.prototype, {
    setSaleChannelId(channelId) {
        this.order.assert_editable();
        const normalizedChannelId = channelId || false;
        this.sale_channel_id = normalizedChannelId;
        this.price_type = "original";

        if (this.comboLines?.length) {
            this.comboLines.forEach((childLine) => {
                childLine.sale_channel_id = normalizedChannelId;
                childLine.price_type = "original";
            });
        }

        this.order.repriceLineForSaleChannel(this, { force: true });
        this.order.save_to_db();
    },
});
