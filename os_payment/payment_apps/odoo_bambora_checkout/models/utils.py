# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import base64
import json
from odoo.http import request
import requests
import logging
import string
import random
import re
import urllib
from urllib.parse import unquote
# from odoo.service import common
from .utils import *

import logging
_logger = logging.getLogger(__name__)


def url_to_dict(url_str):
    url_dict = urllib.parse.parse_qs(url_str)
    print("URL Params : " + str(url_dict))

def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

def href_to_json(kwargs):
    href = kwargs.get('window_href') or kwargs.get('href') or request.params.get(
        'href') or request.params.get('window_href')
    if href:
        href = unquote(href)
        kwargs['href'] = href
    href_items = {}
    for param in href.split("?")[1].split("&"):
        href_items[param.split("=")[0]] = param.split("=")[1]
    kwargs['href_items'] = href_items
    return kwargs, href_items

def get_invoice_flag(kwargs):
    data = kwargs

    invoice_payment = False
    href = kwargs.get('window_href') or kwargs.get('href') or request.params.get(
        'href') or request.params.get('window_href')
    if href:
        href = unquote(href)
        kwargs['href'] = href
        kwargs['window_href'] = href

        if '/website_payment' in href:
            data, href_items = href_to_json(kwargs)
            order = request.env['sale.order']
            if href_items.get('reference') != 'False':
                order = request.env['sale.order'].sudo().search([('id', '=', href_items.get('order_id')),
                                                                 ('name', '=', href_items.get('reference'))])
            if href_items.get('reference') == 'False':
                order = request.env['sale.order'].sudo().search([
                    ('id', '=', href_items.get('order_id')),
                    ('partner_id', '=', href_items.get('partner_id')),
                    ('amount_total', '=', href_items.get('amount'))
                ])
            if len(order) > 0 and 'sale.order' in str(order):
                _logger.info("Order Payment")
                data['actual_total'] = order.amount_total
                if not data.get('order_name'):
                    data['order_name'] = str(order.name)
                if not data.get('charge_total'):
                    data['charge_total'] = str(order.amount_total)

            if href_items:
                _logger.info("\n reference: " +
                             str(href_items.get('reference')))
                _logger.info("\n order_id: " + str(href_items.get('order_id')))

            if len(order) == 0:
                if href_items.get('reference') != 'False':
                    invoice = request.env['account.move'].sudo().search([('id', '=', href_items.get('order_id')),
                                                                         ('name', '=', href_items.get('reference'))])
                if href_items.get('reference') == 'False' and href_items.get('order_id'):
                    invoice = request.env['account.move'].sudo().search([
                        ('id', '=', href_items.get('order_id')),
                        ('partner_id.id', '=', href_items.get('partner_id')),
                        ('amount_total', '=', href_items.get('amount'))
                    ])
                if href_items.get('reference') == 'False' and not href_items.get('order_id'):
                    invoice = request.env['account.move'].sudo().search([
                        ('partner_id.id', '=', href_items.get('partner_id')),
                        ('amount_total', '=', href_items.get('amount')),
                        ('currency_id.id', '=', href_items.get('currency_id')),
                        ('state', '=', 'draft')
                    ])

                if len(invoice) > 0 and 'account.move' in str(invoice):
                    _logger.info("Invoice Payment")
                    invoice_payment = True
                    data['invoice'] = invoice
                    data['invoice_id'] = invoice.id
                    data['actual_total'] = invoice.amount_total
                    if not data.get('order_name'):
                        data['order_name'] = str(invoice.name)
                    if not data.get('charge_total'):
                        data['charge_total'] = str(invoice.amount_total)

            if not kwargs.get('order_id') and href_items.get('order_id'):
                try:
                    kwargs['href'] = href
                except Exception as e:
                    _logger.warning(e.args)

        if '/my/invoices/' in href:
            data['invoice_id'] = href.split("/my/invoices/")[1].split("?")[0]
            invoice = request.env['account.move'].sudo().search([
                ('id', '=', data['invoice_id'])
            ])
            data['invoice'] = invoice
            invoice_payment = True

        if '/my/orders/' in href:
            data['order_id'] = href.split('/my/orders/')[1].split("?")[0]
            order = request.env['sale.order'].sudo().search([
                ('id', '=', data['order_id'])
            ])
            data['order'] = order

    
    data['invoice_payment'] = invoice_payment
    return data, invoice_payment

def get_authorization(merchant_id, api_key):
    message = merchant_id + ":" + api_key
    base64_bytes = base64.b64encode(message.encode('ascii'))
    base64_message = base64_bytes.decode('ascii')
    _logger.info(base64_bytes.decode('ascii'))
    return base64_message


def get_headers(merchant_id, api_key):
    headers = {
        'Authorization': 'Passcode ' + get_authorization(merchant_id, api_key),
        'Content-Type': 'application/json'
    }
    return headers