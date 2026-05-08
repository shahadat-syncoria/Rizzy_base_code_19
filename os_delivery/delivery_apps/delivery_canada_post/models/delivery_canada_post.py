# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from datetime import datetime
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from .canpost_request import CanadaPostRequest
from odoo.tools import pdf
from markupsafe import Markup, escape
from odoo.addons.odoosync_base.utils.app_delivery import AppDelivery

import logging
import json

_logger = logging.getLogger(__name__)


# from odoo.service import common
# version_info = common.exp_version()
# server_serie = version_info.get('server_serie')


def _format_canadapost_price_breakdown(shipment_price):
    """Build multiline plain text from Canada Post shipment-price dict (base, options, adjustments, taxes, due)."""
    if not shipment_price:
        return ""
    parts = []
    base = shipment_price.get("base-amount")
    if base is not None:
        parts.append(_("Base: %s CAD") % base)
    opts = shipment_price.get("priced-options") or {}
    po = opts.get("priced-option")
    if po:
        for opt in (po if isinstance(po, list) else [po]):
            code = opt.get("option-code", "")
            price = opt.get("option-price", "0")
            if code or price != "0.00":
                parts.append(_("Option %s: %s CAD") % (code, price))
    adj = shipment_price.get("adjustments") or {}
    adjs = adj.get("adjustment")
    if adjs:
        for a in (adjs if isinstance(adjs, list) else [adjs]):
            code = a.get("adjustment-code", "")
            amt = a.get("adjustment-amount", "0")
            if code or amt != "0.00":
                parts.append(_("Adjustment %s: %s CAD") % (code, amt))
    pre = shipment_price.get("pre-tax-amount")
    if pre is not None:
        parts.append(_("Pre-tax: %s CAD") % pre)
    for key, label in (("gst-amount", "GST"), ("pst-amount", "PST"), ("hst-amount", "HST")):
        val = shipment_price.get(key)
        if val is not None and val != "0.00":
            parts.append(_("%s: %s CAD") % (label, val))
    due = shipment_price.get("due-amount")
    if due is not None:
        parts.append(_("Due (final cost): %s CAD") % due)
    if not parts:
        return ""
    return _("Cost breakdown:") + "\n" + "\n".join(parts)


def _format_canadapost_price_breakdown_html(shipment_price):
    """Build HTML from Canada Post shipment-price dict (base, options, adjustments, taxes, due)."""
    if not shipment_price:
        return Markup("")
    items = []
    base = shipment_price.get("base-amount")
    if base is not None:
        items.append((_("Base"), _("%s CAD") % base))
    opts = shipment_price.get("priced-options") or {}
    po = opts.get("priced-option")
    if po:
        for opt in (po if isinstance(po, list) else [po]):
            code = opt.get("option-code", "")
            price = opt.get("option-price", "0")
            if code or price != "0.00":
                items.append((_("Option %s") % code, _("%s CAD") % price))
    adj = shipment_price.get("adjustments") or {}
    adjs = adj.get("adjustment")
    if adjs:
        for a in (adjs if isinstance(adjs, list) else [adjs]):
            code = a.get("adjustment-code", "")
            amt = a.get("adjustment-amount", "0")
            if code or amt != "0.00":
                items.append((_("Adjustment %s") % code, _("%s CAD") % amt))
    pre = shipment_price.get("pre-tax-amount")
    if pre is not None:
        items.append((_("Pre-tax"), _("%s CAD") % pre))
    for key, label in (("gst-amount", "GST"), ("pst-amount", "PST"), ("hst-amount", "HST")):
        val = shipment_price.get(key)
        if val is not None and val != "0.00":
            items.append((_(label), _("%s CAD") % val))
    due = shipment_price.get("due-amount")
    if due is not None:
        items.append((_("Due (final cost)"), _("%s CAD") % due))
    if not items:
        return Markup("")
    li = "".join(
        "<li>%s: %s</li>" % (escape(label), escape(value))
        for label, value in items
    )
    return Markup("<div><b>%s</b><ul>%s</ul></div>") % (escape(_("Cost breakdown")), Markup(li))


def _convert_weight(weight, unit='KG'):
    ''' Convert picking weight (always expressed in KG) into the specified unit '''
    if unit != False:
        if unit.upper() == 'KG':
            return weight
        elif unit.upper() == 'LB':
            return round(weight / 0.45359237, 2)
        else:
            raise ValueError
    else:
        raise ValueError


class CanadapostServiceType(models.Model):
    _name = "canadapost.service.code"
    _description = "Canada Post Service Type"

    name = fields.Char(required=True)
    code = fields.Char(required=True)


class CanadapostOptionType(models.Model):
    _name = "canadapost.option.type"
    _description = "Canada Post Option Type"

    name = fields.Char(required=True)
    code = fields.Char(required=True)


class CanadapostPaymentMethod(models.Model):
    _name = "canadapost.payment.method"
    _description = "Canada Post Payment Method"

    name = fields.Char(required=True)


class Providercanadapost(models.Model):
    _inherit = 'delivery.carrier'

    @api.model
    def _get_defaultPackage(self):
        try:
            package_id = self.env.ref("os_delivery.cnpost_packaging_YOUR_PACKAGING").id
        except:
            package_id = None
        return package_id

    @api.model
    def _get_defaultService(self):
        try:
            service_id = self.env.ref("os_delivery.domrp").id
        except:
            service_id = None
        return service_id

    def _domain_cn_service(self):
        return [(["code","=ilike","DOM%"])]



    delivery_type = fields.Selection(selection_add=[('canadapost', ("Canada Post"))],
                                     ondelete={'canadapost': lambda recs: recs.write(
                                         {'delivery_type': 'fixed', 'fixed_price': 0})})
    canadapost_developer_username = fields.Char(
        string="Developer Username", groups="base.group_system")
    canadapost_developer_password = fields.Char(
        string="Developer Password", groups="base.group_system")
    canadapost_production_username = fields.Char(
        string="Production Username", groups="base.group_system")
    canadapost_production_password = fields.Char(
        string="Production Password", groups="base.group_system")
    canadapost_service_code = fields.Many2one(string="Service Type", comodel_name="canadapost.service.code",
                                              ondelete='set null', default=_get_defaultService)
    canadapost_return_service_code = fields.Many2one(string="Return Service Type", comodel_name="canadapost.service.code",
                                              domain=_domain_cn_service,ondelete='set null', default=_get_defaultService)
    canadapost_default_packaging_id = fields.Many2one('stock.package.type', string="Canada-post Default Package Type",
                                                      default=_get_defaultPackage)
    canadapost_weight_unit = fields.Selection(selection=[('kg', ('KG')), ('lb', ('LB'))],
                                              string="Package Weight Unit", default='kg', required=True)
    canadapost_distance_unit = fields.Selection(selection=[('in', ('IN')), ('cm', ('CM'))],
                                                string="Package Dimension Unit", default='cm', required=True)
    canadapost_option_type = fields.Many2many(
        string="Options", comodel_name="canadapost.option.type")
    canadapost_nondelivery_handling = fields.Selection(selection=[
        ('RASE', ('Return at Sender’s Expense')),
        ('RTS', ('Return to Sender')),
        ('ABAN', ('Abandon'))],
        string="Non-delivery Handling", default="RTS")
    canadapost_customer_type = fields.Selection(selection=[(
        'commercial', 'Commercial'), ('counter', 'Counter')], string="Canada-post Customer Type", default='counter')
    canadapost_customer_number = fields.Char(string="Canada-post Customer Number")
    canadapost_contract_id = fields.Char(string="Contract ID")
    canadapost_promo_code = fields.Char(string="Canada-post Promo Code")
    canadapost_payment_method = fields.Many2one(string="Payment Method", comodel_name="canadapost.payment.method",
                                                ondelete='set null')
    canadapost_mailed_on_behalf_of = fields.Char(string="Mailed on Behalf of")
    canadapost_label_image_format = fields.Selection(selection=[('pdf', ('PDF')), ('zpl', ('ZPL'))],
                                                     string="Label Format", default='pdf')
    canadapost_void_shipment = fields.Boolean(string='Canada-post Void Shipment')
    canadapost_pickup_indicator = fields.Selection(selection=[('pickup', (
        'Pick-up')), ('deposit', ('Deposit'))], string='Pick Indicator', default='pickup')
    canadapost_country_flag = fields.Boolean(default=False)

    @api.onchange('canadapost_weight_unit')
    def _onchange_canadapost_weight_unit(self):
        if self.canadapost_weight_unit == False:
            raise UserError(('Package Weight Unit cannot be empyty!'))

    @api.onchange('canadapost_distance_unit')
    def _onchange_canadapost_distance_unit(self):
        if self.canadapost_distance_unit == False:
            raise UserError(('Package Dimension Unit cannot be empyty!'))

    @api.onchange('country_ids')
    def _onchange_country_ids_cnpost(self):
        if self.country_ids:
            for country in self.country_ids:
                if country.code == 'CA':
                    self.canadapost_country_flag = True

    @api.constrains('canadapost_option_type')
    def _onchange_option_type(self):
        if len(self.canadapost_option_type) > 0:
            option_codes = self.canadapost_option_type.mapped('code')
            if 'COD' in option_codes or 'COV' in option_codes or 'D2PO' in option_codes:
                raise UserError(
                    (f'COD/COV/D2PO options are not supported for now. Coming soon...'))
            if 'HFP' in option_codes and 'D2PO' in option_codes:
                raise UserError(
                    ('Select one: Card for pickup or Deliver to Post Office'))
            if 'PA18' in option_codes and 'PA19' in option_codes:
                raise UserError(
                    ('Select one: Proof of Age Required - 18 or Proof of Age Required - 19'))

    @api.model
    def _set_weight_unit(self):
        uom = self.env["uom.uom"].search([('name', 'in', ['kg'])], limit=1)
        self.canadapost_weight_unit = uom.id

    def _set_pack_dimension(self):
        uom = self.env["uom.uom"].search([('name', 'in', ['cm'])], limit=1)
        self.canadapost_distance_unit = uom.id

    def get_services(self):
        superself = self.sudo()
        KEY = superself.canadapost_production_username if superself.prod_environment == True else superself.canadapost_developer_username
        PASS = superself.canadapost_production_password if superself.prod_environment == True else superself.canadapost_developer_password
        des_country = superself.country_ids
        contract_id = superself.canadapost_contract_id
        origpc = superself.zip_from
        destpc = superself.zip_to

        country_code = []
        if len(des_country) > 0:
            for cn in des_country:
                country_code.append(cn.code)
        services = []
        response = {'services': []}

        css = CanadaPostRequest(request_type="services",
                                prod_environment=self.prod_environment)
        css.web_authentication_detail(KEY, PASS)
        if country_code:
            if len(country_code) > 0:
                for code in country_code:
                    response['services'] += css.get_services(
                        code, contract_id, origpc, destpc)
        if not country_code:
            response = css.get_services(
                country_code, contract_id, origpc, destpc)
        Service = self.env['canadapost.service.code'].sudo()
        if response.get('services'):
            services = response.get('services')
            if len(services) > 0:
                for service in services:
                    if len(Service.search([('code', '=', service.get('service-code'))])) == 0:
                        Service.create({
                            'code': service.get('service-code'),
                            'name': service.get('service-name'),
                        })

    def _compute_can_generate_return(self):
        super(Providercanadapost, self)._compute_can_generate_return()
        for carrier in self:
            if not carrier.can_generate_return:
                if carrier.delivery_type == 'canadapost':
                    carrier.can_generate_return = True

    def canadapost_rate_shipment(self, order):
        max_weight = self._canadapost_convert_weight(
            self.canadapost_default_packaging_id.max_weight, self.canadapost_weight_unit)

        est_weight_value = sum([(line.product_id.weight * line.product_uom_qty)
                                for line in order.order_line if not line.display_type]) or 0.0
        weight_value = self._canadapost_convert_weight(
            est_weight_value, self.canadapost_weight_unit)
        print(est_weight_value)
        print(weight_value)

        if weight_value == 0.0:
            weight_value = 0.45 if self.canadapost_weight_unit == 'KG' else 1.00

        superself = self.sudo()

        srm = AppDelivery(service_name='canadapost', service_type='rate', service_key=superself.token)
        if srm:
            packages = []
            srm.set_ship_params(order.warehouse_id.partner_id, order.partner_shipping_id,
                                self.canadapost_service_code.code, packages)
            if order.partner_shipping_id.country_id.code != 'CA':
                srm.set_custom_declaration(order.order_line, self)
            srm.set_payment(self)
            pkg = self.canadapost_default_packaging_id
            if max_weight and weight_value > max_weight:
                total_package = int(weight_value / max_weight)
                last_package_weight = round(weight_value % max_weight, 2)

                for sequence in range(1, total_package + 1):
                    srm.add_package(
                        max_weight,
                        pkg,
                        mode='rating',
                    )
                if last_package_weight:
                    srm.add_package(
                        last_package_weight,
                        pkg,
                        mode='rating',
                    )
            else:
                srm.add_package(
                    weight_value,
                    pkg,
                    mode='rating',
                )

            option_code_list = [option.code for option in self.canadapost_option_type] if order.partner_shipping_id.country_id.code == 'CA' else [option.code for option in self.canadapost_option_type] + [self.canadapost_nondelivery_handling]

            options = {"invoice_no": order.name, 'expected_date': str(datetime.now().date()),'options_code': option_code_list}
            srm.set_options(options)
            if order.partner_shipping_id.country_id.code != 'CA':
                srm.set_custom_declaration(order.order_line, self)
            debug_logging = self.env['omni.account'].search(
                [('state', '=', 'active'), ('id','=',self.account_id.id)], limit=1).debug_logging
            request = srm.rate(order, debug_logging, superself.token, superself.company_id.id,super_self=superself)
            warnings = request.get('warnings_message')
            if warnings:
                _logger.warning(warnings)
            if not request.get('errors_message'):
                ShipmentEstimate = request.get('results')
                price = ShipmentEstimate[0]['total_price']
                choice = self.env['choose.delivery.carrier'].search(
                    [('order_id', '=', order.id), ('carrier_id', '=', self.id)], order='id desc', limit=1)
                choice.canadapost_service_type = False
                sers = self.env['canadapost.service'].sudo().search([])
                for ser in sers:
                    ser.write({'active': False})
                for rating in ShipmentEstimate:
                    rate = self.env['canadapost.service'].sudo().create(
                        {
                            'service_name': rating['service_name'],
                            'service_code': rating['service_code'],
                            'shipment_date': rating['shipment_date'],
                            'expected_delivery_date': rating['expected_delivery_date'],
                            'expected_transit_days': rating['estimated_transit_days'],
                            'base_price': rating['base_price'],
                            'surcharges': rating['surcharges_total'],
                            'taxes': rating['taxes_total'],
                            'options': rating['options_total'],
                            'total_price': rating['total_price'],
                            'order_id': order.id,
                            'choise_id': choice.id,
                            'active': True
                        })
                    if rate:
                        rating['service_id'] = str(rate.id)
                    if rating["service_code"] == self.canadapost_service_code.code:
                        choice.canadapost_service_type = rate.id
                        price = rate.total_price
                        order.canadapost_service = rate.service_code

                canadapost_service_type = self.env['canadapost.service'].sudo().search(
                    [('order_id', '=', order.id), ('active', '=', True)])
            else:
                if request.get('errors_message') == (401, 'Unauthorized'):
                    request[
                        'errors_message'] = "Wrong canadapost Credentials. Please provide correct credentials in canadapost Confirguration."
                return {'success': False,
                        'price': 0.0,
                        'ShipmentEstimate': [],
                        'error_message': ('Error:\n%s') % str(request['errors_message']),
                        'canadapost_service_type': [],
                        'warning_message': False}
        else:
            return {'success': False,
                    'price': 0.0,
                    'ShipmentEstimate': [],
                    'error_message': ('Error:\n%s') % str("Delivery Initialization Error"),
                    'canadapost_service_type': [],
                    'warning_message': False}

        return {'success': True,
                'price': price,
                'ShipmentEstimate': ShipmentEstimate,
                'error_message': False,
                'canadapost_service_type': canadapost_service_type,
                'warning_message': ('Warning:\n%s') % warnings if warnings else False}

    def canadapost_send_shipping(self, pickings):

        try:
            for picking in pickings:
                for line in picking.sale_id.order_line:
                    if line.is_delivery == True:
                        carrier_price = line.price_subtotal
        except Exception as e:
            _logger.warning(str(e))

        debug_logging = self.env['omni.account'].search(
            [('state', '=', 'active'), ('id','=',self.account_id.id)], limit=1).debug_logging

        res = []
        for picking in pickings:
            # Set picking customer type for refund
            picking.canadapost_customer_type = self.canadapost_customer_type
            superself = self.sudo()

            srm = AppDelivery(service_name='canadapost', service_type='shipment', service_key=superself.token)

            packages = picking.move_line_ids.result_package_id
            est_weight_value = sum([pack.weight for pack in packages])

            order = picking.sale_id
            net_weight = self._canadapost_convert_weight(
                picking.shipping_weight, self.canadapost_weight_unit)
            pkg = []
            service_id = order.canadapost_service if order.canadapost_service else self.canadapost_service_code.code
            srm.set_ship_params(order.warehouse_id.partner_id, order.partner_shipping_id,
                                service_id, pkg)

            srm.set_payment(self)
            option_code_list = [option.code for option in
                                self.canadapost_option_type] if order.partner_shipping_id.country_id.code == 'CA' else [
                                                                                                                           option.code
                                                                                                                           for
                                                                                                                           option
                                                                                                                           in
                                                                                                                           self.canadapost_option_type] + [
                                                                                                                           self.canadapost_nondelivery_handling]
            options = {"invoice_no": order.name, 'options_code': option_code_list}
            srm.set_options(options)
            # Add options
            if len(picking.move_line_ids.result_package_id) == 0:
                raise UserError(("Please add atleast one package for this shipment!"))
            package_count = len(picking.move_line_ids.result_package_id) or 1
            carrier_price = 0.0
            for line in order.order_line:
                if line.is_delivery == True:
                    carrier_price = line.price_subtotal
            self_links = link_media = refund_links = ""
            get_label_obj = AppDelivery(service_name='canadapost', service_type='shipment', service_key=superself.token)
            OmniAccount = self.env['omni.account'].sudo()
            omni_account_id = OmniAccount.search(
                [('state', '=', 'active'),
                 ('id', '=', superself.account_id.id)], limit=1)

            ################
            # Multipackage #
            ################
            if package_count > 1:
                # Create multiple shipments for Packages
                package_labels = []
                carrier_tracking_ref = ""
                shipment_ids = []
                shipment_price_rows = []
                shipment_due_total = 0.0
                shipment_due_total_ok = True

                for sequence, package in enumerate(picking.move_line_ids.result_package_id, start=1):
                    package_weight = self._canadapost_convert_weight(
                        package.shipping_weight, self.canadapost_weight_unit)
                    packaging = package.package_type_id

                    srm.add_package(
                        package_weight,
                        packaging,
                        mode='shipment',
                    )
                    if order.partner_shipping_id.country_id.code != 'CA':
                        srm.set_custom_declaration_canadapost(package.quant_ids, self)

                    package_name = package.name or sequence
                    request = srm.process_shipment(debug_logging, self.token, service_key=superself.token,
                                                   company_id=superself.company_id.id)

                    warnings = request.get('warnings_message')
                    if warnings:
                        _logger.info(warnings)
                    if not request.get('errors_message'):
                        if sequence == 1:
                            header = {"Authorization": 'Token ' + omni_account_id.token}
                            bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                                omni_account_id.server_url + request.get('url'), headers=header)
                            picking.write({'canadapost_link_self': self_links})

                            if pdf_status == 200:
                                picking.connector_label_url = picking.connector_label_url + ',' + request.get(
                                    'url') if picking.connector_label_url else request.get('url')
                                package_labels.append(
                                    (package_name, bytepdf))
                            carrier_tracking_ref = request['tracking_number']
                            shipment_price_mp = request.get('shipment_price')
                            shipment_price_rows.append({
                                'package_name': package_name,
                                'tracking_number': request.get('tracking_number'),
                                'master_tracking_id': request.get('master_tracking_id'),
                                'shipment_price': shipment_price_mp,
                            })
                            if shipment_price_mp and shipment_price_mp.get('due-amount') is not None:
                                try:
                                    shipment_due_total += float(shipment_price_mp.get('due-amount'))
                                except (TypeError, ValueError):
                                    shipment_due_total_ok = False
                            else:
                                shipment_due_total_ok = False

                        # Intermediary packages
                        elif sequence > 1 and sequence < package_count:
                            header = {"Authorization": 'Token ' + omni_account_id.token}
                            bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                                omni_account_id.server_url + request.get('url'), headers=header)
                            if pdf_status == 200:
                                picking.connector_label_url = picking.connector_label_url + ',' + request.get(
                                    'url') if picking.connector_label_url else request.get('url')
                                package_labels.append(
                                    (package_name, bytepdf))
                            carrier_tracking_ref = carrier_tracking_ref + \
                                                   "," + request['tracking_number']

                            shipment_price_mp = request.get('shipment_price')
                            shipment_price_rows.append({
                                'package_name': package_name,
                                'tracking_number': request.get('tracking_number'),
                                'master_tracking_id': request.get('master_tracking_id'),
                                'shipment_price': shipment_price_mp,
                            })
                            if shipment_price_mp and shipment_price_mp.get('due-amount') is not None:
                                try:
                                    shipment_due_total += float(shipment_price_mp.get('due-amount'))
                                except (TypeError, ValueError):
                                    shipment_due_total_ok = False
                            else:
                                shipment_due_total_ok = False

                        # Last package
                        elif sequence == package_count:
                            bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                                omni_account_id.server_url + request.get('url'), headers=header)
                            if pdf_status == 200:
                                picking.connector_label_url = picking.connector_label_url + ',' + request.get(
                                    'url') if picking.connector_label_url else request.get('url')

                                package_labels.append(
                                    (package_name, bytepdf))
                            carrier_tracking_ref = carrier_tracking_ref + \
                                                   "," + request['tracking_number']

                            shipment_price_mp = request.get('shipment_price')
                            shipment_price_rows.append({
                                'package_name': package_name,
                                'tracking_number': request.get('tracking_number'),
                                'master_tracking_id': request.get('master_tracking_id'),
                                'shipment_price': shipment_price_mp,
                            })
                            summary_lines = [
                                Markup("<b>%s</b>") % escape(_("Shipment created into Canadapost")),
                            ]
                            logmessage = Markup("<br/>").join(summary_lines)
                            if shipment_price_mp and shipment_price_mp.get('due-amount') is not None:
                                try:
                                    shipment_due_total += float(shipment_price_mp.get('due-amount'))
                                except (TypeError, ValueError):
                                    shipment_due_total_ok = False
                            else:
                                shipment_due_total_ok = False
                            if shipment_price_rows:
                                price_blocks = []
                                for idx, row in enumerate(shipment_price_rows, start=1):
                                    label_bits = []
                                    if row.get('package_name'):
                                        label_bits.append(str(row.get('package_name')))
                                    if row.get('tracking_number'):
                                        label_bits.append(row.get('tracking_number'))
                                    label = " / ".join(label_bits) if label_bits else str(idx)
                                    shipment_id = row.get('master_tracking_id')
                                    shipment_id_label = shipment_id if shipment_id else _("Unknown")
                                    breakdown = _format_canadapost_price_breakdown_html(row.get('shipment_price'))
                                    block_parts = [
                                        Markup("<b>%s</b> %s") %
                                        (escape(_("Shipment ID:")), escape(str(shipment_id_label)))
                                    ]
                                    block_parts.append(
                                        Markup("<b>%s</b> %s") %
                                        (escape(_("Package:")), escape(label))
                                    )
                                    if breakdown:
                                        block_parts.append(breakdown)
                                    else:
                                        block_parts.append(
                                            Markup("%s") % escape(_("No cost breakdown returned."))
                                        )
                                    price_blocks.append(
                                        Markup("<div>%s</div>") % Markup("<br/>").join(block_parts)
                                    )
                                if shipment_due_total_ok and shipment_due_total:
                                    price_blocks.append(
                                        Markup("<div><b>%s</b> %s CAD</div>") %
                                        (escape(_("Total due (all packages):")),
                                         escape("%.2f" % shipment_due_total))
                                    )
                                logmessage = Markup("%s<br/><br/>%s") % (logmessage, Markup("<br/>").join(price_blocks))
                            attachments = [('Labelcanadapost-' + carrier_tracking_ref +
                                            '.pdf', pdf.merge_pdf([pl[1] for pl in package_labels]))]
                            picking.message_post(
                                body=logmessage, attachments=attachments)
                            shipping_data = {'exact_price': shipment_due_total,
                                             'tracking_number': carrier_tracking_ref}
                            # if shipment_price_mp and shipment_price_mp.get('due-amount'):
                            #     try:
                            #         carrier_price = float(shipment_price_mp.get('due-amount'))
                            #         shipping_data['exact_price'] = carrier_price
                            #     except (TypeError, ValueError):
                            #         pass
                            res = res + [shipping_data]
                    else:

                        raise UserError(json.dumps(request.get('errors_message')))

            ###############
            # One package #
            ###############
            elif package_count == 1:
                print("package_count == 1")
                packaging = picking.move_line_ids.result_package_id[
                                :1].package_type_id or picking.carrier_id.canadapost_default_packaging_id
                srm.add_package(
                    net_weight,
                    packaging,
                    mode=None
                )
                if order.partner_shipping_id.country_id.code != 'CA':
                    srm.set_custom_declaration_canadapost(packages.quant_ids, self)

                package_name = picking.move_line_ids.result_package_id.name
                request = srm.process_shipment(debug_logging, self.token, self.company_id.id)
                warnings = request.get('errors_message')
                if warnings:
                    _logger.warning(warnings)

                if not request.get('errors_message'):
                    carrier_tracking_ref = request.get('tracking_number')
                    shipment_price = request.get('shipment_price')
                    if shipment_price and shipment_price.get('due-amount'):
                        try:
                            carrier_price = float(shipment_price.get('due-amount'))
                        except (TypeError, ValueError):
                            if order.order_line[-1].name.split(" ")[0] == 'canadapost':
                                carrier_price = order.order_line[-1].price_subtotal
                    elif order.order_line[-1].name.split(" ")[0] == 'canadapost':
                        carrier_price = order.order_line[-1].price_subtotal
                    if carrier_tracking_ref:
                        package_labels = []
                        header = {"Authorization": 'Token ' + omni_account_id.token}
                        bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                            omni_account_id.server_url + request.get('url'), headers=header)
                        if pdf_status == 200:
                            picking.connector_label_url = picking.connector_label_url + ',' + request.get(
                                'url') if picking.connector_label_url else request.get('url')
                            package_labels.append((package_name, bytepdf))
                            label_bits = []
                            if package_name:
                                label_bits.append(str(package_name))
                            if carrier_tracking_ref:
                                label_bits.append(carrier_tracking_ref)
                            label = " / ".join(label_bits) if label_bits else ""
                            shipment_id = request.get('master_tracking_id')
                            shipment_id_label = shipment_id if shipment_id else _("Unknown")
                            breakdown = _format_canadapost_price_breakdown_html(shipment_price)
                            block_parts = [
                                Markup("<b>%s</b> %s") %
                                (escape(_("Shipment ID:")), escape(str(shipment_id_label))),
                                Markup("<b>%s</b> %s") %
                                (escape(_("Package:")), escape(label)),
                            ]
                            if breakdown:
                                block_parts.append(breakdown)
                            else:
                                block_parts.append(
                                    Markup("%s") % escape(_("No cost breakdown returned."))
                                )
                            logmessage = Markup("<b>%s</b><br/><br/>%s") % (
                                escape(_("Shipment created into Canadapost")),
                                Markup("<div>%s</div>") % Markup("<br/>").join(block_parts),
                            )
                            attachments = [('Labelcanadapost-' + carrier_tracking_ref +
                                            '.pdf', pdf.merge_pdf([pl[1] for pl in package_labels]))]
                            picking.message_post(
                                body=logmessage, attachments=attachments)
                        shipping_data = {'exact_price': carrier_price,
                                         'tracking_number': carrier_tracking_ref}
                        # breakdown included in the main log message above
                        picking.canadapost_link_return = request.get('refund_link')
                        res = res + [shipping_data]
                else:
                    raise UserError(json.dumps(request.get('errors_message')))

            ##############
            # No package #
            ##############
            else:
                raise UserError(('No packages for this picking'))
            return res

    def canadapost_get_tracking_link(self, picking):
        return 'https://www.canadapost-postescanada.ca/track-reperage/en#/resultList?searchFor=%s' % picking.carrier_tracking_ref

    def canadapost_cancel_shipment(self, picking):
        # raise UserError(("You can't cancel canadapost shipping."))
        # picking.message_post(body=(u"You can't cancel canadapost shipping."))
        # picking.write({'carrier_tracking_ref': '', 'carrier_price': 0.0})
        superself = self.sudo()
        KEY = superself.canadapost_production_key if superself.prod_environment == True else superself.canadapost_developer_username
        PASS = superself.canadapost_production_password if superself.prod_environment == True else superself.canadapost_developer_password

        if picking.canadapost_customer_type == 'counter':
            request_type = 'ncrefund'
            if picking.canadapost_link_refund:
                refund_links = picking.canadapost_link_refund.split(",")
        else:
            request_type = 'refund'
            refund_links = picking.canadapost_link_self.split(",")

        for refund_link in refund_links:
            srm = CanadaPostRequest(request_type='request_type', prod_environment=superself.prod_environment,
                                    customer_number=superself.canadapost_customer_number,
                                    contract_id=superself.canadapost_contract_id)
            srm.web_authentication_detail(KEY, PASS)
            email = picking.company_id.email
            result = srm.shipment_refund(refund_link, email)
            print(result)

            warnings = result.get('warnings_message')
            if warnings:
                _logger.info(warnings)
            master_tracking_id = picking.carrier_tracking_ref
            if not result.get('errors_message'):
                picking.message_post(body=(u'Shipment #%s has been cancelled', master_tracking_id))
                picking.write({'carrier_tracking_ref': '',
                               'carrier_price': 0.0})
            else:
                raise UserError(result['errors_message'])
        return False

    def _canadapost_convert_weight(self, weight, unit='KG'):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter(
        )
        if unit.upper() == 'KG':
            return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'), round=False)
        elif unit.upper() == 'LB':
            return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_lb'), round=False)
        else:
            raise ValueError

    def get_pdf_byte(self, TrackingPIN, url, FileFormat):
        srm = CanadaPostRequest(request_type="label")
        try:
            myfile = srm.get_label_url(TrackingPIN, url, '.pdf')
            if myfile.get('status_code') == 200:
                bytepdf = bytearray(myfile.get('pdf_data'))
                return bytepdf
            else:
                return False
        except Exception as e:
            print(e.args)

    def canapost_get_labels(self, picking):
        debug_logging = self.env['omni.account'].search(
            [('state', '=', 'active'), ('company_id', '=', picking.company_id.id)], limit=1).debug_logging
        get_label_obj = AppDelivery(service_name='canadapost', service_type='label', service_key=self.token)
        OmniAccount = self.env['omni.account'].sudo()
        omni_account_id = OmniAccount.search([('state', '=', 'active'),('id','=',self.account_id.id)],
                                             limit=1)
        canadapost_labels = []
        carrier_tracking_ref = ""
        try:
            header = {"Authorization": 'Token ' + omni_account_id.token}
            label_urls = picking.connector_label_url.split(',')
            for label_url in label_urls:
                bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                    omni_account_id.server_url + label_url, headers=header)

                if pdf_status == 200:
                    PDF_NAME = 'LabelPurolator-%s.%s' % (
                    picking.carrier_tracking_ref, self.purolator_label_image_format)
                    PDF_NAME = PDF_NAME.encode('utf-8').decode('utf-8')
                    canadapost_labels.append((PDF_NAME, bytepdf))
                else:
                    logmessage = (
                        "Label PDF cannot be generated for <b>Tracking Number : </b> %s<br/><br><br/> If you want to get the label pdf, click on button <b>GET LABELS</b>.<br><br/> If you want to get the label url, click on button <b>LABEL URL</b><br/>") % (
                                     picking.carrier_tracking_ref)
                    picking.message_post(body=logmessage)
            logmessage = ("Shipment created into Canadapost<br/>"
                           "<b>Tracking Numbers:</b> %s<br/>"
                           ) % (picking.carrier_tracking_ref)
            attachments = [('Labelcanadapost-' + picking.carrier_tracking_ref if picking.carrier_tracking_ref else 'Labelcanadapost-'+
                            '.pdf', pdf.merge_pdf([pl[1] for pl in canadapost_labels]))]
            # Cost: %.2f %s , carrier_price, order_currency.name
            picking.message_post(body=logmessage, attachments=attachments)

        except Exception as e:
            raise UserError(str(e.args))



    def _check_return_partner_country(self,customer_partner,own_warehouse_partner):
        """
        This function checks the country of the customer and the warehouse and returns the country of the customer .
        For Canadapost Return Can not be possible Outside Canada.

         param: customer_partner: Here this param indicate Customer partner who will return the percels
         param: own_warehouse_partner: Here this param indicate this company's selected warehouse partner address who will
        receive the parcel .

        return: If country outside of Canada it will return UserError else it will pass.
        """

        applicable_country_code = ["CA"]

        if customer_partner.country_id.code not in applicable_country_code or own_warehouse_partner.country_id.code not in applicable_country_code:
            raise UserError(("Canadapost Return only support within Canada."))

    # Return Label
    def canadapost_get_return_label(self, pickings, tracking_number=None, origin_date=None):

        debug_logging = self.env['omni.account'].search(
            [('state', '=', 'active'), ('id','=',self.account_id.id)], limit=1).debug_logging

        res = []
        for picking in pickings:
            # Set picking customer type for refund
            picking.canadapost_customer_type = self.canadapost_customer_type
            superself = self.sudo()

            # Canapost Request Class
            srm = AppDelivery(service_name='canadapost', service_type='shipment_return', service_key=superself.token)

            # Get All packages
            packages = picking.move_line_ids.result_package_id
            # Get Sale order no.
            order = picking.sale_id
            pkg = []
            # GET Canadapost Return Service
            # Return Can be possible only in Canada
            # Check Applicable Country
            self._check_return_partner_country(order.partner_shipping_id,order.warehouse_id.partner_id)
            # Choose Service ID
            service_id = self.canadapost_return_service_code.code


            srm.set_ship_params(picking.partner_id,order.warehouse_id.partner_id,
                                service_id, pkg)

            # Add options
            if len(picking.move_line_ids.result_package_id) == 0:
                raise UserError(("Please add at least  one package for this shipment!"))


            package_count = len(picking.move_line_ids.result_package_id) or 1


            get_label_obj = AppDelivery(service_name='canadapost', service_type='shipment_return', service_key=superself.token)
            OmniAccount = self.env['omni.account'].sudo()
            omni_account_id = OmniAccount.search(
                [('state', '=', 'active'),('id','=',superself.account_id.id)], limit=1)

            ################
            # Multipackage #
            ################
            if package_count > 1:
                # Create multiple shipments for Packages
                package_labels = []
                carrier_tracking_ref = ""

                for sequence, package in enumerate(picking.move_line_ids.result_package_id, start=1):
                    srm.data['options'] = {
                        "service_code": self.canadapost_service_code.code,
                        "weight": package.shipping_weight
                    }

                    package_name = package.name or sequence
                    request = srm.process_return(debug_logging, self.token, service_key=superself.token,
                                                   company_id=superself.company_id.id)

                    warnings = request.get('warnings_message')
                    if warnings:
                        _logger.info(warnings)
                    if not request.get('errors_message'):
                        if sequence == 1:
                            header = {"Authorization": 'Token ' + omni_account_id.token}
                            bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                                omni_account_id.server_url + request.get('url'), headers=header)

                            if pdf_status == 200:
                                picking.connector_return_label_url = picking.connector_return_label_url + ',' + request.get(
                                    'url') if picking.connector_return_label_url else request.get('url')
                                package_labels.append(
                                    (package_name, bytepdf))
                            carrier_tracking_ref = request['tracking_number']

                        # Intermediary packages
                        elif sequence > 1 and sequence < package_count:
                            header = {"Authorization": 'Token ' + omni_account_id.token}
                            bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                                omni_account_id.server_url + request.get('url'), headers=header)
                            if pdf_status == 200:
                                picking.connector_return_label_url = picking.connector_return_label_url + ',' + request.get(
                                    'url') if picking.connector_return_label_url else request.get('url')
                                package_labels.append(
                                    (package_name, bytepdf))
                            carrier_tracking_ref = carrier_tracking_ref + \
                                                   "," + request['tracking_number']
                        # Last package
                        elif sequence == package_count:
                            bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                                omni_account_id.server_url + request.get('url'), headers=header)
                            if pdf_status == 200:
                                picking.connector_return_label_url = picking.connector_return_label_url + ',' + request.get(
                                    'url') if picking.connector_return_label_url else request.get('url')

                                package_labels.append(
                                    (package_name, bytepdf))
                            carrier_tracking_ref = carrier_tracking_ref + \
                                                   "," + request['tracking_number']

                            logmessage = ("Return Label created into Canadapost<br/>"
                                           "<b>Tracking Numbers:</b> %s<br/>"
                                           "<b>Packages:</b> %s") % (
                                         carrier_tracking_ref, ','.join([pl[0] for pl in package_labels]))
                            attachments = [('ReturnLabelcanadapost-' + carrier_tracking_ref +
                                            '.pdf', pdf.merge_pdf([pl[1] for pl in package_labels]))]
                            picking.message_post(
                                body=logmessage, attachments=attachments)
                    else:

                        raise UserError(json.dumps(request.get('errors_message')))

            ###############
            # One package #
            ###############
            elif package_count == 1:
                print("package_count == 1")
                srm.data['options'] = {
                    "service_code": self.canadapost_service_code.code,
                    "weight": picking.move_line_ids.result_package_id.shipping_weight
                }

                package_name = picking.move_line_ids.result_package_id.name
                request = srm.process_return(debug_logging, self.token, self.company_id.id)
                warnings = request.get('errors_message')
                if warnings:
                    _logger.warning(warnings)

                if not request.get('errors_message'):
                    carrier_tracking_ref = request.get('tracking_number')
                    if carrier_tracking_ref:
                        package_labels = []
                        header = {"Authorization": 'Token ' + omni_account_id.token}
                        bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                            omni_account_id.server_url + request.get('url'), headers=header)
                        if pdf_status == 200:
                            picking.connector_return_label_url = picking.connector_return_label_url + ',' + request.get(
                                'url') if picking.connector_return_label_url else request.get('url')
                            package_labels.append((package_name, bytepdf))
                            logmessage = ("Return Label created into Canadapost<br/>"
                                           "<b>Tracking Numbers:</b> %s<br/>"
                                           "<b>Packages:</b> %s") % (
                                         carrier_tracking_ref, ','.join([pl[0] for pl in package_labels]))
                            attachments = [('ReturnLabelcanadapost-' + carrier_tracking_ref +
                                            '.pdf', pdf.merge_pdf([pl[1] for pl in package_labels]))]
                            picking.message_post(
                                body=logmessage, attachments=attachments)
                else:
                    raise UserError(json.dumps(request.get('errors_message')))

            ##############
            # No package #
            ##############
            else:
                raise UserError(('No packages for this picking'))
