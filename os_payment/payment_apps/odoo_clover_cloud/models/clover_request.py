# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import requests
import json
import random
import string

import logging

_logger = logging.getLogger(__name__)


class CloverRequest():
    """ Low-level object intended to interface Odoo recordsets with Clover Node.js API,
        through appropriate REST requests """

    def __init__(self, debug_logger, values):
        self.debug_logger = debug_logger
        self.clover_jwt_token = values['cloverJwtToken']
        self.clover_config_id = values['configId']
        self.clover_server_url = values['cloverServerUrl']
        self.x_pos_id = values['posId']
        self.x_clover_device_id = values['deviceId']

    def action_send_clover_payment(self, values):
        # STEPS:
        # 1. Welcome Request
        # 2. Payment Request
        # 3. Receipt Option
        # 4. Receipt
        clover_payment = {'success': False}

        try:
            response1 = self.send_welcome_message(values)

            if response1.get('status_code') == 200:

                if values.get('move_type') == 'out_refund':
                    values['isFullRefund'] = False
                    values['paymentId'] = values.get('clover_payment_id')

                    if values.get('idempotencyId'):
                        if len(values.get('idempotencyId')) > 50:
                            values['idempotencyId'] = values['idempotencyId'].replace(' ', '')[0:49]
                    if values.get('externalPaymentId'):
                        if len(values.get('externalPaymentId')) > 50:
                            values['externalPaymentId'] = values['externalPaymentId'].replace(' ', '')[0:49]
                    response2 = self.send_refund_request(values)
                else:
                    response2 = self.send_payment_request(values)

                response_data = response2

                if response2.get('status_code') == 200:
                    if values.get('move_id'):
                        context = dict(values.get('move_id').env.context)
                        context.update({'cloverResponse': response2.get('response')})
                        values.get('move_id').clover_last_response = json.dumps(context)
                        if values.get('move_id').move_type in ['in_invoice', 'out_invoice']:
                            values['paymentId'] = response2.get('response', {}).get('data', {}).get('payment', {}).get(
                                'id') or response2.get('paymentId')
                        else:
                            values['paymentId'] = response2.get('response', {}).get('data', {}).get('refund', {}).get(
                                'id')

                    response3 = self.send_show_receipt_option(values)

                    if response3.get('status_code') == 200:
                        no_receipt = False

                        if response3.get('response', {}).get('data', {}).get('deliveryOption'):
                            deliveryOption = response3.get('response', {}).get('data', {}).get('deliveryOption')
                            deliveryOption = deliveryOption[0]

                            if deliveryOption['method'] == "EMAIL":
                                values['method'] = "EMAIL"
                                values['additionalData'] = deliveryOption.get('email') or values.get('email', '')
                            elif deliveryOption['method'] == "PRINT":
                                values['method'] = "PRINT"
                            elif deliveryOption['method'] == "SMS":
                                values['method'] = "SMS"
                                values['additionalData'] = deliveryOption.get('phone') or values.get('phone', '')
                            elif deliveryOption['method'] == "NO_RECEIPT":
                                values['method'] = "NO_RECEIPT"
                                no_receipt = True

                        if not no_receipt:
                            response4 = self.send_payment_receipt(values)
                        else:
                            response4 = {'status_code': 200}

                        if response4.get('status_code') == 200:
                            response5 = self.send_thankyou_message(values)

                            if response5.get('status_code') == 200:
                                clover_payment = {'success': True, "data": response_data}
                            else:
                                clover_payment = {'success': False, 'err': response5.get('description')}

                        else:
                            clover_payment = {'success': False, 'err': response4.get('description')}
                            values.update({
                                "err": response4.get('description')
                            })
                            self.send_display_message(values)

                    else:
                        clover_payment = {'success': False, 'err': response3.get('description')}
                        values.update({
                            "err": response3.get('description')
                        })
                        self.send_display_message(values)

                else:
                    clover_payment = {'success': False, 'err': response2.get('description')}
                    values.update({
                        "err": response2.get('description')
                    })
                    self.send_display_message(values)

            else:
                clover_payment = {'success': False, 'err': response1.get('description')}
                values.update({
                    "err": response1.get('description')
                })
                self.send_display_message(values)

        except Exception as e:
            clover_payment.update({'success': False, 'err': str(e.args)})

        _logger.info("clover_payment ===>>>{}".format(clover_payment))
        return clover_payment

    def get_headers(self, values):
        return {
            "Authorization": "Bearer %s" % (self.clover_jwt_token),
            "Content-Type": "application/json",
            "X-Clover-Device-Id": self.x_clover_device_id,
            "X-POS-Id": self.x_pos_id,
        }

    def get_idempotency_id(self, values):
        idempotencyId = values.get('idempotencyId') + ''.join(random.choices(string.ascii_lowercase, k=5))
        if len(idempotencyId) > 50:
            idempotencyId = idempotencyId.replace(' ', '')[0:49]

        print("idempotencyId ===>>>{}".format(idempotencyId))
        return idempotencyId.replace(" ", "")

    # REST API METHODS
    # 1. Device Ping
    def send_device_ping(self, values):
        _logger.info("send_device_ping ===>>>")
        _logger.info("values ===>>>{}".format(values))

        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            return {'success': False, 'description': 'Config id or JWT Token or Server URL is missing'}

        URL = '%s/api/v1/devices/connect/' % (self.clover_server_url)
        headers = self.get_headers(values)
        payload = {
            "configId": values.get('configId'),
            "deviceId": values.get('deviceId'),
            "posId": values.get('posId'),
        }

        response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))

        if self.debug_logger:
            _logger.info("send_device_status")
            _logger.info("URL ===>>>>{}".format(URL))
            _logger.info("headers ===>>>>{}".format(headers))
            _logger.info("payload ===>>>>{}".format(payload))
            _logger.info("response===>>>>" + str(response.text))

        if response.status_code == 200:
            return {
                'status_code': response.status_code,
                'success': True,
                'description': 'Device Ping sent Successfully',
                'action': 'device_ping',
            }
        else:
            return {
                'status_code': response.status_code,
                'success': False,
                'description': 'Device Ping sent failed!',
                'action': 'device_ping',
            }

    # 2. Device Status
    def send_device_status(self, values):
        _logger.info("send_device_status ===>>>")
        _logger.info("values ===>>>{}".format(values))

        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            return {'success': False, 'description': 'Config id or JWT Token or Server URL is missing'}

        URL = '%s/api/v1/devices/status/' % (self.clover_server_url)
        headers = self.get_headers(values)
        payload = {
            "configId": values.get('configId'),
            "deviceId": values.get('deviceId'),
            "posId": values.get('posId'),
        }

        response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))

        if self.debug_logger:
            _logger.info("send_device_status")
            _logger.info("URL ===>>>>{}".format(URL))
            _logger.info("headers ===>>>>{}".format(headers))
            _logger.info("payload ===>>>>{}".format(payload))
            _logger.info("response===>>>>" + str(response.text))

        if response.status_code == 200:
            return {
                'status_code': response.status_code,
                'success': True,
                'description': 'Device Status sent Successfully',
                'action': 'device_ping',
            }
        else:
            return {
                'status_code': response.status_code,
                'success': False,
                'description': response.json().get('message') or 'Device Status sent failed!',
                'action': 'device_ping',
            }

    # 3. Payment
    def send_payment_request(self, values):
        _logger.info("send_payment_request ===>>>")
        _logger.info("values ===>>>{}".format(values))

        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            return {'success': False, 'description': 'Config id or JWT Token or Server URL is missing'}

        URL = '%s/api/v1/make/payment/' % (self.clover_server_url)
        headers = self.get_headers(values)
        payload = {
            "configId": values.get('configId'),
            "deviceId": values.get('deviceId'),
            "posId": values.get('posId'),
            "idempotencyId": values.get('idempotencyId'),
            "amount": int(round(float(values.get('amount')), 0)),
            "externalPaymentId": values.get('externalPaymentId'),
        }

        response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))

        if self.debug_logger:
            _logger.info("send_payment_request")
            _logger.info("URL ===>>>>{}".format(URL))
            _logger.info("headers ===>>>>{}".format(headers))
            _logger.info("payload ===>>>>{}".format(payload))
            _logger.info("response===>>>>" + str(response.text))
        # response.status_code = 200
        if response.status_code == 200:
            res_json = response.json()
            # res_json = {"data": {
            #     "payment": {
            #         "amount": 20.00,
            #         "cardTransaction": {
            #             "authCode": "572535",
            #             "cardType": "AMEX",
            #             "entryType": "EMV_CONTACTLESS",
            #             "extra": {
            #                 "applicationLabel": "414D45524943414E2045585052455353",
            #                 "authorizingNetworkName": "AMEX",
            #                 "cvmResult": "NO_CVM_REQUIRED",
            #                 "applicationIdentifier": "A000000025010402"
            #             },
            #             "first6": "374245",
            #             "last4": "1003",
            #             "referenceId": "217100500665",
            #             "state": "CLOSED",
            #             "token": "903915660561003",
            #             "transactionNo": "000136",
            #             "type": "AUTH",
            #             "vaultedCard": {
            #                 "expirationDate": "1224",
            #                 "first6": "374245",
            #                 "last4": "1003",
            #                 "token": "903915660561003"
            #             }
            #         },
            #         "createdTime": 1655734891583,
            #         "employee": {
            #             "id": "C977Z522P1ETM"
            #         },
            #         "externalPaymentId": "96-837-395-5537",
            #         "id": "4W5RNXTK5G680-1",
            #         "offline": False,
            #         "order": {
            #             "id": "MKWX1BBQNJBTM"
            #         },
            #         "result": "SUCCESS",
            #         "taxAmount": 0,
            #         "tipAmount": 0
            #     }
            # }
            # }

            payment_id = res_json.get('data', {}).get('payment', {}).get('id', '')
            order_id = res_json.get('data', {}).get('payment', {}).get('order', {}).get('id')
            values.update({
                'paymetId': payment_id,
                'order_id': order_id
            })
            return {
                'status_code': response.status_code,
                'success': True,
                'description': 'Payment Message sent Successfully',
                'action': 'payment',
                'response': res_json,
                'paymetId': payment_id,
                'order_id': order_id,
            }
        else:
            return {
                'status_code': response.status_code,
                'success': False,
                'description': response.json().get('message').get('message') or 'Payment Message send failed!',
                'action': 'payment',
                'response': response.json(),
            }

    # 4. Refund
    def send_refund_request(self, values):
        _logger.info("send_refund_request ===>>>")
        _logger.info("values ===>>>{}".format(values))

        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            return {'success': False, 'description': 'Config id or JWT Token or Server URL is missing'}

        URL = '%s/api/v1/make/refund/' % (self.clover_server_url)
        headers = self.get_headers(values)
        payload = {
            "configId": values.get('configId'),
            "deviceId": values.get('deviceId'),
            "posId": values.get('posId'),
            "idempotencyId": self.get_idempotency_id(values),  # values.get('idempotencyId'),
            "amount": int(round(abs(float(values.get('amount'))), 0)),
            "isFullRefund": values.get('isFullRefund'),
            "externalPaymentId": values.get('externalPaymentId'),
            "paymentId": values.get('clover_payment_id'),
        }

        response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))

        if self.debug_logger:
            _logger.info("send_refund_request")
            _logger.info("URL ===>>>>{}".format(URL))
            _logger.info("headers ===>>>>{}".format(headers))
            _logger.info("payload ===>>>>{}".format(payload))
            _logger.info("response===>>>>" + str(response.text))

        if response.status_code == 200:
            return {
                'status_code': response.status_code,
                'success': True,
                'description': 'Refund Message sent Successfully',
                'action': 'payment',
                'response': response.json(),
                'paymentId': response.json().get('data', {}).get('refund').get('id'),
            }
        else:
            return {
                'status_code': response.status_code,
                'success': False,
                'description': response.json().get('message') or 'Refund  process failed!',
                'action': 'payment',
                'response': response.json(),
            }

    # 5. Payment Receipt
    def send_payment_receipt(self, values):
        _logger.info("send_payment_receipt ===>>>")
        _logger.info("values ===>>>{}".format(values))

        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            return {'success': False, 'description': 'Config id or JWT Token or Server URL is missing'}

        URL = '%s/api/v1/payments/%s/receipt/' % (self.clover_server_url, values.get('paymetId'))
        headers = self.get_headers(values)
        payload = {
            "configId": values.get('configId'),
            "deviceId": values.get('deviceId'),
            "posId": values.get('posId'),
            "idempotencyId": self.get_idempotency_id(values),
            "method": values.get('method'),
        }
        if values.get('email'):
            values['email'] = values.get('email', '')
        if values.get('phone'):
            values['phone'] = values.get('phone', '')

        response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))
        response.status_code = 200
        if self.debug_logger:
            _logger.info("send_payment_receipt")
            _logger.info("URL ===>>>>{}".format(URL))
            _logger.info("headers ===>>>>{}".format(headers))
            _logger.info("payload ===>>>>{}".format(payload))
            _logger.info("response===>>>>" + str(response.text))

        if response.status_code == 200:
            return {
                'status_code': response.status_code,
                'success': True,
                'description': 'Payment Receipt Message sent Successfully',
                'action': 'payment_receipt',
            }
        else:
            return {
                'status_code': response.status_code,
                'success': False,
                'description': response.json().get('message') or 'Payment Receipt Message send failed!',
                'action': 'payment_receipt',
            }

    # 6. Refund Receipt
    def send_refund_receipt(self, values):
        _logger.info("send_refund_receipt ===>>>")
        _logger.info("values ===>>>{}".format(values))

        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            return {'success': False, 'description': 'Config id or JWT Token or Server URL is missing'}

        URL = '%s/api/v1/refunds/%s/receipt/' % (self.clover_server_url, values.get('refundId'))
        headers = self.get_headers(values)


        payload = {
            "configId": values.get('configId'),
            "deviceId": values.get('deviceId'),
            "posId": values.get('posId'),
            "idempotencyId": self.get_idempotency_id(values),  # values.get('idempotencyId'),
            "method": values.get('method'),
            "email": values.get('email', ''),
            "phone": values.get('phone', ''),
        }

        response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))
        response.status_code = 200
        if self.debug_logger:
            _logger.info("send_refund_receipt")
            _logger.info("URL ===>>>>{}".format(URL))
            _logger.info("headers ===>>>>{}".format(headers))
            _logger.info("payload ===>>>>{}".format(payload))
            _logger.info("response===>>>>" + str(response.text))

        if response.status_code == 200:
            return {
                'status_code': response.status_code,
                'success': True,
                'description': 'Payment Receipt Message sent Successfully',
                'action': 'payment_receipt',
            }
        else:
            return {
                'status_code': response.status_code,
                'success': False,
                'description': response.json().get('message') or 'Payment Receipt Message send failed!',
                'action': 'payment_receipt',
            }

    # 7. Show Receipt Options
    def send_show_receipt_option(self, values):
        _logger.info("send_show_receipt_option ===>>>")
        _logger.info("values ===>>>{}".format(values))

        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            return {'success': False, 'description': 'Config id or JWT Token or Server URL is missing'}

        URL = '%s/api/v1/receipt-option' % (self.clover_server_url)
        headers = self.get_headers(values)
        payload = {
            "configId": values.get('configId'),
            "deviceId": values.get('deviceId'),
            "posId": values.get('posId'),
            "idempotencyId": self.get_idempotency_id(values),
            "method": values.get('method'),
        }

        if values.get('email'):
            payload['email'] = values['email']
        if values.get('phone'):
            payload['phone'] = values['phone']

        response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))

        if self.debug_logger:
            _logger.info("send_show_receipt_option")
            _logger.info("URL ===>>>>{}".format(URL))
            _logger.info("headers ===>>>>{}".format(headers))
            _logger.info("payload ===>>>>{}".format(payload))
            _logger.info("response===>>>>" + str(response.text))
        response.status_code = 200
        if response.status_code == 200:
            res_json = response.json()
            # res_json = {"status": "OK", "data": {"deliveryOption": [{"additionalData": "", "method": "NO_RECEIPT"}]}}
            # response===>>>>{"status":"OK","data":{"deliveryOption":[{"additionalData":"","method":"NO_RECEIPT"}]}}
            # response===>>>>{"status":"OK","data":{"deliveryOption":[{"additionalData":"","method":"SMS"}]}}
            # response===>>>>{"status":"OK","data":{"deliveryOption":[{"additionalData":"","method":"PRINT"}]}}
            # response===>>>>{"status":"OK","data":{"deliveryOption":[{"additionalData":"","method":"PRINT"}]}}
            return {
                'status_code': response.status_code,
                'success': True,
                'description': 'Show Receipt Options sent Successfully',
                'action': 'receipt_option',
                'response': res_json,
            }

        else:
            return {
                'status_code': response.status_code,
                'success': False,
                'description': response.json().get('message') or 'Show Receipt Options sent Failed!',
                'action': 'receipt_option',
            }

    # 8. Display Thank-you Message
    def send_thankyou_message(self, values):
        _logger.info("send_thankyou_message ===>>>")
        _logger.info("values ===>>>{}".format(values))

        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            return {'success': False, 'description': 'Config id or JWT Token or Server URL is missing'}

        URL = '%s/api/v1/show/thank-you' % (self.clover_server_url)
        headers = self.get_headers(values)
        payload = {
            "configId": values.get('configId'),
            "deviceId": values.get('deviceId'),
            "posId": values.get('posId'),
        }
        response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))
        response.status_code = 200

        if self.debug_logger:
            _logger.info("send_thankyou_message")
            _logger.info("URL ===>>>>{}".format(URL))
            _logger.info("headers ===>>>>{}".format(headers))
            _logger.info("payload ===>>>>{}".format(payload))
            _logger.info("response===>>>>" + str(response.text))

        if response.status_code == 200:
            return {
                'status_code': response.status_code,
                'success': True,
                'description': 'Display Thank-you Message sent Successfully',
                'action': 'thankyou_message',
            }
        else:
            return {
                'status_code': response.status_code,
                'success': False,
                'description': response.json().get('message') or 'Display Thank-you Message send failed!',
                'action': 'thankyou_message',
            }

    # 9. Display Welcome Message
    def send_welcome_message(self, values):
        _logger.info("send_welcome_message ===>>>")
        _logger.info("values ===>>>{}".format(values))
        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            return {'success': False, 'description': 'Config id or JWT Token or Server URL is missing'}

        URL = '%s/api/v1/show/welcome' % (self.clover_server_url)
        headers = self.get_headers(values)
        payload = {
            "configId": values.get('configId'),
            "deviceId": values.get('deviceId'),
            "posId": values.get('posId'),
        }
        response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))
        response.status_code = 200

        if self.debug_logger:
            _logger.info("send_welcome_message")
            _logger.info("URL ===>>>>{}".format(URL))
            _logger.info("headers ===>>>>{}".format(headers))
            _logger.info("payload ===>>>>{}".format(payload))
            _logger.info("response===>>>>" + str(response.text))

        if response.status_code == 200:
            return {
                'status_code': response.status_code,
                'success': True,
                'description': 'Display Welcome Message sent Successfully',
                'action': 'welcome_message',
            }
        else:
            return {
                'status_code': response.status_code,
                'success': False,
                'description': response.json().get('message'),
                'action': 'welcome_message',
            }

        # 10. Display Custom Message

    def send_display_message(self, values):
        _logger.info("send_display_message ===>>>")
        _logger.info("values ===>>>{}".format(values))
        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            return {'success': False, 'description': 'Config id or JWT Token or Server URL is missing'}

        URL = '%s/api/v1/display/message' % (self.clover_server_url)
        headers = self.get_headers(values)
        payload = {
            "configId": values.get('configId'),
            "deviceId": values.get('deviceId'),
            "posId": values.get('posId'),
            "text": values.get("err")
        }
        response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))

        if self.debug_logger:
            _logger.info("send_welcome_message")
            _logger.info("URL ===>>>>{}".format(URL))
            _logger.info("headers ===>>>>{}".format(headers))
            _logger.info("payload ===>>>>{}".format(payload))
            _logger.info("response===>>>>" + str(response.text))

        if response.status_code == 200:
            return {
                'status_code': response.status_code,
                'success': True,
                'description': 'Display  Message sent Successfully',
                'action': 'welcome_message',
            }
        else:
            return {
                'status_code': response.status_code,
                'success': False,
                'description': response.json().get('message'),
                'action': 'welcome_message',
            }

