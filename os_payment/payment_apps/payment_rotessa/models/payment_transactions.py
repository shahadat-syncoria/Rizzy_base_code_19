import logging
from datetime import datetime

from odoo import fields,api,models
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.payment import utils as payment_utils
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class RotessaTransactions(models.Model):
    _inherit='payment.transaction'

    rotessa_track_id = fields.Many2one('rotessa.transaction.tracking')

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """ Override of payment to ensure that Rotessa requirements for references are satisfied.

        Ogone requirements for references are as follows:
        - References must be unique at provider level for a given merchant account.
          This is satisfied by singularizing the prefix with the current datetime. If two
          transactions are created simultaneously, `_compute_reference` ensures the uniqueness of
          references by suffixing a sequence number.

        :param str provider_code: The code of the provider handling the transaction
        :param str prefix: The custom prefix used to compute the full reference
        :param str separator: The custom separator used to separate the prefix from the suffix
        :return: The unique reference for the transaction
        :rtype: str
        """
        if provider_code != 'rotessa':
            return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

        if not prefix:
            # If no prefix is provided, it could mean that a module has passed a kwarg intended for
            # the `_compute_reference_prefix` method, as it is only called if the prefix is empty.
            # We call it manually here because singularizing the prefix would generate a default
            # value if it was empty, hence preventing the method from ever being called and the
            # transaction from received a reference named after the related document.
            prefix = self.sudo()._compute_reference_prefix(provider_code, separator, **kwargs) or None
        prefix = payment_utils.singularize_reference_prefix(prefix=prefix, max_length=40)
        return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

    @api.model
    def _get_specific_create_values(self, provider_code, values):
        """ Complete the values of the `create` method with provider-specific values.

        For a provider to add its own create values, it must overwrite this method and return a dict
        of values. Provider-specific values take precedence over those of the dict of generic create
        values.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict values: The original create values.
        :return: The dict of provider-specific create values.
        :rtype: dict
        """
        if provider_code != 'rotessa':
            return super()._get_specific_create_values(provider_code, values)
        invoice_id = self._get_invoice_id()
        if invoice_id:
            if 'invoice_ids' not in values:
                values['invoice_ids'] = [(4,invoice_id.id)]

        return super()._get_specific_create_values(provider_code, values)
    def _get_invoice_id(self):
        context = request.params.get('kwargs', {}).get('context', {})
        active_model = context.get('active_model')
        active_id = context.get('active_id')
        active_ids = context.get('active_ids')

        if (active_model == 'account.move' and active_id) or (active_model == 'account.move' and active_ids):
            invoice_id = self.env['account.move'].sudo().browse(active_ids)
            return invoice_id
        elif (active_model == 'account.move.line' and active_id) or (active_model == 'account.move.line' and active_ids):
            invoice_id = self.env['account.move'].sudo().search([('line_ids', 'in', context.get('active_ids'))])
            return invoice_id
        else:
            False

    def _send_payment_request(self):
        """ Override of payment to simulate a payment request.

        Note: self.ensure_one()

        :return: None
        """
        super(RotessaTransactions,self)._send_payment_request()
        if self.provider_code != 'rotessa':
            return

        if not self.token_id.rotessa_customer_id:
            raise UserError("Rotessa: " + ("The transaction is not linked to a token with rotessa customer ID."))

        if request.params and (request.params.get('model') == 'account.payment.register'):
            invoice_id = self._get_invoice_id()
        else:
            if self.sale_order_ids and self.sale_order_ids.type_name == 'Subscription' and self.invoice_ids:
                invoice_id =  self.invoice_ids[0]
                invoice_id.write({
                    'rotessa_process_date': fields.Date.today()+ relativedelta(days=1),
                    'rotessa_transaction_comment': self.sale_order_ids.name
                })
                if invoice_id.state == 'draft':
                    invoice_id.action_post()
            else:
                raise UserError(("Payment can be possible only from invoice."))
        invoice_id._check_rotessa_payment_conditions()
        res_content = self.provider_id.transaction_schedule_request(self, token=self.token_id,invoice_id=invoice_id)

        notification_data = {'reference': self.reference,"response":res_content,'invoice_id':invoice_id}
        self._handle_notification_data('rotessa', notification_data)


    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Authorize data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'rotessa':
            return
        final_data = notification_data.get('response')
        if final_data.get('id'):
            # self._set_draft()
            invoice_id = notification_data['invoice_id']
            tracking_id = self.env['rotessa.transaction.tracking'].create({
                'transaction_schedule_id': final_data.get('id'),
                'invoice_no': invoice_id.id,
                'invoice_ref': invoice_id.name,
                'invoice_partner_id': invoice_id.partner_id.id,
                'invoice_date': invoice_id.invoice_date,
                'process_date': invoice_id.rotessa_process_date,
                'state': 'Future',
                'status_reason': '',
                'transaction_id': self.id,
                'provider_id': self.provider_id.id,
                'amount': self.amount,

                'transaction_request_date': datetime.fromisoformat(final_data.get('updated_at').replace('T', ' ').split('.')[0])
            }
            )
            invoice_id.write({
                "rotessa_transaction_sc_id":tracking_id
            })

        # self._finalize_post_processing()

        # self.provider_reference = response_content.get('x_trans_id')
        # status_code = response_content.get('x_response_code', '3')
        # if status_code == '1':  # Approved
        #     status_type = response_content.get('x_type').lower()
        #     if status_type in ('auth_capture', 'prior_auth_capture'):
        #         self._set_done()
        #         if self.tokenize and not self.token_id:
        #             self._authorize_tokenize()
        #     elif status_type == 'auth_only':
        #         self._set_authorized()
        #         if self.tokenize and not self.token_id:
        #             self._authorize_tokenize()
        #         if self.operation == 'validation':
        #             self._send_void_request()  # In last step because it processes the response.
        #     elif status_type == 'void':
        #         if self.operation == 'validation':  # Validation txs are authorized and then voided
        #             self._set_done()  # If the refund went through, the validation tx is confirmed
        #         else:
        #             self._set_canceled()
        #     elif status_type == 'refund' and self.operation == 'refund':
        #         self._set_done()
        #         # Immediately post-process the transaction as the post-processing will not be
        #         # triggered by a customer browsing the transaction from the portal.
        #         self.env.memo('payment.cron_post_process_payment_tx')._trigger()
        # elif status_code == '2':  # Declined
        #     self._set_canceled()
        # elif status_code == '4':  # Held for Review
        #     self._set_pending()
        # else:  # Error / Unknown code
        #     error_code = response_content.get('x_response_reason_text')
        #     _logger.info(
        #         "received data with invalid status (%(status)s) and error code (%(err)s) for "
        #         "transaction with reference %(memo)s",
        #         {
        #             'status': status_code,
        #             'err': error_code,
        #             'memo': self.reference,
        #         },
        #     )
        #     self._set_error(
        #         "Authorize.Net: " + (
        #             "Received data with status code \"%(status)s\" and error code \"%(error)s\"",
        #             status=status_code, error=error_code
        #         )
        #     )