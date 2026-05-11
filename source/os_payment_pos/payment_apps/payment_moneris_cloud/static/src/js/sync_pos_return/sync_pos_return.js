odoo.define('point_of_sale.sync_pos_return', function (require) {
    "use strict";

    const models = require('point_of_sale.models');

    const {Gui} = require('point_of_sale.Gui');
    const {debounce} = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    const ProductScreen = require('point_of_sale.ProductScreen');

    var core = require('web.core');
    var QWeb = core.qweb;

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');

    var _t = core._t;


    // // Start PosBarcodePopupWidget
    // class PosBarcodePopupWidget extends AbstractAwaitablePopup {

    //     constructor() {
    //         super(...arguments);
    //         // $('.modal-dialog').show();
    //         this.renderElement();
    //         useListener('click-back', this.back);
    //         useListener('apply-barcode-return-order', this.renderElement);
    //     }

    //     back() {
    //         $('.modal-dialog').hide();
    //     }

    //     renderElement() {
    //         var selectedOrder = this.env.pos.get_order();
    //         var orderlines = this.env.options.orderlines;
    //         var order = this.env.options.order;
    //         var return_products = {};
    //         var exact_return_qty = {};
    //         var exact_entered_qty = {};
    //         var orders = this.env.pos.get('all_orders_list');


    //         // $('#apply_barcode_return_order').on("click", function (event) {
    //         // var entered_barcode = $("#entered_item_barcode").val();
    //         // var order_id = parseInt(this.id);
    //         // var selectedOrder = null;
    //         // orders =self.pos.get('all_orders_list');
    //         // for(var i = 0, len = Math.min(orders.length,1000); i < len; i++) {
    //         // if (orders[i] && orders[i].barcode == entered_barcode) {
    //         // selectedOrder = orders[i];
    //         // }
    //         // }
    //         // if(selectedOrder){
    //         // var orderlines = [];
    //         // var order_line_data = self.pos.get('all_orders_line_list');
    //         // selectedOrder.lines.forEach(function(line_id) {
    //         // for(var y=0; y<order_line_data.length; y++){
    //         // if(order_line_data[y]['id'] == line_id){
    //         // orderlines.push(order_line_data[y]);
    //         // }
    //         // }
    //         // });
    //         // Gui.showPopup('PosReturnOrderPopupWidget',{'orderlines': orderlines});
    //         // }
    //         // else{

    //         // Gui.showPopup('ErrorPopup', {
    //         // title: _t('Invalid Barcode'),
    //         // body: _t('The Barcode You are Entering is Invalid'),
    //         // });
    //         // }
    //         // });
    //     }
    // } PosBarcodePopupWidget.template = 'PosBarcodePopupWidget';
    // PosBarcodePopupWidget.defaultProps = {
    //     confirmText: 'Ok',
    //     cancelText: 'Cancel',
    //     title: 'Confirm ?',
    //     body: '',
    //     order: [],
    //     orderline: '',
    //     current_date: ''
    // };

    // Registries.Component.add(PosBarcodePopupWidget);
    // // End PosBarcodePopupWidget


    // Start POSBarcodeReturnWidget
    // class POSBarcodeReturnWidget extends PosComponent {
    //     constructor() {
    //         console.log("constructor")
    //         super(...arguments);
    //         useListener('click', this._onClick);
    //         useListener('.button.cancel', this.click_cancel);

    //     }
    //     async _onClick() {
    //         console.log("_onClick")
    //         Gui.showPopup('PosBarcodePopupWidget', {
    //             title: '',
    //             body: ''
    //         });


    //     }
    //     async click_cancel() {
    //         console.log("click_cancel")
    //     }
    //     renderElement() {
    //         var self = this;
    //         // this._super();
    //         var selectedOrder = this.env.pos.get_order();
    //         var orderlines = self.options.orderlines;
    //         var order = self.options.order;
    //         var return_products = {};
    //         var exact_return_qty = {};
    //         var exact_entered_qty = {};

    //         var orders = self.env.pos.get('all_orders_list');

    //         // this.$('#apply_barcode_return_order').click(function() {
    //         // var entered_barcode = $("#entered_item_barcode").val();
    //         // var order_id = parseInt(this.id);
    //         // var selectedOrder = null;
    //         // orders =self.pos.get('all_orders_list');
    //         // for(var i = 0, len = Math.min(orders.length,1000); i < len; i++) {
    //         // if (orders[i] && orders[i].barcode == entered_barcode) {
    //         // selectedOrder = orders[i];
    //         // }
    //         // }
    //         // if(selectedOrder){
    //         // var orderlines = [];
    //         // var order_line_data = self.pos.get('all_orders_line_list');
    //         // selectedOrder.lines.forEach(function(line_id) {
    //         // for(var y=0; y<order_line_data.length; y++){
    //         // if(order_line_data[y]['id'] == line_id){
    //         // orderlines.push(order_line_data[y]);
    //         // }
    //         // }
    //         // });
    //         // Gui.show_popup('PosReturnOrderPopupWidget',{'orderlines': orderlines});
    //         // }
    //         // else{
    //         // self.pos.gui.show_popup('error', {
    //         // 'title': _t('Invalid Barcode'),
    //         // 'body': _t("The Barcode You are Entering is Invalid"),
    //         // });
    //         // }
    //         // });
    //     }
    // } POSBarcodeReturnWidget.template = 'POSBarcodeReturnWidget';
    // ProductScreen.addControlButton({
    //     component: POSBarcodeReturnWidget,
    //     condition: function () {
    //         return this.env.pos;
    //     }
    // });
    // Registries.Component.add(POSBarcodeReturnWidget);
    // // End POSBarcodeReturnWidget


    class PosReturnOrderPopupWidget extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            // $('.bi-pos-modal')[0].style.display = "block";
            useListener('posreturncancel', this.posreturncancel);
            useListener('applyreturnorder', () => this.applyreturnorder);

        }
        // Lifecycle hooks
        posreturncancel() {
            // this.props.resolve({ confirmed: false, payload: false });
            // this.trigger('close-temp-screen');
            if ($('.bi-pos-modal').length > 0) {
                $('.bi-pos-modal')[0].style.display = "none";
            }

        }

        applyreturnorder() {
            var self = this;
            // this._super();
            var selectedOrder = this.env.pos.get_order();

            var orderlines = this.props.orderlines;
            var order = this.props.order;
            var partner_id = false
            var client = false
            if (order && order.partner_id != null) 
                partner_id = order.partner_id[0];
            
            client = this.env.pos.db.get_partner_by_id(partner_id);
            var return_products = {};
            var exact_return_qty = {};
            var exact_entered_qty = {};

            var entered_code = $("#entered_item_qty").val();
            var list_of_qty = $('.entered_item_qty');
            $.each(list_of_qty, function (index, value) {
                var entered_item_qty = $(value).find('input');
                var qty_id = parseFloat(entered_item_qty.attr('qty-id'));
                var line_id = parseFloat(entered_item_qty.attr('line-id'));
                var entered_qty = parseFloat(entered_item_qty.val());
                exact_return_qty = qty_id;
                exact_entered_qty = entered_qty || 0;
                if (! exact_entered_qty) {
                    return;
                } else if (exact_return_qty >= exact_entered_qty) {
                    return_products[line_id] = entered_qty;
                } else {
                    alert("Cannot Return More quantity than purchased");
                    return;
                }
            });
            // return return_products;

            Object.keys(return_products).forEach(function (line_id) {
                var orders_lines = self.env.pos.get('all_orders_line_list');
                var orderline = [];
                for (var n = 0; n < orders_lines.length; n++) {
                    if (orders_lines[n]['id'] == line_id) {
                        var product = self.env.pos.db.get_product_by_id(orders_lines[n].product_id[0]);
                        selectedOrder.add_product(product, {
                            quantity: -parseFloat(return_products[line_id]),
                            price: orders_lines[n].price_unit,
                            discount: orders_lines[n].discount
                        });
                        selectedOrder.selected_orderline.original_line_id = orders_lines[n].id;
                    }
                }
            });
            selectedOrder.set_client(client);
            self.env.pos.set_order(selectedOrder);

            // self.gui.show_screen('products');
            if ($('.bi-pos-modal').length > 0) {
                $('.bi-pos-modal')[0].style.display = "none";
            }
            this.trigger('close-temp-screen');


        }

    } PosReturnOrderPopupWidget.template = 'PosReturnOrderPopupWidget';
    PosReturnOrderPopupWidget.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Confirm ?',
        body: '',
        order: [],
        orderline: ''
    };

    Registries.Component.add(PosReturnOrderPopupWidget);
    // End PosReturnOrderPopupWidget


    return {'PosReturnOrderPopupWidget': PosReturnOrderPopupWidget}

});
