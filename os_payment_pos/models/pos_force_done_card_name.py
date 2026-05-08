# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PosForceDoneCardName(models.Model):
    _name = "pos.force.done.card.name"
    _description = "POS Force Done Card Name"
    _inherit = ["pos.load.mixin"]
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, string="Card Name")
    code = fields.Char(required=True, string="Card Code")
    terminal = fields.Selection(
        [
            ("clover_cloud", "Clover Cloud"),
            ("moneris_cloud", "Moneris Cloud"),
            ("moneris_cloud_go", "Moneris Cloud Go"),
        ],
        required=True,
        default="clover_cloud",
    )
    active = fields.Boolean(default=True)

    @api.model
    def _load_pos_data_fields(self, config):
        return ["id", "name", "code", "sequence", "terminal", "active"]

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [("active", "=", True), ("terminal", "in", ["clover_cloud", "moneris_cloud", "moneris_cloud_go"])]
