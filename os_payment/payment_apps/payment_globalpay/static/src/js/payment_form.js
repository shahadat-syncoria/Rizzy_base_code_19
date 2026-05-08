/* GlobalPay */
odoo.define('payment_globalpay.payment_form', require => {
    'use strict';

    var ajax = require('web.ajax');

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');
    var Dialog = require('web.Dialog');
    var Widget = require('web.Widget');
    var core = require('web.core');


    const globalpayMixin = {

        /**
         * Redirect the customer to GlobalPay hosted payment page.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the payment option's acquirer
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {undefined}
         */
        _processRedirectPayment: function (provider, paymentOptionId, processingValues) {
            if (provider !== 'globalpay') {
                return this._super(...arguments);
            }
            console.log(processingValues);
            console.log(paymentOptionId);
            // // Fetch the GlobalPayments access token with specific permissions
            // const accessToken = this._getGlobalPayAccessToken('single');
            // console.log("accessToken", accessToken)

            // // Open a modal and show the payment form fields
            // this._buildPopup(processingValues,accessToken);

            // Fetch the GlobalPayments access token with specific permissions
            let accessToken = false;
            this._buildPopup(paymentOptionId, processingValues, accessToken);
            // this._getGlobalPayAccessToken('single')
            //     .then(accessToken => {
            //         console.log("accessToken", accessToken);
            //
            //         // Open a modal and show the payment form fields
            //         this._buildPopup(paymentOptionId, processingValues, accessToken);
            //     })
            //     .catch(error => {
            //         console.error('Error getting access token:', error);
            //         // Handle the error as needed
            //     });
        
        },
        _revokeBlockUI: function () {
            if ($.blockUI) {
                $.unblockUI();
            }
            // $("#o_payment_form_pay").removeAttr('disabled');
            //  this._disableButton(true);
        },

        _buildPopup: function (providerId, processingValues,accessToken) {
            
            // var checked_radio = $('input[name="pm_id"]:checked');
            var checked_radio = this.$('input[type="radio"]:checked');
            if (checked_radio[0].dataset.provider == "globalpay") {
                this._revokeBlockUI();
                var data = processingValues;
                var state = "test"
                var CardHolderName = "Apple Mahmud"
                var test_mode = '1'
                var GlobalPayModal = `
                <div id="GlobalPay_payment_form_modal" class="modal-gp modal fade" role="dialog" data-bs-backdrop="static" tabindex="-1">
                    <div class="modal-dialog modal-lg" style="margin-top:100px;">
                        <form action="#" method="post" class="payment-form-box" >
                            <div class="modal-content">
                                <div class="modal-header">
                                    <h4 class="modal-title">Pay with GlobalPay</h4>
                                    <button type="button" class="close btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                </div>
                                <div class="modal-body">
                                    <div class="row">
                                        <div class="col-sm-6">
                                            <div class="form-group">
                                                <label>Card Holder Name:</label>
                                                <input type="text" id="card-holder-name" name="CardHolderName" class="form-control" value="${state == 'test' ? CardHolderName : ''}" />
                                            </div>
                                            <div class="form-group">
                                                <label>Card Number:</label>
                                                <input type="text" id="card-number" name="CardNumber_display" class="form-control" value="${state == 'test' ? '4263970000005262' : ''}" />
                                                <input type="hidden" name="CardNumber" class="form-control" value="${data.state == 'test' ? '4263970000005262' : ''}" />
                                            </div>
                                            <div class="row">
                                                <div class="form-group col-sm-6">
                                                    <label>Month:</label>
                                                    <input type="text" name="CardExpireDateMonth" class="form-control" value="${test_mode == '1' ? '12' : ''}"  />
                                                </div>
                                                <div class="form-group col-sm-6">
                                                    <label>Year:</label>
                                                    <input type="text" name="CardExpireDateYear" class="form-control" value="${test_mode == '1' ? '23' : ''}" />
                                                </div>
                                            </div>
                                            <div class="form-group">
                                                <label>Security Code:</label>
                                                <input type="text" id="card-cvv" name="CardCVV2" class="form-control" value="${test_mode == '1' ? '861' : ''}" />
                                            </div>
                                        </div>
                                        <div class="col-sm-6" style="margin-top:3%;">
                                            <div class='card-wrapper'></div>
                                        </div>
                                    </div>
                                </div>
                                <div class="modal-footer">
                                    <button href="#" id="submit-button" class="btn btn-primary btn-block submit"><i class="fa fa-credit-card"></i> Pay Now </button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>`;
                $(document).ready(function () {
                    "use strict";
                    $('form.payment-form-box').card({
                        container: '.card-wrapper',

                        formSelectors: {
                            nameInput: 'input[name="CardHolderName"]',
                            numberInput: 'input[name="CardNumber_display"]',
                            expiryInput: 'input[name="CardExpireDateMonth"], input[name="CardExpireDateYear"]',
                            cvcInput: 'input[name="CardCVV2"]'
                        }
                    });
                    $('form.payment-form-box input[name="CardNumber_display"]').on('keyup paste', function () {
                        $('form.payment-form-box input[name="CardNumber"]').val($(this).val().replace(/\s/g, ''));
                    });
                    
                    $('#submit-button').on('click', function () {
                        // Disable the submit button to prevent multiple clicks
                        $(this).prop('disabled', true);
                    
                        // Add a loader to the button
                        $(this).html('<i class="fa fa-spinner fa-spin"></i> Verifying Card Information...');
                    
                        // Disable all fields in the modal
                        $('#GlobalPay_payment_form_modal input').prop('disabled', true);
                    
                        // Clear any existing alerts
                        $('#payment-alert').remove();
                    
                        console.log("saving card!!:");
                    
                        // Use Odoo's _rpc method to make a remote call to the server
                        ajax.jsonRpc('/payment/globalpay/store_payment_method', 'call', {
                            reference: processingValues.reference,
                            usage_mode: 'MULTIPLE',
                            card_number: $('input[name="CardNumber"]').val(),
                            expiry_month: $('input[name="CardExpireDateMonth"]').val(),
                            expiry_year: $('input[name="CardExpireDateYear"]').val(),
                            cvv: $('input[name="CardCVV2"]').val(),
                            token: accessToken,
                        }).then(function(response) {
                            // Handle the success response from the server
                            console.log('Payment method stored successfully:', response);
                    
                            // If the payment method is stored successfully, make a call to initiate the payment
                            if (response && response.status === 'ACTIVE') {
                                // Disable the submit button to prevent multiple clicks
                                $('#submit-button').prop('disabled', true);
                            
                                // Add a loader to the button
                                $('#submit-button').html('<i class="fa fa-spinner fa-spin"></i> Processing Payment...');
                            
                                // Disable all fields in the modal
                                $('#GlobalPay_payment_form_modal input').prop('disabled', true);
                            
                                // Clear any existing alerts
                                $('#payment-alert').remove();
                                var payment_done = false

                                ajax.jsonRpc('/payment/globalpay/payment', 'call', {
                                    reference: processingValues.reference,
                                    provider_id: providerId,
                                    currency_id: processingValues.currency_id,
                                    access_token: accessToken,
                                    partner_id: processingValues.partner_id,
                                    payment_ref: response.id,
                                    amount: processingValues.converted_amount,
                                    token_response: response
                                }).then(function(paymentResponse) {
                                    // Handle the success response from the payment initiation
                                    console.log('Payment initiated successfully:', paymentResponse);
                    
                                    // Remove the loader and redirect to the payment status page
                                    $('#submit-button').html('<i class="fa fa-spinner fa-spin"></i> Payment Completed...');
                                    payment_done = true
                                    window.location = '/payment/status';
                                }).catch(function(paymentError) {
                                    // Handle the error response from the payment initiation
                                    console.error('Error initiating payment:', paymentError);
                    
                                    // Show an alert with the error message
                                    displayAlert('danger', 'Error Processing Payment: The transaction could not be completed.');
                                }).finally(function() {
                                    if(payment_done){
                                        $('#submit-button').html('<i class="fa fa-spinner fa-spin"></i> Redirecting...');
                                    }else{
                                        displayAlert('danger', 'Invalid Card Information');

                                        // Enable the submit button, remove the loader, and enable all fields
                                        $('#submit-button').prop('disabled', false).html('<i class="fa fa-credit-card"></i> Pay Now');
                                        $('#GlobalPay_payment_form_modal input').prop('disabled', false);
                                    }
                                });
                            }else{
                                // Enable the submit button, remove the loader, and enable all fields
                                $('#submit-button').prop('disabled', false).html('<i class="fa fa-credit-card"></i> Pay Now');
                                $('#GlobalPay_payment_form_modal input').prop('disabled', false);
                            }
                        }).catch(function(error) {
                            // Handle the error response from the server
                            console.error('Error storing payment method:', error);
                    
                            // Show an alert with the error message
                            displayAlert('danger', 'Invalid Card Information');
                        }).finally(function() {
                            
                        });
                    });
                    
                    // Function to display Bootstrap alert
                    function displayAlert(type, message) {
                        var alertHtml = `
                            <div id="payment-alert" class="alert alert-${type} alert-dismissible fade show" role="alert">
                                ${message}
                                <button type="button" class="close btn-close" data-bs-dismiss="alert" aria-label="Close">
                                </button>
                            </div>
                        `;
                        $('#GlobalPay_payment_form_modal .modal-body').prepend(alertHtml);
                    }
                    
                    
                });

                $(GlobalPayModal).appendTo('#wrapwrap');
                $("#GlobalPay_payment_form_modal").modal('show');
                $("#GlobalPay_payment_form_modal").on("hidden.bs.modal", function () {
                    $(this).remove();
                    $("#o_payment_form_pay").removeAttr('disabled');
                    $("#o_payment_form_pay .o_loader").remove();
                    window.location.reload();
                });
            }
        },

        /**
         * Prepare the options to init the GlobalPay object
         *
         * Function overriden in internal module
         *
         * @param {object} processingValues
         * @return {object}
        */
        _prepareGlobalPayOptions: function () {
            return {};
        },

        /**
         * Fetch the GlobalPayments access token from the server.
         *
         * @private
         * @param {string} permissions - The permissions to include in the request.
         * @returns {Promise<string>} A promise that resolves to the access token.
         */
        _getGlobalPayAccessToken: function (permissions = 'single') {
            return ajax.jsonRpc('/payment/globalpay/access_token', 'call', { permissions: permissions })
                .then(result => result.access_token)
                .catch(error => {
                    console.error('Error fetching GlobalPayments access token:', error);
                    throw error;
                });
        },
    };

    checkoutForm.include(globalpayMixin);
    manageForm.include(globalpayMixin);

});