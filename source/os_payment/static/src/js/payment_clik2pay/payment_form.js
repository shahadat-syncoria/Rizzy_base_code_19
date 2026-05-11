/* global Accept */
//* global clik2pay */

import { _t } from '@web/core/l10n/translation';
import { PaymentForm } from '@payment/interactions/payment_form';
import { rpc,RPCError } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';

patch(PaymentForm.prototype,{

    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
            if (providerCode !== 'clik2pay') {
                await super._prepareInlineForm(...arguments);
                return ;
            }

            // Check if instantiation of the drop-in is needed
            if (flow === 'token') {
                return Promise.resolve(); // No drop-in for tokens
            } else if (this.clik2payDropin && this.clik2payDropin.acquirerId === paymentOptionId) {
                this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation
                return Promise.resolve(); // Don't re-instantiate if already done for this acquirer
            }

            this._setPaymentFlow('direct');
            return Promise.resolve();

    },

    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        console.log("We are in _processDirectPayment");
                console.log('processingValues', processingValues);
                console.table(processingValues);
                if (providerCode !== 'clik2pay') {
                     await super._processDirectFlow(...arguments);
                     return ;
                }
        const providerId = processingValues.provider_id;
        return rpc('/payment/clik2pay/payment',{
                    provider_id: providerId,
                    converted_amount: processingValues.converted_amount,
                    currency_id: processingValues.currency_id,
                    partner_id: processingValues.partner_id,
                    access_token: processingValues.access_token,
                    reference: processingValues.reference,
                }
            )
            .then((response) => {
                const data = JSON.parse(response);
                console.log("we are executed the payment request");
                console.log(data);
                if (data.paymentLink) {
                    // Open a new window with the payment link
                    const paymentWindow = window.open(data.paymentLink, "_blank", "top=100,left=500,height=800,width=800,status=yes,toolbar=no,menubar=no,location=no");

                    // Check if the window was successfully opened
                    if (paymentWindow) {
                        // Add a callback method to check when the window is closed by the user
                        const checkPaymentStatus = () => {
                            if (paymentWindow.closed) {
                                // Window closed by the user, we can perform further actions here
                                console.log("Payment window closed by the user");
                                // Check the payment status with the token
                                this._checkPaymentStatusWithToken(data.id, providerId, true)
                                .then((status) => {
                                    if (status === 'active') {
                                        // Call _cancelPaymentOrder and redirect to /payment/status
                                        this._cancelPaymentOrder(data.id, providerId)
                                        .then(() => {
                                            window.location = '/payment/status';
                                        });
                                    }else{
                                        // Redirect the user to /payment/status
                                        window.location = '/payment/status';
                                    }
                                })
                            }else{
                                setTimeout(checkPaymentStatus, 1000);
                            }
                        };

                        // Start checking for the payment window status
                        checkPaymentStatus();

                        // Call _checkPaymentStatusWithToken every 5 seconds, and wait for up to 1 minute
                        const checkInterval = 5000; // 5 seconds
                        const maxWaitTime = 60000 * 1; // 1 * x minute
                        let elapsedTime = 0;

                        const checkStatusInterval = setInterval(() => {
                            if (elapsedTime >= maxWaitTime) {
                                // Max wait time reached, close the window and redirect
                                console.log("Max wait time reached, payment not confirmed. Closing window.");
                                clearInterval(checkStatusInterval);
                                paymentWindow.close();
                                window.location = '/payment/status';
                            }
                            // Check the payment status with the token
                            this._checkPaymentStatusWithToken(data.id, providerId, false)
                            .then((status) => {
                                if (status === 'completed' || status === 'canceled') {
                                    // Payment is confirmed, you can perform further actions here
                                    console.log("Payment is confirmed");
                                    // Close the window
                                    paymentWindow.close();
                                    // Redirect the user to /payment/status
                                    window.location = '/payment/status';
                                    clearInterval(checkStatusInterval);
                                } else {
                                    // Handle other status if needed
                                    console.log("Payment still pending!")
                                }
                            });
                            elapsedTime += checkInterval;
                        }, checkInterval);
                    } else {
                        // Handle the case where the window could not be opened
                        console.error("Unable to open payment window.");
                    }
                } else {
                    console.error("No payment link found in the response.");
                }
            })
            .catch(error => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Server Error"),
                    _t("We are not able to process your payment."),
                    error.data.message);
                this._enableButton(); // The button has been disabled before initiating the flow.
            } else {
                return Promise.reject(error);
            }
        });
    },
          /**
         * Check the payment status with the token.
         *
         * @private
         * @param {string} token - The token to check the payment status
         * @param {string} provider_id - The provider ID
         * @param {bool} bypass_webhook_check - to avoid clik2pay api call
         * @return {Promise<string>} - Resolves to 'active', 'pending', 'canceled', 'completed', 'failed' or 'error'
         */
    _checkPaymentStatusWithToken: function (token, provider_id, bypass_webhook_check) {
            return rpc('/payment/clik2pay/status',{
                    token: token,
                    provider_id: provider_id,
                    bypass_webhook_check: bypass_webhook_check
                }
            )
            .then((response) => {
                return JSON.parse(response).status;
            })
            .catch(error => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton(); // The button has been disabled before initiating the flow.
            } else {
                return Promise.reject(error);
            }
        });
    },

        /**
         * Cancel the payment order with the given token.
         *
         * @private
         * @param {string} token - The token of the payment order to be canceled
         * @param {string} provider_id - The provider ID
         * @return {Promise<string>} - Resolves to 'cancelled', 'failed', or 'error'
         */
    _cancelPaymentOrder: function (token, provider_id) {
            return rpc('/payment/clik2pay/cancel',{
                    token: token,
                    provider_id: provider_id
                }
            )
            .then((response) => {
                return JSON.parse(response).status;
            }).catch(error => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton(); // The button has been disabled before initiating the flow.
            } else {
                return Promise.reject(error);
            }
        });
    },


})