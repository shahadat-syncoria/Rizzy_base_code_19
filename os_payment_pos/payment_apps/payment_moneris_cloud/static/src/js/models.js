odoo.define('payment_moneris_cloud.models', function (require) {

    var models = require('point_of_sale.models');
    var { Order, Payment } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    var PaymentMonerisCloud = require('payment_moneris_cloud.payment');

    models.register_payment_method('moneris_cloud', PaymentMonerisCloud);



    const PosMonerisCloudPayment = (Payment) => class PosMonerisPayment extends Payment {
    constructor(obj, options) {
        super(...arguments);
         this.cloud_request_id = this.cloud_request_id;
        // this.payment_acuirer_name = this.payment_acuirer_name;
        // this.purchase_cloud_ticket = this.purchase_cloud_ticket;
        // this.purchase_receipt_id = this.purchase_receipt_id;

        this.cloud_val_responsecode = this.cloud_val_responsecode;
        this.cloud_val_message = this.cloud_val_message;
        this.cloud_val_completed = this.cloud_val_completed;
        this.cloud_val_error = this.cloud_val_error;
        this.cloud_val_timeout = this.cloud_val_timeout;
        this.cloud_val_postbackurl = this.cloud_val_postbackurl;
        this.cloud_val_cloudticket = this.cloud_val_cloudticket;

        this.card_type = this.card_type;
        this.transaction_id = this.moneris_cloud_referencenumber;

        this.moneris_cloud_completed = this.moneris_cloud_completed;
        this.moneris_cloud_transtype = this.moneris_cloud_transtype;
        this.moneris_cloud_error = this.moneris_cloud_error;
        this.moneris_cloud_initrequired = this.moneris_cloud_initrequired;
        this.moneris_cloud_safindicator = this.moneris_cloud_safindicator;
        this.moneris_cloud_responsecode = this.moneris_cloud_responsecode;
        this.moneris_cloud_iso = this.moneris_cloud_iso;
        this.moneris_cloud_languagecode = this.moneris_cloud_languagecode;
        this.moneris_cloud_partailauthamount = this.moneris_cloud_partailauthamount;
        this.moneris_cloud_availablebalance = this.moneris_cloud_availablebalance;
        this.moneris_cloud_tipamount = this.moneris_cloud_tipamount;
        this.moneris_cloud_emvcashbackamount = this.moneris_cloud_emvcashbackamount;
        this.moneris_cloud_surchargeamount = this.moneris_cloud_surchargeamount;
        this.moneris_cloud_foreigncurrencyamount = this.moneris_cloud_foreigncurrencyamount;
        this.moneris_cloud_baserate = this.moneris_cloud_baserate;
        this.moneris_cloud_exchangerate = this.moneris_cloud_exchangerate;
        this.moneris_cloud_pan = this.moneris_cloud_pan;
        this.moneris_cloud_cardtype = this.moneris_cloud_cardtype;
        this.moneris_cloud_cardname = this.moneris_cloud_cardname;
        this.moneris_cloud_accounttype = this.moneris_cloud_accounttype;
        this.moneris_cloud_swipeindicator = this.moneris_cloud_swipeindicator;
        this.moneris_cloud_formfactor = this.moneris_cloud_formfactor;
        this.moneris_cloud_cvmindicator = this.moneris_cloud_cvmindicator;
        this.moneris_cloud_reservedfield1 = this.moneris_cloud_reservedfield1;
        this.moneris_cloud_reservedfield2 = this.moneris_cloud_reservedfield2;
        this.moneris_cloud_authcode = this.moneris_cloud_authcode;
        this.moneris_cloud_invoicenumber = this.moneris_cloud_invoicenumber;
        this.moneris_cloud_emvechodata = this.moneris_cloud_emvechodata;
        this.moneris_cloud_reservedfield3 = this.moneris_cloud_reservedfield3;
        this.moneris_cloud_reservedfield4 = this.moneris_cloud_reservedfield4;
        this.moneris_cloud_aid = this.moneris_cloud_aid;
        this.moneris_cloud_applabel = this.moneris_cloud_applabel;
        this.moneris_cloud_apppreferredname = this.moneris_cloud_apppreferredname;
        this.moneris_cloud_arqc = this.moneris_cloud_arqc;
        this.moneris_cloud_tvrarqc = this.moneris_cloud_tvrarqc;
        this.moneris_cloud_tcacc = this.moneris_cloud_tcacc;
        this.moneris_cloud_tvrtcacc = this.moneris_cloud_tvrtcacc;
        this.moneris_cloud_tsi = this.moneris_cloud_tsi;
        this.moneris_cloud_tokenresponsecode = this.moneris_cloud_tokenresponsecode;
        this.moneris_cloud_token = this.moneris_cloud_token;
        this.moneris_cloud_logonrequired = this.moneris_cloud_logonrequired;
        this.moneris_cloud_cncryptedcardinfo = this.moneris_cloud_cncryptedcardinfo;
        this.moneris_cloud_transdate = this.moneris_cloud_transdate;
        this.moneris_cloud_transtime = this.moneris_cloud_transtime;
        this.moneris_cloud_amount = this.moneris_cloud_amount;
        this.moneris_cloud_referencenumber = this.moneris_cloud_referencenumber;
        this.moneris_cloud_receiptid = this.moneris_cloud_receiptid;
        this.moneris_cloud_transid = this.moneris_cloud_transid;
        this.moneris_cloud_timeout = this.moneris_cloud_timeout;
        this.moneris_cloud_cloudticket = this.moneris_cloud_cloudticket;
        this.moneris_cloud_txnname = this.moneris_cloud_txnname;
        this.cloud_receipt_customer = this.cloud_receipt_customer;
        this.cloud_receipt_merchant = this.cloud_receipt_merchant;

    }
    //@override
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.card_type = this.terminalServiceId;
        json.cloud_request_id = this.cloud_request_id;
        // this.payment_acuirer_name = this.payment_acuirer_name;
        // this.purchase_cloud_ticket = this.purchase_cloud_ticket;
        // this.purchase_receipt_id = this.purchase_receipt_id;

        json.cloud_val_responsecode = this.cloud_val_responsecode;
        json.cloud_val_message = this.cloud_val_message;
        json.cloud_val_completed = this.cloud_val_completed;
        json.cloud_val_error = this.cloud_val_error;
        json.cloud_val_timeout = this.cloud_val_timeout;
        json.cloud_val_postbackurl = this.cloud_val_postbackurl;
        json.cloud_val_cloudticket = this.cloud_val_cloudticket;

        json.card_type = this.card_type;
        json.transaction_id = this.moneris_cloud_referencenumber;

        json.moneris_cloud_completed = this.moneris_cloud_completed;
        json.moneris_cloud_transtype = this.moneris_cloud_transtype;
        json.moneris_cloud_error = this.moneris_cloud_error;
        json.moneris_cloud_initrequired = this.moneris_cloud_initrequired;
        json.moneris_cloud_safindicator = this.moneris_cloud_safindicator;
        json.moneris_cloud_responsecode = this.moneris_cloud_responsecode;
        json.moneris_cloud_iso = this.moneris_cloud_iso;
        json.moneris_cloud_languagecode = this.moneris_cloud_languagecode;
        json.moneris_cloud_partailauthamount = this.moneris_cloud_partailauthamount;
        json.moneris_cloud_availablebalance = this.moneris_cloud_availablebalance;
        json.moneris_cloud_tipamount = this.moneris_cloud_tipamount;
        json.moneris_cloud_emvcashbackamount = this.moneris_cloud_emvcashbackamount;
        json.moneris_cloud_surchargeamount = this.moneris_cloud_surchargeamount;
        json.moneris_cloud_foreigncurrencyamount = this.moneris_cloud_foreigncurrencyamount;
        json.moneris_cloud_baserate = this.moneris_cloud_baserate;
        json.moneris_cloud_exchangerate = this.moneris_cloud_exchangerate;
        json.moneris_cloud_pan = this.moneris_cloud_pan;
        json.moneris_cloud_cardtype = this.moneris_cloud_cardtype;
        json.moneris_cloud_cardname = this.moneris_cloud_cardname;
        json.moneris_cloud_accounttype = this.moneris_cloud_accounttype;
        json.moneris_cloud_swipeindicator = this.moneris_cloud_swipeindicator;
        json.moneris_cloud_formfactor = this.moneris_cloud_formfactor;
        json.moneris_cloud_cvmindicator = this.moneris_cloud_cvmindicator;
        json.moneris_cloud_reservedfield1 = this.moneris_cloud_reservedfield1;
        json.moneris_cloud_reservedfield2 = this.moneris_cloud_reservedfield2;
        json.moneris_cloud_authcode = this.moneris_cloud_authcode;
        json.moneris_cloud_invoicenumber = this.moneris_cloud_invoicenumber;
        json.moneris_cloud_emvechodata = this.moneris_cloud_emvechodata;
        json.moneris_cloud_reservedfield3 = this.moneris_cloud_reservedfield3;
        json.moneris_cloud_reservedfield4 = this.moneris_cloud_reservedfield4;
        json.moneris_cloud_aid = this.moneris_cloud_aid;
        json.moneris_cloud_applabel = this.moneris_cloud_applabel;
        json.moneris_cloud_apppreferredname = this.moneris_cloud_apppreferredname;
        json.moneris_cloud_arqc = this.moneris_cloud_arqc;
        json.moneris_cloud_tvrarqc = this.moneris_cloud_tvrarqc;
        json.moneris_cloud_tcacc = this.moneris_cloud_tcacc;
        json.moneris_cloud_tvrtcacc = this.moneris_cloud_tvrtcacc;
        json.moneris_cloud_tsi = this.moneris_cloud_tsi;
        json.moneris_cloud_tokenresponsecode = this.moneris_cloud_tokenresponsecode;
        json.moneris_cloud_token = this.moneris_cloud_token;
        json.moneris_cloud_logonrequired = this.moneris_cloud_logonrequired;
        json.moneris_cloud_cncryptedcardinfo = this.moneris_cloud_cncryptedcardinfo;
        json.moneris_cloud_transdate = this.moneris_cloud_transdate;
        json.moneris_cloud_transtime = this.moneris_cloud_transtime;
        json.moneris_cloud_amount = this.moneris_cloud_amount;
        json.moneris_cloud_referencenumber = this.moneris_cloud_referencenumber;
        json.moneris_cloud_receiptid = this.moneris_cloud_receiptid;
        json.moneris_cloud_transid = this.moneris_cloud_transid;
        json.moneris_cloud_timeout = this.moneris_cloud_timeout;
        json.moneris_cloud_cloudticket = this.moneris_cloud_cloudticket;
        json.moneris_cloud_txnname = this.moneris_cloud_txnname;
        json.cloud_receipt_customer = this.cloud_receipt_customer;
        json.cloud_receipt_merchant = this.cloud_receipt_merchant;
        return json;
    }
    //@override
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.cloud_request_id = json.cloud_request_id;
            // this.payment_acuirer_name = json.payment_acuirer_name;
            // this.purchase_cloud_ticket = json.purchase_cloud_ticket;
            // this.purchase_receipt_id = json.purchase_receipt_id;

            this.cloud_val_responsecode = json.cloud_val_responsecode;
            this.cloud_val_message = json.cloud_val_message;
            this.cloud_val_completed = json.cloud_val_completed;
            this.cloud_val_error = json.cloud_val_error;
            this.cloud_val_timeout = json.cloud_val_timeout;
            this.cloud_val_postbackurl = json.cloud_val_postbackurl;
            this.cloud_val_cloudticket = json.cloud_val_cloudticket;

            this.card_type = json.card_type;
            this.transaction_id = json.moneris_cloud_referencenumber;

            this.moneris_cloud_completed = json.moneris_cloud_completed;
            this.moneris_cloud_transtype = json.moneris_cloud_transtype;
            this.moneris_cloud_error = json.moneris_cloud_error;
            this.moneris_cloud_initrequired = json.moneris_cloud_initrequired;
            this.moneris_cloud_safindicator = json.moneris_cloud_safindicator;
            this.moneris_cloud_responsecode = json.moneris_cloud_responsecode;
            this.moneris_cloud_iso = json.moneris_cloud_iso;
            this.moneris_cloud_languagecode = json.moneris_cloud_languagecode;
            this.moneris_cloud_partailauthamount = json.moneris_cloud_partailauthamount;
            this.moneris_cloud_availablebalance = json.moneris_cloud_availablebalance;
            this.moneris_cloud_tipamount = json.moneris_cloud_tipamount;
            this.moneris_cloud_emvcashbackamount = json.moneris_cloud_emvcashbackamount;
            this.moneris_cloud_surchargeamount = json.moneris_cloud_surchargeamount;
            this.moneris_cloud_foreigncurrencyamount = json.moneris_cloud_foreigncurrencyamount;
            this.moneris_cloud_baserate = json.moneris_cloud_baserate;
            this.moneris_cloud_exchangerate = json.moneris_cloud_exchangerate;
            this.moneris_cloud_pan = json.moneris_cloud_pan;
            this.moneris_cloud_cardtype = json.moneris_cloud_cardtype;
            this.moneris_cloud_cardname = json.moneris_cloud_cardname;
            this.moneris_cloud_accounttype = json.moneris_cloud_accounttype;
            this.moneris_cloud_swipeindicator = json.moneris_cloud_swipeindicator;
            this.moneris_cloud_formfactor = json.moneris_cloud_formfactor;
            this.moneris_cloud_cvmindicator = json.moneris_cloud_cvmindicator;
            this.moneris_cloud_reservedfield1 = json.moneris_cloud_reservedfield1;
            this.moneris_cloud_reservedfield2 = json.moneris_cloud_reservedfield2;
            this.moneris_cloud_authcode = json.moneris_cloud_authcode;
            this.moneris_cloud_invoicenumber = json.moneris_cloud_invoicenumber;
            this.moneris_cloud_emvechodata = json.moneris_cloud_emvechodata;
            this.moneris_cloud_reservedfield3 = json.moneris_cloud_reservedfield3;
            this.moneris_cloud_reservedfield4 = json.moneris_cloud_reservedfield4;
            this.moneris_cloud_aid = json.moneris_cloud_aid;
            this.moneris_cloud_applabel = json.moneris_cloud_applabel;
            this.moneris_cloud_apppreferredname = json.moneris_cloud_apppreferredname;
            this.moneris_cloud_arqc = json.moneris_cloud_arqc;
            this.moneris_cloud_tvrarqc = json.moneris_cloud_tvrarqc;
            this.moneris_cloud_tcacc = json.moneris_cloud_tcacc;
            this.moneris_cloud_tvrtcacc = json.moneris_cloud_tvrtcacc;
            this.moneris_cloud_tsi = json.moneris_cloud_tsi;
            this.moneris_cloud_tokenresponsecode = json.moneris_cloud_tokenresponsecode;
            this.moneris_cloud_token = json.moneris_cloud_token;
            this.moneris_cloud_logonrequired = json.moneris_cloud_logonrequired;
            this.moneris_cloud_cncryptedcardinfo = json.moneris_cloud_cncryptedcardinfo;
            this.moneris_cloud_transdate = json.moneris_cloud_transdate;
            this.moneris_cloud_transtime = json.moneris_cloud_transtime;
            this.moneris_cloud_amount = json.moneris_cloud_amount;
            this.moneris_cloud_referencenumber = json.moneris_cloud_referencenumber;
            this.moneris_cloud_receiptid = json.moneris_cloud_receiptid;
            this.moneris_cloud_transid = json.moneris_cloud_transid;
            this.moneris_cloud_timeout = json.moneris_cloud_timeout;
            this.moneris_cloud_cloudticket = json.moneris_cloud_cloudticket;
            this.moneris_cloud_txnname = json.moneris_cloud_txnname;
            this.cloud_receipt_customer = json.cloud_receipt_customer;
            this.cloud_receipt_merchant = json.cloud_receipt_merchant;

    }
}
    Registries.Model.extend(Payment, PosMonerisCloudPayment);


    const PosMonerisCloudOrder = (Order) => class PosMonerisOrder extends Order {
    constructor(obj, options) {
        super(...arguments);
        this.moneris_cloud_receiptid = this.moneris_cloud_receiptid;
        this.moneris_cloud_transid = this.moneris_cloud_transid;


    }
    //@override
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.moneris_cloud_receiptid = this.moneris_cloud_receiptid;
        json.moneris_cloud_transid = this.moneris_cloud_transid;


        return json;
    }
    //@override
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.moneris_cloud_receiptid = json.moneris_cloud_receiptid;
        this.moneris_cloud_transid = json.moneris_cloud_transid;

    }
}
    Registries.Model.extend(Order, PosMonerisCloudOrder);





});
