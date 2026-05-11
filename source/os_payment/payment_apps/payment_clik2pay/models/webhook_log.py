# -*- coding: utf-8 -*-

from odoo import models, fields

class clik2payWebhookLog(models.Model):
    _name = 'clik2pay.webhook.log'
    _description = 'Clik2pay Webhook Log'
    _rec_name = "resource_id"

    resource_id = fields.Char(string='Transaction ID', readonly=True)
    event_type = fields.Char(string='Event Type', readonly=True)
    message = fields.Text(string='Message', readonly=True)
    resource_type = fields.Char(string='Resource Type', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    payment_method = fields.Char(string='Payment Method', readonly=True)
    json_data = fields.Text(string='Webhook Data', readonly=True)
