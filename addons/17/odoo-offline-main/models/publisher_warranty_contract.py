from odoo import models
from odoo.release import version_info

from datetime import datetime
from dateutil.relativedelta import relativedelta


class PublisherWarrantyContract(models.AbstractModel):
    _inherit = "publisher_warranty.contract"

    def update_notification(self, cron_mode=True):
        if version_info[5] == "e":
            set_param = self.env['ir.config_parameter'].sudo().set_param
            now = datetime.now()
            set_param('database.expiration_date', (now + relativedelta(years=1)).strftime('%Y-%m-%d %H:%M:%S'))
            set_param('database.expiration_reason', 'renewal')
        return True
