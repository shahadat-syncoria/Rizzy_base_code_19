# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
import datetime
from odoo import fields, models, exceptions, _
from pprint import pprint
import re
logger = logging.getLogger(__name__)


class OrderFetchWizard(models.TransientModel):
    _name = 'order.fetch.wizard'
    _description = 'Order Fetch Wizard'

    order_status = fields.Selection([], string="Order Status")

    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
        required=True,
        domain="[('marketplace_state', '=', 'confirm')]"
    )
    date_from = fields.Date('From')
    date_to = fields.Date('To')

    def fetch_orders(self):
        if self.instance_id:
            kwargs = {'marketplace_instance_id': self.instance_id}
            if hasattr(self, '%s_fetch_orders' % self.instance_id.marketplace_instance_type):
                return getattr(self, '%s_fetch_orders' % self.instance_id.marketplace_instance_type)(kwargs)
        else:
            logger.warning(_("No Marketplace Instance Setup!"))
