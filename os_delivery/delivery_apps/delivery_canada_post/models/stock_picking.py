# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError

customs_uom = [('PCE', 'Piece'),
                ('NMB', 'Number'),
                ('PAR', 'Pair'),
                ('PKG', 'Package'),
                ('ENV', 'Envelope'),
                ('LTR', 'Litre'),
                ('MLT', 'Millilitre'),
                ('BOX', 'BOX'),
                ('BAG', 'BAG'),
                ('MTR', 'Metre'),
                ('MMT', 'Millimetre'),
                ('DZN', 'Dozen'),
                ('GRM', 'Gram'),
                ('KGM', 'Kilogram'),
                ('CTN', 'Carton'),
                ('BIN', 'Bin'),
                ('SET', 'Number of sets'),
                ('BOT', 'BOT'),
                ('BOT', 'Bottle'),
                ('TBE', 'Tube'),
                ('KIT', 'Kit'),
                ]

class StockPickingCanadaPost(models.Model):
    _inherit = 'stock.picking'

    canadapost_customer_type = fields.Selection(
        string='Customer type',
        selection=[('counter', 'Counter'), ('commercial', 'Commercial')]
    )
    canadapost_link_self = fields.Char(readonly=True)
    canadapost_link_media= fields.Char(readonly=True)
    canadapost_link_label = fields.Char(readonly=True)
    canadapost_link_return = fields.Char(readonly=True)
    canadapost_cod_remittance = fields.Char(readonly=True)
    canadapost_cod_remittance_return = fields.Char(readonly=True)
    canadapost_link_cminv = fields.Char(readonly=True)
    canadapost_link_details = fields.Char(readonly=True)
    canadapost_link_price = fields.Char(readonly=True)
    canadapost_link_group = fields.Char(readonly=True)
    canadapost_link_receipt = fields.Char(readonly=True)
    canadapost_link_refund = fields.Char(readonly=True)
    canadapost_shipping_pointid = fields.Char()
    connector_label_url = fields.Char(string='Syncoria Connector Label URL')
    connector_return_label_url = fields.Char(string='Syncoria Connector Label URL')


    def _set_links(self, links):
        if self.carrier_id.canadapost_customer_type == 'counter':
            labels = ['self','label','commercialInvoice','details','receipt','refund']
            link_data = {}
            for link in links:
                link_data['canadapost_link'+'_'+str(link.get('@rel'))] = link.get('@href')
            self.write(link_data)

    def canadapost_get_shipping_label(self):
        if self.connector_label_url:
            self.carrier_id.canapost_get_labels(self)
        else:
            raise UserError("No Shipment Created!!")
    