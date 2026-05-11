# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import json
import logging
import requests

from odoo import api, models, fields, _, tools
from odoo.exceptions import UserError
from odoo.tools import pdf
from decimal import *
from odoo.addons.odoosync_base.utils.app_delivery import AppDelivery
_logger = logging.getLogger(__name__)


SERVICE_TYPES = [('PurolatorExpress', 'Purolator Express'),
     ('PurolatorExpress10:30AM', 'Purolator Express 10:30AM'),
     ('PurolatorExpress12PM', 'Purolator Express 12PM'),
     ('PurolatorExpress9AM', 'Purolator Express 9AM'),
     ('PurolatorExpressBox', 'Purolator Express Box'),
     ('PurolatorExpressBox10:30AM', 'Purolator Express Box 10:30AM'),
     ('PurolatorExpressBox12PM', 'Purolator Express Box 12PM'),
     ('PurolatorExpressBox9AM', 'Purolator ExpressBox 9AM'),
     ('PurolatorExpressBoxEvening', 'Purolator Express Box Evening'),
     ('PurolatorExpressBoxInternational', 'Purolator Express Box International'),
     ('PurolatorExpressBoxU.S.', 'Purolator Express Box U.S.'),
     ('PurolatorExpressEnvelope', 'Purolator Express Envelope'),
     ('PurolatorExpressEnvelope10:30AM', 'Purolator Express Envelope 10:30AM'),
     ('PurolatorExpressEnvelope12PM', 'Purolator Express Envelope 12PM'),
     ('PurolatorExpressEnvelope9AM', 'Purolator Express Envelope 9AM'),
     ('PurolatorExpressEnvelopeEvening', 'Purolator Express Envelope Evening'),
     ('PurolatorExpressEnvelopeInternational', 'Purolator Express Envelope International'),
     ('PurolatorExpressEnvelopeU.S.', 'Purolator Express Envelope U.S.'),
     ('PurolatorExpressEvening', 'Purolator Express Evening'),
     ('PurolatorExpressInternational', 'Purolator Express International'),
     ('PurolatorExpressInternational10:30AM', 'Purolator Express International 10:30AM'),
     ('PurolatorExpressInternational12:00', 'Purolator Express International 12:00'),
     ('PurolatorExpressInternational10:30AM', 'Purolator Express International 10:30AM'),
     ('PurolatorExpressInternational9AM', 'Purolator Express International 9AM'),
     ('PurolatorExpressInternationalBox10:30AM', 'Purolator Express International Box 10:30AM'),
     ('PurolatorExpressInternationalBox12:00', 'Purolator Express International Box12:00'),
     ('PurolatorExpressInternationalBox9AM', 'Purolator Express International Box 9AM'),
     ('PurolatorExpressInternationalEnvelope10:30AM', 'Purolator Express International Envelope 10:30AM'),
     ('PurolatorExpressInternationalEnvelope12:00', 'Purolator Express International Envelope 12:00'),
     ('PurolatorExpressInternationalEnvelope9AM', 'Purolator Express International Envelope 9AM'),
     ('PurolatorExpressInternationalPack10:30AM', 'Purolator Express International Pack 10:30 AM'),
     ('PurolatorExpressInternationalPack12:00', 'Purolator Express International Pack 12:00'),
     ('PurolatorExpressInternationalPack9AM', 'Purolator Express International Pack 9AM'),
     ('PurolatorExpressPack', 'Purolator Express Pack'),
     ('PurolatorExpressPack10:30AM', 'Purolator ExpressPack 10:30AM'),
     ('PurolatorExpressPack12PM', 'Purolator Express Pack 12PM'),
     ('PurolatorExpressPack9AM', 'Purolator Express Pack 9AM'),
     ('PurolatorExpressPackEvening', 'Purolator Express Pack Evening'),
     ('PurolatorExpressPackInternational', 'Purolator Express Pack International'),
     ('PurolatorExpressPackU.S.', 'Purolator Express Pack U.S.'),
     ('PurolatorExpressU.S.', 'Purolator Express U.S.'),
     ('PurolatorExpressU.S.10:30AM', 'Purolator Express U.S. 10:30AM'),
     ('PurolatorExpressU.S.12:00', 'Purolator Express U.S. 12:00'),
     ('PurolatorExpressU.S.9AM', 'Purolator Express U.S. 9AM'),
     ('PurolatorExpressU.S.Box10:30AM', 'Purolator Express U.S. Box 10:30AM'),
     ('PurolatorExpressU.S.Box12:00', 'Purolator Express U.S. Box 12:00'),
     ('PurolatorExpressU.S.Box9AM', 'Purolator Express U.S. Box 9AM'),
     ('PurolatorExpressU.S.Envelope10:30AM', 'Purolator Express U.S. Envelope 10:30AM'),
     ('PurolatorExpressU.S.Envelope12:00', 'Purolator Express U.S. Envelope 12:00'),
     ('PurolatorExpressU.S.Envelope9AM', 'Purolator Express U.S. Envelope 9AM'),
     ('PurolatorExpressU.S.Pack10:30AM', 'Purolator Express U.S. Pack 10:30AM'),
     ('PurolatorExpressU.S.Pack12:00', 'PurolatorExpress U.S. Pack 12:00'),
     ('PurolatorExpressU.S.Pack9AM', 'PurolatorExpress U.S. Pack 9AM'),
     ('PurolatorGround', 'Purolator Ground'),
     ('PurolatorGround10:30AM', 'Purolator Ground 10:30AM'),
     ('PurolatorGround9AM', 'Purolator Ground 9AM'),
     ('PurolatorGroundDistribution', 'Purolator Ground Distribution'),
     ('PurolatorGroundEvening', 'Purolator Ground Evening'),
     ('PurolatorGroundRegional', 'Purolator Ground Regional'),
     ('PurolatorGroundU.S.', 'Purolator Ground U.S.'),
     ('PurolatorQuickShip', 'Purolator Quick Ship'),
     ('PurolatorQuickShipBox', 'Purolator Quick Ship Box'),
     ('PurolatorQuickShipEnvelope', 'Purolator Quick Ship Envelope'),
     ('PurolatorQuickShipPack', 'Purolator Quick Ship Pack'),
     ]

class ProviderPurolator(models.Model):
    _inherit = 'delivery.carrier'

    @api.model
    def _get_defaultPackage(self):
        try:
            package_id = self.env.ref("os_delivery.purolator_packaging_PUROLATOR_EXPRESS_CUSTOMER_PACKAGING_CN").id
        except:
            package_id = None
        return package_id

    delivery_type = fields.Selection(selection_add=[('purolator', "Purolator")], ondelete={'purolator': 'set default'})
    purolator_billing_account = fields.Char(string="Billing Account Number", groups="base.group_system",default="9999999999")
    purolator_dropoff_type = fields.Selection([ ('DropOff', 'DROPOFF'),
                                                ('PreScheduled', 'PRESCHEDULED'),],
                                                    string="Purolator Drop Off type",
                                                    default='DropOff')
    purolator_default_packaging_id = fields.Many2one('stock.package.type', string="Default Package Type",default=_get_defaultPackage)
    purolator_service_type = fields.Selection(SERVICE_TYPES,'Purolator Service Type', default='PurolatorExpress')
    purolator_service_type_us = fields.Selection(SERVICE_TYPES,'Purolator Service Type US', default='PurolatorExpressU.S.')
    purolator_service_type_int = fields.Selection(SERVICE_TYPES,'Purolator Service Type International', default='PurolatorExpressInternational')
    purolator_payment_type = fields.Selection([ ('Sender', 'Sender'),
                                                ('Receiver', 'Receiver'),
                                                ('ThirdParty', 'ThirdParty'), 
                                                ('CreditCard', 'CreditCard')], 
                                                string="Purolator Payment Type", required=True, default="Sender")
    purolator_creditcard_type = fields.Selection([  ('Visa', 'Visa'), 
                                                    ('MasterCard', 'MasterCard'),
                                                    ('AmericanExpress', 'AmericanExpress'),], 
                                                    string="Credit Card Type", groups="base.group_system")
    purolator_creditcard_number = fields.Integer(string="Credit Card Number", groups="base.group_system")
    purolator_creditcard_name = fields.Char(string="Credit Card Name", groups="base.group_system")
    purolator_creditcard_expirymonth = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'),
                                                        ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), 
                                                        ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12'), ], 
                                                        string="Expiry Month", groups="base.group_system")
    purolator_creditcard_expiryyear = fields.Char(string="Expiry Year", groups="base.group_system")
    purolator_creditcard_cvv = fields.Char(string="CVV", groups="base.group_system")
    purolator_creditcard_billingpostalcode = fields.Char(string="Billing Postal Code", groups="base.group_system")
    purolator_weight_unit = fields.Selection([('LB', 'LB'),
                                              ('KG', 'KG')],
                                            default='KG')
    purolator_printer_type = fields.Selection([('Regular', 'Regular (8" x 11")'),
                                                ('Thermal', 'Thermal (6" x 4")'),],
                                             default='Thermal', string="Purolator Printer Type")
    purolator_customer_type = fields.Char(string="Customer Type", groups="base.group_system")
    purolator_customer_number = fields.Char(string="Customer Number", groups="base.group_system")
    purolator_promo_code = fields.Char(string="Promo Code", groups="base.group_system")
    purolator_label_image_format = fields.Selection([('PDF', 'PDF'),],
                                             default='PDF', string="Purolator Label File Type")
    purolator_default_weight = fields.Float("Default Weight",default=1.00, readonly=True, groups="base.group_system")
    purolator_product_uom = fields.Many2one("uom.uom","Odoo Product UoM", groups="base.group_system")
    purolator_api_uom = fields.Char("API UoM",default="KG", readonly=True, groups="base.group_system")
    purolator_void_shipment = fields.Boolean("Void Shipment", default=True, groups="base.group_system")
    purolator_shipment_type = fields.Selection([('domestic', 'Domestic'),
                                                ('us', 'US'),
                                                ('int', 'International')],
                                                string='Shipment Type', default='domestic')    
    purolator_from_onlabel = fields.Boolean("From on Label Indicator", default=False)
    purolator_from_onlabel_info = fields.Selection([('same', 'Same as Company Address'),
                                                    ('diff', 'Different')],
                                                    string='From On Label Selection', default='same')
    purolator_label_info = fields.Many2one('res.partner', string='From On Label Partner')
    purolator_notify_sender = fields.Boolean("Email Notification for Sender", default=False, groups="base.group_system")
    purolator_notify_receiver = fields.Boolean("Email Notification for Receiver", default=False, groups="base.group_system")
    purolator_buyer = fields.Selection([('same', 'Same as Receiver'),
                                        ('diff', 'Different')],
                                        string='Buyer Information', default='same')
    purolator_buyer_info = fields.Many2one('res.partner', string='Buyer Contact')
    purolator_preferred_customs = fields.Char(string='Preferred Customs Broker')
    purolator_duty_party = fields.Selection([('sender', 'Sender'),
                                            ('receiver', 'Receiver'),
                                            ('buyer', 'Buyer')],
                                            string='Duty Party', default='sender')   
    purolator_duty_currency = fields.Selection([('cad', 'CAD'),
                                            ('us', 'USD'),      ],                                     
                                            string ='Duty Currency', default='cad')       
    purolator_business_relation = fields.Selection([('related', 'Related'),
                                                    ('notrelated', 'Not Related'),],                                     
                                            string ='Business Relation', default='notrelated')  
    purolator_nafta_document = fields.Boolean("NAFTA Document Indicator", default=False, groups="base.group_system")
    purolator_fda_document = fields.Boolean("FDA Document Indicator", default=False, groups="base.group_system")
    purolator_fcc_document = fields.Boolean("FCC Document Indicator", default=False, groups="base.group_system")
    purolator_sender_is_producer = fields.Boolean("Sender Is Producer Indicator", default=False, groups="base.group_system")
    purolator_textile_indicator = fields.Boolean("Textile Indicator", default=False, groups="base.group_system")
    purolator_textile_manufacturer= fields.Char("Textile Manufacturer", default=False, groups="base.group_system")
    @api.onchange('purolator_service_type')
    def _onchange_service_type(self):
        self.purolator_shipment_type = 'domestic'
        if 'U.S.' in self.purolator_service_type:
            self.purolator_shipment_type = 'us'
        if 'International' in self.purolator_service_type:
            self.purolator_shipment_type = 'int'

    def _compute_can_generate_return(self):
        super(ProviderPurolator, self)._compute_can_generate_return()
        for carrier in self:
            if not carrier.can_generate_return:
                if carrier.delivery_type == 'purolator':
                    carrier.can_generate_return = True

    def purolator_service_options(self, order, ship_date):
        superself = self.sudo()        
        KEY = superself.purolator_production_key if superself.prod_environment == True else superself.purolator_developer_key
        PASS = superself.purolator_production_password if superself.prod_environment == True else superself.purolator_developer_password
        val = AppDelivery(self.log_xml, request_type="services", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
        val.web_authentication_detail(KEY, PASS)         
        val_req = val.address_validate(order.company_id.partner_id, order.partner_id)  
        services = []
        if not val_req.get('errors_message'):
            srm = AppDelivery(self.log_xml, request_type="services", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
            srm.web_authentication_detail(KEY, PASS)        
            request = srm.service_options(order.warehouse_id.partner_id, order.partner_shipping_id, self.purolator_billing_account,ship_date )
            warnings = request.get('warnings_message')
            if warnings:
                _logger.info(warnings)
            if not request.get('errors_message'):
                services = request.get('services')
            else:
                if request.get('errors_message') == (401, 'Unauthorized'):
                    request['errors_message'] = "Wrong Purolator Credentials. Please provide correct credentials in Purolator Confirguration."
                return {'success': False,
                        'services':services,
                        'error_message': ('Error:\n%s') % str(request['errors_message']),
                        'warning_message': False}
        else:
            return {'success': False,
                        'services': services,
                        'error_message': ('Error:\n%s') % str(val_req['errors_message']),
                        'warning_message': False}          
        return {'success': True,
                'services': services,
                'error_message': False,
                'warning_message': ('Warning:\n%s') % warnings if warnings else False}

    def purolator_rate_shipment(self, order):
        order.write({'state':'draft'})
        purolator_service_type = []
        max_weight = self._purolator_convert_weight(self.purolator_default_packaging_id.max_weight, self.purolator_weight_unit)
        price = 0.0
        if order.carrier_id:
            choice = self.env['choose.delivery.carrier'].search([('order_id','=',order.id),('carrier_id','=',order.carrier_id.id)],order='id desc',limit=1)
        else:
            choice = self.env['choose.delivery.carrier'].search([('order_id','=',order.id),('carrier_id','=',self.id)],order='id desc',limit=1)
        if len(choice) == 0:
            pass
        if len(choice) == 1 and choice.purolator_total_weight:
            est_weight_value = choice.purolator_total_weight
            weight_value = self._purolator_convert_weight(est_weight_value, self.purolator_weight_unit)
        else:
            est_weight_value = sum([(line.product_id.weight * line.product_uom_qty) for line in order.order_line if not line.display_type]) or 0.0
            weight_value = self._purolator_convert_weight(est_weight_value, self.purolator_weight_unit)
    
        if 'Pack' and 'Envelope' not in self.purolator_service_type:
            if weight_value == 0.0:
                if self.purolator_weight_unit == 'KG':
                    weight_value =  0.45
                else:
                    weight_value =  1.00
        # order_currency = order.currency_id
        # Rating:
        # To DO: 
        # 1. Create Common Data Format
        # 2. Response Handle
        superself = self.sudo()
        # Authentication stuff
        srm = AppDelivery(service_name='purolator', service_type='rate', service_key=superself.token,super_self=superself)
        packages=[]

        service_type = superself.purolator_service_type if order.partner_shipping_id.country_id.code == 'CA' else(superself.purolator_service_type_us if order.partner_shipping_id.country_id.code == 'US' else superself.purolator_service_type_int )

        srm.set_ship_params(order.warehouse_id.partner_id, order.partner_shipping_id, service_type, packages)
        
        if order.partner_shipping_id.country_id.code != 'CA':
            srm.set_custom_declaration(order.order_line, self)
        
        srm.set_payment(self)
        pkg = self.purolator_default_packaging_id

        if max_weight and weight_value > max_weight:
            total_package = int(weight_value / max_weight)
            last_package_weight = weight_value % max_weight

            for sequence in range(1, total_package + 1):
                srm.add_package(
                    max_weight,
                    pkg,
                    mode='rating'
                )
            if last_package_weight:
                total_package = total_package + 1
                srm.add_package(
                    last_package_weight,
                    pkg,
                    mode='rating'
                )
        else:
            srm.add_package(
                weight_value,
                pkg,
                mode='rating',
            )
        options = {"invoice_no": order.name}
        srm.set_options(options)

        debug_logging = self.env['omni.account'].search([('state','=','active'),('company_id','=',self.company_id.id)], limit=1).debug_logging
        res_json = srm.rate(order, debug_logging, superself.token,superself.company_id.id)
        warnings = res_json.get('warnings_message')
        if res_json.get('warnings_message') == 'Error:\nThe server was unable to process the request due to an internal error.  For more information about the error, either turn on IncludeExceptionDetailInFaults (either from ServiceBehaviorAttribute or from the <serviceDebug> configuration behavior) on the server in order to send the exception information back to the client, or turn on tracing as per the Microsoft .NET Framework SDK documentation and inspect the server trace logs.':
            warnings = 'Error:\nThe server was unable to process the request due to an internal error.'
        if warnings:
            _logger.warning(warnings)


        ShipmentEstimate = []
        if not res_json.get('errors_message'):
            ShipmentEstimate = res_json.get('results')
            price = ShipmentEstimate[0]['total_price']
            choice = self.env['choose.delivery.carrier'].search([('order_id','=',order.id),('carrier_id','=',self.id)],order='id desc',limit=1)
            choice.purolator_service_type = False
            sers = self.env['purolator.service'].sudo().search([])
            for ser in sers:
                ser.write({'active':False})
            for rating in ShipmentEstimate:
                rate = self.env['purolator.service'].sudo().create(
                    {
                        'service_id' : rating['service_code'] ,
                        'shipment_date' :   rating['shipment_date'] ,
                        'expected_delivery_date' :   rating['expected_delivery_date'] ,
                        'expected_transit_days' :   rating['estimated_transit_days'] ,
                        'base_price' :   rating['base_price'] ,
                        'surcharges' :   rating['surcharges_total'] ,
                        'taxes' :   rating['taxes_total'] ,
                        'options' :   rating['options_total'] ,
                        'total_price' :   rating['total_price'] ,
                        'order_id' :   order.id,
                        'choise_id': choice.id,
                        'active': True
                    })   
                if rate:
                    rating['service_id'] = str(rate.id)
                if rating["service_code"] == service_type:
                    choice.purolator_service_type = rate.id
            purolator_service_type = self.env['purolator.service'].sudo().search([('order_id','=',order.id),('active','=',True)])
        else:
            _logger.info(res_json)
            if res_json.get('errors_message') == (401, 'Unauthorized'):
                res_json['errors_message'] = "Wrong Purolator Credentials. Please provide correct credentials in Purolator Confirguration."
            res = {'success': False,
                    'price': 0.0,
                    'ShipmentEstimate' : [],
                    'error_message': ('Error:\n%s') % str(res_json['errors_message']),
                    'purolator_service_type': [],
                    'warning_message': False}
            return res
        service_id = False
        if len(purolator_service_type) > 0 :
            for ser in purolator_service_type:
                if price == ser.total_price:
                    service_id = ser.id
        res = {'success': True,
                'price': price,
                'ShipmentEstimate' : ShipmentEstimate,
                'error_message': False,
                'purolator_service_type': service_id,
                'warning_message': ('Warning:\n%s') % warnings if warnings else False}
        # Response for Free Shipment
        if res['success'] and self.free_over and order._compute_amount_total_without_delivery() >= self.amount:
            _logger.info("FREE SHIPMENT")
            res['free_delivery'] = True
        else:
            res['free_delivery'] = False
            _logger.info("NOT FREE SHIPMENT")

        return res

    def purolator_send_shipping(self, pickings):    
        # Shipping:
        # To DO: 
        # 3. Create Common Data Format
        # 4. Response Handle
        carrier_price = 0
        try:
            for picking in pickings:
                for line in picking.sale_id.order_line:
                    if line.is_delivery == True:
                        carrier_price = line.price_subtotal
        except Exception as e:
            _logger.warning(str(e))

        debug_logging = self.env['omni.account'].search([('state','=','active'),('company_id','=',self.company_id.id)], limit=1).debug_logging

        res = []
        for picking in pickings: 
            choice = self.env['choose.delivery.carrier'].search([('order_id','=',picking.sale_id.id),('carrier_id','=',picking.carrier_id.id)],order='id desc',limit=1)
            if len(choice) == 1:
                purolator_service_type = choice.purolator_service_type.service_id
            else:
                purolator_service_type = self.purolator_service_type

           
            # package_type = picking.move_line_ids.result_package_id and picking.move_line_ids.result_package_id[0].packaging_id.shipper_package_code or self.purolator_default_packaging_id.shipper_package_code
            weight_value = '1'   
            if 'Pack' and 'Envelope' not in purolator_service_type:
                if weight_value == 0.0:
                    if self.purolator_weight_unit == 'KG':
                        weight_value =  0.45
                    else:
                        weight_value =  1.00

            order = picking.sale_id
            net_weight = self._purolator_convert_weight(picking.shipping_weight, self.purolator_weight_unit)
            superself = self.sudo()
            srm = AppDelivery(service_name='purolator', service_type='rate', service_key=superself.token)
            packages=[]
            service_id = order.purolator_service if order.purolator_service else superself.purolator_service_type
            srm.set_ship_params(order.warehouse_id.partner_id, order.partner_shipping_id, service_id, packages)
            if order.partner_shipping_id.country_id.code != 'CA':
                srm.set_custom_declaration(order.order_line, self)
            srm.set_payment(self)
            options = {"invoice_no": order.name,"printer_type":superself.purolator_printer_type}
            srm.set_options(options)
            
            package_count = len(picking.move_line_ids.result_package_id) or 1
            po_number = order.display_name or False
            dept_number = False
            get_label_obj = AppDelivery(service_name='purolator', service_type='shipment', service_key=superself.token)
            OmniAccount = self.env['omni.account'].sudo()
            omni_account_id = OmniAccount.search([('state', '=', 'active'),('id','=',superself.account_id.id)], limit=1)
            ################
            # Multipackage #
            ################
            if package_count > 1:
                # Note: Purolator has a simple multi-piece shipping interface
                # - Multiple packages can be sent in a single request

                master_tracking_id = False
                package_labels = []
                carrier_tracking_ref = ""
                for sequence, package in enumerate(picking.move_line_ids.result_package_id, start=1):
                    package_weight = self._purolator_convert_weight(package.shipping_weight, self.purolator_weight_unit)
                    packaging = package.package_type_id
                    srm.add_package(
                        package_weight,
                        packaging,
                        mode=None
                    )

                res_json = srm.process_shipment(debug_logging, self.token,self.company_id.id)
                # package_name = package.name or sequence

                warnings = res_json.get('warnings_message')
                if warnings:
                    _logger.info(warnings)

                if not res_json.get('errors_message'):
                    carrier_tracking_ref = res_json['tracking_number']  # Array of PINS
                    carrier_price = 0.0
                    if order.order_line[-1].name.split(" ")[0] == self.name:
                        carrier_price = order.order_line[-1].price_subtotal
                    if res_json['master_tracking_id']:
                        purolator_labels=[]
                        header = {"Authorization": 'Token ' + omni_account_id.token}
                        bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                            omni_account_id.server_url + res_json.get('url'), headers=header)
                        if pdf_status == 200:
                            picking.connector_label_url = picking.connector_label_url+','+ res_json.get('url') if picking.connector_label_url else res_json.get('url')
                            PDF_NAME = 'LabelPurolator-%s.%s' % (
                            carrier_tracking_ref, self.purolator_label_image_format)
                            PDF_NAME = PDF_NAME.encode('utf-8').decode('utf-8')
                            purolator_labels.append((PDF_NAME, bytepdf))
                        else:
                            logmessage = (
                                "Label PDF cannot be generated for <b>Tracking Number : </b> %s<br/><br><br/> If you want to get the label pdf, click on button <b>GET LABELS</b>.<br><br/> If you want to get the label url, click on button <b>LABEL URL</b><br/>") % (
                                             carrier_tracking_ref)
                            picking.message_post(body=logmessage)

                        order_currency = picking.sale_id.currency_id or self.company_id.currency_id
                        logmessage = (
                            "Shipment sent to carrier %s for shipping with <br/> <b>Tracking Number : </b> %s<br/>") % (
                                     picking.carrier_id.name,
                                     carrier_tracking_ref)  # Cost: %.2f %s , carrier_price, order_currency.name
                        picking.message_post(body=logmessage, attachments=purolator_labels)
                        shipping_data = {'exact_price': carrier_price, 'tracking_number': carrier_tracking_ref}
                        res = res + [shipping_data]
                        picking.purolator_return_label_url = res_json.get('return_url')
                    else:
                        raise UserError(res_json['error'])
                else:
                    raise UserError(json.dumps(res_json['errors_message']))

            ###############
            # One package #
            ###############
            elif package_count == 1:
                packaging = picking.move_line_ids.result_package_id[:1].package_type_id or picking.carrier_id.purolator_default_packaging_id
                package_weight = self._purolator_convert_weight(picking.move_line_ids.result_package_id.shipping_weight, self.purolator_weight_unit)
                srm.add_package(
                    package_weight,
                    packaging,
                    mode=None
                )
                res_json = srm.process_shipment(debug_logging, self.token,self.company_id.id)
                warnings = res_json.get('warnings_message')
                if warnings:
                    _logger.info(warnings)
                if not res_json.get('errors_message'):
                    carrier_tracking_ref = res_json['tracking_number']#Array of PINS
                    carrier_price = 0.0
                    if order.order_line[-1].name.split(" ")[0] == self.name:
                        carrier_price = order.order_line[-1].price_subtotal
                    if res_json['master_tracking_id']:
                        # lrm = AppDelivery(service_name='purolator', service_type='label', service_key=superself.token)
                        # get_label_url = lrm.get_label_url(carrier_tracking_ref,self.purolator_label_image_format,debug_logging,self.token)
                        header = {"Authorization": 'Token ' + omni_account_id.token}
                        bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                            omni_account_id.server_url + res_json.get('url'), headers=header)
                        purolator_labels=[]
                        if pdf_status == 200:
                            picking.connector_label_url = picking.connector_label_url+','+ res_json.get('url') if picking.connector_label_url else res_json.get('url')
                            PDF_NAME = 'LabelPurolator-%s.%s' % (carrier_tracking_ref, self.purolator_label_image_format)
                            PDF_NAME = PDF_NAME.encode('utf-8').decode('utf-8')
                            purolator_labels.append((PDF_NAME,bytepdf))
                        else:
                            logmessage = ("Label PDF cannot be generated for <b>Tracking Number : </b> %s<br/><br><br/> If you want to get the label pdf, click on button <b>GET LABELS</b>.<br><br/> If you want to get the label url, click on button <b>LABEL URL</b><br/>") % (carrier_tracking_ref)
                            picking.message_post(body=logmessage)

                        order_currency = picking.sale_id.currency_id or self.company_id.currency_id
                        logmessage = ("Shipment sent to carrier %s for shipping with <br/> <b>Tracking Number : </b> %s<br/>") % (picking.carrier_id.name, carrier_tracking_ref)#Cost: %.2f %s , carrier_price, order_currency.name
                        picking.message_post(body=logmessage, attachments=purolator_labels)
                        shipping_data = {'exact_price': carrier_price, 'tracking_number': carrier_tracking_ref}
                        res = res + [shipping_data]
                        picking.purolator_return_label_url = res_json.get('return_url')
                else:
                    raise UserError(json.dumps(res_json['errors_message']))

            ##############
            # No package #
            ##############
            else:
                raise UserError(('No packages for this picking'))
            return res

    def purolator_get_tracking_link(self, pickings):
        return 'https://www.purolator.com/en/shipping/tracker?pins=' + '%s' % pickings.carrier_tracking_ref

    def purolator_cancel_shipment(self, picking):
        picking.message_post(body=(u"You can't cancel Purolator shipping without pickup date."))
        picking.write({'carrier_tracking_ref': '', 'carrier_price': 0.0})

    def _purolator_convert_weight(self, weight, unit='KG'):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        if unit == 'KG':
            return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'), round=False)
        elif unit == 'LB':
            return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_lb'), round=False)
        else:
            raise ValueError

    def purolator_get_pdf_byte(self,url):
        try:
            _logger.info(url)
            myfile = requests.get(url)
            _logger.info(myfile.status_code)
            bytepdf = bytearray(myfile.content)
            return bytepdf, myfile.status_code
        except Exception as e:
            raise UserError(str(e.args))

    def purolator_get_labels(self,picking):
        debug_logging = self.env['omni.account'].search([('state', '=', 'active')], limit=1).debug_logging
        get_label_obj = AppDelivery(service_name='purolator', service_type='label', service_key=self.token)
        OmniAccount = self.env['omni.account'].sudo()
        omni_account_id = OmniAccount.search([('state', '=', 'active'),('id','=',self.account_id.id)], limit=1)
        try:
            header = {"Authorization": 'Token ' + omni_account_id.token}
            label_urls = picking.connector_label_url.split(',')
            for label_url in label_urls:
                bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                    omni_account_id.server_url + label_url, headers=header)
                purolator_labels=[]
                if pdf_status == 200:
                    PDF_NAME = 'LabelPurolator-%s.%s' % (picking.carrier_tracking_ref, self.purolator_label_image_format)
                    PDF_NAME = PDF_NAME.encode('utf-8').decode('utf-8')
                    purolator_labels.append((PDF_NAME, bytepdf))
                else:
                    logmessage = (
                        "Label PDF cannot be generated for <b>Tracking Number : </b> %s<br/><br><br/> If you want to get the label pdf, click on button <b>GET LABELS</b>.<br><br/> If you want to get the label url, click on button <b>LABEL URL</b><br/>") % (
                                     picking.carrier_tracking_ref)
                    picking.message_post(body=logmessage)
            logmessage = ("Shipment sent to carrier %s for shipping with <br/> <b>Tracking Number : </b> %s<br/>") % (
            picking.carrier_id.name, picking.carrier_tracking_ref)  # Cost: %.2f %s , carrier_price, order_currency.name
            picking.message_post(body=logmessage, attachments=purolator_labels)

        except Exception as e:
            raise UserError(str(e.args))


    def purolator_get_return_label(self, picking, tracking_number=None, origin_date=None):

        debug_logging = self.env['omni.account'].search(
            [('state', '=', 'active'), ('company_id', '=', self.company_id.id)], limit=1).debug_logging
        get_label_obj = AppDelivery(service_name='canadapost', service_type='label', service_key=self.token)
        OmniAccount = self.env['omni.account'].sudo()
        omni_account_id = OmniAccount.search([('state', '=', 'active'),('id','=',self.account_id.id)],
                                             limit=1)

        label_urls = picking.purolator_return_label_url
        package_labels=[]
        try:
            header = {"Authorization": 'Token ' + omni_account_id.token}
            bytepdf, pdf_status = get_label_obj.get_pdf_byte(
                omni_account_id.server_url + label_urls, headers=header)
            if pdf_status == 200:
                PDF_NAME = 'PurolatorReturnLabelPurolator.%s' % (self.purolator_label_image_format)
                PDF_NAME = PDF_NAME.encode('utf-8').decode('utf-8')
                package_labels.append((PDF_NAME, bytepdf))
            else:
                logmessage = (
                    "Return Label PDF cannot be generated.")
                picking.message_post(body=logmessage)

            logmessage = ("Return Label created into Purolator<br/>"
                           )
            attachments = [('Purolator ReturnLabelcanadapost-'+
                            '.pdf', pdf.merge_pdf([pl[1] for pl in package_labels]))]
            picking.message_post(
                body=logmessage, attachments=attachments)
        except Exception as e:
            raise UserError(str(e.args))

    # def get_label_urls(self, picking):
    #     debug_logging = self.env['omni.account'].search([('state', '=', 'active')], limit=1).debug_logging
    #     try:
    #         lrm = AppDelivery(service_name='label', service_type='rate', service_key=self.token)
    #         lrm.label_info(picking,self.purolator_label_image_format)
    #         superself = self.sudo()
    #         get_label_url = lrm.get_label_url(picking.carrier_tracking_ref,self.purolator_label_image_format,debug_logging,self.token)
    #         if "errors" not in get_label_url:
    #             return get_label_url
    #     except Exception as e:
    #         raise UserError(str(e.args))