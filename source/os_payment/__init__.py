# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from . import models
from . import payment_apps
from odoo.addons.payment import setup_provider, reset_payment_provider


def pre_init_check(cr):
    from odoo.service import common
    from odoo.exceptions import ValidationError
    version_info = common.exp_version()
    server_serie = version_info.get('server_serie')
    if server_serie != '19.0':raise ValidationError('Module support Odoo series 19.0 found {}.'.format(server_serie))
    return True
