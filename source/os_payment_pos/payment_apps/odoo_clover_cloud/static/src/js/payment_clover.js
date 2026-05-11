odoo.define("odoo_clover_cloud.payment", function (require) {
  "use strict";

  const { Gui } = require("point_of_sale.Gui");
  var core = require("web.core");
  var PaymentInterface = require("point_of_sale.PaymentInterface");

  var _t = core._t;

  var rpc = require("web.rpc");
  var pos_model = require("point_of_sale.models");
  var ajax = require("web.ajax");

window.onTimApiReady = function () {};
window.onTimApiPublishLogRecord = function (record) {
    // Log only warning or errors
    if (record.matchesLevel(timapi.LogRecord.LogLevel.warning)) {
        timapi.log(String(record));
    }
};


var PaymentClover = PaymentInterface.extend({
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
      settings.cloverServerUrl = this.payment_method.clover_server_url;
      settings.cloverConfigId = this.payment_method.clover_config_id;
      settings.cloverJwtToken = this.payment_method.clover_jwt_token;
      settings.cloverDeviceId = this.payment_method.clover_device_id;
      settings.cloverDeviceName = this.payment_method.clover_device_name;
      settings.cloverXPosId = this.payment_method.clover_x_pos_id;
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
    },

    /**
     * @override
     */
    send_payment_cancel: function () {

      console.log("send_payment_cancel");
      this._super.apply(this, arguments);
      var action = "CANCEL";
      var pos_order = this.pos.get_order();
      pos_order.selected_paymentline.clover_action = action;
      console.log(
        "cloverpayments",
        pos_order.selected_paymentline.cloverpayments
      );
      return this._sendTransaction(action);
    },

    /**
     * @override
     */
    send_payment_request: function () {

      console.log("send_payment_request");
      console.log(this.pos.get_order().selected_paymentline.amount);

      if (this.pos.get_order().selected_paymentline.amount >= 0) {
        console.log("PURCHASE");
        var action = "PURCHASE";
      } else {
        var action = "REFUND";
      }
      if (this.pos.get_order().selected_paymentline.clover_action == "CANCEL") {
        action = "CANCEL";
      }

      console.log("action-->", action);
      this._super.apply(this, arguments);
      this.pos.get_order().selected_paymentline.setPaymentStatus("waitingCard");
      return this._sendTransaction(action);
    },

    /**
     * @override
     */
    send_payment_reversal: function () {

      console.log("send_payment_reversal");
      var action = "CANCEL";
      console.log("action", action);
      this._super.apply(this, arguments);
      this.pos.get_order().selected_paymentline.setPaymentStatus("reversing");
      return this._sendTransaction(action);
    },

    // --------------------------------------------------------------------------
    // Private
    // --------------------------------------------------------------------------

    _onTransactionComplete: function (event, data) {

      if (event.exception) {
        console.log(event.exception);

        if (event.exception == true) {
          Gui.showPopup("ErrorPopup", {
            title: _t("Terminal Response"),
            body: _t(event.description.message|| "Internal Error"),
          });
        }
        else {
          Gui.showPopup("ErrorPopup", {
            title: _t("Terminal Error"),
            body: _t("Transaction was not processed correctly"),
          });
        }
        this.transactionResolve();
        if ("action" in data) {
          if (data.action != undefined) {
            this.pos.get_order().selected_paymentline.clover_last_action =
              data.action;
          }
        }
      } else {
        debugger
        console.log("No Error");
        let payment_details_info  = data.response.data.payment
        let payment_card_info  = data.response.data.payment.cardTransaction
        let payment_line = this.pos.get_order().selected_paymentline
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



        this.pos.get_order().clover_request_id = data.paymetId
        this.pos.get_order().selected_paymentline.clover_request_id = data.paymetId

        this.transactionResolve(true);

      }
    },

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
    //             this.pos.get_order().selected_paymentline.set_receipt_info(value);
    //         }
    //     });
    // },

    _sendTransaction: function (transactionType) {
      var order = this.pos.get_order();
      return new Promise((resolve) => {
        this._cloverRequest(order, transactionType);
        this.transactionResolve = resolve;

      });
    },

    /**
     * @private
     * @param {Object} order
     * @param {Object} transactionType
     */
    _cloverRequest: function (order, transactionType) {
      var self = this;
      if (transactionType == "CANCEL") {
        var event = {
                exception: true
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
          description: "Please configure clover Credentials Properly.",
        };
        var result = {};
        self._onTransactionComplete(event, result);
      } else {
        self._createTrxRequest(transactionType);
      }
    },


    _createTrxRequest: function (transactionType) {
      console.log("_createTrxRequest");
      if (transactionType === "PURCHASE") {
        var pos_order = this.pos.get_order();
        var settings = this.terminal.settings;
        var selected_paymentline = this.pos.get_order().selected_paymentline;
        var amount = selected_paymentline.amount * 100.0;

        var headers = {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "X-Clover-Device-Id": settings.cloverDeviceId[1],
          "X-POS-Id": settings.cloverXPosId,
          "Authorization": "Bearer " + settings.cloverJwtToken,
        };
        var payload = {
          configId: settings.cloverConfigId,
          deviceId: settings.cloverDeviceId[1],
          posId: settings.cloverXPosId,
          idempotencyId: this.pos.get_order().name.replace(/\s/g, '')+Math.floor((Math.random() * 10) + 1),
          amount: amount,
          externalPaymentId: this.pos.get_order().name+"-"+Math.floor((Math.random() * 10) + 1),
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
          clover_order_id : pos_order.name,
          payment_method_id : selected_paymentline.payment_method.id,
          order_name : pos_order.name,
        }

        var self = this;
        ajax
          .jsonRpc("/pos/order/payment", "call", values)
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

        console.log("REFUND", "REFUND");
       var pos_order = this.pos.get_order();
        var settings = this.terminal.settings;
        var selected_paymentline = this.pos.get_order().selected_paymentline;
        var amount = selected_paymentline.amount * 100.0;
        // var refunded_order =

        var headers = {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "X-Clover-Device-Id": settings.cloverDeviceId[1],
          "X-POS-Id": settings.cloverXPosId,
          "Authorization": "Bearer " + settings.cloverJwtToken,
        };
        var payload = {
          move_type: "out_refund",
          clover_payment_id: pos_order.clover_request_id,
          configId: settings.cloverConfigId,
          deviceId: settings.cloverDeviceId[1],
          posId: settings.cloverXPosId,
          idempotencyId: "Refund-"+this.pos.get_order().name.replace(/\s/g, '')+"-"+Math.floor((Math.random() * 100) + 1),
          amount: amount,
          externalPaymentId: "Refund-"+this.pos.get_order().name+"-"+Math.floor((Math.random() * 100) + 1),
        };

        console.log("pos_order ===>>>", pos_order);
        console.log("headers ===>>>", headers);
        console.log("payload ===>>>", payload);
        console.log("selected_paymentline ===>>>", selected_paymentline);


        var values = {
          headers : headers,
          payload : payload,
          clover_order_id : pos_order.name,
          payment_method_id : selected_paymentline.payment_method.id,
          order_name : pos_order.name,
        }

        var self = this;
        ajax
          .jsonRpc("/pos/order/payment", "call", values)
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
          });
      }

      if (transactionType === "CANCEL") {
        // https://community.clover.com/questions/30406/partial-refund-amount-display.html
        var sel_payline = this.pos.get_order().selected_paymentline;
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
    },


    _createLogging: function (params) {
      try {
        var payment_method_name =
          document.getElementsByClassName("payment-terminal")[0].children[0]
            .innerText;
      } catch (error) {
        console.log("Error");
      }
      var pos_order = this.pos.get_order();
      if (pos_order.get_paymentlines().length > 0) {
        var payment_method_id =
          pos_order.get_paymentlines()[0].payment_method.id;

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
    },


  });



  export PaymentClover;
});
