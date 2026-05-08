# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from os import access

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)


STATECODE_REQUIRED_COUNTRIES = ["US", "CA", "PR ", "IN"]


class AppDelivery:
    def __init__(self, service_name, service_type, service_key):
        self.service_name = service_name
        self.service_type = service_type
        self.service_key = service_key
        self.data = {}
        self.data['sender'] = {}
        self.data['receiver'] = {}
        self.data['packages'] = {}

    # sender, receiver, packages
    def set_ship_params(
        self, warehouse_partner, recipient_partner, service_id, packages
    ):
        self.data['sender'] = self.get_shipper(warehouse_partner)
        self.data['receiver'] = self.get_shipper(recipient_partner)
        # self.service_id = service_id
        self.data['packages']["service_id"] = service_id
        self.data['packages']["pieces"] = []
        for package in packages:
            self.add_packages(package=package)

    def get_shipper(self, partner):
        """Function Convert Partner to OmniSync Partner Vals

        Args:
            partner (res.partner): Contact

        Returns:
            partner_vals: A dict contaning partner values
        """
        partner_vals = {}
        if partner.is_company:
            partner_vals["name"] = partner.name
            partner_vals["company_name"] = partner.name or ''
        else:
            partner_vals["name"] = partner.name
            partner_vals["company_name"] = partner.parent_id.name or ''

        street_no = partner.street or ""
        street_no += (
            ", " + partner.street2
            if partner.street2 != "" and partner.street2 != False
            else ""
        )
        partner_vals["street_no"] = street_no

        partner_vals["city"] = partner.city or ""

        if partner.country_id.code in STATECODE_REQUIRED_COUNTRIES:
            partner_vals["state"] = partner.state_id.code or ""
        else:
            partner_vals["state"] = ""
        partner_vals["country"] = partner.country_id.code or ""
        partner_vals["zip_code"] = partner.zip or ""

        # SndPhoneNumber = self.factory.PhoneNumber()
        snd_phone_or = (
            partner.phone.replace("-", "").replace("(", "").replace(")", "")
            if partner.phone != False
            else partner.phone
        )
        snd_phone_sp = snd_phone_or.replace(" ", "") if snd_phone_or != False else False
        if snd_phone_sp != False:
            snd_phone_cn_code = (
                snd_phone_sp[:-10]
                if len(snd_phone_sp) > 1
                else "+" + str(partner.country_id.phone_code)
            )
            snd_phone_ar_code = snd_phone_sp[-10:-7] if len(snd_phone_sp) > 3 else False
            snd_phone = snd_phone_sp[-7:] if len(snd_phone_sp) > 3 else False
        else:
            snd_phone_cn_code = (
                "+" + str(partner.country_id.phone_code)
                if len(partner.country_id) > 0
                else ""
            )
            snd_phone_ar_code = ""
            snd_phone = ""

        partner_vals["phone"] = snd_phone_cn_code + snd_phone_ar_code + snd_phone
        return partner_vals

    def add_package(self, ship_weight, package, mode=None):
        # Odoo Version 14.0
        length_uom_name = 'cm' if package.length_uom_name == 'm' or 'mm' else package.length_uom_name
        self.data['packages']["pieces"] =[{
                "length": package.packaging_length,
                "width": package.width,
                "height": package.height,
                "distance_unit": length_uom_name,
                "weight": ship_weight,
                "mass_unit": package.weight_uom_name,
            }]


    def set_payment(self, carrier_id):
        self.data['payment'] = {
            "payment_type": carrier_id.purolator_payment_type if carrier_id.delivery_type =='purolator' else "Sender",
            "account_number": carrier_id.purolator_billing_account if carrier_id.delivery_type =='purolator' else "9999999999",
        }

    def set_custom_declaration(self, order_line, carrier_id):
        self.data['international_information'] ={"tax_number":False}
        product_information = []
        for line in order_line:
            if line.product_id.type != 'service':
                product_information.append(
                    {
                        "product_name": line.product_id.name,
                        "hs_code": line.product_id.hs_code,
                        "manufacturer": line.product_id.country_of_manufacture.code,
                        "product_code": line.product_id.default_code,
                        "unit_price": line.price_unit,
                        "unit_weight": line.product_id.weight,
                        "quantity": line.product_qty,
                    }
                )

        self.data['international_information']['product_information'] =product_information

    def set_custom_declaration_canadapost(self, order_line, carrier_id):
            self.data['international_information'] = {"tax_number": False,"currency":carrier_id.company_id.currency_id.display_name}
            product_information = []
            for line in order_line:
                if line.product_id.type != 'service':
                    product_information.append(
                        {
                            "product_name": line.product_id.name,
                            "hs_code": line.product_id.hs_code,
                            "manufacturer": line.product_id.country_of_manufacture.code,
                            "product_code": line.product_id.default_code,
                            "unit_price": line.product_id.list_price,
                            "unit_weight": line.product_id.weight,
                            "quantity": int(line.quantity),
                            "country_of_origin": line.product_id.country_of_origin.code,
                        }
                    )

            self.data['international_information']['product_information'] = product_information

    def set_options(self, options):
        self.data['options'] = options
        # ref1 = picking.order_id.name or order.name
        #{
        #     "ref_1": ref1,
        #     "ref_2": "",
        #     "ref_3": "",
        #     "ref_4": "",
        #     "ref_5": "",
        # }

    def label_info(self,picking,label_format):
        self.data['tracking_pin'] = picking.carrier_tracking_ref
        self.data['document_type'] = label_format


    def rate(self, order, debug_logging, user_access_token,company_id,super_self=None):
        self.service_type = 'rate'
        url = "/api/v1/services/delivery/"
        request_type = "POST"
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": self.service_key
        }
        data = self.__dict__

        omnisync_id = False
        super_env=request.env
        if super_self:
            super_env = super_self.env
        delivery_id = super_env['delivery.carrier'].sudo().search([('token', '=', self.service_key)],limit=1)
        if delivery_id:
            omnisync_id = delivery_id[0].account_id
        
        rate_list = super_env["omnisync.connector"].sudo().omnisync_api_call(
            headers=headers, 
            url=url, 
            request_type=request_type, 
            data=data,
            debug_logging=debug_logging,
            access_token=user_access_token,
            company_id=company_id,
            omnisync_id=omnisync_id,
        )

        _logger.info("rate_list ====>>>>", rate_list)

        rate_list['errors_message'] = 'No Rating Found' if rate_list == 0 else rate_list.get("errors")

        return rate_list


    #Shipping Stuff
    def process_shipment(self, debug_logging, access_token,company_id,**kwargs):
        self.service_type = 'shipment'
        formatted_response = {'tracking_number': 0.0,
                              'price': {},
                              'master_tracking_id': None,
                              'date': None}

        url = "/api/v1/services/delivery/"
        request_type = "POST"
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": self.service_key if hasattr(self,'service_key') else kwargs.get('service_key'),
        }
        data = self.__dict__

        omnisync_id = False
        delivery_id = request.env['delivery.carrier'].search([('token', '=', self.service_key if hasattr(self,'service_key') else kwargs.get('service_key'))],limit=1)
        if delivery_id:
            omnisync_id = delivery_id[0].account_id

        try:
            formatted_response = request.env["omnisync.connector"].omnisync_api_call(
                headers=headers, 
                url=url, 
                request_type=request_type, 
                data=data,
                debug_logging=debug_logging,
                access_token=access_token,
                company_id=company_id,
                omnisync_id=omnisync_id
            )

            _logger.info("formatted_response ====>>>>", formatted_response)
            formatted_response['errors_message'] = formatted_response.get("errors") if formatted_response.get("errors") else None

            return formatted_response

        except Exception as e:
            formatted_response['errors_message'] = e.args[0]
        return formatted_response

    def get_label_url(self,tracking,label_format,debug_logging, access_token):
        """[summary]"""

        formatted_response = {"url":[]}

        url = "/api/v1/services/delivery/"
        request_type = "POST"
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": self.service_key,
        }
        data = self.__dict__
        data['data']={
            "tracking_pin": tracking,
            "document_type": label_format
        }
        omnisync_id = False
        delivery_id = request.env['delivery.carrier'].search([('token', '=', self.service_key)],limit=1)
        if delivery_id:
            omnisync_id = delivery_id[0].account_id


        try:
            formatted_response = request.env["omnisync.connector"].omnisync_api_call(
                headers=headers,
                url=url,
                request_type=request_type,
                data=data,
                debug_logging=debug_logging,
                access_token=access_token,
                omnisync_id=omnisync_id
            )

            _logger.info("formatted_response ====>>>>", formatted_response)
            formatted_response['error'] = formatted_response.get("errors") if formatted_response.get("errors") else None

            return formatted_response

        except Exception as e:
            formatted_response['errors_message'] = e.args[0]
        return formatted_response

    def get_pdf_byte(self, url,headers=None):
        try:
            _logger.info(url)
            headers['X-Service-Key'] = self.service_key
            myfile = requests.get(url,headers=headers)
            _logger.info(myfile.status_code)
            bytepdf = bytearray(myfile.content)
            return bytepdf, myfile.status_code
        except Exception as e:
            raise UserError(str(e.args))

    # Return Stuff
    def process_return(self, debug_logging, access_token, company_id, **kwargs):
        self.service_type = 'shipment_return'
        formatted_response = {'tracking_number': 0.0,
                              'master_tracking_id': None,
                              'expiry-date': None,
                              }

        url = "/api/v1/services/delivery/"
        request_type = "POST"
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": self.service_key if hasattr(self, 'service_key') else kwargs.get('service_key'),
        }
        data = self.__dict__
        omnisync_id = False
        delivery_id = request.env['delivery.carrier'].search([('token', '=', self.service_key)],limit=1)
        if delivery_id:
            omnisync_id = delivery_id[0].account_id

        try:
            formatted_response = request.env["omnisync.connector"].omnisync_api_call(
                headers=headers,
                url=url,
                request_type=request_type,
                data=data,
                debug_logging=debug_logging,
                access_token=access_token,
                company_id=company_id,
                omnisync_id=omnisync_id
            )

            _logger.info("formatted_response ====>>>>", formatted_response)
            formatted_response['errors_message'] = formatted_response.get("errors") if formatted_response.get(
                "errors") else None

            return formatted_response

        except Exception as e:
            formatted_response['errors_message'] = e.args[0]
        return formatted_response

