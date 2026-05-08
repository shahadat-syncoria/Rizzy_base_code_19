# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, exceptions, _,fields
import logging
import re

logger = logging.getLogger(__name__)


class CustomerFetchWizard(models.TransientModel):
    _name = 'customer.fetch.wizard'
    _description = 'Customer Fetch Wizard'
    _inherit = 'order.fetch.wizard'

    def fetch_customers_to_odoo(self):
        if self.instance_id:
            kwargs = {'marketplace_instance_id': self.instance_id}
            if hasattr(self, '%s_fetch_customers_to_odoo' % self.instance_id.marketplace_instance_type):
                return getattr(self, '%s_fetch_customers_to_odoo' % self.instance_id.marketplace_instance_type)(kwargs)
        else:
            logger.warning(_("No Marketplace Instance Setup!"))
