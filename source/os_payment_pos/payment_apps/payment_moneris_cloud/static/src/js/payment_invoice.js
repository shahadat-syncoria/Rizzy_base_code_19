odoo.define("payment_moneris_cloud.form_controller", function (require) {
  "use strict";

  var core = require("web.core");
  var Dialog = require('web.Dialog');
  var _t = core._t;
  var rpc = require("web.rpc");
  var session = require("web.session");


  var finalResponseCodes = ['207','209','210','211','220','450','451','452','453','454','454','455','460','461','462','463']
  var errorResponseCodes = ['450','451','452','453','454','454','455','460','461','462','463']
  

  var FormController = require("web.FormController");

  FormController.include({
    /**
     * @override
     */
    init: function () {
      this._super.apply(this, arguments);
      this.enable_reversals();
    },

    enable_reversals: function () {
      this.supports_reversals = true;
    },

    renderButtons: function () {
      this._super.apply(this, arguments); // Sets this.$buttons

      if (this.$buttons) {
        var self = this;
        var state = this.model.get(self.handle, { raw: true });

        this.$buttons.find(".send_payment_request_inv").click(function () {
          debugger;
          var sendBtn = document.getElementsByClassName("send_payment_request_inv")
          if (sendBtn) {
            sendBtn[0].innerHTML = "<i class='fa fa-spinner fa-spin' role='img' title='spinner'/>";
          }

          if ($('#terminal_message').length > 0) {
            $('#terminal_message')[0].innerHTML = "Waiting";
          }

          if ($('#btn-mon-cancel').length > 0) {
            $('#btn-mon-cancel')[0].style.display = "hide";
          }

          return self._sendPaymnetRequest(state);
        });

        this.$buttons.find(".send_refund_request").click(function () {
          var sendBtn = document.getElementsByClassName("send_refund_request")
          if (sendBtn) {
            sendBtn[0].innerHTML = "<i class='fa fa-spinner fa-spin' role='img' title='spinner'/>";
          }

          if ($('#terminal_message').length > 0) {
            $('#terminal_message')[0].innerHTML = "Waiting";
          }

          if ($('#btn-mon-cancel').length > 0) {
            $('#btn-mon-cancel')[0].style.display = "hide";
          }

          return self._sendPaymnetRequest(state);
        });
      }
    },

    /**
     * Send Payment Request button to the Moneris Terminal
     *
     * @private
     */
    _sendPaymnetRequest: function (state) {
      // var context = $(this).data("context");
      // var context = state.getContext();
        debugger
      var journal_id = state.data.journal_id;
      var journal_pos = document.getElementsByName("journal_id");
      if (journal_pos.length > 0) {
        for (let index = 0; index < journal_pos.length; index++) {
          if (journal_pos[index].options != undefined)
            journal_id = journal_pos[index].value;
        }
      }

      var payment_method_ids, payment_method_id;
      payment_method_ids = document.getElementsByName("payment_method_id")[0].children;
      for (let index = 0; index < payment_method_ids.length; index++) {
        if (payment_method_ids[index].children[0].checked == true) {
          payment_method_id = payment_method_ids[index].children[0].dataset.value;
        }
      }


      console.log("journal_id ===>>>", journal_id);
      console.log("payment_method_id ===>>>", payment_method_id);

      var settings = new monerisCloud.CloudSettings();

      if(state.context.active_ids != undefined){
        var move_ids = state.context.active_ids;
      }
      if(state.context.active_id != undefined){
        var move_ids = state.context.active_id;
      }
      
      var params = {
        'journal': {
          'journal_id': journal_id,
        },
        'move': {
          'move_ids': move_ids ,
        },
        'register': {
          'register_id': state.id,
        },
        'payment_method': {
          'payment_method_id': payment_method_id,
        },
      }


      var self = this;
      rpc.query({
        route: "/monerisinv/moneris_records",
        params: params,
      }).then(function (result) {
        self.result = result;
        var journal = self.result.journal;

        if (journal) {
          settings.cloud_store_id = journal.cloud_store_id;
          settings.cloud_api_token = journal.cloud_api_token;
          settings.cloud_terminal_id = journal.cloud_terminal_id;
          settings.cloud_pairing_token = journal.cloud_pairing_token;
          settings.cloud_postback_url = journal.cloud_postback_url;
          settings.cloud_integration_method = journal.cloud_integration_method;
          settings.cloud_cloud_environment = journal.cloud_cloud_environment;
          settings.cloud_cloud_paired = journal.cloud_cloud_paired;
          settings.cloud_cloud_ticket = journal.cloud_cloud_ticket;
          settings.cloud_inout_url = journal.cloud_inout_url;
          settings.cloud_inout_url = journal.cloud_inout_url;
          settings.cloud_out_url2 = journal.cloud_out_url2;
          settings.cloud_merchant_id = journal.cloud_merchant_id;
          self.terminal = new monerisCloud.Terminal(settings);

          state.terminal = self.terminal;
          state.terminal.settings = settings;
          state.result = result;

          //Depends on payment_method_id.code
          //if inbound--> Purchase
          //if outbound --> REFUND

          var payment_type = result.payment_method.payment_type;

          if (payment_type == "inbound") {
            var action = "PURCHASE";
          } else {
            var action = "REFUND";
          }

          console.log("payment_type-->", payment_type);
          console.log("action-->", action);

          return self._sendTransaction(action, state);
        }
      });
    },


    _onTransactionComplete: function (event, data) {
      console.log("_onTransactionComplete");
      console.log("event ===>>>>", event);

      if (event.exception) {
        if(data.action == 'PURCHASE'){
          var sendBtn = document.getElementsByClassName("send_payment_request_inv");
          if (sendBtn) {
            sendBtn[0].innerHTML = "RETRY";
          }
        }
        if(data.action == 'REFUND'){
          var rtnBtn = document.getElementsByClassName("send_refund_request");
          if (rtnBtn) {
            rtnBtn[0].innerHTML = "RETRY";
          }
        }
  

        if (event.exception == true) {
          Dialog.alert(self, _t(event.description), {
            title: _t('Terminal Error'),
          });
        } else {
          Dialog.alert(self, _t("Transaction was not processed correctly"), {
            title: _t('Terminal Error'),
          });
        }

        
        this.transactionResolve();
        if ("action" in data) {
          if (data.action != undefined) {
            this.result.move.moneris_last_action =
              data.action;
          }
        }
      } else {

        try {
          console.log("Session Update Trying");
          session.user_context.terminalResponse = JSON.stringify(event.terminalResponse);
          session.user_context.result = event.state.result;
        } catch (error) {
          console.log("Session Update Error" + str(error));
        }

        if (event) {
          if (event.terminalResponse) { 
              var action_create_payments = document.getElementsByName("action_create_payments");
              if(action_create_payments.length > 0){
                action_create_payments[0].click();
              }
              
              if ($('#terminal_message').length > 0) {
                  $('#terminal_message')[0].innerHTML = "Payment Successful";
              }
              // setTimeout(function () { location.reload(1); }, 1000);
          }
        }

      }

      this.transactionResolve(true);
    },


    _sendTransaction: function (transactionType, state) {
      console.log("_sendTransaction")
      console.log(state);
      // var order = state.data.id;
      return new Promise((resolve) => {
          this.transactionResolve = resolve;
          var journal_id, move_ids;
          var journal_pos = document.getElementsByName("journal_id");
          if (journal_pos.length > 0) {
            for (let index = 0; index < journal_pos.length; index++) {
              if (journal_pos[index].options != undefined)
                journal_id = journal_pos[index].value;
            }
          }
         

          if(state.context.active_ids != undefined){
            var move_ids = state.context.active_ids;
          }
          if(state.context.active_id != undefined){
            var move_ids = state.context.active_id;
          }

          var request_data =  {
            'transaction' : '_sendTransaction',
            'journal_id' : journal_id,
            'move_id' : move_ids,
            'transactionType' : transactionType,
          };
          var result = this.terminal.settings;
          console.log("request_data ===>>>", request_data);
          console.log("move_ids ===>>>", move_ids);
          return this._cloudRequest(request_data, state, result);

        });

    
  },

    /**
     * @private
     * @param {Object} request_data
     * @param {Object} state
     */
    _cloudRequest: function (request_data, state, result) {
        console.log("_cloudRequest")
        console.log("request_data ===>>>", request_data);
        console.log("state ===>>>", state)
        
        // if (request_data.transactionType != 'CANCEL') {
        //   var cancelBtn = document.getElementsByClassName("send_payment_cancel");
        //   if (cancelBtn) {
        //       cancelBtn[0].style.display = "none";
        //   }
        // }

        var xhr = new XMLHttpRequest();
        var val_url = '/moneriscloudinv/validation';
        xhr.open("POST", val_url, true);
        xhr.setRequestHeader("Content-Type", "application/json");

        if ($('#terminal_message').length > 0) {
          $('#terminal_message')[0].innerHTML = "Payment Request Sent";
        }
        var self = this;

        xhr.onreadystatechange = function () {
          if (this.readyState === 4 && this.status === 200) {
              var validation = JSON.parse(this.responseText);
              console.log("Response from terminal-->");
              console.log("validation ===>>>>", validation);

              if (validation) {
                console.log("111111 ===>>>>");
                  if (validation.result) {
                    console.log("222222 ===>>>>");
                          validation = JSON.parse(validation.result);
                          if (typeof(validation) =="string"){
                              validation = JSON.parse(validation);
                          }
                          console.log(validation);
                          if (validation.error == true) {
                            var description = validation.description;
                            if(!description){
                              description = validation.error.message;
                            }
                            var event = {'exception':true, 'description': description};
                            var data = {action : request_data.transactionType};
                            self._onTransactionComplete(event, data);
                        }
                          else if (validation.error == true) {
                              console.log("description")
                              console.log(validation.description)
                              var event = {'exception':true, 'description':validation.description};
                              var data = {action : request_data.transactionType};
                              self._onTransactionComplete(event,data);
                          }else{
                              //Success Transaction Message
                              if(validation.receipt.ResponseCode == "001" && validation.receipt.Completed == "false"){
                                console.log("Success Validation Message");
                                console.log(validation.receipt.Message);

                                if ($('#terminal_message').length > 0) {
                                  $('#terminal_message')[0].innerHTML = validation.receipt.Message;
                                }

                              }

                              if(validation.receipt.Error == "false"){
                        
                                  (function () {
                                      var intervalTime = 2000;
                                      var interval = setInterval(getTransaction,intervalTime);
                                      var maxPollErrors = 10;
                                      var pollErrors = 0;
                                      function getTransaction() {

                                          var xhr2 = new XMLHttpRequest();
                                          var tran_url = '/moneriscloud/transaction';
                                          xhr2.open("POST", tran_url, true);
                                          xhr2.setRequestHeader("Content-Type", "application/json");
                                          console.log('OPENED', xhr2.readyState); // readyState will be 1

                                          xhr2.onreadystatechange = function () {
                                              if (this.readyState === 4 && this.status === 200) {
                                                  var tranRes = JSON.parse(this.responseText);
                                                  console.log("Response from Cloud-->");
                                                  console.log("tranRes", tranRes);

                                                      if (tranRes) {
                                                          if (tranRes.result) {
                                                              if (tranRes.result.error ==  true) {
                                                                if ($('#terminal_message').length > 0) {
                                                                  $('#terminal_message')[0].innerHTML = "Error Message";
                                                                }
                                                                var event = {'exception':true,'description':tranRes.result.description};
                                                                var data = {action : request_data.transactionType};
                                                                clearInterval(interval); // stop the interval
                                                                self._onTransactionComplete(event,data);
                                                              }

                                                              console.log(typeof(tranRes));
                                                              
                                                              if (typeof(tranRes.result) =="string"){
                                                                  tranRes = JSON.parse(tranRes.result);
                                                              }
                                                              if (typeof(tranRes) =="string"){
                                                                  tranRes = JSON.parse(tranRes);
                                                              }
                                                              
                                                              console.log(tranRes);
                                                              console.log(typeof(tranRes));

                                                              if (tranRes) {
                                                                  if (tranRes.receipt) {
                                                                      if (tranRes.receipt.Error) {
                                                                          console.log("Error ===>>>", tranRes.receipt.Error);

                                                                          if (tranRes.receipt.Error == "false") {
                                                                              if (tranRes.receipt.Completed == "true") {
                                                                                var ResponseCode = parseInt(tranRes.receipt.ResponseCode);
                                                                                if(ResponseCode < 50){
                                                                                  console.log("tranRes.receipt.Completed");
                                                                                  var event = { success: true };
                                                                                  event.state = state;
                                                                                  event.terminalResponse = tranRes;
                                                                                  clearInterval(interval); // stop the interval
                                                                                  var data = {action : request_data.transactionType};
                                                                                }
                                                                                  
                                                                                if(ResponseCode >= 50){
                                                                                  console.log("Payment Declined");
                                                                                  var event = {'exception':true, 'description':'Payment Declined'};
                                                                                }

                                                                                if(ResponseCode == null){
                                                                                    console.log("Payment Incomplete");
                                                                                    var event = {'exception':true, 'description':'Payment Incomplete'};
                                                                                }
                                                                                  
                                                                                self._onTransactionComplete(event, data);
                                                                              }

                                                                              else if (tranRes.receipt.Completed == "false") {
                                                                                  console.log("tranRes.receipt.False");
                                                                              }
                                                                          }
                                                                          else if(tranRes.receipt.Error != "false") {
                                                                              var event = {'exception':true,'description':'Error in Transaction'};
                                                                              var data = {action : request_data.transactionType};
                                                                              clearInterval(interval); // stop the interval
                                                                              self._onTransactionComplete(event, data);
                                                                              
                                                                          } 
                                                                      }
                                                                  }
                                                              
                                                              }
                                                          }
                                                      }

                                              }


                                          }
                                          xhr2.onprogress = function () {
                                              console.log('LOADING', xhr2.readyState); // readyState will be 3
                                          };
                                          xhr2.onload = function () {
                                              console.log('DONE', xhr2.readyState); // readyState will be 4
                                          };
                                          xhr2.onerror = function() { // only triggers if the request couldn't be made at all
                                              console.log('Disconnected from server', xhr2.readyState);
                                                      console.log("Eroro");
                                                      pollErrors += 1;
                                                      if (pollErrors > maxPollErrors) {
                                                          clearInterval(interval); // stop the interval
                                                      }
                                          };
                                          var tran_data = {
                                              "params":
                                              {
                                                  "receiptUrl": validation.receipt.receiptUrl,
                                                  "request_data" : request_data,
                                              }
                                          }
                                          console.log(tran_data);
                                          xhr2.send(JSON.stringify(tran_data));
                                      
                                      }
                                  })();
                              }
                              //Failure Transaction Message
                              else if(validation.receipt.Error == "true"){
                                  var event = {'exception':true,'description':'Error Message: ' + validation.receipt.Message};
                                  var data = {};
                                  self._onTransactionComplete(event,data);
                              }

                      } 
                  }
              }


          }else if ((xhr.readyState === 4 && xhr.status !== 200)) {
              console.log(xhr.status);
              var event = {'exception':true, 'description':'Can not connect to Moneris Cloud'};
              data = {};
              self._onTransactionComplete(event,data);
          }
        }

        xhr.onprogress = function () {
          console.log('LOADING', xhr.readyState); // readyState will be 3
        };
        xhr.onload = function () {
            console.log('DONE', xhr.readyState); // readyState will be 4
        };
        xhr.onerror = function() { // only triggers if the request couldn't be made at all
            console.log('Disconnected from server', xhr.readyState);
        };

        if(state.context.active_ids != undefined){
          var move_ids = state.context.active_ids;
        }
        if(state.context.active_id != undefined){
          var move_ids = state.context.active_id;
        }

        var order = move_ids;
        var transactionType = request_data.transactionType;
        var request_data = this._populate_data(state, transactionType, result);
        console.log("request_data====>>>>-", request_data);


        var move_id, journal_id;
        var journal_id = document.getElementsByName('journal_id')[0].value;
        move_id = state.result.move.move_id;//Order ID
        console.log(move_id);
        
        
        var val_data = {
            "params":
            {
                "request_data" : request_data,
                "result" : result,
                "move_id" : move_id,
                "href" : window.location.href,
                "journal_id" : journal_id,
            }
        }
        console.log("val_data===>>>>", val_data);
        xhr.send(JSON.stringify(val_data));

        if ($('#terminal_message').length > 0) {
          $('#terminal_message')[0].innerHTML = "Waiting for card";
        }


    },


    _populate_data: function (state, transactionType, result) {
      if (this.terminal.settings.cloud_store_id == false 
          || this.terminal.settings.cloud_terminal_id == false
          || this.terminal.settings.cloud_api_token == false
          ) {
              var event = {'exception':true,'description':'Please configure Moneris Credentials Properly.'};
              this._onTransactionComplete(event,result);       
      }

      console.log("*****_populate_data*****");
      
      var txRequest = {}
      txRequest.storeId =  this.terminal.settings.cloud_store_id;
      txRequest.terminalId = this.terminal.settings.cloud_terminal_id;
      txRequest.txnType = transactionType;
      // postbackUrl method
      if (result.cloud_integration_method == 'postbackurl'){
          txRequest.apiToken = result.cloud_api_token;
          txRequest.postbackUrl = result.cloud_postback_url;
      }
      //Polling
      if (result.cloud_integration_method == 'polling'){
          txRequest.apiToken = result.cloud_api_token;
          // txRequest.polling = true;
      }
      //Combined
      if (txRequest.cloud_integration_method == 'combined'){
          txRequest.postbackUrl = result.cloud_postback_url;
          txRequest.polling = true;
      }

      function makeid(length) {
          var result           = '';
          var characters       = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
          var charactersLength = characters.length;
          for ( var i = 0; i < length; i++ ) {
             result += characters.charAt(Math.floor(Math.random() * charactersLength));
          }
          return result;
       }
      var incre = makeid(5);
      var order = state.result.move;
      if(state.result.move_names){
        order.name = state.result.move_names
      }

      if (order.cloud_request_id == null) {
        var incre =  '/1';
        incre = incre.replace(/ /g,'');
        order.cloud_request_id = state.result.move_names + incre;
      } else if(order.cloud_request_id != null){
          let newid = parseInt(order.cloud_request_id.split("/")[1]);
          incre = '/'+ (newid + 1).toString();
          order.cloud_request_id = state.result.move_names + incre;
      }


      if (state.result.move.moneris_request_id == null) {
        var requestId = this.terminal.settings.storeId + "_" + order.name + "/1";
        console.log("2. requestId" + requestId);
        requestId = requestId.replace(/ /g, "");
        console.log("requestId" + requestId);
      } else if (
        state.result.move.moneris_request_id != null ||
        (state.result.move.moneris_last_action ==
          "PURCHASE" &&
          transactionType == "PURCHASE")
      ) {
        console.log("moneris_request_id RETRY");
        let newid = 0;
        if (state.result.move.moneris_request_id.includes(order.name)) {
          newid = parseInt(state.result.move.moneris_request_id.split("/")[1]);
        }

        if (transactionType == "PURCHASE") {
          requestId =
            this.terminal.settings.cloud_store_id +
            "_" +
            state.data.communication +
            "/" +
            (newid + 1).toString();

          console.log("3. requestId" + requestId);
        }
        if (transactionType == "REFUND") {
          requestId =
            this.terminal.settings.cloud_store_id +
            "_" +
            order.name +
            "/" +
            (newid + 1).toString();

          console.log("4. requestId" + requestId);
        }

      }
      state.result.move.moneris_request_id = requestId;

      var order;

      try {
        order = state.result.move;
      } catch (error) {
        order = this.result.move;
      }

      var amountDisplay = state.data.amount;
      if (typeof (amountDisplay) === "number") {
        amountDisplay = amountDisplay.toFixed(2);
      }
      if (document.getElementsByName("amount").length > 0) {
        var amountDisplay = document.getElementsByName("amount")[0].children[1].value;
      }
      console.log("amountDisplay", amountDisplay)
      if (amountDisplay != state.data.amount) {
        var amountDisplay = document.getElementsByName("amount_div")[0].children[0].children[0].value;
        if (amountDisplay === undefined) {
          amountDisplay = document.getElementsByName("amount_div")[0].children[0].lastElementChild.value;
        }
      }
      if (amountDisplay.includes(",")) {
        amountDisplay = amountDisplay.replace(",", "");
      }

      //-----------------------------------------------------
      // Function for checking Payment Amount
      console.log("amountDisplay")
      console.log(amountDisplay)
      console.log("state.data.amount")
      console.log(state.data.amount);


      var currency = "";
      if($('.o_field_monetary').length > 0)
      {
        currency = $('.o_field_monetary')[$('.o_field_monetary').length - 1].innerText.replace("0.00","").replace(" ")[1]
      }

      if (state.result.journal && state.result.journal.use_cloud_terminal == true &&
        state.result.payment_method.code == 'electronic') {
          var acceptedLangs = ['fr_FR', 'fr_BE' , 'fr_CA', 'fr_CH'];
          if (acceptedLangs.includes(state.context.lang)){

            if (state.result.payment_method.payment_type == 'inbound' && Math.abs(amountDisplay/100) > Math.abs(state.data.amount)) {
              console.log("inbound: True")
              var description = "You can not pay with this amount." +
                "\r\nPayment Amount: "  + currency + " " + parseFloat(amountDisplay).toFixed(2) + "\r\nInvoice Due: "  + currency + " " + parseFloat(state.data.amount).toFixed(2) + ""
              var event = {};
              event.description = description
              event.exception = true;
              request.event = event;
            }
    
            if (state.result.payment_method.payment_type == 'outbound' && Math.abs(amountDisplay/100) > Math.abs(state.data.amount)) {
              console.log("outbound: True")
              var description = "You can not refund with this amount." +
                "\r\nPayment Amount: "   + currency + " " +  parseFloat(amountDisplay).toFixed(2) + "\r\nCredit Note Due Amount: "  + currency + " " + parseFloat(state.data.amount).toFixed(2) + ""
              var event = {};
              event.description = description;
              event.exception = true;
              request.event = event;
            }

        }else{

          if (state.result.payment_method.payment_type == 'inbound' && Math.abs(amountDisplay) > Math.abs(state.data.amount)) {
            console.log("inbound: True")
            var description = "You can not pay with this amount." +
              "\r\nPayment Amount: "  + currency + " " + parseFloat(amountDisplay).toFixed(2) + "\r\nInvoice Due: "  + currency + " " + parseFloat(state.data.amount).toFixed(2) + ""
            var event = {};
            event.description = description
            event.exception = true;
            request.event = event;
          }
  
          if (state.result.payment_method.payment_type == 'outbound' && Math.abs(amountDisplay) > Math.abs(state.data.amount)) {
            console.log("outbound: True")
            var description = "You can not refund with this amount." +
              "\r\nPayment Amount: "   + currency + " " +  parseFloat(amountDisplay).toFixed(2) + "\r\nCredit Note Due Amount: "  + currency + " " + parseFloat(state.data.amount).toFixed(2) + ""
            var event = {};
            event.description = description;
            event.exception = true;
            request.event = event;
          }

        }

      }

      if (transactionType == "PURCHASE") {
        txRequest.txnType = "purchase";
        if(state.data.amount){
          if(Math.floor(state.data.amount * 100.0)  != Math.floor(amountDisplay * 100.0)){
            console.log("Amount does not match");
            amountDisplay = state.data.amount;
          }
        }
        txRequest.request = {
          orderId : state.result.move_names,
          amount : amountDisplay,
        };


      } else if (transactionType == "CORRECTION") {
        console.log("VOID REQUEST");
        var data = {};
        data.referenceNumber = state.result.move.moneris_reference_number;
        var orderObj = {};
        orderObj.orderId = order.name.split(" ")[1];
        data.order = orderObj;
      } else if (transactionType == "CANCEL") {

        console.log("CANCEL REQUEST");
      } else if (transactionType == "REFUND") {

        console.log("REFUND REQUEST");
        console.log("amountDisplay");
        console.log(amountDisplay);

        var orderObj = {}
        // orderObj.orderId = state.result.move_names;
        orderObj.amount = amountDisplay;//(amountDisplay*100).toFixed(2);//"string"

        var moneris_cloud_transid = document.getElementsByName('moneris_cloud_transid');
        if(moneris_cloud_transid){
          orderObj.txnNumber = moneris_cloud_transid[0].innerText;//(amountDisplay*100).toFixed(2);//"string"
        }
        var moneris_cloud_receiptid = document.getElementsByName('moneris_cloud_receiptid');
        if(moneris_cloud_receiptid){
          orderObj.orderId = moneris_cloud_receiptid[0].innerText;//(amountDisplay*100).toFixed(2);//"string"
        }

        txRequest.request = orderObj;
        txRequest.txnType = "refund";

      }
      //=============================================================

      console.log("Request Object");
      console.log(txRequest);
      return txRequest;
  },





  });
});
