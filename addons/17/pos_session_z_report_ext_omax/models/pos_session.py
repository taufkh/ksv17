# -*- coding: utf-8 -*-
import datetime
from odoo import fields, models, api
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from collections import Counter
import json, ast, requests
import logging

_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _inherit = 'pos.config'

    omax_session_z_report = fields.Boolean(string='Session Z Report', help='This will allow to print Session Z Report directly from POS screen')
    show_details_in_session_z_report = fields.Boolean(string='Show Details in Session Z Report')
    show_product_wise_detail = fields.Boolean(string='Product Or Variant Wise Detail')
    product_or_variant = fields.Selection([
        ('product', 'Product'),
        ('variant', 'Product Variant'),], default='variant', string='Product Or Variant')
    show_category_wise_sales = fields.Boolean(string='Category Wise Sales')
    show_taxes_detail = fields.Boolean(string='Taxes Detail')
    show_pricelist_detail = fields.Boolean(string='Pricelist Detail')
    show_payment_detail = fields.Boolean(string='Payment Detail')
    show_cash_in_out_details = fields.Boolean(string='Cash In Out Details')
    session_z_printer = fields.Char(string='Session Z Printer IP', help='IP Address for Session Z Report printer (e.g., 192.168.1.17)')
    use_session_z_printer_for_pos = fields.Boolean(string='Use Session Z Printer for POS', help='Use Session Z Printer for POS Session Report instead of Epson printer')

class ResConfigZreport(models.TransientModel):
    _inherit = 'res.config.settings'

    omax_session_z_report = fields.Boolean(related='pos_config_id.omax_session_z_report', readonly=False)
    show_details_in_session_z_report = fields.Boolean(related='pos_config_id.show_details_in_session_z_report', readonly=False)
    show_product_wise_detail = fields.Boolean(related='pos_config_id.show_product_wise_detail', readonly=False)
    product_or_variant = fields.Selection(related='pos_config_id.product_or_variant', readonly=False)
    show_category_wise_sales = fields.Boolean(related='pos_config_id.show_category_wise_sales', readonly=False)
    show_taxes_detail = fields.Boolean(related='pos_config_id.show_taxes_detail', readonly=False)
    show_pricelist_detail = fields.Boolean(related='pos_config_id.show_pricelist_detail', readonly=False)
    show_payment_detail = fields.Boolean(related='pos_config_id.show_payment_detail', readonly=False)
    show_cash_in_out_details = fields.Boolean(related='pos_config_id.show_cash_in_out_details', readonly=False)
    session_z_printer = fields.Char(related='pos_config_id.session_z_printer', readonly=False)
    use_session_z_printer_for_pos = fields.Boolean(related='pos_config_id.use_session_z_printer_for_pos', readonly=False)

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_config(self):
        result = super()._loader_params_pos_config()
        fields = result['search_params'].get('fields')
        if fields:
            for field_name in [
                'omax_session_z_report',
                'show_details_in_session_z_report',
                'show_product_wise_detail',
                'product_or_variant',
                'show_category_wise_sales',
                'show_taxes_detail',
                'show_pricelist_detail',
                'show_payment_detail',
                'show_cash_in_out_details',
                'session_z_printer',
                'use_session_z_printer_for_pos',
            ]:
                if field_name not in fields:
                    fields.append(field_name)
        return result
    
    def action_session_z_report(self):
        return self.env.ref('pos_session_z_report_ext_omax.action_report_session_z').report_action(self)
    
    def action_hello(self):
        """Method untuk tombol Hello - mengembalikan JSON data laporan closing harian"""
        # Kumpulkan semua data yang sama dengan report PDF
        session_amount_data = self.get_session_amount_data()
        product_sales = dict(self.get_product_variant_wise_sale()) if self.config_id.show_product_wise_detail else {}
        taxes_data = self.get_taxes_data() if self.config_id.show_taxes_detail else {}
        pricelist_data = self.get_pricelist() if self.config_id.show_pricelist_detail else {}
        payment_data = self.get_payment_data() if self.config_id.show_payment_detail else []
        
        # Ambil cash in/out data jika diperlukan
        cash_in_out_data = []
        if self.config_id.show_cash_in_out_details and self.statement_line_ids:
            cash_in_out_data = self.env['account.bank.statement.line'].browse(self.statement_line_ids.ids).read([
                'payment_ref', 'amount'
            ])
        
        # Struktur JSON yang sama dengan struk PDF
        closing_report_data = {
            'report_title': 'Laporan Closing Harian',
            'report_on': self.get_current_datetime(),
            
            # Company Information
            'company': {
                'name': self.user_id.company_id.name,
                'street': self.user_id.company_id.street,
                'street2': self.user_id.company_id.street2,
                'city': self.user_id.company_id.city,
                'state': self.user_id.company_id.state_id.name if self.user_id.company_id.state_id else '',
                'country': self.user_id.company_id.country_id.name if self.user_id.company_id.country_id else '',
                'phone': self.user_id.company_id.phone,
                'email': self.user_id.company_id.email,
                'website': self.user_id.company_id.website,
            },
            
            # Session Information
            'session': {
                'name': self.name,
                'salesperson': self.user_id.name,
                'opened_date': str(self.get_opened_date()) if self.start_at else '',
                'closed_date': str(self.get_closed_date()) if self.stop_at else '',
                'status': self.state,
                'config_name': self.config_id.name,
            },
            
            # Financial Summary
            'financials': {
                'opening_balance': self.cash_register_balance_start,
                'closing_balance': self.cash_register_balance_end_real,
                'difference': self.cash_register_difference,
                'gross_sales': session_amount_data.get('total_sale', 0),
                'tax': session_amount_data.get('tax', 0),
                'discount_amount': session_amount_data.get('discount', 0),
                'total': session_amount_data.get('final_total', 0),
                'currency': self.currency_id.name,
                'currency_symbol': self.currency_id.symbol,
            },
            
            # Product Details (jika diaktifkan)
            'product_details': {
                'enabled': self.config_id.show_product_wise_detail,
                'type': self.config_id.product_or_variant,
                'products': product_sales,
                'total_items': sum(product_sales.values()) if product_sales else 0,
            },
            
            # Category Sales (jika diaktifkan)
            'category_sales': {
                'enabled': self.config_id.show_category_wise_sales,
                'categories': session_amount_data.get('products_sold', {}),
                'total_category_qty': session_amount_data.get('total_sale_product', 0),
            },
            
            # Tax Details (jika diaktifkan)
            'tax_details': {
                'enabled': self.config_id.show_taxes_detail,
                'taxes': taxes_data,
                'total_tax': sum(taxes_data.values()) if taxes_data else 0,
            },
            
            # Pricelist Details (jika diaktifkan)
            'pricelist_details': {
                'enabled': self.config_id.show_pricelist_detail,
                'pricelists': pricelist_data,
                'total_pricelist_amount': sum(pricelist_data.values()) if pricelist_data else 0,
            },
            
            # Payment Details (jika diaktifkan)
            'payment_details': {
                'enabled': self.config_id.show_payment_detail,
                'payments': payment_data,
                'total_payment_amount': sum([p.get('total', 0) for p in payment_data]) if payment_data else 0,
            },
            
            # Cash In/Out Details (jika diaktifkan)
            'cash_in_out_details': {
                'enabled': self.config_id.show_cash_in_out_details,
                'transactions': cash_in_out_data,
                'total_cash_in_out': sum([t.get('amount', 0) for t in cash_in_out_data]) if cash_in_out_data else 0,
            },
            
            # Configuration Settings
            'config': {
                'show_details_in_session_z_report': self.config_id.show_details_in_session_z_report,
                'show_product_wise_detail': self.config_id.show_product_wise_detail,
                'product_or_variant': self.config_id.product_or_variant,
                'show_category_wise_sales': self.config_id.show_category_wise_sales,
                'show_taxes_detail': self.config_id.show_taxes_detail,
                'show_pricelist_detail': self.config_id.show_pricelist_detail,
                'show_payment_detail': self.config_id.show_payment_detail,
                'show_cash_in_out_details': self.config_id.show_cash_in_out_details,
                'session_z_printer': self.config_id.session_z_printer,
            }
        }
        
        # Return sebagai custom client action dengan data JSON
        return {
            'type': 'ir.actions.client',
            'tag': 'hello_world_action',
            'params': {
                'closing_report_data': closing_report_data,
                'session_name': self.name
            }
        }
    
    def get_current_datetime(self):
        current = fields.datetime.now()
        return current.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        
    def get_opened_date(self):
        return datetime.datetime.strptime(str(self.start_at), DEFAULT_SERVER_DATETIME_FORMAT)
        
    def get_closed_date(self):
        if self.stop_at:
            return datetime.datetime.strptime(str(self.stop_at), DEFAULT_SERVER_DATETIME_FORMAT)

    def get_product_variant_wise_sale(self):
        pos_order_ids = self.env['pos.order'].search([('session_id', '=', self.id)])
        result = {}
        if self.config_id.product_or_variant == 'product':
            for pos_order in pos_order_ids:
                # For canceled orders, ignore them
                if pos_order.state == 'cancel':
                    continue
                multiplier = 1
                for line in pos_order.lines:
                    qty_multiplier = line.qty * multiplier
                    if line.product_id.product_tmpl_id.name in result:
                        result[line.product_id.product_tmpl_id.name] += qty_multiplier
                    else:
                        result.update({line.product_id.product_tmpl_id.name: qty_multiplier})

        if self.config_id.product_or_variant == 'variant':
            for pos_order in pos_order_ids:
                # For canceled orders, ignore them
                if pos_order.state == 'cancel':
                    continue
                multiplier = 1
                for line in pos_order.lines:
                    qty_multiplier = line.qty * multiplier
                    if line.product_id.display_name in result:
                        result[line.product_id.display_name] += qty_multiplier
                    else:
                        result.update({line.product_id.display_name: qty_multiplier})
        return list(result.items())
        
    def get_session_amount_data(self):
        pos_order_ids = self.env['pos.order'].search([('session_id', '=', self.id)])
        discount_amount = 0.0
        taxes_amount = 0.0
        total_sale_amount = 0.0
        total_gross_amount = 0.0
        total_sale_product = 0.0##
        sold_product = {}
        for pos_order in pos_order_ids:
            currency = pos_order.session_id.currency_id
            # For canceled orders, ignore them
            if pos_order.state == 'cancel':
                continue
            multiplier = 1
            total_gross_amount += pos_order.amount_total * multiplier
            for line in pos_order.lines:
                ####
                total_sale_product += line.qty * multiplier##
                ####
                qty_multiplier = line.qty * multiplier
                if line.product_id.pos_categ_ids:
                    for pos_categ_id in line.product_id.pos_categ_ids:
                        if pos_categ_id.name in sold_product:
                            sold_product[pos_categ_id.name] += qty_multiplier
                        else:
                            sold_product.update({pos_categ_id.name: qty_multiplier})
                else:
                    if 'undefine' in sold_product:
                        sold_product['undefine'] += qty_multiplier
                    else:
                        sold_product.update({'undefine': qty_multiplier})  
                """if line.product_id.pos_categ_id and line.product_id.pos_categ_id.name:
                    if line.product_id.pos_categ_id.name in sold_product:
                        sold_product[line.product_id.pos_categ_id.name] += line.qty
                    else:
                        sold_product.update({line.product_id.pos_categ_id.name: line.qty})
                else:
                    if 'undefine' in sold_product:
                        sold_product['undefine'] += line.qty
                    else:
                        sold_product.update({'undefine': line.qty})"""
                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.compute_all(line.price_unit * (1 - (line.discount or 0.0) / 100.0), currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes_amount += tax.get('amount', 0) * multiplier
                if line.discount > 0:
                    discount_amount += (((line.price_unit * line.qty) * line.discount) / 100) * multiplier
                if line.qty > 0:
                    total_sale_amount += line.price_unit * line.qty * multiplier
        #print("sold_product===>>>",sold_product, total_sale_product)
        return {
            'total_sale': total_sale_amount,
            'discount': discount_amount,
            'tax': taxes_amount,
            'products_sold': sold_product,
            'total_gross': total_gross_amount - taxes_amount - discount_amount,
            'final_total': total_gross_amount,
            'total_sale_product': total_sale_product,##
        }
    
    def get_taxes_data(self):
        order_ids = self.env['pos.order'].search([('session_id', '=', self.id)])
        taxes = {}
        for order in order_ids:
            currency = order.pricelist_id.currency_id
            # For canceled orders, ignore them
            if order.state == 'cancel':
                continue
            multiplier = 1
            for line in order.lines:
                if line.tax_ids_after_fiscal_position:
                    for tax in line.tax_ids_after_fiscal_position:
                        discount_amount = 0
                        if line.discount > 0:
                            discount_amount = ((line.qty*line.price_unit)* line.discount) / 100
                        untaxed_amount = (line.qty*line.price_unit) - discount_amount
                        tax_amount = ((untaxed_amount * tax.amount) / 100) * multiplier
                        if tax.name:
                            if tax.name in taxes:
                                taxes[tax.name] += tax_amount
                            else:
                                taxes.update({tax.name : tax_amount})
                        else:
                            if 'undefine' in taxes:
                                taxes['undefine'] += tax_amount
                            else:
                                taxes.update({'undefine': tax_amount})
        return taxes    
    
    
    def get_pricelist(self):
        pos_order_ids = self.env['pos.order'].search([('session_id', '=', self.id)])
        pricelist = {}
        for pos_order in pos_order_ids:
            # For canceled orders, ignore them
            if pos_order.state == 'cancel':
                continue
            multiplier = 1
            amount_multiplier = pos_order.amount_total * multiplier
            if pos_order.pricelist_id.name:
                if pos_order.pricelist_id.name in pricelist:
                    pricelist[pos_order.pricelist_id.name] += amount_multiplier
                else:
                    pricelist.update({pos_order.pricelist_id.name : amount_multiplier})
            else:
                if 'undefine' in pricelist:
                    pricelist['undefine'] += amount_multiplier
                else:
                    pricelist.update({'undefine': amount_multiplier})
        return pricelist
        
    def get_pricelist_qty(self, pricelist):
        if pricelist:
            qty_pricelist = 0
            pricelist_obj = self.env['product.pricelist'].search([('name','=', str(pricelist))])
            if pricelist_obj:
                pos_order_ids = self.env['pos.order'].search([('session_id', '=', self.id),('pricelist_id.id','=',pricelist_obj.id), ('state', '!=', 'cancel')])
                qty_pricelist = len(pos_order_ids)
            else:
                if pricelist == 'undefine':
                    pos_order_ids = self.env['pos.order'].search([('session_id', '=', self.id),('pricelist_id','=',False), ('state', '!=', 'cancel')])
                    qty_pricelist = len(pos_order_ids)
            return int(qty_pricelist)
            
    def get_payment_data(self):
        pos_payment_ids = self.env["pos.payment"].search([('session_id', '=', self.id)]).ids
        if pos_payment_ids:
            # Join with pos_order to check if order is canceled, then ignore it
            self.env.cr.execute("""
                SELECT ppm.name, 
                       sum(pp.amount) total
                FROM pos_payment AS pp
                INNER JOIN pos_order AS po ON pp.pos_order_id = po.id
                INNER JOIN pos_payment_method AS ppm ON pp.payment_method_id = ppm.id
                WHERE pp.id IN %s AND po.state != 'cancel'
                GROUP BY ppm.name;
            """, (tuple(pos_payment_ids),))
            payments = self.env.cr.dictfetchall()
        else:
            payments = []
        #add tri
        for payment in payments:
            for key, value in payment.items():
                if key == 'name':
                    if self.env.user.lang in list(value.keys()):
                        payment.update({'name':value[self.env.user.lang]})
                    else:
                        for k, v in value.items():
                            payment.update({'name':v})
        return payments
        
    def get_payment_qty(self, payment_method):
        qty_payment_method = 0
        if payment_method:
            orders = self.env['pos.order'].search([('session_id', '=', self.id), ('state', '!=', 'cancel')])
            st_line_obj = self.env["account.bank.statement.line"].search([('pos_statement_id', 'in', orders.ids)])
            if len(st_line_obj) > 0:
                res = []
                for line in st_line_obj:
                    res.append(line.journal_id.name)
                res_dict = ast.literal_eval(json.dumps(dict(Counter(res))))
                if payment_method in res_dict:
                    qty_payment_method = res_dict[payment_method]
        return int(qty_payment_method)
