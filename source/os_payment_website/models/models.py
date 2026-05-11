# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class os_payment_website(models.Model):
#     _name = 'os_payment_website.os_payment_website'
#     _description = 'os_payment_website.os_payment_website'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
