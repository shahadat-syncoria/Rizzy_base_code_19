/* global Accept */
//* global clik2pay */

import { _t } from '@web/core/l10n/translation';
import { PaymentForm } from '@payment/interactions/payment_form';
import { rpc, RPCError } from '@web/core/network/rpc';
import { loadJS } from "@web/core/assets";
import { Dialog } from "@web/core/dialog/dialog";
import { patch } from '@web/core/utils/patch';

var isCardNumberComplete = false;
    var isCVVComplete = false;
    var isExpiryComplete = false;
    try {
        var customCheckout = customcheckout();
    } catch (error) {

    }
    var store = {}
    var SAVE_TOKEN = false

patch(PaymentForm.prototype, {

    /**
         * Return all relevant inline form inputs based on the payment method type of the provider.
         *
         * @private
         * @param {number} providerId - The id of the selected provider
         * @return {Object} - An object mapping the name of inline form inputs to their DOM element
         */

        _getInlineFormBamboraInputs(providerId) {
            debugger
            return {
                provider_id: document.getElementById(`provider_id`),
                provider_state: document.getElementById(`provider_state`),
                bamborachk_transaction_type: document.getElementById(`bamborachk_transaction_type`),
                bamborachk_merchant_id: document.getElementById(`bamborachk_merchant_id`),
                bamborachk_payment_api: document.getElementById(`bamborachk_payment_api`),
                bamborachk_profile_api: document.getElementById(`bamborachk_profile_api`),
                window_href: document.getElementById(`window_href`),
            };
        },

        /**
         * Return the credit card or bank data to pass to the Accept.dispatch request.
         *
         * @private
         * @param {number} providerId - The id of the selected provider
         * @return {Object} - Data to pass to the Accept.dispatch request
         */
        _getPaymentDetails: function(providerId) {
            const inputs = this._getInlineFormBamboraInputs(providerId);
            try {
                var providerForm = $(".bamborachk_form");
                var inputsForm = $("input", providerForm);
                var formData = this.getBamboraFormData(inputsForm);
            } catch (error) {
                console.log("error ===>>>", error);
                var formData = this.getBamboraFormData(inputs);
            }
            return formData;
        },

        /**
         * Prepare the inline form of Authorize.Net for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The provider of the selected payment option's provider
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
            debugger
            if (providerCode !== "bamborachk") {
                await super._prepareInlineForm(...arguments);
                return ;
            }

            console.log("_prepareInlineForm");
            const ll = this
            function callRpc(params, rpc = rpc) {
                return rpc('/payment/bamborachk/payment', params
                                                    )
                                                        .then(() =>{
                                                        window.location = '/payment/status'}
                                                    )
            }
            // debugger
            store._rpc = rpc


            if (flow === "token") {
                return Promise.resolve(); // Don't show the form for tokens
            }

            this._setPaymentFlow("direct");

            let acceptJSUrl = "https://libs.na.bambora.com/customcheckout/1/customcheckout.js";
            let self = this;
            return rpc("/payment/bamborachk/get_provider_info", {
                        provider_id: paymentOptionId,
                    },
                )
                .then((providerInfo) => {
                    if (providerInfo.state !== "enabled") {
                        // debugger
                        acceptJSUrl = "https://libs.na.bambora.com/customcheckout/1/customcheckout.js";
                    }
                    this.authorizeInfo = providerInfo;
                })
                .then(() => {
                    // debugger
                    // var self= this
                    loadJS(acceptJSUrl);


                    //========================================================================================
                    // var bamboraCancel = document.getElementById("bamboraCancel");
                    // if(bamboraCancel){
                    //     document.getElementById("bamboraCancel").addEventListener("click", function() {
                    //         console.log("******bamboraCancel*******");
                    //         if (window.location.href.includes('/my/payment_method')) {
                    //             var btnPayPm = document.getElementById("o_payment_form_add_pm");
                    //             btnPayPm.disabled = false;
                    //         } else if (window.location.href.includes('/shop/payment')) {
                    //             var btnPay = document.getElementById("o_payment_form_pay");
                    //             btnPay.disabled = false;
                    //         }
                    //         location.reload();
                    //     });
                    // }
                    //========================================================================================

                    var bamboraPay = document.getElementById("pay-button");
                    var one_time_click = false
                    if (bamboraPay) {
                        bamboraPay.addEventListener("click", function(event) {
                            console.log("bamboraPay.addEventListener")
                            console.log("event ===>>>", event)
                            if (one_time_click === false) {
                                // console.log("One Time Click =================>",one_time_click)
                                // document.getElementById('pay-button').disabled = true;
                                setPayButton(false)

                                var self = this;
                                event.preventDefault();

                                //============================================
                                // self.setPayButton(false);
                                //============================================
                                var enabled = false;

                                function setPayButton(enabled) {
                                    console.log('checkout.setPayButton() disabled: ' + !enabled);
                                    var payButton = document.getElementById('pay-button');
                                    if (enabled) {
                                        payButton.disabled = false;
                                        payButton.className = 'btn btn-primary';
                                    } else {
                                        payButton.disabled = true;
                                        payButton.className = 'btn btn-primary disabled';
                                    }
                                }

                                function toggleProcessingScreen() {
                                    var processingScreen = document.getElementById('processing-screen');
                                    if (processingScreen) {
                                        processingScreen.classList.toggle('visible');
                                    }
                                }

                                function processTokenError(error) {
                                    error = JSON.stringify(error, undefined, 2);
                                    console.log('processTokenError: ' + error);
                                    this.showErrorFeedback(
                                        'Error creating token: </br>' + JSON.stringify(error, null, 4)
                                    );
                                    setPayButton(true);
                                    toggleProcessingScreen();
                                }

                                var callback = function (result) {
                                    document.getElementById('pay-button').disabled = true;
                                    // debugger
                                    console.log('token result : ' + JSON.stringify(result));
                                    if (result.error) {
                                        // self.processTokenError(result.error);
                                        processTokenError(result.error);
                                    } else {
                                       console.log(one_time_click,"Inside===>")
                                        function processTokenSuccess(result) {

                                            console.log('processTokenSuccess: ' + result);
                                            var self = this;

                                            // var enabled = false;
                                            function setPayButton(enabled, showLoadingAnimation = false) {
                                                console.log('checkout.setPayButton() disabled: ' + !enabled);
                                                var payButton = document.getElementById('pay-button');
                                                if (enabled) {
                                                    payButton.disabled = false;
                                                    payButton.className = 'btn btn-primary';
                                                } else {
                                                    payButton.disabled = true;
                                                    payButton.className = 'btn btn-primary disabled';
                                                    if (showLoadingAnimation) {
                                                        payButton.innerHTML = '<i class = "fa fa-spinner fa-spin"></i> Please wait...';
                                                    }
                                                }
                                            }

                                            setPayButton(true);

                                            function toggleProcessingScreen() {
                                                var processingScreen = document.getElementById('processing-screen');
                                                if (processingScreen) {
                                                    processingScreen.classList.toggle('visible');
                                                }
                                            }

                                            toggleProcessingScreen();
                                            console.log(result.token);

                                            function _getPaymentOptionIdFromRadio(radio) {
                                                return $(radio).data('payment-option-id')
                                            }

                                            var $checkedRadio = $('input[type="radio"]:checked');
                                            var paymentOptionId = _getPaymentOptionIdFromRadio($checkedRadio);
                                            var acquirerForm = $(".bamborachk_form");
                                            var inputsForm = $("input", acquirerForm);

                                            console.log("acquirerForm ===>>>", acquirerForm)
                                            console.log("inputsForm ===>>>", inputsForm)

                                            function getBamboraFormData($form) {
                                                var unindexed_array = $form.serializeArray();
                                                var indexed_array = {};

                                                $.map(unindexed_array, function (n, i) {
                                                    indexed_array[n.name] = n.value;
                                                });
                                                return indexed_array;
                                            }

                                            function _getPaymentDetails(acquirerId) {
                                                function _getInlineFormBamboraInputs(acquirerId) {
                                                    return {
                                                        acquirer_id: document.getElementById(`acquirer_id`),
                                                        acquirer_state: document.getElementById(`acquirer_state`),
                                                        bamborachk_transaction_type: document.getElementById(`bamborachk_transaction_type`),
                                                        bamborachk_merchant_id: document.getElementById(`bamborachk_merchant_id`),
                                                        bamborachk_payment_api: document.getElementById(`bamborachk_payment_api`),
                                                        bamborachk_profile_api: document.getElementById(`bamborachk_profile_api`),
                                                        window_href: document.getElementById(`window_href`),
                                                    };
                                                }

                                                const inputs = _getInlineFormBamboraInputs(acquirerId);
                                                try {
                                                    var acquirerForm = $(".bamborachk_form");
                                                    var inputsForm = $("input", acquirerForm);
                                                    var formData = getBamboraFormData(inputsForm);
                                                } catch (error) {
                                                    console.log("error ===>>>", error);
                                                    var formData = getBamboraFormData(inputs);
                                                }
                                                return formData;
                                            }

                                            // const paymentOptionId = _getPaymentOptionIdFromRadio(checked_radio);
                                            // debugger;
                                            //console.log("****************************************")
                                            var formData = _getPaymentDetails(paymentOptionId)
                                            var nameOncard = document.getElementById(`card_name`);
                                            formData['code'] = result.code;
                                            formData['expiryMonth'] = result.expiryMonth;
                                            formData['expiryYear'] = result.expiryYear;
                                            formData['last4'] = result.last4;
                                            formData['token'] = result.token;
                                            formData['save_token_request'] = SAVE_TOKEN;
                                            if (nameOncard) {
                                                formData['nameOncard'] = nameOncard.value;
                                            }


                                            //console.log("formData ===>>>", formData)
                                            //console.log("formData.data_set ===>>>", formData.data_set)
                                            debugger;
                                            if (result.code == "200") {
                                                let showLoadingAnimation = true;
                                                setPayButton(false, showLoadingAnimation = showLoadingAnimation);

                                                debugger
                                                rpc(formData.data_set, formData).then(function (data) {
                                                    //debugger

                                                    if (window.location.href.includes("/my/payment_method")) {
                                                        //debugger
                                                        if (formData.return_url) {
                                                            window.location = formData.return_url;
                                                        } else {
                                                            if (data.error) {
                                                                alert("Error:" + data.error)
                                                            }
                                                            window.location.reload();
                                                        }
                                                    } else {
                                                        $checkedRadio.val(data.id);
                                                        //=============================================================================
                                                        // Create the transaction and retrieve the processing values
                                                        // if (data.result === false) {
                                                        //      window.location.reload();
                                                        // }
                                                        if (data.error) {
                                                            alert("Error:" + data.error)
                                                            window.location.reload();
                                                        }
                                                        var params = {
                                                            'reference': data.payment_reference,
                                                            'partner_id': data.partner_id,
                                                            'opaque_data': data,
                                                            'access_token': data.access_token,
                                                        }
                                                        // console.log("params--->", params);

                                                        // console.log("self.txContext.transactionRoute--->", self.txContext.transactionRoute);
                                                        // console.log("params--->", self._prepareTransactionRouteParams('bamborachk', receipt.formData.acquirer_id, 'direct'));
                                                        // debugger
                                                        // store._responseHandler(7,params)
                                                        // bamborachkMixin._responseHandler(7,params)
                                                        return rpc(
                                                            '/payment/bamborachk/payment', params
                                                        )
                                                            .then(() => {
                                                                    window.location = '/payment/status'
                                                                    // window.location = '/shop/confirmation'
                                                                }
                                                            )
                                                        // =============================================================================


                                                    }
                                                }).catch(function (error) {
                                                    // error.event.preventDefault();
                                                    acquirerForm.removeClass('d-none');
                                                    $('#bamboraModal').modal('hide');

                                                    if ($checkedRadio.length === 0) {
                                                        return new Dialog(null, {
                                                            title: _t('Server Error: '),
                                                            size: 'medium',
                                                            $content: "<p>" + _t("We are not able to add your payment method at the moment.") + "</p>",
                                                            buttons: [
                                                                {text: _t('Ok'), close: true}
                                                            ]
                                                        }).open();
                                                    }

                                                });
                                            } else {
                                                // ?Show ERROR
                                            }
                                        }
                                        console.log("Token Success ================>")
                                        if (!one_time_click){
                                            console.log("Start Tone Success ================>",one_time_click)
                                            processTokenSuccess(result);
                                            one_time_click = true
                                        }

                                    }
                                };
                                customCheckout.createToken(callback);




                            }

                        });
                    }


                })
                .catch((error) => {
                    if (error instanceof RPCError) {
                self._displayErrorDialog(_t("Server Error"),
                    _t("We are not able to process your payment."),
                    error.data.message);
                this._enableButton(); // The button has been disabled before initiating the flow.
            } else {
                return Promise.reject(error);
            }
                });
        },




        /**
         * Dispatch the secure data to bambora Checkout.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the payment option's provider
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} flow - The online payment flow of the transaction
         * @return {Promise}
         */
        async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
            console.log("--------------------------------------");
            console.log("bambora ==>>>_processPayment ===>>>>");
            console.log("paymentOptionId ===>>>>", paymentOptionId);
            console.log("flow ===>>>>", flow);
            console.log("--------------------------------------");
            debugger;

            if (providerCode !== "bamborachk" || flow === "token") {
                await super._initiatePaymentFlow(...arguments); // Tokens are handled by the generic flow
                return
            }

            if (!this._validateBamboraFormInputs(paymentOptionId)) {
                this._enableButton(); // The submit button is disabled at this point, enable it
                return Promise.resolve();
            }

            // // Build the authentication and card data objects to be dispatched to Bambora Checkout
            // const secureData = {
            //   authData: {
            //       apiLoginID: this.authorizeInfo.login_id,
            //       clientKey: this.authorizeInfo.client_key,
            //   },
            //   ...this._getPaymentDetails(paymentOptionId),
            // };

            var ev = {};
            // ev.txContext = this.txContext;
            ev.txContext = this.paymentContext;
            const save_token_requst = ev.txContext.tokenizationRequested
            SAVE_TOKEN = ev.txContext.tokenizationRequested
            var checked_radio = $('input[name="o_payment_radio"]:checked');
            this._createBamboraToken(ev, checked_radio);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Payment Request for bambora Checkout
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the provider
         * @param {number} providerId - The id of the provider handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {Promise}
         */
        async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
            console.log("processingValues ===>>>", processingValues);

            if (providerCode !== "bamborachk") {
                await super._processDirectFlow(...arguments);
                return
            }

            //======================================================================
            //==========PROCESS BAMBORA PAYMENT=====================================
            //======================================================================
        },

        /**
         * Handle the response from bambora Checkout and initiate the payment.
         *
         * @private
         * @param {number} providerId - The id of the selected provider
         * @param {object} response - The payment ticket returned by bambora Checkout
         * @return {Promise}
         */
        _responseHandler(providerId, response) {
            window.location = "/payment/status"
            // if (response.response_code != "001") {
            //     let error = "";
            //     response.messages.message.forEach(
            //         (msg) => (error += `${msg.code}: ${msg.text}\n`)
            //     );
            //     this._displayError(
            //         _t("Server Error"),
            //         _t("We are not able to process your payment."),
            //         error
            //     );
            //     return Promise.resolve();
            // }

            // Create the transaction and retrieve the processing values
            // return this._rpc({
            //         route: this.txContext.transactionRoute,
            //         params: this._prepareTransactionRouteParams(
            //             "bamborachk",
            //             providerId,
            //             "direct"
            //         ),
            //     })
            //     .then((processingValues) => {
            //         // Initiate the payment
            //         return this._rpc({
            //             route: "/payment/bamborachk/payment",
            //             params: {
            //                 reference: processingValues.reference,
            //                 partner_id: processingValues.partner_id,
            //                 opaque_data: response.opaqueData,
            //                 access_token: processingValues.access_token,
            //             },
            //         }).then(() => (window.location = "/payment/status"));
            //     })
            //     .guardedCatch((error) => {
            //         error.event.preventDefault();
            //         this._displayError(
            //             _t("Server Error"),
            //             _t("We are not able to process your payment."),
            //             error.message.data.message
            //         );
            //     });
        },

        /**
         * Checks that all payment inputs adhere to the DOM validation constraints.
         *
         * @private
         * @param {number} providerId - The id of the selected provider
         * @return {boolean} - Whether all elements pass the validation constraints
         */
        _validateBamboraFormInputs(providerId) {
            debugger
            console.log("_validateBamboraFormInputs ===>>>");
            const inputs = Object.values(this._getInlineFormBamboraInputs(providerId));
            console.log("inputs ===>>>", inputs);
            return inputs.every(element => element.reportValidity());
        },


        /**
         * called when clicking on pay now or add payment event.
         *
         * @private
         * @param {Event} ev
         * @param {DOMElement} checkedRadio
         * @param {Boolean} addPmEvent
         */
        _createBamboraToken(ev, $checkedRadio, addPmEvent) {
            console.log("_createBamboraToken")
            this.txContext = ev.txContext;

            // if (this.options.partnerId === undefined) {
            //     console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
            // }

            var checked_radio = $('input[name="o_payment_radio"]:checked');
            if (checked_radio) {
                if (checked_radio[0].dataset.providerCode == 'bamborachk') {

                    console.log("Create customCheckoutController");

                    var self = this;
                    store.rpc = rpc;
                    self.customCheckoutController = {
                        init: function() {
                            console.log('checkout.init()');
                            self.createInputs();
                            self.addListeners();
                        },
                    };
                    self.customCheckoutController.init();

                    // if (!window.location.href.includes('/my/payment_method')) {
                    //     $.unblockUI()
                    // }
                    // $.unblockUI()
                    // self.env.services.ui.unblock();
                    self._enableButton()

                    // if (
                    //     window.location.href.includes('/my/orders/') ||
                    //     window.location.href.includes('/my/invoices/') ||
                    //     window.location.href.includes('/my/payment_method/')
                    // ) {
                    //     document.getElementById("pay-button").addEventListener("click", function(event) {
                    //         console.log("pay-button click ");
                    //         return self._bamboraPay(event);
                    //     });
                    // }


                }
            }
        },


        getBamboraFormData($form) {
            debugger
            var unindexed_array = $form.serializeArray();
            var indexed_array = {};

            $.map(unindexed_array, function(n, i) {
                indexed_array[n.name] = n.value;
            });
            return indexed_array;
        },



        // ------------------------------------------------------------------------------------------------------------------
        // ------------------------------------------Bambora Functions-------------------------------------------------------
        // ------------------------------------------------------------------------------------------------------------------


        _bamboraPay(event) {
            console.log("_bamboraPay")
            console.log("event")
            console.log(event)

            var self = this;
            event.preventDefault();
            // self.setPayButton(false);
            var enabled = false;
            console.log('checkout.setPayButton() disabled: ' + !enabled);
            var payButton = document.getElementById('pay-button');
            if (enabled) {
                payButton.disabled = false;
                payButton.className = 'btn btn-primary';
            } else {
                payButton.disabled = true;
                payButton.className = 'btn btn-primary disabled';
            }


            var processingScreen = document.getElementById('processing-screen');
            if (processingScreen) {
                processingScreen.classList.toggle('visible');
            }


            var callback = function(result) {
                console.log('token result : ' + JSON.stringify(result));
                if (result.error) {
                    var error = JSON.stringify(result.error, undefined, 2);
                    console.log('processTokenError: ' + error);
                    this.showErrorFeedback(
                        'Error creating token: </br>' + JSON.stringify(error, null, 4)
                    );
                    //==============================
                    // this.setPayButton(true);
                    //==============================
                    var enabled = true;
                    console.log('checkout.setPayButton() disabled: ' + !enabled);
                    var payButton = document.getElementById('pay-button');
                    if (enabled) {
                        payButton.disabled = false;
                        payButton.className = 'btn btn-primary';
                    } else {
                        payButton.disabled = true;
                        payButton.className = 'btn btn-primary disabled';
                    }
                    var processingScreen = document.getElementById('processing-screen');
                    if (processingScreen) {
                        processingScreen.classList.toggle('visible');
                    }



                } else {
                    self.processTokenSuccess(result);
                }
            };
            customCheckout.createToken(callback);
        },

        createInputs() {
            console.log('createInputs');

            $("#bamboraModal").modal('show');
            setTimeout(function() {
                var options = {};
                options.placeholder = 'Card number';
                customCheckout.create('card-number', options).mount('#card-number');
                options.placeholder = 'CVV';
                customCheckout.create('cvv', options).mount('#card-cvv');
                options.placeholder = 'MM / YY';
                customCheckout.create('expiry', options).mount('#card-expiry');
            }, 500);

        },

        addListeners() {
            console.log('addListeners');
            var self = this;

            var bamboraCancel = document.getElementById("bamboraCancel");
            if (bamboraCancel) {
                document.getElementById("bamboraCancel").addEventListener("click", function() {
                    console.log("******bamboraCancel*******");
                    $("#bamboraModal").remove();
                    location.reload();


//                    if (window.location.href.includes('/my/payment_method')) {
//                        var $submitButton = $('button[name="o_payment_submit_button"]');
//                        var iconClass = $submitButton.data('icon-class');
//                        $submitButton.attr('disabled', false);
//                        $submitButton.find('i').removeClass(iconClass);
//                        // $submitButton.prepend(
//                        //     '<span class="o_loader"><i class="fa fa-refresh fa-spin"></i>&nbsp;</span>'
//                        // );
//                    } else if (window.location.href.includes('/shop/payment')) {
//                        var btnPay = document.getElementById("o_payment_form_pay");
//                        btnPay.disabled = false;
//                    }
                    // location.reload();
                });
            }


            customCheckout.on('brand', function(event) {
                var cardLogo = 'none';
                if (event.brand && event.brand !== 'unknown') {
                    var filePath = 'https://cdn.na.bambora.com/downloads/images/cards/' + event.brand + '.svg';
                    cardLogo = 'url(' + filePath + ')';
                }
                // document.getElementById('card-number').style.backgroundImage = cardLogo;
                document.getElementById("card_logo").src = filePath;
            });

            customCheckout.on('empty', function(event) {
                if (event.empty) {
                    if (event.field === 'card-number') {
                        isCardNumberComplete = false;
                    } else if (event.field === 'cvv') {
                        isCVVComplete = false;
                    } else if (event.field === 'expiry') {
                        isExpiryComplete = false;
                    }
                    self.setPayButton(false);
                }
            });

            customCheckout.on('complete', function(event) {
                if (event.field === 'card-number') {
                    isCardNumberComplete = true;
                    self.hideErrorForId('card-number');
                } else if (event.field === 'cvv') {
                    isCVVComplete = true;
                    self.hideErrorForId('card-cvv');
                } else if (event.field === 'expiry') {
                    isExpiryComplete = true;
                    self.hideErrorForId('card-expiry');
                }
                self.setPayButton(
                    isCardNumberComplete && isCVVComplete && isExpiryComplete
                );
            });

            customCheckout.on('error', function(event) {
                if (event.field === 'card-number') {
                    isCardNumberComplete = false;
                    self.showErrorForId('card-number', event.message);
                } else if (event.field === 'cvv') {
                    isCVVComplete = false;
                    self.showErrorForId('card-cvv', event.message);
                } else if (event.field === 'expiry') {
                    isExpiryComplete = false;
                    self.showErrorForId('card-expiry', event.message);
                }
                self.setPayButton(false);
            });
        },

        /**
         * @private
         * @param {id} id
         */
        hideErrorForId(id) {
            var element = document.getElementById(id);
            if (element !== null) {
                var errorElement = document.getElementById(id + '-error');
                if (errorElement !== null) {
                    errorElement.innerHTML = '';
                }
                var bootStrapParent = document.getElementById(id + '-bootstrap');
                if (bootStrapParent !== null) {
                    bootStrapParent.classList.remove('has-error');
                    bootStrapParent.classList.add('has-success');
                }
            } else {
                console.log('showErrorForId: Could not find ' + id);
            }
        },

        /**
         * @private
         * @param {id} id
         * @param {message} message
         */
        showErrorForId(id, message) {
            console.log('showErrorForId: ' + id + ' ' + message);

            var element = document.getElementById(id);
            if (element !== null) {
                var errorElement = document.getElementById(id + '-error');
                if (errorElement !== null) {
                    errorElement.innerHTML = message;
                }
                var bootStrapParent = document.getElementById(id + '-bootstrap');
                if (bootStrapParent !== null) {
                    bootStrapParent.classList.add('has-error');
                    bootStrapParent.classList.remove('has-success');
                }
            } else {
                console.log('showErrorForId: Could not find ' + id);
            }
        },

        /**
         * @private
         * @param {enabled} enabled
         */

        setPayButton(enabled) {
            console.log('checkout.setPayButton() disabled: ' + !enabled);
            var payButton = document.getElementById('pay-button');
            if (enabled) {
                payButton.disabled = false;
                payButton.className = 'btn btn-primary';
            } else {
                payButton.disabled = true;
                payButton.className = 'btn btn-primary disabled';
            }
        },

        toggleProcessingScreen() {
            var processingScreen = document.getElementById('processing-screen');
            if (processingScreen) {
                processingScreen.classList.toggle('visible');
            }
        },

        /**
         * @private
         * @param {message} message
         */
        showErrorFeedback(message) {
            console.log(message);
            var xMark = '\u2718';
            this.feedback = document.getElementById('feedback');
            this.feedback.innerHTML = xMark + ' ' + message;
            this.feedback.classList.add('error');
        },

        /**
         * @private
         * @param {message} message
         */
        showSuccessFeedback(message) {
            console.log(message);
            var checkMark = '\u2714';
            this.feedback = document.getElementById('feedback');
            this.feedback.innerHTML = checkMark + ' ' + message;
            this.feedback.classList.add('success');
        },

        /**
         * @private
         * @param {error} error
         */

        processTokenError(error) {
            error = JSON.stringify(error, undefined, 2);
            console.log('processTokenError: ' + error);
            this.showErrorFeedback(
                'Error creating token: </br>' + JSON.stringify(error, null, 4)
            );
            this.setPayButton(true);
            this.toggleProcessingScreen();
        },

        /**
         * @private
         * @param {result} result
         */
        processTokenSuccess(result) {
            console.log('private: processTokenSuccess: ' + result.token);
            var self = this;

            function setPayButton(enabled) {
                console.log('checkout.setPayButton() disabled: ' + !enabled);
                var payButton = document.getElementById('pay-button');
                if (enabled) {
                    payButton.disabled = false;
                    payButton.className = 'btn btn-primary';
                } else {
                    payButton.disabled = true;
                    payButton.className = 'btn btn-primary disabled';
                }
            }
            setPayButton(true);
            self.toggleProcessingScreen();
            console.log(result.token);

            function _getPaymentOptionIdFromRadio(radio) {
                return $(radio).data('payment-option-id');
            }

            var $checkedRadio = $('input[name="o_payment_radio"]:checked');
            var PaymentOptionId = _getPaymentOptionIdFromRadio($checkedRadio);
            var providerForm = $('#o_payment_add_token_acq_' + PaymentOptionId);
            var inputsForm = $('input', providerForm);

            function getBamboraform_data($form) {
                var unindexed_array = $form.serializeArray();
                var indexed_array = {};
                $.map(unindexed_array, function(n, i) {
                    indexed_array[n.name] = n.value;
                });
                return indexed_array;
            }
            var form_data = getBamboraform_data(inputsForm);
            console.log("form_data ===>>>>", form_data);
            form_data['code'] = result.code;
            form_data['expiryMonth'] = result.expiryMonth;
            form_data['expiryYear'] = result.expiryYear;
            form_data['last4'] = result.last4;
            form_data['token'] = result.token;
            form_data['save_token_request'] = SAVE_TOKEN;

            if (result.code == "200") {
                var $checkedRadio = $('input[name="o_payment_radio"]:checked');
                rpc(form_data.data_set, form_data).then(function(data) {

                    if (window.location.href.includes("/my/payment_method")) {
                        if (form_data.return_url) {
                            window.location = form_data.return_url;
                        } else {
                            debugger
                            window.location.reload();
                        }
                    } else {
                        $checkedRadio.val(data.id);
                        // document.getElementById('container_bambora').style.display = "hidden";
                        // document.getElementById('loading_image').style.display = "block";
                        self.el.submit();
                    }
                }).catch(function(error) {
                    // error.event.preventDefault();
                    providerForm.removeClass('d-none');
                    $('#bamboraModal').modal('hide');
                    if (error instanceof RPCError) {
                self._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                self._enableButton(); // The button has been disabled before initiating the flow.
            } else {
                return Promise.reject(error);
            }
                });
            }
        },

        // /**
        //  * @private
        //  */
        // bamboraCancel() {
        //     console.log("bamboraCancel Payment Form-->")
        //     if (window.location.href.includes('/my/payment_method')) {
        //         var btnPayPm = document.getElementById("o_payment_form_add_pm");
        //         btnPayPm.disabled = false;
        //     } else if (window.location.href.includes('/shop/payment')) {
        //         var btnPay = document.getElementById("o_payment_form_pay");
        //         btnPay.disabled = false;
        //     }
        //     location.reload();
        // },

        /**
         * @private
         * @param {DOMElement} element
         */
        getBamboraChkcquirerIdFromRadio(element) {
            return $(element).data("paymentOptionId");
        },

        /**
         * @private
         * @param {jQuery} $form
         */
        getBamboraChkFormData($form) {
            var unindexed_array = $form.serializeArray();
            var indexed_array = {};

            $.map(unindexed_array, function(n, i) {
                indexed_array[n.name] = n.value;
            });
            return indexed_array;
        },

        bamboraCancel() {
            console.log("bamboraCancel Payment Form-->")
            if (window.location.href.includes('/my/payment_method')) {
                var btnPayPm = document.getElementById("o_payment_form_add_pm");
                btnPayPm.disabled = false;
            } else if (window.location.href.includes('/shop/payment')) {
                var btnPay = document.getElementById("o_payment_form_pay");
                btnPay.disabled = false;
            }
            location.reload();
        },

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         */
        _onImportClickTest() {
            console.log("**********_onImportClickTest**********")

        }


})

$("#bamboraCancel").on('click', () => {
         $("#bamboraModal").remove();
});

