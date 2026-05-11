/* global clovercloud */

import {_t} from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { rpc } from "@web/core/network/rpc";


export class PaymentClover extends PaymentInterface {

 // --------------------------------------------------------------------------
    // Public
    // --------------------------------------------------------------------------

    /**
     * @override
     */
    setup()  {
      super.setup(...arguments);
      // this.enable_reversals();
      var settings = new clovercloud.TerminalSettings();
      settings.connectionMode = "onFixIp";
      settings.cloverServerUrl = this.payment_method_id.clover_server_url;
      settings.cloverConfigId = this.payment_method_id.clover_config_id;
      settings.cloverJwtToken = this.payment_method_id.clover_jwt_token;
      settings.cloverDeviceId = this.payment_method_id.clover_device_id;
      settings.cloverDeviceName = this.payment_method_id.clover_device_name;
      settings.cloverXPosId = this.payment_method_id.clover_x_pos_id;
      this.terminal = new clovercloud.Terminal(settings);
      console.log(settings);

      if (settings.connectionMode === "onFixIp") {
        if (
          settings.$cloverServerUrl === 0 ||
          settings.$cloverConfigId === 0 ||
          settings.$cloverJwtToken === 0 ||
          settings.$cloverDeviceId === 0 ||
          settings.$cloverDeviceName === 0 ||
          settings.$cloverXPosId === 0
        ) {
          console.log(
            _(
              "Please configure for Clover Cloud Properly. Some credentials are misising."
            )
          );
        }
      }
    }

    /**
     * @override
     */
    sendPaymentCancel() {

      console.log("sendPaymentCancel");
      super.sendPaymentCancel(...arguments);
      // var action = "CANCEL";
      // var pos_order = this.pos.getOrder();
      // pos_order.getSelectedPaymentline().clover_action = action;
      // console.log(
      //   "cloverpayments",
      //   pos_order.getSelectedPaymentline().cloverpayments
      // );
      // return this._sendTransaction(action);
      return Promise.resolve();
    }

    /**
     * @override
     */
    sendPaymentRequest(){

      console.log("sendPaymentRequest");
      console.log(this.pos.getOrder().getSelectedPaymentline().amount);

      if (this.pos.getOrder().getSelectedPaymentline().amount >= 0) {
        console.log("PURCHASE");
        var action = "PURCHASE";
      } else {
        var action = "REFUND";
      }
      if (this.pos.getOrder().getSelectedPaymentline().clover_action == "CANCEL") {
        action = "CANCEL";
      }

      console.log("action-->", action);
      super.sendPaymentRequest(...arguments);
      this.pos.getOrder().getSelectedPaymentline().setPaymentStatus("waitingCard");
      return this._sendTransaction(action);
    }

    /**
     * @override
     */
    sendPaymentReversal () {

      console.log("sendPaymentReversal");
      var action = "CANCEL";
      console.log("action", action);
      super.sendPaymentReversal(...arguments);
      this.pos.getOrder().getSelectedPaymentline().setPaymentStatus("reversing");
      return this._sendTransaction(action);
    }

    // --------------------------------------------------------------------------
    // Private
    // --------------------------------------------------------------------------

    _onTransactionComplete(event, data) {

      if (event.exception) {
        console.log(event.exception);

        if (event.exception == true) {
          this.env.services.dialog.add(AlertDialog, {
            title: _t("Terminal Response"),
            body: _t(event.description.message|| "Internal Error"),
        });
        }
        else {
          this.env.services.dialog.add(AlertDialog, {
            title: _t("Terminal Error"),
            body: _t("Transaction was not processed correctly"),
          });
        }
        this.transactionResolve();
        if ("action" in data) {
          if (data.action != undefined) {
            this.pos.getOrder().getSelectedPaymentline().clover_last_action =
              data.action;
          }
        }
      } else {
        debugger
        console.log("No Error");
        let payment_details_info  = data.response.data.payment
        let payment_card_info  = data.response.data.payment.cardTransaction
        let payment_line = this.pos.getOrder().getSelectedPaymentline()
        // ================== All data save =====================


        debugger
        if (payment_details_info) {
          payment_line.clover_success = payment_details_info.result;
          payment_line.clover_result = payment_details_info.result;
          payment_line.clover_payment_id = payment_details_info.id;
          payment_line.clover_order_id = data.order_id;
          // this.clover_tender_id = json.clover_tender_id;
          payment_line.clover_ext_id = payment_details_info.externalPaymentId;
          payment_line.clover_emp_id = payment_details_info.employee.id;
          payment_line.clover_created_time = payment_details_info.createdTime;
          payment_line.clover_payment_result = payment_details_info.result;
        }
        if (payment_card_info) {
          payment_line.clover_entry_type = payment_card_info.entryType;
          payment_line.clover_type = payment_card_info.type;
          payment_line.clover_auth_code = payment_card_info.authCode;
          payment_line.clover_reference_id = payment_card_info.referenceId;
          payment_line.clover_transaction_no = payment_card_info.transactionNo;
          payment_line.clover_state = payment_card_info.state;

          // Odoo Basic Fields
          payment_line.card_type = payment_card_info.cardType;
          payment_line.cardholder_name = payment_card_info.cardholderName;
          if (payment_card_info.vaultedCard){
            payment_line.clover_last_digits = payment_card_info.vaultedCard.last4;
            payment_line.clover_expiry_date = payment_card_info.vaultedCard.expirationDate;
            payment_line.clover_token = payment_card_info.vaultedCard.token;

          }
        }



        this.pos.getOrder().clover_request_id = data.paymetId
        this.pos.getOrder().getSelectedPaymentline().clover_request_id = data.paymetId

        this.transactionResolve(true);

      }
    }

    // _printReceipts: function (receipts) {
    //     _.forEach(receipts, (receipt) => {
    //         var value = receipt.value.replace(/\n/g, "<br />");
    //         if (receipt.recipient === timapi.constants.Recipient.merchant && this.pos.proxy.printer) {
    //             this.pos.proxy.printer.print_receipt(
    //                 "<div class='pos-receipt'><div class='pos-payment-terminal-receipt'>" +
    //                     value +
    //                 "</div></div>"
    //             );
    //         } else if (receipt.recipient === timapi.constants.Recipient.cardholder) {
    //             this.pos.getOrder().getSelectedPaymentline().set_receipt_info(value);
    //         }
    //     });
    // },

    _sendTransaction(transactionType) {

      var order = this.pos.getOrder();
      return new Promise((resolve) => {
        this.transactionResolve = resolve;
        this._cloverRequest(order, transactionType);


      });
    }

    /**
     * @private
     * @param {Object} order
     * @param {Object} transactionType
     */
    _cloverRequest (order, transactionType) {

      var self = this;
      if (transactionType == "CANCEL") {
        var event = {
                exception: true,
                description:{message:"Please cancel from device"}
              };
        var result = {};
        self._onTransactionComplete(event, result);
      }

      // if (transactionType == "REFUND") {
      //   var event = {};
      //   var result = {};
      //   self._onTransactionComplete(event, result);
      // }

      if (
        self.terminal.settings.connectionMode == false ||
        self.terminal.settings.cloverServerUrl == false ||
        self.terminal.settings.cloverConfigId == false ||
        self.terminal.settings.cloverJwtToken == false ||
        self.terminal.settings.cloverDeviceId == false ||
        self.terminal.settings.cloverDeviceName == false ||
        self.terminal.settings.cloverXPosId == false
      ) {
        var event = {
          exception: true,
          description:{message:"Please configure clover Credentials Properly."}
        };
        var result = {};
        self._onTransactionComplete(event, result);
      } else {
        self._createTrxRequest(transactionType);
      }
    }


    _createTrxRequest (transactionType) {

      console.log("_createTrxRequest");
      if (transactionType === "PURCHASE") {
        var pos_order = this.pos.getOrder();
        var settings = this.terminal.settings;
        var selected_paymentline = this.pos.getOrder().getSelectedPaymentline();
        var amount = Math.round(selected_paymentline.amount * 100);

        var headers = {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "X-Clover-Device-Id": settings.cloverDeviceName,
          "X-POS-Id": settings.cloverXPosId,
          "Authorization": "Bearer " + settings.cloverJwtToken,
        };
        var payload = {
          configId: settings.cloverConfigId,
          deviceId: settings.cloverDeviceName,
          posId: settings.cloverXPosId,
          idempotencyId: this.pos.getOrder().pos_reference.replace(/\s/g, '')+Math.floor((Math.random() * 10) + 1),
          amount: amount,
          externalPaymentId: this.pos.getOrder().pos_reference+"-"+Math.floor((Math.random() * 10) + 1),
        };
        if (pos_order.partner){
          if (pos_order.partner.email){
            payload.email= pos_order.partner.email
          }
          if (pos_order.partner.phone){
            payload.phone= pos_order.partner.phone
          }
        }

        console.log("pos_order ===>>>", pos_order);
        console.log("headers ===>>>", headers);
        console.log("payload ===>>>", payload);
        console.log("selected_paymentline ===>>>", selected_paymentline);


        var values = {
          headers : headers,
          payload : payload,
          clover_order_id : pos_order.pos_reference,
          payment_method_id : selected_paymentline.payment_method_id.id,
          order_name : pos_order.pos_reference,
        }

        var self = this;
        rpc("/pos/order/payment", values)
          .then(function (payment) {
            debugger
            console.log("payment", payment);
            if(!payment.success){
              var event = {
                exception: true,
                description: {message:payment.err},
              };
              var result = {};
              self._onTransactionComplete(event, result);

            }
            else {
              var event = {
                exception: false
              };
              var result = payment.data;
              self._onTransactionComplete(event, result);
            }
          });



      }

      if (transactionType === "REFUND") {
        debugger
        // var $button = $('.button.next.validation');
        // $button[0].style.pointerEvents = "none";
        console.log("REFUND", "REFUND");
       var pos_order = this.pos.getOrder();
        var settings = this.terminal.settings;
        var selected_paymentline = this.pos.getOrder().getSelectedPaymentline();
        var amount = Math.round(selected_paymentline.amount * 100);
        // var refunded_order =

        var headers = {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "X-Clover-Device-Id": settings.cloverDeviceName,
          "X-POS-Id": settings.cloverXPosId,
          "Authorization": "Bearer " + settings.cloverJwtToken,
        };
        var payload = {
          move_type: "out_refund",
          clover_payment_id: pos_order.clover_request_id,
          configId: settings.cloverConfigId,
          deviceId: settings.cloverDeviceName,
          posId: settings.cloverXPosId,
          idempotencyId: "Refund-"+this.pos.getOrder().pos_reference.replace(/\s/g, '')+"-"+Math.floor((Math.random() * 100) + 1),
          amount: amount,
          externalPaymentId: "Refund-"+this.pos.getOrder().pos_reference+"-"+Math.floor((Math.random() * 100) + 1),
        };

        console.log("pos_order ===>>>", pos_order);
        console.log("headers ===>>>", headers);
        console.log("payload ===>>>", payload);
        console.log("selected_paymentline ===>>>", selected_paymentline);


        var values = {
          headers : headers,
          payload : payload,
          clover_order_id : pos_order.pos_reference,
          payment_method_id : selected_paymentline.payment_method_id.id,
          order_name : pos_order.pos_reference,
        }

        var self = this;
        rpc("/pos/order/payment", values)
          .then(function (payment) {
            debugger
            console.log("payment", payment);
            if(!payment.success){
               let err_message=""
              if (payment.err.hasOwnProperty('message')){
                err_message = payment.err.message
              }
              else {
                err_message=payment.err
              }
              var event = {
                exception: true,
                description: {message:err_message},
              };
              var result = {};

              self._onTransactionComplete(event, result);

            }
            else {
              var event = {
                exception: false
              };
              var result = payment.data;
              self._onTransactionComplete(event, result);
            }
             // $button[0].style.pointerEvents = "";
          });
      }

      if (transactionType === "CANCEL") {
        // https://community.clover.com/questions/30406/partial-refund-amount-display.html
        var sel_payline = this.pos.getOrder().getSelectedPaymentline();
        console.log("VOID VoidPaymentRequest");
        console.log(
          "sel_payline.clover_order_id===>>>",
          sel_payline.clover_order_id
        );
        console.log(
          "sel_payline.clover_payment_id===>>>",
          sel_payline.clover_payment_id
        );


      }
    }


    _createLogging (params) {
      try {
        var payment_method_name =
          document.getElementsByClassName("payment-terminal")[0].children[0]
            .innerText;
      } catch (error) {
        console.log("Error");
      }
      var pos_order = this.pos.getOrder();
      if (pos_order.get_paymentlines().length > 0) {
        var payment_method_id =
          pos_order.get_paymentlines()[0].payment_method_id.id;

        var commu = "";
        var id = payment_method_id; // window.location.href.split("id=")[1].split("&")[0];
        id = parseInt(id, 10);
        console.log("payment_id", id);

        var url = "/clover/updateflag";
        var xhr = new XMLHttpRequest();
        xhr.open("POST", url, false); // `false` makes the request synchronous
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.onreadystatechange = function () {
          if (this.readyState === 4 && this.status === 200) {
            var json = JSON.parse(this.responseText);
            var result = json.result;
            console.log("result", result);
          }
        };
        var data = {
          params: {
            model: "pos.payment.method",
            id: parseInt(id, 10),
            name: params.name,
            function: params.function,
            message: params.message + commu + "",
            payment_method_name: payment_method_name,
          },
        };
        xhr.send(JSON.stringify(data));
      }
    }

}