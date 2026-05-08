// /* clover_checkout */
// odoo.define('payment_clover_checkout.payment_form', require => {
//     'use strict';
//
//     var ajax = require('web.ajax');
//
//     const checkoutForm = require('payment.checkout_form');
//     const manageForm = require('payment.manage_form');
//     var Dialog = require('web.Dialog');
//     var Widget = require('web.Widget');
//     var core = require('web.core');
//     const { loadJS } = require('@web/core/assets');
//
//
//     const clovercheckoutMixin = {
//
//
//      /**
//      * Prepare the inline form of clover for direct payment.
//      *
//      * @override method from payment.payment_form_mixin
//      * @private
//      * @param {string} provider - The provider of the selected payment option's provider
//      * @param {number} paymentOptionId - The id of the selected payment option
//      * @param {string} flow - The online payment flow of the selected payment option
//      * @return {Promise}
//      */
//     _prepareInlineForm: function (provider, paymentOptionId, flow) {
//       console.log("_prepareInlineForm");
//       if (provider !== "clover_checkout") {
//         return this._super(...arguments);
//       }
//       let acceptJSUrl = "https://checkout.clover.com/sdk.js";
//         return this._rpc({
//             route: '/payment/clovercheckout/get_provider_info',
//             params: {
//                 'provider_id': paymentOptionId,
//             },
//         }).then(providerInfo => {
//             if (providerInfo.state !== 'enabled') {
//                 acceptJSUrl = "https://checkout.sandbox.dev.clover.com/sdk.js";
//             }
//             this.cloverCheckoutInfo = providerInfo;
//         }).then(() => {
//             loadJS(acceptJSUrl);
//         }).guardedCatch((error) => {
//             error.event.preventDefault();
//             this._displayError(
//                 _t("Server Error"),
//                 _t("An error occurred when displayed this payment form."),
//                 error.message.data.message
//             );
//         });
// //      return loadJS(acceptJSUrl);
// //      return Promise.resolve()
//       },
//
//
//         /**
//          * Redirect the customer to clover_checkout hosted payment page.
//          *
//          * @override method from payment.payment_form_mixin
//          * @private
//          * @param {string} provider - The provider of the payment option's acquirer
//          * @param {number} paymentOptionId - The id of the payment option handling the transaction
//          * @param {object} processingValues - The processing values of the transaction
//          * @return {undefined}
//          */
//         _processRedirectPayment: function (provider, paymentOptionId, processingValues) {
//             if (provider !== 'clover_checkout') {
//                 return this._super(...arguments);
//             }
//             console.log(processingValues);
//             console.log(paymentOptionId);
//             // // Fetch the clover_checkoutments access token with specific permissions
//             // const accessToken = this._getclover_checkoutAccessToken('single');
//             // console.log("accessToken", accessToken)
//
//             // // Open a modal and show the payment form fields
//             // this._buildPopup(processingValues,accessToken);
//
//             // Fetch the clover_checkoutments access token with specific permissions
//             let accessToken ;
//
//             this._buildPopup(paymentOptionId, processingValues, accessToken);
//             // this._getclover_checkoutAccessToken('single')
//             //     .then(accessToken => {
//             //         console.log("accessToken", accessToken);
//             //
//             //         // Open a modal and show the payment form fields
//             //         this._buildPopup(paymentOptionId, processingValues, accessToken);
//             //     })
//             //     .catch(error => {
//             //         console.error('Error getting access token:', error);
//             //         // Handle the error as needed
//             //     });
//
//         },
//         _revokeBlockUI: function () {
//             if ($.blockUI) {
//                 $.unblockUI();
//             }
//             // $("#o_payment_form_pay").removeAttr('disabled');
//             //  this._disableButton(true);
//         },
//
//         _buildPopup: function (providerId, processingValues,accessToken) {
//
//             // var checked_radio = $('input[name="pm_id"]:checked');
//             debugger;
//             var checked_radio = this.$('input[type="radio"]:checked');
//             if (checked_radio[0].dataset.provider == "clover_checkout") {
//                 this._revokeBlockUI();
// //                const clover = new Clover('8f176cfbf7339ef5556bad115240e727', { //public-key
// //                    merchantId: 'NANK6094CCP51'
//                 const clover = new Clover(this.cloverCheckoutInfo.clover_public_key,);
//
//
//                 const elements = clover.elements();
//                 this._enableButton();
//                 var data = processingValues;
//
//
//
//                 var clovercheckoutModal = `
//                 <div id="clovercheckout_payment_form_modal" class="modal-gp modal fade" role="dialog" data-bs-backdrop="static" tabindex="-1">
//                     <div class="modal-dialog modal-lg" style="margin-top:100px;">
//
//                           <form action="#" method="post" id="payment-form-box">
//                           <div class="modal-content">
//                                 <div class="modal-header">
//                                     <h4 class="modal-title">Pay with Clover Checkout</h4>
//                                     <button type="button" class="close btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
//                                 </div>
//                                 <div class="modal-body">
//                           <div class="clover_container" >
//
//
//
//                             <div class="form-row top-row">
//                               <div id="card-number" class="field card-number"></div>
//                               <div class="input-errors" id="card-number-errors" role="alert"></div>
//                             </div>
//
//                             <div class="form-row">
//                               <div id="card-date" class="field third-width"></div>
//                               <div class="input-errors" id="card-date-errors" role="alert"></div>
//                             </div>
//
//                             <div class="form-row">
//                               <div id="card-cvv" class="field third-width"></div>
//                               <div class="input-errors" id="card-cvv-errors" role="alert"></div>
//                             </div>
//
//                             <div class="form-row">
//                               <div id="card-postal-code" class="field third-width"></div>
//                               <div class="input-errors" id="card-postal-code-errors" role="alert"></div>
//                             </div>
//
//                             <div id="card-response" role="alert"></div>
//
//                             <div class="button-container">
//                               <button type="submit" id="submit-button">Submit Payment</button>
//                             </div>
//                              <div class="clover-footer" style="padding: 18px 24px; background-color: #F4F5F5; border-radius: 0 0 14px 14px; text-align: center">
//                                 <div class="clover-secure-payments" style="color: #B1B6B8; font-family: Roboto; font-size: 14px; font-weight: bold; line-height: 16px;">
//                                     <img style="margin: -2px 8px;max-width: 12px;" src="https://checkout.sandbox.dev.clover.com/assets/icons/lock.png">Secure Payments Powered by <b>Clover</b><img style="margin: -4px 8px;max-width: 20px;" src="https://checkout.sandbox.dev.clover.com/assets/icons/clover-symbol.png">
//                                 </div>
//                                     <a class="clover-privacy-link" title="Privacy Policy" href="https://www.clover.com/privacy-policy" style="font-family: Roboto; font-size: 14px; font-weight: bold; line-height: 16px;">Privacy Policy</a>
//                              </div>
//
//                             </div>
//                             </div>
//                            </div>
//                           </form>
//
//
//                     </div>
//                 </div>`;
//                 $(document).ready(function () {
//                     "use strict";
//
//                     var accessToken;
//                     const form = document.getElementById('payment-form-box');
//
//
//                     const cardNumber = elements.create('CARD_NUMBER' );
//                     const cardDate = elements.create('CARD_DATE' );
//                     const cardCvv = elements.create('CARD_CVV');
//                     const cardPostalCode = elements.create('CARD_POSTAL_CODE');
//
//
//                     cardNumber.mount('#card-number');
//                     cardDate.mount('#card-date');
//                     cardCvv.mount('#card-cvv');
//                     cardPostalCode.mount('#card-postal-code');
//
//                     const cardResponse = document.getElementById('card-response');
//                     const displayCardNumberError = document.getElementById('card-number-errors');
//                     const displayCardDateError = document.getElementById('card-date-errors');
//                     const displayCardCvvError = document.getElementById('card-cvv-errors');
//                     const displayCardPostalCodeError = document.getElementById('card-postal-code-errors');
//
//
//
//
//
// //                    const paymentRequestButton = elements.create('PAYMENT_REQUEST_BUTTON', {
// //                            paymentReqData
// //                            });
// //                            paymentRequestButton.mount('#payment-request-button');
// //                            paymentRequestButton.addEventListener('paymentMethod', function(ev) {
// //                            alert(JSON.stringify(ev));
// //                            })
// //                            paymentRequestButton.addEventListener('paymentMethodStart', function(ev) {
// //
//                     //                              })
//
//                        debugger;
//                       // Handle real-time validation errors from the card element
//                       cardNumber.addEventListener('change', function(event) {
//                         console.log(`cardNumber changed ${JSON.stringify(event)}`);
//                         displayCardNumberError.innerHTML=event.CARD_NUMBER.error || '';
//                       });
//
//
// //                      cardNumberInput.addEventListener('input', function(event) {
// //                        console.log('Card Number:', event.target.value);
// //                      });
//
//
//                       cardNumber.addEventListener('blur', function(event) {
//                         console.log(`cardNumber blur ${JSON.stringify(event)}`);
//                         displayCardNumberError.innerHTML=event.CARD_NUMBER.error || '';
//                       });
//
//                       cardDate.addEventListener('change', function(event) {
//                         console.log(`cardDate changed ${JSON.stringify(event)}`);
//                         displayCardDateError.innerHTML=event.CARD_DATE.error || '';
//                       });
//
//                       cardDate.addEventListener('blur', function(event) {
//                         console.log(`cardDate blur ${JSON.stringify(event)}`);
//                         displayCardDateError.innerHTML=event.CARD_DATE.error || '';
//
//                       });
//
//                       cardCvv.addEventListener('change', function(event) {
//                         console.log(`cardCvv changed ${JSON.stringify(event)}`);
//                         displayCardCvvError.innerHTML=event.CARD_CVV.error || '';
//                       });
//
//                       cardCvv.addEventListener('blur', function(event) {
//                         console.log(`cardCvv blur ${JSON.stringify(event)}`);
//                         displayCardCvvError.innerHTML=event.CARD_CVV.error || '';
//                       });
//
//                       cardPostalCode.addEventListener('change', function(event) {
//                         console.log(`cardPostalCode changed ${JSON.stringify(event)}`);
//                       });
//
//                       cardPostalCode.addEventListener('blur', function(event) {
//                         console.log(`cardPostalCode blur ${JSON.stringify(event)}`);
//                         displayCardPostalCodeError.innerHTML=event.CARD_POSTAL_CODE.error || '';
//                       });
//
//                                           // Wait for the document to be fully loaded
//
//
//
//
//
//                         //                      form.addEventListener('submit', handleFormSubmit);/ Create credit card token from form */
//
//
//
// //
// //                    // Function to handle form submission
// //                    function handleFormSubmit(event) {
// //                      event.preventDefault();
// //                      clover.createToken().then(handleTokenResponse);
// //                    }
// //
// //                    // Function to handle token response
// //                    function handleTokenResponse(result) {
// //                      const displayError = document.getElementById('card-response');
// //                      if (result.errors) {
// //                        Object.values(result.errors).forEach(function (value) {
// //                          displayError.textContent = value;
// //                        });
// //                      } else {
// //                        cloverTokenHandler(result.token);
// //                      }
// //                    }
// //
// //                    // Function to handle token submission to server
// //                    function cloverTokenHandler(token) {
// //                      const hiddenInput = document.createElement('input');
// //                      hiddenInput.setAttribute('type', 'hidden');
// //                      hiddenInput.setAttribute('name', 'cloverToken');
// //                      hiddenInput.setAttribute('value', token);
// //                      form.appendChild(hiddenInput);
// //                      form.submit();
// //                    }
//
//                     // Function to handle card input change
// //                    function handleCardInputChange(event) {
// //                      console.log(`Input changed: ${event}`);
// //                      // Additional error handling logic if needed
// //                    }
//
// //                    $('form.payment-form-box').card({
// //                        container: '.card-wrapper',
// //
// //                        formSelectors: {
// //                            nameInput: 'input[name="CardHolderName"]',
// //                            numberInput: 'input[name="CardNumber_display"]',
// //                            expiryInput: 'input[name="CardExpireDateMonth"]',
// //                            cvcInput: 'input[name="CardCVV2"]',
// //                            postalCode: 'input[name="CardPostalCode"]'
// //                        }
// //                    });
//
//                     $('#submit-button').on('click', function (response) {
//                         // Disable the submit button to prevent multiple clicks
//                         $(this).prop('disabled', true);
//
//
//                         // Add a loader to the button
//                         $(this).html('<i class="fa fa-spinner fa-spin"></i> Verifying Card Information...');
//
//                         // Disable all fields in the modal
//                         $('#clovercheckout_payment_form_modal input').prop('disabled', true);
//
//                         // Clear any existing alerts
//                         $('#payment-alert').remove();
//                             event.preventDefault();
//                             clover.createToken()
//                                 .then(async function(result){
//                                     if (result.errors) {
//                                         Object.values(result.errors).forEach(function(value){
//                                             console.log(value);
//                                         });
//                                     } else{
//                                         accessToken = await result.token;
//                                         console.log(accessToken);
//
//                                         storePaymentMethod(accessToken);
//                                     }
//                                 }).catch(function(data){
//                                     console.log(data);
//                                 });
//
//                         console.log("saving card!!:");
//                         console.log(accessToken)
//                         var payment_done = false
//
//                         function storePaymentMethod(accessToken) {
//                             var isFromPaymentMethodPage = window.location.pathname === '/my/payment_method';
//
//                             ajax.jsonRpc('/payment/clovercheckout/store_payment_method', 'call', {
//                             reference: processingValues.reference,
//                             usage_mode: 'MULTIPLE',
//                             partner_id: processingValues.partner_id,
//                             token: accessToken,
//                             window_location: window.location.pathname
//                         }).then(function(response) {
//                             // Handle the success response from the server
//                             console.log('Payment method stored successfully:', response);
//                              if (isFromPaymentMethodPage) {
//                                          if(response.id){
//                                             savePaymentToken(response);
//                                          }else{
//                                              displayAlert('danger', response.error.message);
//                                          }
//                                             return;
//                                         }
//
//
//                                 debugger;
//                             // If the payment method is stored successfully, make a call to initiate the payment
//                             if (response) {
//                                 // Disable the submit button to prevent multiple clicks
//                                 $('#submit-button').prop('disabled', true);
//
//                                 // Add a loader to the button
//                                 $('#submit-button').html('<i class="fa fa-spinner fa-spin"></i> Processing Payment...');
//
//                                 // Disable all fields in the modal
//                                 $('#clovercheckout_payment_form_modal input').prop('disabled', true);
//
//                                 // Clear any existing alerts
//                                 $('#payment-alert').remove();
//                                 var payment_done = false
//
//                                 ajax.jsonRpc('/payment/clovercheckout/payment', 'call', {
//                                     reference: processingValues.reference,
//                                     provider_id: providerId,
//                                     currency_id: processingValues.currency_id,
//                                     access_token: response.id,
//                                     partner_id: processingValues.partner_id,
//                                     payment_ref: response.i,
//                                     amount: processingValues.amount,
//                                     token_response: response.id,
//                                     clover_data_id:response?.sources?.data?.[0] ?? ''
//
//                                 }).then(function(paymentResponse) {
//
//                                     // Handle the success response from the payment initiation
//                                     console.log('Payment initiated successfully:', paymentResponse);
//                                     var response = JSON.parse(paymentResponse);
//                                     // Remove the loader and redirect to the payment status page
//                                     if(response.status === 'succeeded' && response.paid === true){
//                                             payment_done = true
//                                             window.location = '/payment/status';
//                                             $('#submit-button').html('<i class="fa fa-spinner fa-spin"></i> Payment Completed...');
//                                      }else{
//                                         displayAlert('danger', response.error.message);
//
//                                         // Enable the submit button, remove the loader, and enable all fields
//                                         $('#submit-button').prop('disabled', false).html('<i class="fa fa-credit-card"></i> Pay Now');
//                                         $('#clovercheckout_payment_form_modal input').prop('disabled', false);
//                                     }
//                                 }).catch(function(paymentError) {
//                                     // Handle the error response from the payment initiation
//                                     console.error('Error initiating payment:', paymentError);
//
//                                     // Show an alert with the error message
//                                     displayAlert('danger', 'Error Processing Payment: The transaction could not be completed.');
//                                 }).finally(function() {
//                                     if(payment_done){
//                                         $('#submit-button').html('<i class="fa fa-spinner fa-spin"></i> Redirecting...');
//                                     }else{
//                                         displayAlert('danger', 'Invalid Card Information');
//
//                                         // Enable the submit button, remove the loader, and enable all fields
//                                         $('#submit-button').prop('disabled', false).html('<i class="fa fa-credit-card"></i> Pay Now');
//                                         $('#clovercheckout_payment_form_modal input').prop('disabled', false);
//                                     }
//                                 });
//                             }else{
//                                 // Enable the submit button, remove the loader, and enable all fields
//                                 $('#submit-button').prop('disabled', false).html('<i class="fa fa-credit-card"></i> Pay Now');
//                                 $('#clovercheckout_payment_form_modal input').prop('disabled', false);
//                             }
//                         }).catch(function(error) {
//                             // Handle the error response from the server
//                             console.error('Error storing payment method:', error);
//
//                             // Show an alert with the error message
//                             displayAlert('danger', 'Invalid Card Information');
//                         }).finally(function() {
//
//                         });
//
// //                                ajax.jsonRpc('/payment/clovercheckout/payment','call', {
// //                                    reference: processingValues.reference,
// //                                    provider_id: providerId,
// //                                    currency_id: processingValues.currency_id,
// //                                    access_token: accessToken,
// //                                    partner_id: processingValues.partner_id,
// //                                    payment_ref: response.id,
// //                                    amount: processingValues.amount,
// //                                    token_response: accessToken
// //                                }).then(function(paymentResponse) {
// //                                    // Handle the success response from the payment initiation
// //                                    console.log('Payment initiated successfully:', paymentResponse);
// //                                    var response = JSON.parse(paymentResponse);
// //                                    console.log('Payment initiated successfully:', response);
// //                                    // Remove the loader and redirect to the payment status page
// //                                    if(response.status === 'succeeded' && response.paid === true){
// //                                    payment_done = true
// //                                    window.location = '/payment/status';
// //                                    $('#submit-button').html('<i class="fa fa-spinner fa-spin"></i> Payment Completed...');
// //                                    }
// ////
// ////                                    window.location = '/payment/status';
// //                                }).catch(function(paymentError) {
// //                                    // Handle the error response from the payment initiation
// //                                    console.error('Error initiating payment:', paymentError);
// //
// //                                    // Show an alert with the error message
// //                                    displayAlert('danger', 'Error Processing Payment: The transaction could not be completed.');
// //                                }).finally(function() {
// //                                 if(payment_done){
// //                                        $('#submit-button').html('<i class="fa fa-spinner fa-spin"></i> Redirecting...');
// //                                    }else{
// //                                        displayAlert('danger', 'Payment processing failed.');
// //
// //                                        // Enable the submit button, remove the loader, and enable all fields
// //                                        $('#submit-button').prop('disabled', false).html('<i class="fa fa-credit-card"></i> Pay Now');
// //                                        $('#clovercheckout_payment_form_modal input').prop('disabled', false);
// //                                    }
// //
// //                                });
//                                 }
//
//
//
//                     });
//
//                     // Function to display Bootstrap alert
//                     function displayAlert(type, message) {
//                         var alertHtml = `
//                             <div id="payment-alert" class="alert alert-${type} alert-dismissible fade show" role="alert">
//                                 ${message}
//                                 <button type="button" class="close btn-close" data-bs-dismiss="alert" aria-label="Close">
//                                 </button>
//                             </div>
//                         `;
//                         $('#clovercheckout_payment_form_modal .modal-body').prepend(alertHtml);
//                     }
//
//
//                 });
//
//                 $(clovercheckoutModal).appendTo('#wrapwrap');
//                 $("#clovercheckout_payment_form_modal").modal('show');
//                 $("#clovercheckout_payment_form_modal").on("hidden.bs.modal", function () {
//                     $(this).remove();
//                     $("#o_payment_form_pay").removeAttr('disabled');
//                     $("#o_payment_form_pay .o_loader").remove();
//                     window.location.reload();
//                 });
//
//                 function savePaymentToken(response) {
//                     // Send the token ID to the server to save the payment token
//                     ajax.jsonRpc('/payment/clovercheckout/save_payment_token', 'call', {
//                         token_id: response.id,
//                         reference: processingValues.reference,
//                         provider_id: providerId,
//                         currency_id: processingValues.currency_id,
//                         partner_id: processingValues.partner_id,
//                         clover_checkout_id:response.sources.data[0]
//
//                     }).then(function(response) {
//                         window.location = '/payment/status';
//                         // Handle the success response if needed
//                         console.log('Payment token saved successfully:', response);
//                     }).catch(function(error) {
//                         // Handle the error response if needed
//                         console.error('Error saving payment token:', error);
//                     });
//                 }
//
//
//
// //            function cloverTokenHandler(token) {
// //                var form = document.getElementById('payment-form-box');
// //                var hiddenInput = document.createElement('input');
// //                hiddenInput.setAttribute('type', 'hidden');
// //                hiddenInput.setAttribute('name', 'cloverToken');
// //                hiddenInput.setAttribute('value', token);
// //                form.appendChild(hiddenInput);
// //                form.submit();
// //            }
// //
// //            $('form.payment-form-box').on('submit', function (event) {
// //                  event.preventDefault();
// //                  clover.createToken()
// //                      .then(function (result) {
// //                           if (result.errors) {
// //                                // Handle tokenization errors
// //                              console.error("Tokenization errors:", result.errors);
// //                           } else {
// //                              cloverTokenHandler(result.token);
// //                           }
// //                      })
// //                      .catch(function (error) {
// //                            // Handle tokenization failure
// //                            console.error("Tokenization failed:", error);
// //                      });
// //                  });
//             }
//
//
//
//         // Function to handle token submission to server
//         },
//
//         /**
//          * Prepare the options to init the clover_checkout object
//          *
//          * Function overriden in internal module
//          *
//          * @param {object} processingValues
//          * @return {object}
//         */
//         _prepareClovercheckoutOptions: function () {
//             return {};
//         },
//
//
//
//
//     };
//
//
//     checkoutForm.include(clovercheckoutMixin);
//     manageForm.include(clovercheckoutMixin);
//
// });