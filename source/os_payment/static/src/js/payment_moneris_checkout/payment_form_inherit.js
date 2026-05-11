/* global Accept */

import { _t } from '@web/core/l10n/translation';
import { PaymentForm } from '@payment/interactions/payment_form';
import { rpc,RPCError } from "@web/core/network/rpc";
import { patch } from '@web/core/utils/patch';

import { loadJS } from "@web/core/assets";

var response_codes = {
    "001": "Success",
    "902": "3-D Secure failed on response",
    "2001": "Invalid ticket/ticket re-use",
  }

const getMonerisPartnerId = () => {
  const hidden = document.getElementById("moneris_partner_id");
  if (!hidden) {
    return 0;
  }
  const parsed = parseInt(hidden.value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
};

const syncMonerisPartnerId = () => {
  const input = document.getElementById("moneris_partner_search");
  const hidden = document.getElementById("moneris_partner_id");
  const list = document.getElementById("moneris_partner_datalist");
  if (!input || !hidden || !list) {
    return;
  }
  const value = (input.value || "").trim();
  const option = Array.from(list.options).find((opt) => opt.value === value);
  hidden.value = option ? option.dataset.id || "0" : "0";
};

const bindMonerisPartnerSearch = () => {
  const input = document.getElementById("moneris_partner_search");
  if (!input) {
    return;
  }
  input.addEventListener("change", syncMonerisPartnerId);
  input.addEventListener("input", syncMonerisPartnerId);
};
//$(document).on('click', '#monerisBtnCncl', function(){
//             debugger
//
//            console.log("I am here");
//            try {
//                $("#monerisModal").modal('hide');
//                myCheckout.closeCheckout()
//            } catch (error) {
//            }
//                       });
patch(PaymentForm.prototype, {
   /**
     * Return all relevant inline form inputs based on the payment method type of the provider.
     *
     * @private
     * @param {number} providerId - The id of the selected provider
     * @return {Object} - An object mapping the name of inline form inputs to their DOM element
     */
    _getInlineFormInputs(providerId) {
      return {
        provider_id: document.getElementById(`mon_provider_id`),
        provider_state: document.getElementById(`mon_provider_state`),
        store_id: document.getElementById(`store_id`),
        api_token: document.getElementById(`api_token`),
        order_id: document.getElementById(`order_id`),
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
    _getPaymentDetails(providerId) {
      const inputs = this._getInlineFormInputs(providerId);
      try {
        // var providerForm = this.$(".moneris_form");
        var providerForm = this.el.querySelector('.moneris_form');
        var inputsForm = $("input", providerForm);
        var formData = this.getMonerisFormData(inputsForm);
      } catch (error) {
        console.log("error ===>>>", error);
        var formData = this.getMonerisFormData(inputs);

      }
      return formData;
    },

    /**
     * Prepare the inline form of Moneris for direct payment.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} provider - The provider of the selected payment option's provider
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} flow - The online payment flow of the selected payment option
     * @return {Promise}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
      console.log("_prepareInlineForm");
      if (providerCode !== "monerischeckout") {
        await super._prepareInlineForm(...arguments);
            return;
      }

      if (flow === "token") {
        return; // Don't show the form for tokens
      }

      this._setPaymentFlow("direct");

      let acceptJSUrl = "https://gateway.moneris.com/chkt/js/chkt_v1.00.js";
      return await rpc("/payment/monerischeckout/get_provider_info",{
          provider_id: paymentOptionId,
        },
      )
        .then((providerInfo) => {
          if (providerInfo.state !== "enabled") {
            acceptJSUrl = "https://gatewayt.moneris.com/chkt/js/chkt_v1.00.js";
          }
          this.authorizeInfo = providerInfo;
        })
        .then(() => {
          loadJS(acceptJSUrl);
        })
        .catch((error) => {
          // error.event.preventDefault();
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
     * Dispatch the secure data to Moneris Checkout.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} provider - The provider of the payment option's provider
     * @param {number} paymentOptionId - The id of the payment option handling the transaction
     * @param {string} flow - The online payment flow of the transaction
     * @return {Promise}
     */
    async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
      if (providerCode !== "monerischeckout" || flow === "token") {
        await super._initiatePaymentFlow(...arguments); // Tokens are handled by the generic flow
        return ;
      }

      if (!this._validateFormInputs(paymentOptionId)) {
        this._enableButton(); // The submit button is disabled at this point, enable it
        return Promise.resolve();
      }

      // // Build the authentication and card data objects to be dispatched to Moneris Checkout
      // const secureData = {
      //   authData: {
      //       apiLoginID: this.authorizeInfo.login_id,
      //       clientKey: this.authorizeInfo.client_key,
      //   },
      //   ...this._getPaymentDetails(paymentOptionId),
      // };

      var ev = {};
      ev.txContext = this.paymentContext;
      // ev.transactionRoute = this.txContext.transactionRoute;
      // var checked_radio = this.$('input[name="o_payment_radio"]:checked');
      var checked_radio = this.el.querySelector('input[name="o_payment_radio"]:checked');
      await this._createMonerisToken(ev, checked_radio);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Payment Request for Moneris Checkout
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} provider - The provider of the provider
     * @param {number} providerId - The id of the provider handling the transaction
     * @param {object} processingValues - The processing values of the transaction
     * @return {Promise}
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
      console.log("provider ===>>>", providerCode);
      console.log("providerId ===>>>", paymentOptionId);
      console.log("processingValues ===>>>", processingValues);

      if (providerCode !== "monerischeckout") {
        await super._processDirectFlow(...arguments);
        return ;
      }

      //======================================================================
      //==========PROCESS MONERIS PAYMENT=====================================
      //======================================================================
    },

    /**
     * Handle the response from Moneris Checkout and initiate the payment.
     *
     * @private
     * @param {number} providerId - The id of the selected provider
     * @param {object} response - The payment ticket returned by Moneris Checkout
     * @return {Promise}
     */
    _responseHandler(providerId, response) {
      if (response.response_code != "001") {
        let error = "";
        response.messages.message.forEach(
          (msg) => (error += `${msg.code}: ${msg.text}\n`)
        );
        this._displayError(
          _t("Server Error"),
          _t("We are not able to process your payment."),
          error
        );
        return Promise.resolve();
      }

      // Create the transaction and retrieve the processing values
      console.log("--------------------");
      return rpc(this.txContext.transactionRoute, this._prepareTransactionRouteParams(
          "monerischeckout",
          providerId,
          "direct"
        ),
      )
        .then((processingValues) => {
          // Initiate the payment
          return rpc("/payment/monerischeckout/payment", {
              reference: processingValues.reference,
              partner_id: processingValues.partner_id,
              opaque_data: response.opaqueData,
              access_token: processingValues.access_token,
            },
          ).then(() => (window.location = "/payment/status"));
        })
        .catch((error) => {
          if (error instanceof RPCError) {
                self._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                self._enableButton(); // The button has been disabled before initiating the flow.
            } else {
                return Promise.reject(error);
            }
        });
    },

    /**
     * Checks that all payment inputs adhere to the DOM validation constraints.
     *
     * @private
     * @param {number} providerId - The id of the selected provider
     * @return {boolean} - Whether all elements pass the validation constraints
     */
    _validateFormInputs(providerId) {
      console.log("_validateFormInputs ===>>>");
      const inputs = Object.values(this._getInlineFormInputs(providerId));
      console.log("inputs ===>>>", inputs);
      return inputs.every((element) => element.reportValidity());
    },

            /**
         * Prepare the params to send to the transaction route.
         *
         * For an provider to overwrite generic params or to add provider-specific ones, it must
         * override this method and return the extended transaction route params.
         *
         * @private
         * @param {string} provider - The provider of the selected payment option's provider
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {object} The transaction route params
         */
          _prepareMonericCheckoutTransactionRouteParams(provider, paymentOptionId, flow) {
              return {

                  // 'provider_id': this.txContext.providerId,
                  // 'payment_method_id': this.txContext.paymentMethodId,
                  // 'token_id': this.paymentContext.tokenId ?? null,
                  // 'amount':this.txContext.amount,
                  // 'flow': flow,
                  // 'tokenization_requested': this.txContext.tokenizationRequested,
                  // 'landing_route': this.txContext.landingRoute,
                  // 'is_validation': this.txContext.isValidation,
                  // 'access_token': this.txContext.accessToken
                  //     ? this.txContext.accessToken : undefined,
                  // 'csrf_token': odoo.csrf_token,
                  'provider_id': this.paymentContext.providerId,
                  'payment_method_id': this.paymentContext.paymentMethodId ?? null,
                  'token_id': this.paymentContext.tokenId ?? null,
                  'amount': this.paymentContext['amount'] !== undefined
                      ? parseFloat(this.paymentContext['amount']) : null,
                  'flow': this.paymentContext['flow'],
                  'tokenization_requested': this.paymentContext['tokenizationRequested'],
                  'landing_route': this.paymentContext['landingRoute'],
                  'is_validation': this.paymentContext['mode'] === 'validation',
                  'access_token': this.paymentContext['accessToken'],
                  'csrf_token': odoo.csrf_token,
                  'partner_id': parseInt(this.paymentContext['partnerId']),
                    'currency_id': this.paymentContext['currencyId']
                            ? parseInt(this.paymentContext['currencyId']) : null,
                    'reference_prefix':this.paymentContext['referencePrefix']?.toString(),
                  // 'invoice_id': this.txContext.invoiceId
                  //     ? parseInt(this.txContext.invoiceId) : null,


              };
          },


    // Moneris Checkout Functions

    /**
     * called when clicking on pay now or add payment event.
     *
     * @private
     * @param {Event} ev
     * @param {DOMElement} checkedRadio
     * @param {Boolean} addPmEvent
     */
    _createMonerisToken(ev, checked_radio, addPmEvent) {
//        function monerisCancel() {
//            debugger
//            // var btnPay = document.getElementById("o_payment_form_pay");
//            // if (window.location.href.includes('/my/payment_method')) {} else {
//            //     btnPay.disabled = false;
//            // }
//            console.log("I am here");
//            try {
//                $("#monerisModal").modal('hide');
//                myCheckout.closeCheckout()
//            } catch (error) {
//            }
//
//      }
      console.log("_createMonerisToken");
      this.txContext = ev.txContext;

      var providerForm = this.el.querySelector('.moneris_form');
      var inputsForm = $("input", providerForm);
      var formData = this.getMonerisFormData(inputsForm);
      const delegatedPartnerId = getMonerisPartnerId();
      if (delegatedPartnerId) {
        formData.moneris_partner_id = delegatedPartnerId.toString();
      }
      if (!formData.partner_id || formData.partner_id === "0") {
        const fallbackPartnerId = this.paymentContext?.partnerId;
        if (fallbackPartnerId) {
          formData.partner_id = fallbackPartnerId.toString();
        }
      }

      // if (this.options.partnerId === undefined) {
      //   console.warn(
      //     "payment_form: unset partner_id when adding new token; things could go wrong"
      //   );
      // }
      var checked_radio = this.el.querySelector('input[name="o_payment_radio"]:checked');
      var provider_id = this.txContext.providerId
      // console.log("provider_id ===>>>", provider_id);
      // this.txContext.providerId = provider_id;

      function myPageLoad(data) {
        console.log("myPageLoad::data ==>>>", data);
        data = JSON.parse(data);
        if (data.handler == "page_loaded") {
          if (data.response_code == "001") {
            var chktLoading = document.getElementsByClassName("chkt_loading");
            if (chktLoading.length > 0) {
              chktLoading[0].style.display = "none";
            }
            var btnCheckout = document.getElementById("process");
            if (btnCheckout) {
              btnCheckout.style.display = "none";
            }
          } else {
            console.log("myPageLoad failure--->", data.response_code);
            if (data.ticket) {
              myCheckout.closeCheckout([data.ticket]);
            }
            var monerisBtnCncl = document.getElementById("monerisBtnCncl");
            if (monerisBtnCncl) {
              monerisBtnCncl.click();
            }
            var message = "";
            if (data.response_code) {
              message = response_codes[data.response_code];
            }

            new Dialog(this, {
              title: _t("Moneris Checkout Error!"),
              size: "medium",
              $content: $("<div>").append(
                "Error Message: " +
                  message +
                  "\n.Please check your Moneris Checkout Configurations."
              ),
              buttons: [
                {
                  text: _t("Ok"),
                  classes: "btn-primary",
                  close: true,
                  click: execute,
                },
                {
                  text: _t("Cancel"),
                  close: true,
                },
              ],
            }).open();

          }
        }
      }

      function myErrorEvent(data) {
        console.log("myErrorEvent::data ==>>>", data);
        // When an error occurs during the checkout process. This requires the Moneris Checkout
        // session to be closed using the closeCheckout function
        myCheckout.closeCheckout([data.ticket]);
      }

      function myCancelTransaction(data) {
        console.log("myCancelTransaction::data ==>>>", data);
        myCheckout.closeCheckout([data.ticket]);
        var btnPay = document.getElementById("o_payment_form_pay");
        btnPay.disabled = false;
      }

      function myPaymentReceipt(data) {
        console.log("myPaymentReceipt:data--->", data);

        var response = JSON.parse(data);
        console.log("response--->", response);

        if (response.response_code == "001") {
          formData.ticket_no = response.ticket;
          var checked_radio = $('input[name="o_payment_radio"]:checked');
          console.log("checked_radio--->", checked_radio);

          if (checked_radio.length > 0) {
            var provider = checked_radio[0];

            if (window.location.href.indexOf("shop/payment") > -1) {
              for (let index = 0; index < checked_radio.length; index++) {
                const element = checked_radio[index];
                if (element.dataset.providerCode == "monerischeckout") {
                  provider = checked_radio[index];
                }
              }
            }

            console.log("provider--->", provider);
            console.log("provider--->", provider.dataset.providerCode);

            if (provider.dataset.providerCode == "monerischeckout") {
              var provider_id = provider.dataset.providerId;
              console.log("provider_id--->", provider_id);

              if (typeof data == "string") {
                data = JSON.parse(data);
              }

              if (data.ticket || data.name) {
                var ticket = data.name || data.ticket;
                console.log("ticket--->", ticket);
                data.ticket = ticket;
                var request = {
                  provider_id: provider.dataset.providerId,
                  provider: provider.dataset.providerCode,
                  preload_response: data,
                  formData: formData,
                };
                console.log("request--->", request);

                rpc( "/payment/monerischeckout/receipt",request)
                  .then(function (receipt) {
                    console.log("receipt response", receipt);
                    if (receipt) {
                      if (receipt.response.success != "true") {
                        let error = "";
                        response.messages.message.forEach(
                          (msg) => (error += `${msg.code}: ${msg.text}\n`)
                        );
                        // self._displayError(
                        //   _t("Server Error"),
                        //   _t("We are not able to process your payment."),
                        //   error
                        // );
                        self._displayErrorDialog(_t("Payment processing failed"), error);
                        return Promise.resolve();
                      }
                      debugger

                      if (window.location.href.indexOf("jhsa") > -1) {
                        location.reload();
                      }else{
                        debugger
                        var providerId = self.txContext.providerId;
                        var params = self._prepareMonericCheckoutTransactionRouteParams('monerischeckout', providerId, 'direct');

                        console.log("providerId", self.txContext.providerId);
                        console.log("transactionRoute", self.txContext.transactionRoute);
                        console.log("params", params);
                        // Create the transaction and retrieve the processing values

                        // returnrpc(self.txContext.transactionRoute,self._prepareMonericCheckoutTransactionRouteParams('monerischeckout', providerId, 'direct'),
                        return rpc(self.txContext.transactionRoute,self._prepareTransactionRouteParams(),
                        ).then(processingValues => {
                            console.log("processingValues", processingValues);
                            // Initiate the payment
                        if (window.location.href.includes("/my/payment_method")) {
                          const selectedPartnerId = getMonerisPartnerId();
                          if (selectedPartnerId) {
                            receipt.moneris_partner_id = selectedPartnerId;
                            if (receipt.formData) {
                              receipt.formData.moneris_partner_id = selectedPartnerId;
                            }
                          }
                        }
                        return rpc('/payment/monerischeckout/payment',{
                                  // 'reference': receipt.response.request.order_no,
                                  // 'partner_id': receipt.response.request.cust_id.split("/")[1],
                                  'opaque_data': receipt,
                                  // 'access_token': receipt.formData.access_token,
                                  // 'csrf_token': receipt.formData.csrf_token,

                                  'reference': processingValues.reference,
                                  'partner_id': processingValues.partner_id,
                                  // 'opaque_data': response.opaqueData,
                                  'access_token': processingValues.access_token,
                                }
                            ).then(() => window.location = '/payment/status');
                        }).catch((error) => {
                            if (error instanceof RPCError) {
                self._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                self._enableButton(); // The button has been disabled before initiating the flow.
            } else {
                return Promise.reject(error);
            }
                        });


                      }




                    } else {
                      var monerisBtnCncl =
                        document.getElementById("monerisBtnCncl");
                      if (monerisBtnCncl) {
                        monerisBtnCncl.click();
                      }
                      try {
                        myCheckout.closeCheckout([data.ticket]);
                        $("#monerisModal").modal("hide");
                      } catch (error) {}
                    }
                  })
                  .catch(function (error) {
                    // error.event.preventDefault();
                    providerForm.classList.remove('d-none');
                    // alert("Server Error:We are not able to add your payment method at the moment.")
                    if (error instanceof RPCError) {
                self._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                self._enableButton(); // The button has been disabled before initiating the flow.
            } else {
                return Promise.reject(error);
            }
                  });


              }
            }
          }


        }

        myCheckout.closeCheckout([data.ticket]);
      }


      function myErrorEvent(data) {
        console.log("myErrorEvent::data ==>>>", data);
        // When an error occurs during the checkout process. This requires the Moneris Checkout
        // session to be closed using the closeCheckout function
        myCheckout.closeCheckout([data.ticket]);
      }

      function myPaymentComplete(data) {
        debugger
        var self = this;
        self.myPaymentReceipt(data);
      }


      function myPageClosed(data) {
        if (data.handler == "page_closed") {
          if (data.response_code == "001") {
            console.error(
              "User has closed window or clicked Browser back button or Reload Button"
            );
          } else if (data.ticket) {
            console.error("JavaScript error occurred from Moneris Script");
          }
        }
      }

      function myPaymentSubmitted(data) {
        if (data.handler == "payment_submitted") {
          if (data.response_code == "001") {
            msg =
              "Cardholder clicked Checkout button and payment processing is started.";
            console.log(msg);
          }
        }
      }

      //======================================================================
      if (checked_radio) {
        debugger
        if (checked_radio.dataset.providerCode == "monerischeckout") {
          if (
            window.location.href.includes("/shop/payment") ||
            window.location.href.includes("my/orders") ||
            window.location.href.includes("/my/invoices/") ||
            window.location.href.includes("/my/payment_method") ||
            window.location.href.includes("/website_payment") ||
            window.location.href.includes("/payment/pay")
          ) {
            console.log("monerischeckout ===>>>>", checked_radio.dataset.providerCode)
            debugger
            var myCheckout = new monerisCheckout();
            var self = this;

            console.log("Create  myCheckout==>>>");
            console.log(
              "  formData.provider_state==>>>",
              formData.provider_state
            );

            if (formData.provider_state === "test") {
              myCheckout.setMode("qa");
            } else {
              myCheckout.setMode("prod");
            }
            myCheckout.setCheckoutDiv("monerisCheckout");
            myCheckout.setCallback("page_loaded", myPageLoad);
            myCheckout.setCallback("cancel_transaction", myCancelTransaction);
            myCheckout.setCallback("error_event", myErrorEvent);
            myCheckout.setCallback("payment_receipt", myPaymentReceipt);
            myCheckout.setCallback("payment_complete", myPaymentComplete);
            myCheckout.setCallback("page_closed", myPageClosed);
            myCheckout.setCallback("payment_submitted", myPaymentSubmitted);

            var session = session;
            var data = formData;
            data.provider_id = provider_id;
            data.href = window.location.href;

            if (window.location.href.includes("my/orders")) {
              data.sale_order_id = window.location.href
                .split("my/orders")[1]
                .split("/")[1]
                .split("?")[0];
            }

            if (window.location.href.includes("/my/invoices/")) {
              var invoice_id = window.location.href
                .split("/my/invoices/")[1]
                .split("?")[0];
              data.invoice_id = invoice_id;
            }
            try {
              var self = this;
              rpc("/payment/monerischeckout/preload", data)
                  .then(function (result) {
                    debugger
                    var result = JSON.parse(result);
                    console.log("result", result);
                    let response_error = result.errors_message || result.errors
                    if (response_error){
                        throw new Error(response_error)
                    }
                    if (result.response.ticket) {
                      var ticket = result.response.ticket;
                      self._enableButton();

                      console.log("remove class[d-none]");
                      // this.call('ui', 'unblock');


                      const $submitButton = $('button[name="o_payment_submit_button"]');
                      $submitButton.removeClass("d-none");
                      var chktLoading = document.getElementsByClassName("monerisBody");
                      if (chktLoading.length > 0) {
                        chktLoading[0].style.display = "none";
                      }
                      myCheckout.startCheckout([ticket]);
                    }

                    if (result.response.ticket) {
                      if (
                          window.location.href.includes("/shop/payment") ||
                          window.location.href.includes("/my/payment_method") ||
                          window.location.href.includes("/my/orders") ||
                          window.location.href.includes("my/invoices") ||
                          window.location.href.includes("pay/invoices") ||
                          window.location.href.includes("/payment/pay")
                      ) {
                        $("#monerisModal").modal('show');
                      }
                    }

                    if (result.response.success == "false") {
                      try {
                        console.log("payment_method", window.location.href.includes("/my/payment_method"));
                        if (window.location.href.includes("/my/payment_method")) {
                        } else {
                          var monerisBtnCncl = document.getElementById("monerisBtnCncl");
                          if (monerisBtnCncl) {
                            // monerisBtnCncl.click();
                          }
                        }

                        console.log("**********ENDS**************");


                      } catch (error) {
                      }

                      if (result.response.error) {
                        // alert(_t(JSON.stringify(result.response.error)));
                        // if (document.getElementsByName("o_payment_submit_button")) {
                        //   // document.getElementsByName("o_payment_submit_button")[0].removeClass("o_loader");
                        //   // document.getElementsByName("o_payment_submit_button")[0].disabled = "false";
                        //   self._enableButton();

                         // self._displayErrorDialog(_t("Payment processing failed"),  _t(JSON.stringify(result.response.error)));
                         // throw new Error(_t(JSON.stringify(result.response.error)));
                         //  throw (_t(JSON.stringify(result.response.error)))
                          self._displayErrorDialog(_t("Payment processing failed"), _t(JSON.stringify(result.response.error)));
                          self._enableButton();
                          return Promise.resolve();
                        // }
                      }
                    }

                  }).catch(function(error) {
                    if (error instanceof RPCError) {
                self._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                self._enableButton(); // The button has been disabled before initiating the flow.
                        return Promise.resolve();
            } else {
                self._displayErrorDialog(_t("Payment processing failed"), error.toString());
                self._enableButton(); // The button has been disabled before initiating the flow.
                return Promise.resolve();
            }
                });
            }
            catch (error) {
              debugger
              if (error instanceof RPCError) {
                self._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                self._enableButton(); // The button has been disabled before initiating the flow.
                  return Promise.resolve();
            } else {
                self._displayErrorDialog(_t("Payment processing failed"), error.toString());
                self._enableButton(); // The button has been disabled before initiating the flow.
                  return Promise.resolve();
            }
            }
          }
        }
      }else{
        console.log("Not Moneris Checkout")
      }
    },

    /**
     * @private
     * @param {DOMElement} element
     */
    getMonerisproviderIdFromRadio(element) {
      return $(element).data("paymentOptionId");
    },

    payMonerisEvent(ev) {
      console.log("payMonerisEvent");
      ev.preventDefault();
      // var checked_radio = this.$('input[name="o_payment_radio"]:checked');
      var checked_radio = this.el.querySelector('input[name="o_payment_radio"]:checked');;

      if (
        checked_radio.length === 1 &&
        this.isNewPaymentRadio(checked_radio) &&
        checked_radio.data("provider") === "monerischeckout"
      ) {
        if (window.location.href.includes("/my/invoices/")) {
          var pay_with = document.getElementById("pay_with");
          if (pay_with != undefined) {
            pay_with.style.display = "none";
          }
        }
        // if (window.location.href.includes("/my/orders/")) {
        //   var modalaccept = document.getElementById("modalaccept");
        //   if (modalaccept != undefined) {
        //     modalaccept.style.display = "none";
        //   }
        //   var modalaccept = document.getElementById("modalaccept");
        // }

        if (window.location.href.includes("/website_payment")) {
          var modalaccept = document.getElementById("modalaccept");
          if (modalaccept != undefined) {
            modalaccept.style.display = "none";
          }
          var modalaccept = document.getElementById("modalaccept");
        }
        if (window.location.href.includes("/payment/pay")) {
          var modalaccept = document.getElementById("modalaccept");
          if (modalaccept != undefined) {
            modalaccept.style.display = "none";
          }
          var modalaccept = document.getElementById("modalaccept");
        }

        var btnPay = document.getElementById("o_payment_form_pay");
        btnPay.dataset.toggle = "modal";
        btnPay.dataset.target = "#monerisModal";
        $("#monerisModal").modal({ backdrop: "static", keyboard: false });

        this._createMonerisToken(ev, checked_radio);
      } else {
        super.apply(this, arguments);
      }
    },

    /**
     * @private
     * @param {jQuery} $form
     */
    getMonerisFormData($form) {
      var unindexed_array = $form.serializeArray();
      var indexed_array = {};

      $.map(unindexed_array, function (n, i) {
        indexed_array[n.name] = n.value;
      });
      return indexed_array;
    },

});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bindMonerisPartnerSearch);
} else {
  bindMonerisPartnerSearch();
}

$("#monerisBtnCncl").on('click', () => {
          debugger;
          try {
            $("#monerisModal").modal('hide');
             myCheckout.closeCheckout();
           } catch (error) {

       }
});


