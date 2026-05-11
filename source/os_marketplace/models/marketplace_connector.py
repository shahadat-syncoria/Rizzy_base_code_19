# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
import json
from odoo import models, fields, api, exceptions, _
from ast import literal_eval
import requests
logger = logging.getLogger(__name__)


class MarketplaceConnect(models.Model):
    _name = 'marketplace.connector'
    _description = 'Marketplace Connector'

    def marketplace_api_call(self, **kwargs):
        """
            We will be running the api calls from here
            :param kwargs: dictionary with all the necessary parameters,
            such as url, header, data,request type, etc
            :return: response obtained for the api call
        """
        if not kwargs:
            # no arguments passed
            return

        marketplace_instance = kwargs.get('marketplace_instance_id')
        if not marketplace_instance:
            raise exceptions.Warning(_('Please check the Marketplace Configurations!'))
        if hasattr(self, '%s_api_call' % marketplace_instance.marketplace_instance_type):
            return getattr(self, '%s_api_call' % marketplace_instance.marketplace_instance_type)(kwargs=kwargs)
