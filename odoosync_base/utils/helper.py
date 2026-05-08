import base64

import requests

from odoo.http import request
from odoo import fields


def image_processing(image_path):
    image_base64 = False
    if image_path:
        is_image = requests.get(request.httprequest.host_url+image_path)
        if is_image.status_code == 200:
            image_base64 = base64.b64encode(is_image.content)
    return image_base64

def is_module_installed(module_name):
    ir_module = request.env['ir.module.module']
    is_module_installed = ir_module.sudo().search([('name', '=', module_name)])
    if is_module_installed.state == 'installed':
        return True
    return False

def convert_curency(acq,amount,order_currency):
    # currency_object = request.env['res.currency'].sudo().with_context(company_id=acq.company_id).search([('name','=','CAD')],limit=1)
    company_currency = acq.company_id.currency_id
    # company_currency = currency_object
    final_amount =  round(order_currency._convert(float(amount),company_currency,acq.company_id,fields.Date.today()),4)
    final_amount_string = f'{final_amount:.2f}'
    return final_amount_string