// pos_orders_list js
odoo.define('point_of_sale.sync_pos_orders', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    const {Gui} = require('point_of_sale.Gui');
    const PosComponent = require('point_of_sale.PosComponent');
    const {posbus} = require('point_of_sale.utils');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const PaymentScreen = require('point_of_sale.PaymentScreen');

    const {debounce} = owl.utils;
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var utils = require('web.utils');
    var round_di = utils.round_decimals;

    var QWeb = core.qweb;
    var _t = core._t;
    var pos_order_domain = [];

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');

    var OrderSuper = models.Order;
    var posorder_super = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function (attr, options) {
            this.barcode = this.barcode || "";
            this.set_barcode();
            posorder_super.initialize.call(this, attr, options);
        },

        set_barcode: function () {
            var self = this;
            var temp = Math.floor(100000000000 + Math.random() * 9000000000000)
            self.barcode = temp.toString();
        },

        export_as_JSON: function () {
            var self = this;
            var loaded = OrderSuper.prototype.export_as_JSON.call(this);
            loaded.barcode = self.barcode;
            return loaded;
        }

    });


    // Start SeeAllOrdersButtonWidget
    class SeeAllOrdersButtonWidget extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this._onClick);

        }
        is_available() {
            const order = this.env.pos.get_order();
            return order
        }

        async _onClick() {
            var self = this;
            var params = self.env.pos.get_order().get_screen_data('params');
            if (params && params['selected_partner_id']) {
                params['selected_partner_id'] = undefined;
            }

            var currentClient = false;
            // const { confirmed, payload: newClient } = await this.showTempScreen(
				const { } = await this.showTempScreen(
					'SeeAllOrdersScreenWidget',
					{ client: currentClient }
				);

        }


    } SeeAllOrdersButtonWidget.template = 'SeeAllOrdersButtonWidget';
    ProductScreen.addControlButton({
        component: SeeAllOrdersButtonWidget,
        condition: function () {
            return this.env.pos;
        }
    });
    Registries.Component.add(SeeAllOrdersButtonWidget);
    // End SeeAllOrdersButtonWidget


    class SeeOrderDetailsPopupWidget extends AbstractAwaitablePopup {} SeeOrderDetailsPopupWidget.template = 'SeeOrderDetailsPopupWidget';
    SeeOrderDetailsPopupWidget.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Confirm ?',
        body: '',
        order: [],
        orderline: '',
        current_date: ''
    };

    Registries.Component.add(SeeOrderDetailsPopupWidget);
    // End SeeOrderDetailsPopupWidget


    // Start OrdersLine
    class OrdersLine extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click-back', this.back);
            useListener('click-return-order', () => this.returnOrder);
            useListener('.return-order', () => this.returnOrder);

            // Return Order
            $('.return-order').on("click", function () {

                console.log("return-order")

                var order_id = parseInt(this.id);
                var selectedOrder = null;
                orders = self.pos.get('all_orders_list');
                for (var i = 0, len = Math.min(orders.length, 1000); i < len; i++) {
                    if (orders[i] && orders[i].id == order_id) {
                        selectedOrder = orders[i];
                    }
                }
                var orderlines = [];
                var order_line_data = self.pos.get('all_orders_line_list');
                selectedOrder.lines.forEach(function (line_id) {
                    for (var y = 0; y < order_line_data.length; y++) {
                        if (order_line_data[y]['id'] == line_id) {
                            orderlines.push(order_line_data[y]);
                        }
                    }
                });


                Gui.showPopup('SeeOrderDetailsPopupWidget', {
                    title: 'Unable to create order',
                    body: 'Orders cannot be created when there is no active table in restaurant mode',
                    order: [orders1],
                    orderline: orderline,
                    current_date: current_date
                });

            });
            // End Return Order

        }

        // Lifecycle hooks
        back() {
            this.props.resolve({confirmed: false, payload: false});
            this.trigger('close-temp-screen');
        }

        returnOrder() {
            Gui.showPopup("ErrorPopup", {
                title: this.env._t('Payment Screen Custom Button Clicked'),
                body: this.env._t('Welcome to OWL')
            });
        }
    } OrdersLine.template = 'OrdersLine';

    // End OrdersLine

    return {
		'SeeAllOrdersButtonWidget':SeeAllOrdersButtonWidget,
		'OrdersLine': OrdersLine,
		'SeeOrderDetailsPopupWidget':SeeOrderDetailsPopupWidget,
	}
});
