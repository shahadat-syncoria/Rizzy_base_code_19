import pprint
import json
import re
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    marketplace_type = fields.Selection(related="marketplace_instance_id.marketplace_instance_type", string="Marketplace Type",store=True)
    marketplace_instance_id = fields.Many2one("marketplace.instance", string="Marketplace Instance ID")