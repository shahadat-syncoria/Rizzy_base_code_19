# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields

class PosPaymentAcquirer(models.Model):
    _inherit = 'pos.payment.method'

    account_id = fields.Many2one(
        string='account',
        comodel_name='omni.account',
        ondelete='restrict',
    )
    token = fields.Char()
    omnisync_active = fields.Boolean(
        string='Odoosync Active',
        )
    enable_card_wise_journal = fields.Boolean(string="Enable Card-wise Journal")
    test_with_demo_response = fields.Boolean(string="Test With Demo Response")
    demo_card_name = fields.Char(string="Card Name")
    force_done_card_name_ids = fields.Many2many(
        "pos.force.done.card.name",
        "pos_payment_method_force_done_card_rel",
        "payment_method_id",
        "card_name_id",
        string="Force Done Card Names",
    )

    def init(self):
        super().init()
        self.env.cr.execute(
            """
            INSERT INTO pos_payment_method_force_done_card_rel (payment_method_id, card_name_id)
            SELECT ppm.id, pfdcn.id
            FROM pos_payment_method ppm
            JOIN pos_force_done_card_name pfdcn
              ON pfdcn.terminal = CASE
                    WHEN ppm.use_payment_terminal = 'clover_cloud' THEN 'clover_cloud'
                    WHEN ppm.use_payment_terminal = 'moneris_cloud' AND COALESCE(ppm.is_moneris_go_cloud, false) THEN 'moneris_cloud_go'
                    WHEN ppm.use_payment_terminal = 'moneris_cloud' THEN 'moneris_cloud'
                    ELSE ''
                 END
            WHERE ppm.use_payment_terminal IN ('clover_cloud', 'moneris_cloud')
              AND NOT EXISTS (
                  SELECT 1
                  FROM pos_payment_method_force_done_card_rel rel
                  WHERE rel.payment_method_id = ppm.id
                    AND rel.card_name_id = pfdcn.id
              )
            """
        )

    # def _compute_omnisync_active(self):
    #     for record in self:
    #         record.omnisync_active = False
