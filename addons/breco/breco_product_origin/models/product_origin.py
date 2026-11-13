from odoo import fields, models


class BrecoProductProcessor(models.Model):
    _name = 'breco.product.processor'
    _description = 'Product Processor'
    _order = 'name, id'

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)


class BrecoProductRegion(models.Model):
    _name = 'breco.product.region'
    _description = 'Product Region'
    _order = 'name, id'

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    breco_processor_id = fields.Many2one('breco.product.processor', string='Processor', ondelete='restrict', index=True)
    breco_region_id = fields.Many2one('breco.product.region', string='Region', ondelete='restrict', index=True)
