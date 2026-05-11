# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import xml.sax
import xmltodict
import json
import requests

from odoo.addons.odoosync_base.utils.app_payment import AppPayment


class mpgHttpsPost(object):
    """"
        param: host
        param: store_id
        param: api_token
        param: trxn
    """
    __url = {'protocol': 'https', 'port': '443',
             'file': 'gateway2/servlet/MpgRequest'}
    __agent = "Python API 1.1.0"
    __timeout = 40
    __requestData = ""
    __Response = None

    def __init__(self, host, trxn):
        self.__trxn = trxn
        # self.__storeId = store_id
        # self.__apiToken = api_token
        self.__url["host"] = host
        self.__data = str(self.__toXml())

    def postRequest(self,provider):
        requestUrl = self.__url["protocol"] + "://" + self.__url["host"] + \
            ":" + self.__url["port"] + "/" + self.__url["file"]
        print("requestUrl", requestUrl)
        try:
            add_xml_tags = True
            if add_xml_tags == True:
                # data = "<?xml version='1.0' encoding='UTF-8'?>" + self.__data
                data =self.__data
            # headers = {'Content-Type': 'application/xml'}
            print(data)
            srm = AppPayment(service_name='moneris', service_type='mpg', service_key=provider.token)
            srm.data = data
            response = srm.payment_process(company_id=provider.company_id.id)
            # response = requests.post(url, data=json.dumps(data_request))
            res_json = response
            # response = requests.post(requestUrl, data=data, headers=headers)
            if "response" in response:
                jsondumps = json.dumps(xmltodict.parse(response.get("response")))
                response = json.loads(jsondumps)
            else:
                response = response.text

        except Exception as e:
            response = self.__GlobalError(e)
        self.__Response = response

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
        # '[' + str( errorNumber) + '] ' +
        if 'ConnectionError' in str(error):
            errorMessage = 'ConnectionError'
        errorResponse = '<?xml version="1.0" standalone="yes"?><response><receipt><ReceiptId>null</ReceiptId><ReferenceNum>null</ReferenceNum><ResponseCode>null</ResponseCode><ISO>null</ISO><AuthCode>null</AuthCode><TransTime>null</TransTime><TransDate>null</TransDate><TransType>null</TransType><Complete>false</Complete><Message>' +\
            errorMessage + '</Message><TransAmount>null</TransAmount><CardType>null</CardType><TransID>null</TransID><TimedOut>null</TimedOut><BankTotals>null</BankTotals><Ticket>null</Ticket></receipt></response>'
        errorResponse = xmltodict.parse(errorResponse)
        return errorResponse


class mpgTransaction:
    def __init__(self):
        self._Request = ""
        self._tags = {}
        self._order = None

    def toXml(self):
        requestXml = "<" + self._Request + ">"
        # if type(self._order) == dict:
        #     for key,value in self._order.items():
        #         requestXml = requestXml + "<" + key + ">" + value + "</" + key + ">"
        for index, tag in enumerate(self._order):
            value = self._tags[tag]
            if isinstance(value, str):
                requestXml = requestXml + "<" + tag + ">" + value + "</" + tag + ">"
            elif isinstance(value, mpgTransaction):
                requestXml = requestXml + value.toXml()
            elif isinstance(value, list):
                for item in value:
                    requestXml = requestXml + item.toXml()
        requestXml = requestXml + "</" + self._Request + ">"
        # Amount missing in requestXml
        if '<amount>' not in requestXml:
            requestXml = requestXml.split("</order_id>")[0] + "</order_id><amount>" + str(
                self._tags['amount']) + "</amount>" + requestXml.split("</order_id>")[1]
        return requestXml

    def toXmlNew(self):
        requestXml = "<" + self._Request + ">"
        for index, tag in enumerate(self._order):
            value = self._tags[tag]
            if isinstance(value, str):
                requestXml = requestXml + "<" + tag + ">" + value + "</" + tag + ">"
            elif isinstance(value, mpgTransaction):
                requestXml = requestXml + value.toXml()
            elif isinstance(value, list):
                for item in value:
                    requestXml = requestXml + item.toXml()
        requestXml = requestXml + "</" + self._Request + ">"
        return requestXml


class Purchase(mpgTransaction):
    def __init__(self, order_id, amount, pan, expdate, crypt_type):
        self._Request = "purchase"
        self._tags = {"order_id": order_id, "amount": amount, "pan": pan, "expdate": expdate, "crypt_type": crypt_type,
                      "cvd": None, "avs": None, }
        self._order = ["order_id", "amount", "pan", "expdate", "crypt_type"]

    def setCustId(self, cust_id):
        self._tags["cust_id"] = cust_id
        self._order.append("cust_id")

    def setCvdInfo(self, cvdInfo):
        self._tags["cvd"] = cvdInfo
        self._order.append("cvd")

    def setAvsInfo(self, avsInfo):
        self._tags["avs"] = avsInfo
        self._order.append("avs")

    def setCustInfo(self, custInfo):
        self._tags["CustInfo"] = custInfo
        self._order.append("CustInfo")

    def setRecur(self, recur):
        self._tags["recur"] = recur
        self._order.append("recur")


class Preauth(mpgTransaction):
    def __init__(self, order_id, amount, pan, expdate, crypt_type):
        self._Request = "preauth"
        self._tags = {"order_id": order_id, "amount": amount, "pan": pan, "expdate": expdate, "crypt_type": crypt_type,
                      "cvd": None, "avs": None}
        self._order = ["order_id", "amount", "pan", "expdate", "crypt_type"]

    def setCustId(self, cust_id):
        self._tags["cust_id"] = cust_id
        self._order.append("cust_id")

    def setCvdInfo(self, cvdTemplate):
        self._tags["cvd_indicator"] = cvdTemplate['cvd_indicator']
        self._tags["cvd_value"] = cvdTemplate['cvd_value']

    def setAvsInfo(self, avsInfo):
        self._tags["avs"] = avsInfo
        self._order.append("avs")

    def setCustInfo(self, custInfo):
        self._tags["CustInfo"] = custInfo
        self._order.append("CustInfo")

    def setProcCountryCode(self, procCountryCode):
        self._tags["procCountryCode"] = procCountryCode
        self._order.append("procCountryCode")

    def setTestMode(self, testMode):
        self._tags["testMode"] = testMode
        self._order.append("testMode")

    def getData(self, store_id, api_token):
        self.__data = "<request>" + "<store_id>" + store_id + "</store_id>" + "<api_token>" + api_token + "</api_token>" + \
            self.getXml()
        self.__data = self.__data.split("</preauth>")[0] +\
            "<cvd_info>" +\
            "<cvd_indicator>" + self._tags["cvd_indicator"] + "</cvd_indicator>" +\
            "<cvd_value>" + self._tags["cvd_value"] + "</cvd_value>" +\
            "</cvd_info>" +\
            "</preauth>" +\
            self.__data.split("</preauth>")[1] +\
            "</request>"
        self.__data = "<?xml version='1.0' encoding='UTF-8'?>" + self.__data
        # print(self.__data)
        return self.__data

    def getResponse(self):
        return self.__Response

    def __GlobalError(self, error):
        errorNumber, errorMessage = error.reason
        errorResponse = '<?xml version="1.0" standalone="yes"?><response><receipt><ReceiptId>null</ReceiptId><ReferenceNum>null</ReferenceNum><ResponseCode>null</ResponseCode><ISO>null</ISO><AuthCode>null</AuthCode><TransTime>null</TransTime><TransDate>null</TransDate><TransType>null</TransType><Complete>false</Complete><Message>' + '[' + str(
            errorNumber) + '] ' + errorMessage + '</Message><TransAmount>null</TransAmount><CardType>null</CardType><TransID>null</TransID><TimedOut>null</TimedOut><BankTotals>null</BankTotals><Ticket>null</Ticket></receipt></response>'
        return errorResponse

    def getXml(self):
        request = self.toXmlNew() + "<procCountryCode>" + self._tags["procCountryCode"] + "</procCountryCode>" +\
            "<testMode>" + self._tags["testMode"] + "</testMode>"
        return request


class Correction(mpgTransaction):
    def __init__(self, order_id, txn_number, crypt_type):
        self._Request = "purchasecorrection"
        self._tags = {"order_id": order_id,
                      "txn_number": txn_number, "crypt_type": crypt_type}
        self._order = ["order_id", "txn_number", "crypt_type"]

    def setCorrectionAmount(self, amount):
        self._tags["amount"] = amount
        self._order.append("amount")

    def setStatusCheck(self, status_check):
        self._tags["status_check"] = status_check
        self._order.append("status_check")

    def setCustId(self, custid):
        self._tags["custid"] = custid
        self._order.append("custid")

    def setDynamicDescriptor(self, dynamic_descriptor):
        self._tags["dynamic_descriptor"] = dynamic_descriptor
        self._order.append("dynamic_descriptor")

    def setShipIndicator(self, ship_indicator):
        self._tags["ship_indicator"] = ship_indicator
        self._order.append("ship_indicator")


class PreauthCompletion(mpgTransaction):
    def __init__(self, order_id, comp_amount, txn_number, crypt_type):
        self._Request = "completion"
        self._tags = {"order_id": order_id, "comp_amount": comp_amount, "txn_number": txn_number,
                      "crypt_type": crypt_type}
        self._order = ["order_id", "comp_amount", "txn_number", "crypt_type"]

    def setShipIndicator(self, ship_indicator):
        self._tags["ship_indicator"] = ship_indicator
        self._order.append("ship_indicator")

    def toXml(self):
        return mpgTransaction.toXml(self)

    def getData(self, store_id, api_token):
        self.__data = "<request>" + "<store_id>" + store_id + "</store_id>" + "<api_token>" + api_token + "</api_token>" + \
            self.getXml() + "</request>"
        self.__data = "<?xml version='1.0' encoding='UTF-8'?>" + self.__data
        return self.__data

    def setProcCountryCode(self, procCountryCode):
        self._tags["procCountryCode"] = procCountryCode
        self._order.append("procCountryCode")

    def setTestMode(self, testMode):
        self._tags["testMode"] = testMode
        self._order.append("testMode")

    def getResponse(self):
        return self.__Response

    def __GlobalError(self, error):
        errorNumber, errorMessage = error.reason
        errorResponse = '<?xml version="1.0" standalone="yes"?><response><receipt><ReceiptId>null</ReceiptId><ReferenceNum>null</ReferenceNum><ResponseCode>null</ResponseCode><ISO>null</ISO><AuthCode>null</AuthCode><TransTime>null</TransTime><TransDate>null</TransDate><TransType>null</TransType><Complete>false</Complete><Message>' + '[' + str(
            errorNumber) + '] ' + errorMessage + '</Message><TransAmount>null</TransAmount><CardType>null</CardType><TransID>null</TransID><TimedOut>null</TimedOut><BankTotals>null</BankTotals><Ticket>null</Ticket></receipt></response>'
        return errorResponse

    def getXml(self):
        request = self.toXmlNew() + "<procCountryCode>" + self._tags["procCountryCode"] + "</procCountryCode>" +\
            "<testMode>" + self._tags["testMode"] + "</testMode>"
        return request


class Refund(mpgTransaction):
    def __init__(self, order_id, amount, crypt_type, txn_number):
        self._Request = "refund"
        self._tags = {"order_id": order_id, "amount": amount,
                      "txn_number": txn_number, "crypt_type": crypt_type}
        self._order = ["order_id", "amount", "txn_number", "crypt_type"]


    def setProcCountryCode(self, procCountryCode):
        self._tags["procCountryCode"] = procCountryCode
        self._order.append("procCountryCode")

    def setTestMode(self, testMode):
        self._tags["testMode"] = testMode
        self._order.append("testMode")


class IndRefund(mpgTransaction):
    def __init__(self, order_id, amount, pan, expdate, crypt_type):
        self._Request = "ind_refund"
        self._tags = {"order_id": order_id, "amount": amount,
                      "pan": pan, "expdate": expdate, "crypt_type": crypt_type}
        self._order = ["order_id", "amount", "pan", "expdate", "crypt_type"]

    def setCustId(self, cust_id):
        self._tags["cust_id"] = cust_id
        self._order.append("cust_id")


class iDebitPurchase(mpgTransaction):
    def __init__(self, order_id, amount, idebit_track2):
        self._Request = "idebit_purchase"
        self._tags = {"order_id": order_id,
                      "amount": amount, "idebit_track2": idebit_track2}
        self._order = ["order_id", "amount", "idebit_track2"]


class iDebitRefund(mpgTransaction):
    def __init__(self, order_id, amount, txn_number):
        self._Request = "idebit_refund"
        self._tags = {"order_id": order_id,
                      "amount": amount, "txn_number": txn_number}
        self._order = ["order_id", "amount", "txn_number"]


class OpenTotals(mpgTransaction):
    def __init__(self, ecr_number):
        self._Request = "opentotals"
        self._tags = {"ecr_number": ecr_number}
        self._order = ["ecr_number"]


class BatchClose(mpgTransaction):
    def __init__(self, ecr_number):
        self._Request = "batchclose"
        self._tags = {"ecr_number": ecr_number}
        self._order = ["ecr_number"]


class CavvPurchase(mpgTransaction):
    def __init__(self, order_id, amount, pan, expdate, cavv):
        self._Request = "cavv_purchase"
        self._tags = {"order_id": order_id, "amount": amount, "pan": pan, "expdate": expdate, "cavv": cavv, "cvd": None,
                      "avs": None}
        self._order = ["order_id", "amount", "pan", "expdate", "cavv"]

    def setCustId(self, cust_id):
        self._tags["cust_id"] = cust_id
        self._order.append("cust_id")

    def setCvdInfo(self, cvdInfo):
        self._tags["cvd"] = cvdInfo
        self._order.append("cvd")

    def setAvsInfo(self, avsInfo):
        self._tags["avs"] = avsInfo
        self._order.append("avs")

    def setCustInfo(self, custInfo):
        self._tags["CustInfo"] = custInfo
        self._order.append("CustInfo")


class CavvPreauth(mpgTransaction):
    def __init__(self, order_id, amount, pan, expdate, cavv):
        self._Request = "cavv_preauth"
        self._tags = {"order_id": order_id, "amount": amount, "pan": pan, "expdate": expdate, "cavv": cavv, "cvd": None,
                      "avs": None}
        self._order = ["order_id", "amount", "pan", "expdate", "cavv"]

    def setCustId(self, cust_id):
        self._tags["cust_id"] = cust_id
        self._order.append("cust_id")

    def setCvdInfo(self, cvdInfo):
        self._tags["cvd"] = cvdInfo
        self._order.append("cvd")

    def setAvsInfo(self, avsInfo):
        self._tags["avs"] = avsInfo
        self._order.append("avs")

    def setCustInfo(self, custInfo):
        self._tags["CustInfo"] = custInfo
        self._order.append("CustInfo")


class RecurUpdate(mpgTransaction):
    def __init__(self, order_id):
        self._Request = "recur_update"
        self._tags = {"order_id": order_id}
        self._order = ["order_id"]

    def setCustId(self, cust_id):
        self._tags["cust_id"] = cust_id
        self._order.append("cust_id")

    def setRecurAmount(self, recur_amount):
        self._tags["recur_amount"] = recur_amount
        self._order.append("recur_amount")

    def setPan(self, pan):
        self._tags["pan"] = pan
        self._order.append("pan")

    def setExpDate(self, expdate):
        self._tags["expdate"] = expdate
        self._order.append("expdate")

    def setAddNumRecurs(self, add_num_recurs):
        self._tags["add_num_recurs"] = add_num_recurs
        self._order.append("add_num_recurs")

    def setTotalNumRecurs(self, total_num_recurs):
        self._tags["total_num_recurs"] = total_num_recurs
        self._order.append("total_num_recurs")

    def setHold(self, hold):
        self._tags["hold"] = hold
        self._order.append("hold")

    def setTerminate(self, terminate):
        self._tags["terminate"] = terminate
        self._order.append("terminate")


class CvdInfo(mpgTransaction):
    def __init__(self, cvd_indicator, cvd_value):
        self._Request = "cvd_info"
        self._tags = {"cvd_indicator": cvd_indicator, "cvd_value": cvd_value}
        self._order = ["cvd_indicator", "cvd_value"]


class AvsInfo(mpgTransaction):
    def __init__(self, avs_street_number, avs_street_name, avs_zipcode):
        self._Request = "avs_info"
        self._tags = {"avs_street_number": avs_street_number, "avs_street_name": avs_street_name,
                      "avs_zipcode": avs_zipcode}
        self._order = ["avs_street_number", "avs_street_name", "avs_zipcode"]


class Recur(mpgTransaction):
    def __init__(self, recur_unit, start_now, start_date, num_recurs, period, recur_amount):
        self._Request = "recur"
        self._tags = {"recur_unit": recur_unit, "start_now": start_now, "start_date": start_date,
                      "num_recurs": num_recurs, "period": period, "recur_amount": recur_amount}
        self._order = ["recur_unit", "start_now", "start_date",
                       "num_recurs", "period", "recur_amount"]


class CustInfo(mpgTransaction):
    def __init__(self):
        self._Request = "cust_info"
        self._tags = {"billing": None, "shipping": None,
                      "email": "", "instructions": "", "item": []}
        self._order = []

    def setBilling(self, billingInfo):
        self._tags["billing"] = billingInfo
        self._order.append("billing")

    def setShipping(self, shippingInfo):
        self._tags["shipping"] = shippingInfo
        self._order.append("shipping")

    def setEmail(self, email):
        self._tags["email"] = email
        self._order.append("email")

    def setInstruction(self, instructions):
        self._tags["instructions"] = instructions
        self._order.append("instructions")

    def addItem(self, item):
        itm = self._tags["item"]
        itm.append(item)
        self._tags["item"] = itm
        if "item" not in self._order:
            self._order.append("item")


class BillingInfo(mpgTransaction):
    def __init__(self, first_name, last_name, company_name, address, city, province, postal_code, country, phone_number,
                 fax, tax1, tax2, tax3, shipping_cost):
        self._Request = "billing"
        self._tags = {}
        self._tags["first_name"] = first_name
        self._tags["last_name"] = last_name
        self._tags["company_name"] = company_name
        self._tags["address"] = address
        self._tags["city"] = city
        self._tags["province"] = province
        self._tags["postal_code"] = postal_code
        self._tags["country"] = country
        self._tags["phone_number"] = phone_number
        self._tags["fax"] = fax
        self._tags["tax1"] = tax1
        self._tags["tax2"] = tax2
        self._tags["tax3"] = tax3
        self._tags["shipping_cost"] = shipping_cost
        self._order = ["first_name", "last_name", "company_name", "address", "city", "province", "postal_code",
                       "country", "phone_number", "fax", "tax1", "tax2", "tax3", "shipping_cost"]

    def setFirstName(self, first_name):
        self._tags["first_name"] = first_name

    def setLastName(self, last_name):
        self._tags["last_name"] = last_name

    def setCompanyName(self, company_name):
        self._tags["company_name"] = company_name

    def setAddress(self, address):
        self._tags["address"] = address

    def setCity(self, city):
        self._tags["city"] = city

    def setProvince(self, province):
        self._tags["province"] = province

    def setPostalCode(self, postal_code):
        self._tags["postal_code"] = postal_code

    def setCountry(self, country):
        self._tags["country"] = country

    def setPhoneNumber(self, phone_number):
        self._tags["phone_number"] = phone_number

    def setFax(self, fax):
        self._tags["fax"] = fax

    def setTax1(self, tax1):
        self._tags["tax1"] = tax1

    def setTax2(self, tax2):
        self._tags["tax2"] = tax2

    def setTax3(self, tax3):
        self._tags["tax3"] = tax3

    def setShippingCost(self, shipping_cost):
        self._tags["shipping_cost"] = shipping_cost


class ShippingInfo(mpgTransaction):
    def __init__(self, first_name, last_name, company_name, address, city, province, postal_code, country, phone_number,
                 fax, tax1, tax2, tax3, shipping_cost):
        self._Request = "shipping"
        self._tags = {}
        self._tags["first_name"] = first_name
        self._tags["last_name"] = last_name
        self._tags["company_name"] = company_name
        self._tags["address"] = address
        self._tags["city"] = city
        self._tags["province"] = province
        self._tags["postal_code"] = postal_code
        self._tags["country"] = country
        self._tags["phone_number"] = phone_number
        self._tags["fax"] = fax
        self._tags["tax1"] = tax1
        self._tags["tax2"] = tax2
        self._tags["tax3"] = tax3
        self._tags["shipping_cost"] = shipping_cost
        self._order = ["first_name", "last_name", "company_name", "address", "city", "province", "postal_code",
                       "country", "phone_number", "fax", "tax1", "tax2", "tax3", "shipping_cost"]

    def setFirstName(self, first_name):
        self._tags["first_name"] = first_name

    def setLastName(self, last_name):
        self._tags["last_name"] = last_name

    def setCompanyName(self, company_name):
        self._tags["company_name"] = company_name

    def setAddress(self, address):
        self._tags["address"] = address

    def setCity(self, city):
        self._tags["city"] = city

    def setProvince(self, province):
        self._tags["province"] = province

    def setPostalCode(self, postal_code):
        self._tags["postal_code"] = postal_code

    def setCountry(self, country):
        self._tags["country"] = country

    def setPhoneNumber(self, phone_number):
        self._tags["phone_number"] = phone_number

    def setFax(self, fax):
        self._tags["fax"] = fax

    def setTax1(self, tax1):
        self._tags["tax1"] = tax1

    def setTax2(self, tax2):
        self._tags["tax2"] = tax2

    def setTax3(self, tax3):
        self._tags["tax3"] = tax3

    def setShippingCost(self, shipping_cost):
        self._tags["shipping_cost"] = shipping_cost


class Item(mpgTransaction):
    def __init__(self, itemName, quantity, product_code, extended_amount):
        self._Request = "item"
        self._tags = {"name": itemName, "quantity": quantity, "product_code": product_code,
                      "extended_amount": extended_amount}
        self._order = ["name", "quantity", "product_code", "extended_amount"]

    def setitemName(self, itemName):
        self._tags["itemName"] = itemName

    def setquantity(self, quantity):
        self._tags["quantity"] = quantity

    def setproduct_code(self, product_code):
        self._tags["product_code"] = product_code

    def setextended_amount(self, extended_amount):
        self._tags["extended_amount"] = extended_amount


# ---------------------------#Vault Temporary Token Add-------------------------------------
class mpgRequest(mpgTransaction):
    def __init__(self, type_of, pan, expdate, duration, crypt_type):
        self._Request = type_of
        self._tags = {"type_of": type_of, "pan": pan, "expdate": expdate,
                      "duration": duration, "crypt_type": crypt_type}
        self._order = ["pan", "expdate", "duration", "crypt_type"]
        self.__url = {}

    def setProcCountryCode(self, procCountryCode):
        self._tags["procCountryCode"] = procCountryCode
        self._order.append("procCountryCode")

    def setTestMode(self, testMode):
        self._tags["testMode"] = testMode
        self._order.append("testMode")

    def getXml(self):
        request = self.toXmlNew() + "<procCountryCode>" + self._tags["procCountryCode"] + "</procCountryCode>" +\
            "<testMode>" + self._tags["testMode"] + "</testMode>"
        return request

    def getData(self, store_id, api_token):
        self.__data = "<request>" + "<store_id>" + store_id + "</store_id>" + "<api_token>" + api_token + "</api_token>" + \
            self.getXml() + "</request>"
        self.__data = "<?xml version='1.0' encoding='UTF-8'?>" + self.__data
        return self.__data

    def getResponse(self):
        return self.__Response

class PurchaseVault(mpgTransaction):
    """Purchase with Vault"""
    def __init__(self, type_of, data_key, order_id, cust_id, amount, pan, expdate, crypt_type, dynamic_descriptor):
        self._Request = 'res_purchase_cc'  # type_of#res_purchase_cc
        self._tags = {"type_of": type_of, "data_key": data_key, "order_id": order_id, "cust_id": cust_id, "amount": amount,
                      "pan": pan, "expdate": expdate, "crypt_type": crypt_type, "dynamic_descriptor": dynamic_descriptor, }
        self._order = ["data_key", "order_id", "cust_id", "amount",
                       "pan", "expdate", "crypt_type", "dynamic_descriptor"]
        self.__url = {}

    def setProcCountryCode(self, procCountryCode):
        self._tags["procCountryCode"] = procCountryCode
        self._order.append("procCountryCode")

    def setTestMode(self, testMode):
        self._tags["testMode"] = testMode
        self._order.append("testMode")

    def getXml(self):
        request = self.toXml().split("</res_purchase_cc>")[0] +\
            "<cvd_info>" + "<cvd_indicator>" + self._tags["cvd_indicator"] + "</cvd_indicator>" +\
            "<cvd_value>" + self._tags["cvd_value"] + "</cvd_value>" + "</cvd_info>" + "</res_purchase_cc>" +\
            self.toXml().split("</res_purchase_cc>")[1] +\
            "<procCountryCode>" + self._tags["procCountryCode"] + "</procCountryCode>" +\
            "<testMode>" + self._tags["testMode"] + "</testMode>"

        return request

    def getData(self, store_id, api_token):
        self.__data = "<request>" + "<store_id>" + store_id + "</store_id>" + "<api_token>" + api_token + "</api_token>" + \
            self.getXml() + "</request>"
        self.__data = "<?xml version='1.0' encoding='UTF-8'?>" + self.__data
        return self.__data

    def setCvdInfo(self, cvdTemplate):
        self._tags["cvd_indicator"] = cvdTemplate['cvd_indicator']
        self._tags["cvd_value"] = cvdTemplate['cvd_value']

    def getResponse(self):
        return self.__Response

    def __GlobalError(self, error):
        errorNumber, errorMessage = error.reason
        errorResponse = '<?xml version="1.0" standalone="yes"?><response><receipt><ReceiptId>null</ReceiptId><ReferenceNum>null</ReferenceNum><ResponseCode>null</ResponseCode><ISO>null</ISO><AuthCode>null</AuthCode><TransTime>null</TransTime><TransDate>null</TransDate><TransType>null</TransType><Complete>false</Complete><Message>' + '[' + str(
            errorNumber) + '] ' + errorMessage + '</Message><TransAmount>null</TransAmount><CardType>null</CardType><TransID>null</TransID><TimedOut>null</TimedOut><BankTotals>null</BankTotals><Ticket>null</Ticket></receipt></response>'
        return errorResponse


class CcVerification(mpgTransaction):
    """Card Verification"""
    def __init__(self, type_of, order_id, pan, expdate, crypt_type):
        self._Request = type_of  # card_verification
        self._tags = {"type_of": type_of, "order_id": order_id,
                      "pan": pan, "expdate": expdate, "crypt_type": crypt_type}
        self._order = ["order_id", "pan", "expdate", "crypt_type"]
        self.__url = {}

    def setProcCountryCode(self, procCountryCode):
        self._tags["procCountryCode"] = procCountryCode
        self._order.append("procCountryCode")

    def setTestMode(self, testMode):
        self._tags["testMode"] = testMode
        self._order.append("testMode")

    def setCvdInfo(self, cvdTemplate):
        self._tags["cvd_indicator"] = cvdTemplate['cvd_indicator']
        self._tags["cvd_value"] = cvdTemplate['cvd_value']

    def getXml(self):
        request = self.toXmlNew()
        # + "<procCountryCode>" + self._tags["procCountryCode"] + "</procCountryCode>" +\
        #      "<testMode>" + self._tags["testMode"] + "</testMode>"
        return request

    def getData(self, store_id, api_token):
        self.__data = "<request>" + "<store_id>" + store_id + "</store_id>" + "<api_token>" + api_token + "</api_token>" + \
            self.getXml() + \
            "<cvd_info>" +\
            "<cvd_indicator>" + self._tags["cvd_indicator"] + "</cvd_indicator>" +\
            "<cvd_value>" + self._tags["cvd_value"] + "</cvd_value>" +\
            "</cvd_info>" +\
            "</request>"
        self.__data = "<?xml version='1.0' encoding='UTF-8'?>" + self.__data
        return self.__data


    def getResponse(self):
        return self.__Response

    def __GlobalError(self, error):
        errorNumber, errorMessage = error.reason
        errorResponse = '<?xml version="1.0" standalone="yes"?><response><receipt><ReceiptId>null</ReceiptId><ReferenceNum>null</ReferenceNum><ResponseCode>null</ResponseCode><ISO>null</ISO><AuthCode>null</AuthCode><TransTime>null</TransTime><TransDate>null</TransDate><TransType>null</TransType><Complete>false</Complete><Message>' + '[' + str(
            errorNumber) + '] ' + errorMessage + '</Message><TransAmount>null</TransAmount><CardType>null</CardType><TransID>null</TransID><TimedOut>null</TimedOut><BankTotals>null</BankTotals><Ticket>null</Ticket></receipt></response>'
        return errorResponse


class VaultAddCc(mpgTransaction):
    """VaultAddCc"""
    def __init__(self, type_of, cvd_info, cof_info):
        self._Request = type_of
        self._tags = {"type_of": type_of,
                      "cvd_info": cvd_info, "cof_info": cof_info}
        self._order = ["type_of", "cvd_info", "cof_info"]
        self.__url = {}

    def setProcCountryCode(self, procCountryCode):
        self._tags["procCountryCode"] = procCountryCode
        self._order.append("procCountryCode")

    def setTestMode(self, testMode):
        self._tags["testMode"] = testMode
        self._order.append("testMode")

    def setCvdInfo(self, cvdTemplate):
        self._tags["cvd_indicator"] = cvdTemplate['cvd_indicator']
        self._tags["cvd_value"] = cvdTemplate['cvd_value']

    def setIssuerId(self, issuer_id):
        self._tags["issuer_id"] = issuer_id

    def getXml(self):
        request = self.toXmlNew()
        return request

    def getData(self, store_id, api_token):
        self.__data = "<request>" +\
            "<store_id>" + store_id + "</store_id>" +\
            "<api_token>" + api_token + "</api_token>" +\
            "<res_add_cc>" +\
            "<cvd_info>" +\
            "<cust_id>" + self._tags["cvd_info"]["cust_id"] + "</cust_id>" +\
            "<phone>" + self._tags["cvd_info"]["phone"] + "</phone>" +\
            "<email>" + self._tags["cvd_info"]["email"] + "</email>" +\
            "<note>" + self._tags["cvd_info"]["note"] + "</note>" +\
            "<pan>" + self._tags["cvd_info"]["pan"] + "</pan>" +\
            "<expdate>" + self._tags["cvd_info"]["expdate"] + "</expdate>" +\
            "<crypt_type>" + self._tags["cvd_info"]["expdate"] + "</crypt_type>" +\
            "</cvd_info>" +\
            "<cof_info>" +\
            "<issuer_id>" + self._tags["issuer_id"] + "</issuer_id>" +\
            "</cof_info>" +\
            "</res_add_cc>" +\
            "<procCountryCode>" + self._tags["procCountryCode"] + "</procCountryCode>" +\
            "<testMode>" + self._tags["testMode"] + "</testMode>" +\
            "</request>"
        self.__data = "<?xml version='1.0' encoding='UTF-8'?>" + self.__data
        return self.__data

    def getResponse(self):
        return self.__Response

    def __GlobalError(self, error):
        errorNumber, errorMessage = error.reason
        errorResponse = '<?xml version="1.0" standalone="yes"?><response><receipt><ReceiptId>null</ReceiptId><ReferenceNum>null</ReferenceNum><ResponseCode>null</ResponseCode><ISO>null</ISO><AuthCode>null</AuthCode><TransTime>null</TransTime><TransDate>null</TransDate><TransType>null</TransType><Complete>false</Complete><Message>' + '[' + str(
            errorNumber) + '] ' + errorMessage + '</Message><TransAmount>null</TransAmount><CardType>null</CardType><TransID>null</TransID><TimedOut>null</TimedOut><BankTotals>null</BankTotals><Ticket>null</Ticket></receipt></response>'
        return errorResponse


class PurchaseRecurCc(mpgTransaction):
    """Purchase with Vault and Recurring Billing"""
    def __init__(self, type_of, cvd_info, cof_info, txnArray, recurArray):
        self._Request = type_of
        self._tags = {"type_of": type_of, "cvd_info": cvd_info,
                      "cof_info": cof_info, "txnArray": txnArray, "recur": recurArray}
        self._order = ["type_of", "cvd_info", "cof_info", "txnArray"]
        self.__url = {}

    def setTranx(self, txnArray):
        self._tags["txnArray"]['type'] = txnArray['type']
        self._tags["txnArray"]['data_key'] = txnArray['data_key']
        self._tags["txnArray"]['order_id'] = txnArray['order_id']
        self._tags["txnArray"]['cust_id'] = txnArray['cust_id']
        self._tags["txnArray"]['amount'] = txnArray['amount']
        self._tags["txnArray"]['crypt_type'] = txnArray['crypt_type']

    def setProcCountryCode(self, procCountryCode):
        self._tags["procCountryCode"] = procCountryCode
        self._order.append("procCountryCode")

    def setTestMode(self, testMode):
        self._tags["testMode"] = testMode
        self._order.append("testMode")

    def setCvdInfo(self, cvdTemplate):
        self._tags["cvd_info"]["cvd_indicator"] = cvdTemplate['cvd_indicator']
        self._tags["cvd_info"]["cvd_value"] = cvdTemplate['cvd_value']

    def setIssuerId(self, issuer_id):
        self._tags["issuer_id"] = issuer_id

    def getXml(self):
        request = self.toXmlNew()
        return request

    def getRecur(self, recurArray):
        self._tags['recur']["recur_unit"] = recurArray['recur_unit']
        self._tags['recur']["start_now"] = recurArray['start_now']
        self._tags['recur']["start_date"] = recurArray['start_date']
        self._tags['recur']["num_recurs"] = recurArray['num_recurs']
        self._tags['recur']["period"] = recurArray['period']
        self._tags['recur']["recur_amount"] = recurArray['recur_amount']
        self._order.append("recur")

    def getData(self, store_id, api_token):
        self.__data = "<request>" +\
            "<store_id>" + str(store_id) + "</store_id>" +\
            "<api_token>" + str(api_token) + "</api_token>" +\
            "<res_purchase_cc>" +\
            "<data_key>" + str(self._tags["txnArray"]['data_key']) + "</data_key>" +\
            "<order_id>" + str(self._tags["txnArray"]['order_id']) + "</order_id>" +\
            "<amount>" + str(self._tags["txnArray"]['amount']) + "</amount>" +\
            "<cust_id>" + str(self._tags["txnArray"]['cust_id']) + "</cust_id>" +\
            "<crypt_type>" + \
            str(self._tags["txnArray"]['crypt_type']) + "</crypt_type>"
        if "cvd_indicator" in self._tags["cvd_info"] and "cvd_value" in self._tags["cvd_info"]:
            self.__data += "<cvd_info>" +\
                "<cvd_indicator>" + str(self._tags["cvd_indicator"]) + "</cvd_indicator>" +\
                "<cvd_value>" + str(self._tags["cvd_value"]) + "</cvd_value>" +\
                "</cvd_info>"
        self.__data += "<recur>" +\
            "<recur_unit>" + str(self._tags['recur']["recur_unit"]) + "</recur_unit>" +\
            "<start_date>" + str(self._tags['recur']["start_date"]) + "</start_date>" +\
            "<num_recurs>" + str(self._tags['recur']["num_recurs"]) + "</num_recurs>" +\
            "<start_now>" + str(self._tags['recur']["start_now"]) + "</start_now>" +\
            "<period>" + str(self._tags['recur']["period"]) + "</period>" +\
            "<recur_amount>" + str(self._tags['recur']["recur_amount"]) + "</recur_amount>" +\
            "</recur>" +\
            "</res_purchase_cc>" +\
            "<procCountryCode>" + str(self._tags["procCountryCode"]) + "</procCountryCode>" +\
            "<testMode>" + str(self._tags["testMode"]) + "</testMode>" +\
            "</request>"
        self.__data = "<?xml version='1.0' encoding='UTF-8'?>" + self.__data
        return self.__data

    def getResponse(self):
        return self.__Response

    def __GlobalError(self, error):
        errorNumber, errorMessage = error.reason
        errorResponse = '<?xml version="1.0" standalone="yes"?><response><receipt><ReceiptId>null</ReceiptId><ReferenceNum>null</ReferenceNum><ResponseCode>null</ResponseCode><ISO>null</ISO><AuthCode>null</AuthCode><TransTime>null</TransTime><TransDate>null</TransDate><TransType>null</TransType><Complete>false</Complete><Message>' + '[' + str(
            errorNumber) + '] ' + errorMessage + '</Message><TransAmount>null</TransAmount><CardType>null</CardType><TransID>null</TransID><TimedOut>null</TimedOut><BankTotals>null</BankTotals><Ticket>null</Ticket></receipt></response>'
        return errorResponse



class VaultDeleteCc(mpgTransaction):
    """Vault Delete Credit Card"""
    def __init__(self, type_of, txnArray):
        self._Request = type_of
        self._tags = {"type_of": type_of, "txnArray": txnArray}
        self._order = ["type_of", "txnArray"]
        self.__url = {}

    def setTranx(self, txnArray):
        self._tags["txnArray"]['type'] = txnArray['type']
        self._tags["txnArray"]['data_key'] = txnArray['data_key']

    def setProcCountryCode(self, procCountryCode):
        self._tags["procCountryCode"] = procCountryCode
        self._order.append("procCountryCode")

    def setTestMode(self, testMode):
        self._tags["testMode"] = testMode
        self._order.append("testMode")

    def getXml(self):
        request = self.toXmlNew()
        return request

    def getData(self, store_id, api_token):
        self.__data = "<request>" +\
            "<store_id>" + str(store_id) + "</store_id>" +\
            "<api_token>" + str(api_token) + "</api_token>" +\
            "<res_delete>" +\
            "<data_key>" + str(self._tags["txnArray"]['data_key']) + "</data_key>" +\
            "</res_delete>" +\
            "<procCountryCode>" + str(self._tags["procCountryCode"]) + "</procCountryCode>" +\
            "<testMode>" + str(self._tags["testMode"]) + "</testMode>" +\
            "</request>"
        self.__data = "<?xml version='1.0' encoding='UTF-8'?>" + self.__data
        return self.__data

    def getResponse(self):
        return self.__Response

    def __GlobalError(self, error):
        errorNumber, errorMessage = error.reason
        errorResponse = '<?xml version="1.0" standalone="yes"?><response><receipt><ReceiptId>null</ReceiptId><ReferenceNum>null</ReferenceNum><ResponseCode>null</ResponseCode><ISO>null</ISO><AuthCode>null</AuthCode><TransTime>null</TransTime><TransDate>null</TransDate><TransType>null</TransType><Complete>false</Complete><Message>' + '[' + str(
            errorNumber) + '] ' + errorMessage + '</Message><TransAmount>null</TransAmount><CardType>null</CardType><TransID>null</TransID><TimedOut>null</TimedOut><BankTotals>null</BankTotals><Ticket>null</Ticket></receipt></response>'
        return errorResponse
