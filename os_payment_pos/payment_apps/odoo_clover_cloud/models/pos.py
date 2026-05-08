# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import fields, models, api, _
from datetime import date, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class pos_order(models.Model):
    _inherit = "pos.order"

    pos_order_date = fields.Date("Oder Date", compute="get_order_date")
    barcode = fields.Char(string="Order Barcode")
    barcode_img = fields.Binary("Order Barcode Image")

    def get_order_date(self):
        for i in self:
            is_dt = i.date_order.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            d1 = datetime.strptime(is_dt, DEFAULT_SERVER_DATETIME_FORMAT).date()
            i.pos_order_date = d1

    @api.model
    def _order_fields(self, ui_order):
        res = super(pos_order, self)._order_fields(ui_order)
        res["barcode"] = ui_order.get("barcode")
        # res['barcode_img'] = ui_order['barcode_img']
        return res

    def get_odoo_clover_cloud(self):
        if (
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", "odoo_clover_cloud")])
            .state
            == "installed"
        ):
            return {"odoo_clover_cloud": "true"}
        else:
            return {"odoo_clover_cloud": "false"}


class pos_config(models.Model):
    _inherit = "pos.config"

    show_order = fields.Boolean("Show Orders")
    pos_session_limit = fields.Selection(
        [
            ("all", "Load all Session's Orders"),
            ("last3", "Load last 3 Session's Orders"),
            ("last5", " Load last 5 Session's Orders"),
            ("current_day", "Only Current Day Orders"),
            ("current_session", "Only Current Session's Orders"),
        ],
        string="Session limit",
        default="current_day",
    )
    show_barcode = fields.Boolean("Show Barcode in Receipt")
    show_draft = fields.Boolean("Show Draft Orders")
    show_posted = fields.Boolean("Show Posted Orders")
