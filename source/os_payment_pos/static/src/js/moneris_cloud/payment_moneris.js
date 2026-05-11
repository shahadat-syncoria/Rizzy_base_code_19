/** @odoo-module */
/* global monerisCloud */

import {_t} from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { rpc } from "@web/core/network/rpc";
import { markup } from "@odoo/owl";
import {escape} from "@web/core/utils/strings";

export class PaymentMonerisCloud extends PaymentInterface {
     //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * @override
         */
        setup () {
            super.setup(...arguments);
            // this.enable_reversals();
            this.supports_reversals = false;

            var settings = new monerisCloud.CloudSettings();
            settings.connectionMode = "onFixIp";
            // settings.connectionIPString = this.payment_method_id.cloud_terminal_ip;
            // settings.connectionIPPort = this.payment_method_id.cloud_terminal_port;
            settings.merchantId = this.payment_method_id.cloud_merchant_id;
            // settings.configCode = this.payment_method_id.cloud_config_code;
            settings.terminalId = this.payment_method_id.cloud_terminal_id;
            settings.storeId = this.payment_method_id.cloud_store_id;
            settings.token = this.payment_method_id.token;
            settings.company_id = this.payment_method_id.company_id.id;
            this.terminal = new monerisCloud.Terminal(settings);
        }

        /**
         * @override
         */
        sendPaymentCancel (uuid) {
            console.log("sendPaymentCancel");
            // if (this.pos.getOrder().getSelectedPaymentline().payment_method_id.use_payment_terminal == 'moneris_cloud'){
            //     return;
            // }
            super.sendPaymentCancel(...arguments);
            // var action = 'CANCEL';
            // return this._sendTransaction(action);
        }

        /**
         * @override
         */
        sendPaymentRequest (uuid) {
            console.log("sendPaymentRequest");
            console.log(this.pos.getOrder().getSelectedPaymentline().amount);
            if (this.pos.getOrder().getSelectedPaymentline().amount >= 0) {
                var action = 'purchase';
            } else {
                var action = 'refund';
            }
            console.log("action-->",action);
            super.sendPaymentRequest(...arguments);
            this.pos.getOrder().getSelectedPaymentline().setPaymentStatus('waitingCard');
            return this._sendTransaction(action);

        }

        /**
         * @override
         */
        sendPaymentReversal (uuid) {
            console.log("sendPaymentReversal");
            super.sendPaymentReversal(...arguments);
            this.pos.getOrder().getSelectedPaymentline().setPaymentStatus('reversing');
            var action = 'purchase_correction';
            return this._sendTransaction(action);
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _onTransactionComplete (event, data) {
            console.log("_onTransactionComplete")
            console.log("event");console.log(event);
            Object.size = function(obj) {
                var size = 0, key;
                for (key in obj) {
                    if (obj.hasOwnProperty(key)) size++;
                }
                return size;
            };
            if (event.exception) {
                if(event.exception == true){
                    this.env.services.dialog.add(AlertDialog, {
                        title: _t('Moneris Cloud Error'),
                        body: _t(event.description),
                    });

                }else{
                   this.env.services.dialog.add(AlertDialog, {
                        title: _t('Terminal Error'),
                        body: _t('Transaction was not processed correctly'),
                    });
                }
                this.transactionResolve();
            }
            else {
                console.log("No Error");
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

        _sendTransaction (transactionType) {
            var order = this.pos.getOrder();
            return new Promise((resolve) => {
                this.transactionResolve = resolve;
                var request_data =  {
                        'transaction' : '_sendTransaction',
                        'payment_method_id' : order.getSelectedPaymentline().payment_method_id.id,
                        'transactionType' : transactionType,
                };
                console.log("_sendTransaction");
                rpc('/moneriscloud/gettransaction', request_data
                ).then(this._cloudRequest.bind(this, request_data));
            });
        }



        /**
         * @private
         * @param {Object} request_data
         * @param {Object} result
         */
        _cloudRequest (request_data,result) {
            // debugger
            result = JSON.parse(result);
            console.log("request_data ===>>>",  request_data);
            console.log("result ===>>>",  result);
            console.log("Payment Line ===>>>",  this.pos.getOrder().getSelectedPaymentline().uuid);
            var selected_paymentline = this.pos.getOrder().getSelectedPaymentline()


            if (result.error != true) {
                if (result.use_payment_terminal == 'moneris_cloud') {
                        if (request_data.transactionType != 'CANCEL') {
                            var cancelBtn = document.getElementsByClassName("sendPaymentCancel");
                            if (cancelBtn && cancelBtn.length > 0) {
                                cancelBtn[0].style.display = "none";
                            }
                        var xhr = new XMLHttpRequest();
                        var val_url = '/moneriscloud/validation';
                        xhr.open("POST", val_url, true);
                        xhr.setRequestHeader("Content-Type", "application/json");
                        console.log('OPENED', xhr.readyState); // readyState will be 1
                        var self = this;
                        xhr.onreadystatechange = async function () {
                            // debugger
                                if (this.readyState === 4 && this.status === 200) {
                                    var tranRes = JSON.parse(this.responseText);
                                    if (tranRes) {
                                        if (tranRes.result) {
                                            if (typeof (tranRes.result) == "string") {
                                                tranRes = JSON.parse(tranRes.result);
                                            }
                                            if (typeof (tranRes) == "string") {
                                                tranRes = JSON.parse(tranRes);
                                            }

                                            if (tranRes.error == true) {
                                                if (self.payment_method_id.is_moneris_go_cloud){
                                                    var error_description = 'Error in Transaction'
                                                    try {
                                                        if (tranRes.description.statusCode=='5904') {
                                                            selected_paymentline.is_same_ipodency = true;
                                                            error_description = 'Pinpad is Currently Performing Another Transaction. Please complete the transaction or reset the payment terminal. \nERROR CODE:5904'
                                                        }
                                                        else if (tranRes.description.statusCode=='408') {
                                                            selected_paymentline.is_same_ipodency = true;
                                                            error_description = tranRes.description.data.response[0].status+'\nERROR CODE:'+tranRes.description.statusCode
                                                        }
                                                        else if (tranRes.description.statusCode=='5903' || tranRes.description.statusCode=='5476') {
                                                            selected_paymentline.is_same_ipodency = true;
                                                            error_description = tranRes.description.data.response[0].status+'\nERROR CODE:'+tranRes.description.statusCode
                                                        }
                                                        else{
                                                           error_description  = tranRes.description.data.response[0].status+'\nERROR CODE:'+tranRes.description.statusCode

                                                        }

                                                    }
                                                    catch (error) {
                                                        console.log(error);
                                                    }
                                                    var event = {
                                                    'exception': true,
                                                    'description': error_description
                                                };
                                                }
                                                else{
                                                    var event = {
                                                    'exception': true,
                                                    'description': tranRes.description
                                                };
                                                }

                                                var data = {};
                                                return self._onTransactionComplete(event, data);
                                            }
                                            console.log(typeof (tranRes));


                                            console.log(tranRes);
                                            console.log(typeof (tranRes));

                                            //==================================================
                                            //ResponseCode
                                            //==================================================
                                            // Result
                                            // 0 – 49 (inclusive) Approved
                                            // 50 – 999 (inclusive) Declined
                                            // null Incomplete
                                            //==================================================
                                            try {
                                                if (tranRes) {
                                                    if (tranRes.receipt === undefined ){
                                                        throw "Error"
                                                    }
                                                    if (tranRes.receipt) {
                                                        if (self.payment_method_id.is_moneris_go_cloud){
                                                            if (tranRes.receipt.statusCode ) {
                                                            if (tranRes.receipt.statusCode == "5207") {
                                                                if (tranRes.receipt.Completed == "true") {
                                                                    var response = tranRes.receipt.data.response[0]

                                                                    var ResponseCode = parseInt(response.responseCode);
                                                                    if (ResponseCode < 50) {
                                                                        var order = self.pos.getOrder()
                                                                        var paymentline = order.getSelectedPaymentline();
                                                                        if (response.tipAmount && order.config_id.tip_product_id){
                                                                            self.pos.setTip(parseFloat(response.tipAmount)/100);
                                                                            order.getSelectedPaymentline().setAmount( order.getSelectedPaymentline().amount + (parseFloat(response.tipAmount)/100))
                                                                        }


                                                                        // ===========================
                                                                        //         Receipt ID save in pos order

                                                                        // ============================
                                                                        paymentline.card_type = response.cardType;
                                                                        paymentline.transaction_id = response.transactionId;
                                                                        paymentline.moneris_cloud_completed = response.completed;
                                                                        paymentline.moneris_cloud_transtype = response.action;
                                                                        // paymentline.moneris_cloud_error = response.Error;
                                                                        paymentline.moneris_cloud_responsecode = response.responseCode;
                                                                        paymentline.moneris_cloud_iso = response.iso;
                                                                        // paymentline.moneris_cloud_pan = response.Pan;
                                                                        paymentline.moneris_cloud_cardtype = response.cardType;
                                                                        paymentline.moneris_cloud_cardname = response.cardName;
                                                                        // paymentline.moneris_cloud_accounttype = response.AccountType;
                                                                        // paymentline.moneris_cloud_cvmindicator = response.CvmIndicator;
                                                                        paymentline.moneris_cloud_authcode = response.authCode;
                                                                        // paymentline.moneris_cloud_invoicenumber = response.InvoiceNumber;
                                                                        // paymentline.moneris_cloud_applabel = response.AppLabel;
                                                                        // paymentline.moneris_cloud_cncryptedcardinfo = response.EncryptedCardInfo;
                                                                        // paymentline.moneris_cloud_transdate = response.TransDate;
                                                                        // paymentline.moneris_cloud_transtime = response.TransTime;
                                                                        paymentline.moneris_cloud_amount = response.totalAmount;
                                                                        // paymentline.moneris_cloud_referencenumber = response.ReferenceNumber;
                                                                        if (response.action === 'purchase') {
                                                                            // debugger
                                                                            paymentline.moneris_cloud_receiptid = response.orderId;
                                                                            order.moneris_cloud_receiptid = response.orderId;
                                                                            order.moneris_cloud_transid = response.transactionId;

                                                                        }
                                                                        paymentline.moneris_cloud_transid = response.transactionId;
                                                                        // paymentline.moneris_cloud_timeout = response.TimedOut;
                                                                        paymentline.moneris_cloud_cloudticket = tranRes.receipt.CloudTicket;
                                                                        paymentline.moneris_cloud_txnname = tranRes.receipt.TxnName;
                                                                        var event = {'description': 'Payment Completed'};
                                                                        self._delete_last_refund_data();
                                                                        try{
                                                                            // let receipt_data = await self.env.services.rpc('/moneriscloud/getreceipt',
                                                                            //     {"payment_method_id":order.getSelectedPaymentline().payment_method_id.id,
                                                                            //                 "transaction_resposnse": response.receipt
                                                                            // }
                                                                            // );
                                                                            if (response.receipt){
                                                                            var order = self.pos.getOrder()
                                                                            var paymentline = order.getSelectedPaymentline();
                                                                            var parsed_data=response.receipt

                                                                                // debugger
                                                                            paymentline.cloud_receipt_customer = parsed_data
                                                                            paymentline.cloud_receipt_merchant = parsed_data
                                                                            // console.log(data)
                                                                            console.log(paymentline.cloud_receipt_customer)
                                                                            }





                                                                            // .then(function (data) {
                                                                            //     var order = self.pos.getOrder()
                                                                            //     var paymentline = order.getSelectedPaymentline();
                                                                            //     var parsed_data=JSON.parse(data)
                                                                            //     if (parsed_data.length === 2) {
                                                                            //         // debugger
                                                                            //     paymentline.cloud_receipt_customer = parsed_data[0].receipt.Receipt
                                                                            //     paymentline.cloud_receipt_merchant = parsed_data[1].receipt.Receipt
                                                                            //     // console.log(data)
                                                                            //     console.log(paymentline.cloud_receipt_customer)
                                                                            //     }
                                                                            //
                                                                            //
                                                                            // });
                                                                        }
                                                                        catch(error){
                                                                            console.log("Receipt Fetch Failed.")
                                                                        }





                                                                    }

                                                                    if (ResponseCode >= 50) {
                                                                        console.log("Payment Declined");
                                                                        var event = {
                                                                            'exception': true,
                                                                            'description': 'Payment Declined\nERROR CODE:'+ResponseCode
                                                                        };
                                                                    }

                                                                    if (ResponseCode == null) {
                                                                        console.log("Payment Incomplete");
                                                                        var event = {
                                                                            'exception': true,
                                                                            'description': 'Payment Incomplete'
                                                                        };
                                                                    }
                                                                    var data = {};
                                                                    // debugger
                                                                    self._onTransactionComplete(event, data);
                                                                } else if (tranRes.receipt.Completed === "false") {
                                                                    console.log("tranRes.receipt.False");
                                                                    var event = {
                                                                    'exception': true,
                                                                    'description': tranRes.receipt.status+'\nERROR CODE:'+tranRes.receipt.statusCode
                                                                };
                                                                var data = {};
                                                                self._onTransactionComplete(event, data);
                                                                }
                                                            } else if (tranRes.receipt.statusCode) {
                                                                var event = {
                                                                    'exception': true,
                                                                    'description': tranRes.receipt.status+'\nERROR CODE:'+tranRes.receipt.statusCode
                                                                };
                                                                var data = {};
                                                                self._onTransactionComplete(event, data);

                                                            }
                                                        }
                                                        }
                                                        else {
                                                            if (tranRes.receipt.Error) {
                                                            if (tranRes.receipt.Error == "false") {
                                                                if (tranRes.receipt.Completed == "true") {

                                                                    var ResponseCode = parseInt(tranRes.receipt.ResponseCode);
                                                                    if (ResponseCode < 50) {
                                                                        console.log("tranRes.receipt.Completed");
                                                                        var order = self.pos.getOrder()
                                                                        var paymentline = order.getSelectedPaymentline();
                                                                        if (tranRes.receipt.TipAmount && order.config_id.tip_product_id){
                                                                            var tip_amount = parseFloat(tranRes.receipt.TipAmount);
                                                                            self.pos.setTip(tip_amount);
                                                                            order.getSelectedPaymentline().setAmount(
                                                                                order.getSelectedPaymentline().amount + tip_amount
                                                                            );
                                                                        }


                                                                        // ===========================
                                                                        //         Receipt ID save in pos order

                                                                        // ============================
                                                                        paymentline.card_type = tranRes.receipt.CardType;
                                                                        paymentline.transaction_id = tranRes.receipt.TransId;
                                                                        paymentline.moneris_cloud_completed = tranRes.receipt.Completed;
                                                                        paymentline.moneris_cloud_transtype = tranRes.receipt.TransType;
                                                                        paymentline.moneris_cloud_error = tranRes.receipt.Error;
                                                                        paymentline.moneris_cloud_responsecode = tranRes.receipt.ResponseCode;
                                                                        paymentline.moneris_cloud_iso = tranRes.receipt.ISO;
                                                                        paymentline.moneris_cloud_pan = tranRes.receipt.Pan;
                                                                        paymentline.moneris_cloud_cardtype = tranRes.receipt.CardType;
                                                                        paymentline.moneris_cloud_cardname = tranRes.receipt.CardName;
                                                                        paymentline.moneris_cloud_accounttype = tranRes.receipt.AccountType;
                                                                        paymentline.moneris_cloud_cvmindicator = tranRes.receipt.CvmIndicator;
                                                                        paymentline.moneris_cloud_authcode = tranRes.receipt.AuthCode;
                                                                        paymentline.moneris_cloud_invoicenumber = tranRes.receipt.InvoiceNumber;
                                                                        paymentline.moneris_cloud_applabel = tranRes.receipt.AppLabel;
                                                                        paymentline.moneris_cloud_cncryptedcardinfo = tranRes.receipt.EncryptedCardInfo;
                                                                        paymentline.moneris_cloud_transdate = tranRes.receipt.TransDate;
                                                                        paymentline.moneris_cloud_transtime = tranRes.receipt.TransTime;
                                                                        paymentline.moneris_cloud_amount = tranRes.receipt.Amount;
                                                                        paymentline.moneris_cloud_referencenumber = tranRes.receipt.ReferenceNumber;
                                                                        if (tranRes.receipt.TxnName === 'Purchase') {
                                                                            // debugger
                                                                            paymentline.moneris_cloud_receiptid = tranRes.receipt.ReceiptId;
                                                                            order.moneris_cloud_receiptid = tranRes.receipt.ReceiptId;
                                                                            order.moneris_cloud_transid = tranRes.receipt.TransId;

                                                                        }
                                                                        paymentline.moneris_cloud_transid = tranRes.receipt.TransId;
                                                                        paymentline.moneris_cloud_timeout = tranRes.receipt.TimedOut;
                                                                        paymentline.moneris_cloud_cloudticket = tranRes.receipt.CloudTicket;
                                                                        paymentline.moneris_cloud_txnname = tranRes.receipt.TxnName;
                                                                        var event = {'description': 'Payment Completed'};
                                                                        self._delete_last_refund_data();

                                                                        function cleanReceipt(str) {
                                                                            // decode HTML entities like &nbsp;
                                                                            var txt = document.createElement("textarea");
                                                                            txt.innerHTML = str;
                                                                            let decoded = txt.value;

                                                                            // replace <br/> with actual newlines
                                                                            decoded = decoded.replace(/<br\s*\/?>/gi, '\n');

                                                                            return decoded;
                                                                        }
                                                                        try{
                                                                            debugger
                                                                            let receipt_data = await rpc('/moneriscloud/getreceipt',
                                                                                {"payment_method_id":order.getSelectedPaymentline().payment_method_id.id,
                                                                                            "transaction_resposnse": tranRes.receipt
                                                                            }
                                                                            );
                                                                            if (receipt_data){
                                                                            var order = self.pos.getOrder()
                                                                            var paymentline = order.getSelectedPaymentline();
                                                                            var parsed_data=JSON.parse(receipt_data)
                                                                            if (parsed_data.length === 2) {
                                                                                // // debugger
                                                                            // paymentline.cloud_receipt_customer = markup(parsed_data[0].receipt.Receipt)
                                                                            paymentline.cloud_receipt_customer = cleanReceipt(parsed_data[0].receipt.Receipt);
                                                                            paymentline.cloud_receipt_merchant = parsed_data[1].receipt.Receipt
                                                                            // console.log(data)
                                                                            console.log(paymentline.cloud_receipt_customer)
                                                                            }}





                                                                            // .then(function (data) {
                                                                            //     var order = self.pos.getOrder()
                                                                            //     var paymentline = order.getSelectedPaymentline();
                                                                            //     var parsed_data=JSON.parse(data)
                                                                            //     if (parsed_data.length === 2) {
                                                                            //         // // debugger
                                                                            //     paymentline.cloud_receipt_customer = parsed_data[0].receipt.Receipt
                                                                            //     paymentline.cloud_receipt_merchant = parsed_data[1].receipt.Receipt
                                                                            //     // console.log(data)
                                                                            //     console.log(paymentline.cloud_receipt_customer)
                                                                            //     }
                                                                            //
                                                                            //
                                                                            // });
                                                                        }
                                                                        catch(error){
                                                                            console.log("Receipt Fetch Failed.")
                                                                        }





                                                                    }

                                                                    if (ResponseCode >= 50) {
                                                                        console.log("Payment Declined");
                                                                        var event = {
                                                                            'exception': true,
                                                                            'description': 'Payment Declined\nERROR CODE:'+ResponseCode
                                                                        };
                                                                    }

                                                                    if (ResponseCode == null) {
                                                                        console.log("Payment Incomplete");
                                                                        var event = {
                                                                            'exception': true,
                                                                            'description': 'Payment Incomplete'
                                                                        };
                                                                    }
                                                                    var data = {};
                                                                    // // debugger
                                                                    self._onTransactionComplete(event, data);
                                                                } else if (tranRes.receipt.Completed === "false") {
                                                                    console.log("tranRes.receipt.False");
                                                                    var event = {
                                                                    'exception': true,
                                                                    'description': 'Error in Transaction\nERROR CODE:'+tranRes.receipt.ResponseCode
                                                                };
                                                                var data = {};
                                                                self._onTransactionComplete(event, data);
                                                                }
                                                            } else if (tranRes.receipt.Error !== "false") {
                                                                var event = {
                                                                    'exception': true,
                                                                    'description': 'Error in Transaction\nERROR CODE:'+tranRes.receipt.ResponseCode
                                                                };
                                                                var data = {};
                                                                self._onTransactionComplete(event, data);

                                                            }
                                                        }
                                                        }

                                                    }

                                                }
                                            }
                                            catch (error){
                                                if (typeof event === "undefined") {
                                                   var event = {
                                                        'exception': true,
                                                        'description': 'Can not connect to Moneris Cloud'
                                                    };
                                                }
                                                data = {};
                                                self._onTransactionComplete(event, data);
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
                        var order = this.pos.getOrder();
                        var transactionType = request_data.transactionType;
                        var request_data = this._populate_data(order, transactionType, result);
                        console.log("-------------");
                        console.log(request_data);
                        // // debugger
                        var sale_id;
                        sale_id = this.pos.getOrder().last_order_ref || this.pos.last_order_ref;//Order ID
                        console.log(sale_id);
                        var val_data = {
                            "params":
                            {
                                "request_data" : request_data,
                                "result" : result,
                                "pos_order" : sale_id,
                            }
                        }
                        console.log(val_data);
                        selected_paymentline.is_same_ipodency = false;
                        xhr.send(JSON.stringify(val_data));
                    }
                }
            }else{
                console.log("NOT Cancel");
                var event = {'exception':true,'description':'Cancel Transaction is not permitted'};
                var data ={};
                this._onTransactionComplete(event,data);
            }
        }



        _delete_last_refund_data (){
            this.pos.moneris_cloud_cloudticket = null;
            this.pos.moneris_cloud_receiptid = null;
            this.pos.moneris_cloud_transid = null;
            this.pos.last_order_ref = null;
        }


        _populate_data (order,txnType, result) {
            console.log(this.terminal.settings.storeId, this.terminal.settings.terminalId, this.terminal.settings.cloud_inout_url);
            if (this.terminal.settings.storeId == false || this.terminal.settings.terminalId == false
                // || this.terminal.settings.cloud_inout_url == false
                ) {
                    var event = {'exception':true,'description':'Please configure Moneris Credentials Properly.'};
                    this._onTransactionComplete(event,result);
            }

            var txRequest = {}
            // // debugger
            txRequest.storeId =  this.terminal.settings.storeId;
            txRequest.token =  this.terminal.settings.token;
            txRequest.company_id =  this.terminal.settings.company_id;
            txRequest.terminalId = this.terminal.settings.terminalId;
            txRequest.txnType = txnType;
            // postbackUrl method
            if (result.cloud_integration_method == 'postbackurl'){
                txRequest.apiToken = result.cloud_api_token;//this.terminal.settings.apiToken;
                txRequest.postbackUrl = result.cloud_postback_url;
            }
            //Polling
            if (result.cloud_integration_method == 'combined'){
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
            //------------------------------------------------------
                //New lines
               if ((this.pos.getOrder().moneris_cloud_cloudticket == null || this.pos.getOrder().moneris_cloud_cloudticket == false) && txnType != 'refund') {
                    var incre =  '/1';
                    incre = incre.replace(/ /g,'');
                    this.pos.getOrder().moneris_cloud_cloudticket = incre;
                } else if((this.pos.getOrder().moneris_cloud_cloudticket != null || this.pos.getOrder().moneris_cloud_cloudticket != false) && txnType != 'refund'){
                    let newid = parseInt(this.pos.getOrder().moneris_cloud_cloudticket.split("/")[1]);
                    incre = '/'+ (newid + 1).toString();
                    this.pos.getOrder().moneris_cloud_cloudticket = incre;
                }
            //------------------------------------------------------
            console.log(incre);
                // // debugger
            if(txnType == 'purchase' || txnType == 'refund' || txnType == 'purchase_correction'){
                var orderObj = {}
                orderObj.orderId = order.pos_reference + incre.toString();
                if (txnType == 'refund') {
                    console.log("Refund--->");
                    orderObj.orderId = this.moneris_cloud_receiptid || this.pos.moneris_cloud_receiptid;
                    // In the transaction response, this variable is referenced by ReceiptId
                }
                else if (txnType == 'purchase_correction'){
                    orderObj.orderId = this.pos.getOrder().getSelectedPaymentline().moneris_cloud_receiptid;
                    orderObj.txnNumber = this.pos.getOrder().getSelectedPaymentline().moneris_cloud_transid;
                }
                var amount = this.pos.getOrder().getSelectedPaymentline().amount;
                if (amount < 0){
                    amount = Math.abs(amount);
                    console.log(amount);
                }
                orderObj.amount = amount.toFixed(2);//"string"
            }
            txRequest.request = orderObj;
            // This Part only for Moneris Go Cloud
            if (this.payment_method_id.is_moneris_go_cloud) {
                    var selected_paymentline = this.pos.getOrder().getSelectedPaymentline()

                    function generate_idempotency_key() {
                        const now = new Date();
                        const timestampPart = now.getFullYear().toString() +
                            (now.getMonth() + 1).toString().padStart(2, '0') +
                            now.getDate().toString().padStart(2, '0') +
                            now.getHours().toString().padStart(2, '0') +
                            now.getMinutes().toString().padStart(2, '0') +
                            now.getSeconds().toString().padStart(2, '0');
                        const randomPart = Math.floor(Math.random() * 90) + 10;
                        const idempotencyKey = `${timestampPart}${randomPart}`;
                        return idempotencyKey;
                    }

                    if (selected_paymentline.is_same_ipodency) {
                        txRequest.idempotencyKey = selected_paymentline.moneris_cloud_idempotency_key;
                    } else {
                        txRequest.idempotencyKey = generate_idempotency_key();
                        selected_paymentline.moneris_cloud_idempotency_key = txRequest.idempotencyKey
                    }
                }



            console.log("Request Object");
            console.log(txRequest);
            return txRequest;

        }
}
