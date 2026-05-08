odoo.define('payment_moneris_cloud.payment', function (require) {
    "use strict";
    
    const { Gui } = require('point_of_sale.Gui');
    var core = require('web.core');
    var PaymentInterface = require('point_of_sale.PaymentInterface');
    var _t = core._t;
    var rpc = require('web.rpc');
    var pos_model = require('point_of_sale.models');
    const {Markup} = require('web.utils');
    
    var PaymentMonerisCloud = PaymentInterface.extend({
    
    
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
    
        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.enable_reversals();
    
            var settings = new monerisCloud.CloudSettings();
            settings.connectionMode = "onFixIp";
            settings.connectionIPString = this.payment_method.cloud_terminal_ip;
            settings.connectionIPPort = this.payment_method.cloud_terminal_port;
            settings.merchantId = this.payment_method.cloud_merchant_id;
            settings.configCode = this.payment_method.cloud_config_code;
            settings.terminalId = this.payment_method.cloud_terminal_id;
            settings.storeId = this.payment_method.cloud_store_id;
            settings.token = this.payment_method.token;
            settings.company_id = this.payment_method.company_id;
            this.terminal = new monerisCloud.Terminal(settings);
        },
    
        /**
         * @override
         */
        send_payment_cancel: function () {
            console.log("send_payment_cancel");
            this._super.apply(this, arguments);
            var action = 'CANCEL';
            return this._sendTransaction(action);    
        },
    
        /**
         * @override
         */
        send_payment_request: function () {
            console.log("send_payment_request");
            console.log(this.pos.get_order().selected_paymentline.amount);
            if (this.pos.get_order().selected_paymentline.amount >= 0) {
                var action = 'purchase';            
            } else {
                var action = 'refund';             
            }
            console.log("action-->",action);
            this._super.apply(this, arguments);
            this.pos.get_order().selected_paymentline.setPaymentStatus('waitingCard');
            return this._sendTransaction(action);
    
        },
    
        /**
         * @override
         */
        send_payment_reversal: function () {
            console.log("send_payment_reversal");
            this._super.apply(this, arguments);
            this.pos.get_order().selected_paymentline.setPaymentStatus('reversing');
            var action = 'purchase_correction';
            return this._sendTransaction(action);    
        },
    
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
    
        _onTransactionComplete: function (event, data) {
            console.log("_onTransactionComplete")
            console.log("event");console.log(event);
            Object.size = function(obj) {
                var size = 0, key;
                for (key in obj) {
                    if (obj.hasOwnProperty(key)) size++;
                }
                return size;
            };
            var size = Object.size(this.pos.get_order().paymentlines._byId);
            if (event.exception) {
                if(event.exception == true){
                    Gui.showPopup('ErrorPopup', {
                        title: _t('Moneris Cloud Error'),
                        body: _t(event.description),
                    });
                   
                }else{
                    Gui.showPopup('ErrorPopup', {
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
                this.transactionResolve = resolve;
                var request_data =  {
                        'transaction' : '_sendTransaction',
                        'payment_method_id' : order.selected_paymentline.payment_method.id,
                        'transactionType' : transactionType,
                };
                console.log("_sendTransaction");
                rpc.query({
                    route: '/moneriscloud/gettransaction',
                    params: request_data,
                }).then(this._cloudRequest.bind(this, request_data));
            });
        },
    
    
    
        /**
         * @private
         * @param {Object} request_data
         * @param {Object} result
         */
        _cloudRequest: function (request_data,result) {
            debugger
            result = JSON.parse(result);
            console.log("request_data ===>>>",  request_data);
            console.log("result ===>>>",  result);

            if (result.error != true) {
                if (result.use_payment_terminal == 'moneris_cloud') {
                        if (request_data.transactionType != 'CANCEL') {
                            var cancelBtn = document.getElementsByClassName("send_payment_cancel");
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
                            debugger
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
                                                var event = {
                                                    'exception': true,
                                                    'description': tranRes.description
                                                };
                                                var data = {};
                                                self._onTransactionComplete(event, data);
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
                                                        if (tranRes.receipt.Error) {
                                                            if (tranRes.receipt.Error == "false") {
                                                                if (tranRes.receipt.Completed == "true") {

                                                                    var ResponseCode = parseInt(tranRes.receipt.ResponseCode);
                                                                    if (ResponseCode < 50) {
                                                                        console.log("tranRes.receipt.Completed");
                                                                        var order = self.pos.get_order()
                                                                        var paymentline = order.selected_paymentline;
                                                                        if (tranRes.receipt.TipAmount && order.pos.config.tip_product_id){
                                                                            order.set_tip(tranRes.receipt.TipAmount);
                                                                            order.selected_paymentline.amount = order.selected_paymentline.amount + parseFloat(tranRes.receipt.TipAmount)
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
                                                                            debugger
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
                                                                        try{
                                                                            let receipt_data = await rpc.query({
                                                                                route: '/moneriscloud/getreceipt',
                                                                                params: {"payment_method_id":order.selected_paymentline.payment_method.id,
                                                                                            "transaction_resposnse": tranRes.receipt
                                                                            },
                                                                            })
                                                                            if (receipt_data){
                                                                            var order = self.pos.get_order()
                                                                            var paymentline = order.selected_paymentline;
                                                                            var parsed_data=JSON.parse(receipt_data)
                                                                            if (parsed_data.length === 2) {
                                                                                debugger
                                                                            paymentline.cloud_receipt_customer = Markup(parsed_data[0].receipt.Receipt)
                                                                            paymentline.cloud_receipt_merchant = parsed_data[1].receipt.Receipt
                                                                            // console.log(data)
                                                                            console.log(paymentline.cloud_receipt_customer)
                                                                            }}





                                                                            // .then(function (data) {
                                                                            //     var order = self.pos.get_order()
                                                                            //     var paymentline = order.selected_paymentline;
                                                                            //     var parsed_data=JSON.parse(data)
                                                                            //     if (parsed_data.length === 2) {
                                                                            //         debugger
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
                                                                    debugger
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
                                            catch (error){
                                                var event = {
                                                    'exception': true,
                                                    'description': 'Can not connect to Moneris Cloud'
                                                };
                                                data = {};
                                                self._onTransactionComplete(event, data);
                                            }
                                        }
                                    }


                                // console.log("Response from terminal-->");
                                //     if (validation) {
                                //
                                //             if (validation.result) {
                                //                     validation = JSON.parse(validation.result);
                                //                     if (typeof(validation) =="string"){
                                //                         validation = JSON.parse(validation);
                                //                     }
                                //                     console.log(validation);
                                //                     if (validation.error == true) {
                                //                         console.log("description")
                                //                         console.log(validation.description)
                                //                         var event = {'exception':true, 'description':validation.description};
                                //                         data = {};
                                //                         self._onTransactionComplete(event,data);
                                //                     }else{
                                //                     //Success Transaction Message
                                //                         if(validation.receipt.ResponseCode == "001"){
                                //                             console.log("Success Message");
                                //                         }
                                //                         if(validation.receipt.Error == "false"){
                                //                             var paymentline = self.pos.get_order().selected_paymentline;
                                //                             paymentline.cloud_val_responsecode = validation.receipt.ResponseCode;
                                //                             if (validation.receipt.Message) {
                                //                                 paymentline.cloud_val_completed = validation.receipt.Message;
                                //                             }
                                //                             paymentline.cloud_val_error = validation.receipt.Error;
                                //                             paymentline.cloud_val_timeout = validation.receipt.TimedOut;
                                //                             if ( validation.receipt.PostbackUrl) {
                                //                                 paymentline.cloud_val_postbackurl = validation.receipt.PostbackUrl;
                                //                             }
                                //                             paymentline.cloud_val_cloudticket = validation.receipt.CloudTicket;
                                //
                                //                             (function () {
                                //                                 var interval = setInterval(getTransaction,1000);
                                //                                 var maxPollErrors = 10;
                                //                                 var pollErrors = 0;
                                //                                 function getTransaction() {
                                //                                     console.log("Poll function");
                                //                                     // ------------------------------------------
                                //                                     var xhr2 = new XMLHttpRequest();
                                //                                     var tran_url = '/moneriscloud/transaction';
                                //                                     xhr2.open("POST", tran_url, true);
                                //                                     xhr2.setRequestHeader("Content-Type", "application/json");
                                //                                     console.log('OPENED', xhr2.readyState); // readyState will be 1
                                //
                                //                                     xhr2.onreadystatechange = function () {
                                //                                         debugger
                                //                                         if (this.readyState === 4 && this.status === 200) {
                                //                                             debugger
                                //
                                //                                             var tranRes = JSON.parse(this.responseText);
                                //                                             console.log("Response from Cloud-->");
                                //                                                 if (tranRes) {
                                //                                                     if (tranRes.result) {
                                //                                                         if (tranRes.result.error ==  true) {
                                //                                                             var event = {'exception':true,'description':tranRes.result.description};
                                //                                                             var data = {};
                                //                                                             clearInterval(interval); // stop the interval
                                //                                                             self._onTransactionComplete(event,data);
                                //                                                         }
                                //                                                         console.log(typeof(tranRes));
                                //
                                //                                                         if (typeof(tranRes.result) =="string"){
                                //                                                             tranRes = JSON.parse(tranRes.result);
                                //                                                         }
                                //                                                         if (typeof(tranRes) =="string"){
                                //                                                             tranRes = JSON.parse(tranRes);
                                //                                                         }
                                //
                                //                                                         console.log(tranRes);
                                //                                                         console.log(typeof(tranRes));
                                //
                                //                                                         //==================================================
                                //                                                         //ResponseCode
                                //                                                         //==================================================
                                //                                                         // Result
                                //                                                         // 0 – 49 (inclusive) Approved
                                //                                                         // 50 – 999 (inclusive) Declined
                                //                                                         // null Incomplete
                                //                                                         //==================================================
                                //
                                //                                                         if (tranRes) {
                                //                                                             if (tranRes.receipt) {
                                //                                                                 if (tranRes.receipt.Error) {
                                //                                                                     if (tranRes.receipt.Error == "false") {
                                //                                                                         if (tranRes.receipt.Completed == "true") {
                                //
                                //                                                                             var ResponseCode = parseInt(tranRes.receipt.ResponseCode);
                                //                                                                             if(ResponseCode < 50){
                                //                                                                                 console.log("tranRes.receipt.Completed");
                                //                                                                                 var order = self.pos.get_order()
                                //                                                                                 var paymentline = order.selected_paymentline;
                                //                                                                                 // ===========================
                                //                                                                                 //         Receipt ID save in pos order
                                //
                                //                                                                                 // ============================
                                //                                                                                 paymentline.card_type = tranRes.receipt.CardType;
                                //                                                                                 paymentline.transaction_id = tranRes.receipt.TransId;
                                //                                                                                 paymentline.moneris_cloud_completed =  tranRes.receipt.Completed;
                                //                                                                                 paymentline.moneris_cloud_transtype =  tranRes.receipt.TransType;
                                //                                                                                 paymentline.moneris_cloud_error = tranRes.receipt.Error;
                                //                                                                                 paymentline.moneris_cloud_responsecode = tranRes.receipt.ResponseCode;
                                //                                                                                 paymentline.moneris_cloud_iso = tranRes.receipt.ISO;
                                //                                                                                 paymentline.moneris_cloud_pan = tranRes.receipt.Pan;
                                //                                                                                 paymentline.moneris_cloud_cardtype = tranRes.receipt.CardType;
                                //                                                                                 paymentline.moneris_cloud_cardname = tranRes.receipt.CardName;
                                //                                                                                 paymentline.moneris_cloud_accounttype = tranRes.receipt.AccountType;
                                //                                                                                 paymentline.moneris_cloud_cvmindicator = tranRes.receipt.CvmIndicator;
                                //                                                                                 paymentline.moneris_cloud_authcode = tranRes.receipt.AuthCode;
                                //                                                                                 paymentline.moneris_cloud_invoicenumber = tranRes.receipt.InvoiceNumber;
                                //                                                                                 paymentline.moneris_cloud_applabel = tranRes.receipt.AppLabel;
                                //                                                                                 paymentline.moneris_cloud_cncryptedcardinfo = tranRes.receipt.EncryptedCardInfo;
                                //                                                                                 paymentline.moneris_cloud_transdate = tranRes.receipt.TransDate;
                                //                                                                                 paymentline.moneris_cloud_transtime =tranRes.receipt.TransTime;
                                //                                                                                 paymentline.moneris_cloud_amount =tranRes.receipt.Amount;
                                //                                                                                 paymentline.moneris_cloud_referencenumber = tranRes.receipt.ReferenceNumber;
                                //                                                                                 if (tranRes.receipt.TxnName == 'Purchase'){
                                //                                                                                     debugger
                                //                                                                                     paymentline.moneris_cloud_receiptid = tranRes.receipt.ReceiptId;
                                //                                                                                     order.moneris_cloud_receiptid = tranRes.receipt.ReceiptId;
                                //                                                                                     order.moneris_cloud_transid = tranRes.receipt.TransId;
                                //
                                //                                                                                 }
                                //                                                                                 paymentline.moneris_cloud_transid = tranRes.receipt.TransId;
                                //                                                                                 paymentline.moneris_cloud_timeout = tranRes.receipt.TimedOut;
                                //                                                                                 paymentline.moneris_cloud_cloudticket = tranRes.receipt.CloudTicket;
                                //                                                                                 paymentline.moneris_cloud_txnname = tranRes.receipt.TxnName;
                                //                                                                                 var event = {'description':'Payment Completed'};
                                //                                                                             }
                                //
                                //                                                                             if(ResponseCode >= 50){
                                //                                                                                 console.log("Payment Declined");
                                //                                                                                 var event = {'exception':true, 'description':'Payment Declined'};
                                //                                                                             }
                                //
                                //                                                                             if(ResponseCode == null){
                                //                                                                                 console.log("Payment Incomplete");
                                //                                                                                 var event = {'exception':true, 'description':'Payment Incomplete'};
                                //                                                                             }
                                //
                                //                                                                             clearInterval(interval); // stop the interval
                                //                                                                             var data = {};
                                //                                                                             self._onTransactionComplete(event,data);
                                //                                                                         }
                                //                                                                         else if (tranRes.receipt.Completed == "false") {
                                //                                                                             console.log("tranRes.receipt.False");
                                //                                                                         }
                                //                                                                     }
                                //                                                                     else if(tranRes.receipt.Error != "false") {
                                //                                                                         var event = {'exception':true,'description':'Error in Transaction'};
                                //                                                                         var data = {};
                                //                                                                         clearInterval(interval); // stop the interval
                                //                                                                         self._onTransactionComplete(event,data);
                                //
                                //                                                                     }
                                //                                                                 }
                                //                                                             }
                                //
                                //                                                         }
                                //                                                     }
                                //                                                 }
                                //
                                //                                         }
                                //
                                //
                                //                                     }
                                //                                     xhr2.onprogress = function () {
                                //                                         console.log('LOADING', xhr2.readyState); // readyState will be 3
                                //                                     };
                                //                                     xhr2.onload = function () {
                                //                                         console.log('DONE', xhr2.readyState); // readyState will be 4
                                //                                     };
                                //                                     xhr2.onerror = function() { // only triggers if the request couldn't be made at all
                                //                                         console.log('Disconnected from server', xhr2.readyState);
                                //                                                 console.log("Eroro");
                                //                                                 pollErrors += 1;
                                //                                                 if (pollErrors > maxPollErrors) {
                                //                                                     clearInterval(interval); // stop the interval
                                //                                                 }
                                //                                     };
                                //                                     var tran_data = {
                                //                                         "params":
                                //                                         {
                                //                                             "receiptUrl": validation.receipt.receiptUrl,
                                //                                             "request_data" : request_data,
                                //                                         }
                                //                                     }
                                //                                     console.log(tran_data);
                                //                                     xhr2.send(JSON.stringify(tran_data));
                                //
                                //                                 }
                                //                             })();
                                //                         }
                                //                     //Failure Transaction Message
                                //                     else if(validation.receipt.Error == "true"){
                                //                         var event = {'exception':true,'description':'Error Message: ' + validation.receipt.Message};
                                //                         var data = {};
                                //                         self._onTransactionComplete(event,data);
                                //                         }
                                //
                                //                 }
                                //             }
                                //         }

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
                        var order = this.pos.get_order();
                        var transactionType = request_data.transactionType;
                        var request_data = this._populate_data(order, transactionType, result);
                        console.log("-------------");
                        console.log(request_data);
                        debugger
                        var sale_id;
                        sale_id = this.pos.get_order().last_order_ref || this.pos.last_order_ref;//Order ID
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
                        xhr.send(JSON.stringify(val_data));
                    }
                }
            }else{
                console.log("NOT Cancel");
                var event = {'exception':true,'description':'Cancel Transaction is not permitted'};
                var data ={};
                this._onTransactionComplete(event,data);
            }
        },



        _delete_last_refund_data:function (){
            this.pos.moneris_cloud_cloudticket = null;
            this.pos.moneris_cloud_receiptid = null;
            this.pos.moneris_cloud_transid = null;
            this.pos.last_order_ref = null;
        },


        _populate_data: function (order,txnType, result) {
            console.log(this.terminal.settings.storeId, this.terminal.settings.terminalId, this.terminal.settings.cloud_inout_url);
            if (this.terminal.settings.storeId == false || this.terminal.settings.terminalId == false
                // || this.terminal.settings.cloud_inout_url == false
                ) {
                    var event = {'exception':true,'description':'Please configure Moneris Credentials Properly.'};
                    this._onTransactionComplete(event,result);       
            }
            
            var txRequest = {}
            debugger
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
               if (this.pos.get_order().moneris_cloud_cloudticket == null && txnType != 'refund') {
                    var incre =  '/1';
                    incre = incre.replace(/ /g,'');
                    this.pos.get_order().moneris_cloud_cloudticket = incre;
                } else if(this.pos.get_order().moneris_cloud_cloudticket != null && txnType != 'refund'){
                    let newid = parseInt(this.pos.get_order().moneris_cloud_cloudticket.split("/")[1]);
                    incre = '/'+ (newid + 1).toString();
                    this.pos.get_order().moneris_cloud_cloudticket = incre;
                }
            //------------------------------------------------------
            console.log(incre);
                debugger
            if(txnType == 'purchase' || txnType == 'refund' || txnType == 'purchase_correction'){
                var orderObj = {}
                orderObj.orderId = order.name + incre.toString();
                if (txnType == 'refund') {
                    console.log("Refund--->");
                    orderObj.orderId = this.moneris_cloud_receiptid || this.pos.moneris_cloud_receiptid;
                    // In the transaction response, this variable is referenced by ReceiptId
                }
                else if (txnType == 'purchase_correction'){
                    orderObj.orderId = this.pos.get_order().selected_paymentline.moneris_cloud_receiptid;
                    orderObj.txnNumber = this.pos.get_order().selected_paymentline.moneris_cloud_transid;
                }
                var amount = this.pos.get_order().selected_paymentline.amount;
                if (amount < 0){
                    amount = Math.abs(amount);
                    console.log(amount);
                }
                orderObj.amount = amount.toFixed(2);//"string"
            }
            txRequest.request = orderObj;

            console.log("Request Object");
            console.log(txRequest);
            return txRequest;
        },
    });

    return PaymentMonerisCloud;
    
    });
    
    
    
    