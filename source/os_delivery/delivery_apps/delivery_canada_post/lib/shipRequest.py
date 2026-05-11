# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import xml.sax
import xmltodict
import json
import requests
import logging

_logger = logging.getLogger(__name__)


class canHttpsPost(object):
    __url = {}
    __agent = "Python API 1.1.0"
    __timeout = 40
    __requestData = ""
    __Response = None
    __request_type = ""

    def __init__(self, base_url, headers, trxn, request_type):
        _logger.info(str(base_url) + "\n" +  str(headers) + "\n" +  str(trxn) + "\n" +  str(request_type))
        self.__trxn = trxn
        self.__status_code = ''
        self.__headers = headers
        self.__url["host"] = base_url
        self.__data = str(self.__toXml())
        self.__request_type = request_type

    def postRequest(self):
        requestUrl = self.__url["host"]
        ret_res = {}
        try:
            data  = '<?xml version="1.0" encoding="utf-8"?>'+ self.__data
            from pprint import pprint
            pprint(xmltodict.parse(data))
            if self.__request_type == 'tracking':
                response = requests.get(requestUrl, data=data, headers=self.__headers)
            else:
                response = requests.post(requestUrl, data=data, headers=self.__headers)
            if response.status_code == 200:
                jsondumps = json.dumps(xmltodict.parse(response.text))
                res_json= json.loads(jsondumps)
                ret_res ={'error': False, 'response':res_json, "status_code": response.status_code}
            else:
                ret_res ={'error': True, 'response':response.text, "status_code":response.status_code}

        except Exception as e:
            response = self.__GlobalError(e)
        self.__Response = ret_res

    def getResponse(self):
        return self.__Response

    def __toXml(self):
        request = self.__trxn.toXml() 
        return request

    def __GlobalError(self, error):
        try:
            errorNumber, errorMessage = error.reason
        except Exception as e:
            errorNumber, errorMessage = 1, str(error)
        if 'ConnectionError' in str(error):
            errorMessage = 'ConnectionError'
        errorResponse = '<?xml version="1.0" standalone="yes"?><response><Message>' + errorMessage + '</Message></response>'
        errorResponse = xmltodict.parse(errorResponse)
        return errorResponse


class canRequest:
    def __init__(self):
        self._Request = ""
        self._tags = {}
        self._order = None

    def toXml(self):
        requestXml = "<" + self._Request + ">" if self._Request != '' else ''
        if self._Request == 'non-contract-shipment':
            requestXml = "<" + self._Request + " xmlns='http://www.canadapost.ca/ws/ncshipment-v4'" + ">" 
        if self._Request == 'mailing-scenario':
            requestXml = "<" + self._Request + " xmlns='http://www.canadapost.ca/ws/ship/rate-v4'" + ">" 
        if self._Request == 'shipment':
            requestXml = "<" + self._Request + " xmlns='http://www.canadapost.ca/ws/shipment-v8'" + ">" 
        for index, tag in enumerate(self._order):
            value = self._tags[tag]
            if isinstance(value, str):
                requestXml = requestXml + "<" + tag + ">" + value + "</" + tag + ">"
            elif isinstance(value, canRequest):
                requestXml = requestXml + value.toXml()
            elif isinstance(value, list):
                for item in value:
                    requestXml = requestXml + item.toXml()
        requestXml = requestXml + "</" + self._Request + ">" if self._Request != '' else requestXml
        return requestXml

class CanpostGetRates(canRequest):
    def __init__(self):
        self._Request = "mailing-scenario"
        self._tags = {"customer-number": None, "parcel-characteristics": None, 
                        "destination": None, "origin-postal-code":None}
        self._order = []

    def setCustNum(self, customer_number):
        self._tags["customer-number"] = customer_number
        self._order.append("customer-number")

    def setParcel(self, parcel_characteristics):
        self._tags["parcel-characteristics"] = parcel_characteristics
        self._order.append("parcel-characteristics")
    
    def setOriginPC(self, origin_postal_code):
        self._tags["origin-postal-code"] = origin_postal_code
        self._order.append("origin-postal-code")

    def setDestination(self, destination):
        self._tags["destination"] = destination
        self._order.append("destination")

    def setOptions(self, options):
        self._tags["options"] = options
        self._order.append("options")

    def setOthers(self, mail_date, promo_code):
        print("setOthers")
        self._tags["expected-mailing-date"] = str(mail_date.strftime("%Y-%m-%d")) if mail_date != False else None 
        self._tags["promo-code"] = promo_code if promo_code != False else None 
        self._order.append("expected-mailing-date")
        self._order.append("promo-code")


class Sender(canRequest):
    def __init__(self, name, company, contact_phone=False):
        self._Request = "sender"
        self._tags = {"name": name, "company": company, "contact-phone": contact_phone}
        self._order = ["name", "company", "contact-phone" ]

    def setAddress(self, addressdetails):
        self._tags["address-details"] = addressdetails
        self._order.append("address-details")

class Destination(canRequest):
    def __init__(self, name, company, contact_phone=False):
        self._Request = "destination"
        self._tags = {"name": name, "company": company, "contact-phone":contact_phone}
        self._order = ["name", "company"]

    def setAddress(self, address):
        self._tags["address-details"] = address
        self._order.append("address-details")

    def setAddressInfo(self, additionalainfo=None, cvnumber=None):
        self._tags["additional-address-info"] = additionalainfo
        self._tags["client-voice-number"] = cvnumber
        self._order.append("additional-address-info")
        self._order.append("client-voice-number")

class AddressDetails(canRequest):
    def __init__(self, partner):
        self._Request = "address-details"
        self._tags = {"address-line-1": partner.street ,"address-line-2": partner.street2 ,"city":partner.city,"prov-state":partner.state_id.code if partner.state_id.code else None,
            "postal-zip-code": partner.zip.replace(" ","") if partner.zip else None, "contact-phone":partner.phone,"country-code":partner.country_id.code}
        self._order = ["address-line-1","address-line-2","city","prov-state","postal-zip-code"]

    def setPostalCode(self, postal_code):
        self._tags["postal-zip-code"] = postal_code
        self._order.append("postal-zip-code")

    def setCountry(self, partner):
        self._tags["country-code"] = partner.country_id.code
        self._order.append("country-code")

    def setReturnNotify(self, partner):
        self._tags["return-notification"] = partner.email
        self._order.append("return-notification")

class ParcelCharacteristics(canRequest):
    def __init__(self):
        self._Request = "parcel-characteristics"
        self._tags = {"weight": None,"dimensions":None,"document":None,"unpackaged":None,"mailing-tube":None}
        self._order = []

    def setWeight(self, weight):
        self._tags["weight"] = weight
        self._order.append("weight")

    def setDimension(self, dimensions):
        self._tags["dimensions"] = dimensions
        self._order.append("dimensions")

    def setDetails(self, document, unpackaged, mailing_tube):
        self._tags["document"] = document
        self._tags["unpackaged"] = unpackaged
        self._tags["mailing-tube"] = mailing_tube
        self._order.append("dimensions")
        self._order.append("unpackaged")
        self._order.append("mailing-tube")

class Dimension(canRequest):
    def __init__(self, length, width, height):
        self._Request = "dimensions"
        self._tags = {"length": length,"width": width, "height":height,"unpackaged":False,"mailing-tube":False,"oversized":False}
        self._order = ["length","width","height"]

class Notification(canRequest):
    def __init__(self, email, on_shipment, on_exception, on_delivery):
        self._Request = "notification"
        self._tags = {"email": email,"on-shipment": on_shipment,"on-exception":on_exception,"on-delivery":on_delivery}
        self._order = ["email", "on-shipment", "on-exception", "on-delivery"]

class Preferences(canRequest):
    def __init__(self, spinstructions, sprate, sivalue):
        self._Request = "preferences"
        self._tags = {"show-packing-instructions": str(spinstructions).lower(),"show-postage-rate":str(sprate).lower(),"show-insured-value":str(sivalue).lower()}
        self._order = ["show-packing-instructions", "show-postage-rate", "show-insured-value"]

class References(canRequest):
    def __init__(self, cost_centre, customerref1, customerref2):
        self._Request = "references"
        self._tags = {"cost-centre": cost_centre,"customer-ref-1":customerref1,"customer-ref-2":customerref2}
        self._order = ["cost-centre", "customer-ref-1", "customer-ref-2"]

class Customs(canRequest):
    def __init__(self, currency, convfromcad, reasonforexport, otherreason, sku_list, dutiestaxesprepaid,cert_number, license_no, inv_no ):
        print("Customs")
        print(currency, convfromcad, reasonforexport, otherreason, sku_list, dutiestaxesprepaid,cert_number, license_no, inv_no)
        self._Request = "customs"
        self._tags = {"currency": currency,"conversion-from-cad":str(convfromcad) if convfromcad else None,
            "reason-for-export":reasonforexport,
            "other-reason": otherreason,"sku-list": sku_list,"duties-and-taxes-prepaid":dutiestaxesprepaid,"certificate-number":cert_number,
            "licence-number": license_no, "invoice-number": inv_no}
        self._order = ["currency", "conversion-from-cad", "reason-for-export", "other-reason", "sku-list", "duties-and-taxes-prepaid", "certificate-number",
            "licence-number", "invoice-number"]

class SkuList(canRequest):
    def __init__(self):
        self._Request = "sku-list"
        self._tags = {"item": None}
        self._order = []

    def setItem(self,item):
        self._tags["item"] = item
        self._order.append("item")

class Item(canRequest):
    def __init__(self, hscode, sku, cus_des, uweight, cvpu, cnou, cuom,coo, poorigin):
        print(hscode, sku, cus_des, uweight, cvpu, cnou, cuom,coo, poorigin)
        self._Request = "item"
        self._tags = {"hs-tariff-code": hscode, "sku": sku, "customs-description": cus_des, "unit-weight": uweight,
            "customs-value-per-unit": str(cvpu), "customs-number-of-units": str(cnou), "customs-unit-of-measure":cuom,
            "country-of-origin":coo, "province-of-origin":poorigin }
        self._order = ["hs-tariff-code", "sku", "customs-description", "unit-weight",
            "customs-value-per-unit", "customs-number-of-units", "customs-unit-of-measure",
            "country-of-origin", "province-of-origin"]

class SettlementInfo(canRequest):
    def __init__(self, values):
        print("SettlementInfo")
        self._Request = "settlement-info"
        self._tags = values
        # {"paid-by-customer": values.get('paid-by-customer'), "contract-id": values.get('contract-id') , 
        #     "cif-shipment": values.get('cif-shipment'), 
        #     "intended-method-of-payment": values.get('intended-method-of-payment'),
        #     "promo-code": values.get('promo_code')}
        # self._order = ["paid-by-customer", "contract-id", "cif-shipment", "intended-method-of-payment","promo-code"]
        self._order = []
        self._order += [key for key,value in self._tags.items()]
class ShipDestination(canRequest):
    def __init__(self):
        self._Request = "destination"
        self._tags = {"domestic": None, "united-states": None, "international": None}
        self._order = []

    def setDestination(self, destination):
        self._tags[destination._Request] = destination
        self._order.append(destination._Request)

class Domestic(canRequest):
    def __init__(self):
        self._Request = "domestic"
        self._tags = {"postal-code": None}
        self._order = []

    def setPostalCode(self, postal_code):
        self._tags["postal-code"] = postal_code
        self._order.append("postal-code")

class UnitedStates(canRequest):
    def __init__(self):
        self._Request = "united-states"
        self._tags = {}
        self._order = []

    def setZipCode(self, zip_code):
        self._tags["zip-code"] = zip_code
        self._order.append("zip-code")

class International(canRequest):
    def __init__(self, country_code):
        self._Request = "international"
        self._tags = {"country-code": country_code}
        self._order = ["country-code"]

    def setPostalCode(self, postal_code):
        self._tags["postal-code"] = postal_code
        self._order.append("postal-code")

class DeliverySpec(canRequest):
    def __init__(self, service_code, sender, destination, parcel_characteristics=None, preferences=None):
        self._Request = "delivery-spec"
        self._tags = {"service-code": service_code ,"sender":sender,"destination":destination,
            "parcel-characteristics": parcel_characteristics,"preferences":preferences}
        self._order = ["service-code","sender","destination","parcel-characteristics","preferences"]

    def setParcel(self, parcel_characteristics):
        self._tags["parcel-characteristics"] = parcel_characteristics
        self._order.append("parcel-characteristics")

    def setPostalCode(self, postal_code):
        self._tags["address-details"] = postal_code
        self._order.append("address-details")

    def setPreferences(self, preferences):
        self._tags["preferences"] = preferences
        self._order.append("preferences")

    def setSettlement(self, settlement_info):
        self._tags["settlement-info"] = settlement_info
        self._order.append("settlement-info")

    def setNotification(self, notification):
        self._tags["notification"] = notification
        self._order.append("notification")

    def setCustoms(self, customs):
        self._tags["customs"] = customs
        self._order.append("customs")

    def setOptions(self, options):
        self._tags["options"] = options
        self._order.append("options")

class Options(canRequest):
    def __init__(self):
        self._Request = "options"
        self._tags = {}
        self._order = []
  
    def set_option(self, option):
        self._tags = {"option": option }
        self._order = ["option"]

class Option(canRequest):
    def __init__(self, option, option_amount):
        self._Request = "option"
        self._tags = {"option-code": option,"option-amount":option_amount }
        self._order = ["option-code","option-amount"]

class NCShipping(canRequest):
    def __init__(self, rs_point, delivery_spec):
        self._Request = "non-contract-shipment"
        self._tags = {"requested-shipping-point": rs_point ,"delivery-spec":delivery_spec}
        self._order = ["requested-shipping-point","delivery-spec"]

# Commercial Shipment
class Shipment(canRequest):
    def __init__(self, values):
        self._Request = "shipment"
        self._tags = values
        self._order = []
        self._order += [key for key,value in self._tags.items()]


class ReturnRecipient(canRequest):
    def __init__(self, values):
        self._Request = "return-recipient"
        self._tags = {
            "name": values.get('name') ,
            "company":values.get('company'),
            "address-details": values.get('address-details')
        }
        self._order = ["name","company","address-details"]


class PreAuthroizedPayment(canRequest):
    def __init__(self, values):
        self._Request = "pre-authorized-payment"
        self._tags = {
            "account-number": values.get('account-number'),
            "auth-code":values.get('auth-code'),
            "auth-timestamp": values.get('auth-timestamp'), 
            "charge-amount": values.get('charge-amount')
        }
        self._order = ["account-number","auth-code","auth-timestamp","charge-amount"]


class NcRefund(canRequest):
    def __init__(self, email):
        self._Request = "non-contract-shipment-refund-request"
        self._tags = {"email": email}
        self._order = ["email"]

