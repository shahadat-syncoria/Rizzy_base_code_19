from odoo.http import request
def _get_provider(code):
    provider_id = request.env['payment.provider'].sudo().search([('code','=',code)],limit=1)
    return provider_id