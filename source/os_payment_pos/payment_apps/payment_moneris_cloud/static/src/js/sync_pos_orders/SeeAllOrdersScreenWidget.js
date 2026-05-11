odoo.define('point_of_sale.SeeAllOrdersScreenWidget', function (require) {
	'use strict';


	var models = require('point_of_sale.models');

	const { Gui } = require('point_of_sale.Gui');
	const PosComponent = require('point_of_sale.PosComponent');
	const { useListener } = require('web.custom_hooks');
	const Registries = require('point_of_sale.Registries');

	var core = require('web.core');
	var field_utils = require('web.field_utils');
	var utils = require('web.utils');
	var round_di = utils.round_decimals;

	var QWeb = core.qweb;
	var _t = core._t;
	var pos_order_domain = [];
	var rpc = require('web.rpc');

	// SeeAllOrdersScreenWidget start

	/**
	 * Render this screen using `showTempScreen` to show orders.
	 * When the shown screen is confirmed ('Set Customer' or 'Deselect Customer'
	 * button is clicked), the call to `showTempScreen` resolves to the
	 * selected client. E.g.
	 *
	 * ```js
	 * const { confirmed, payload: selectedClient } = await showTempScreen('ClientListScreen');
	 * if (confirmed) {
	 *   // do something with the selectedClient
	 * }
	 * ```
	 *
	 * @props client - originally selected client
	 */
	class SeeAllOrdersScreenWidget extends PosComponent {
		constructor() {
			super(...arguments);
			console.log("SeeAllOrdersScreenWidget")
			useListener('click-back', () => this.back());
			useListener('pos-order-click', () => this.back());
			// useListener('click-return-order', () => this.returnOrder);//doesnot work
			// useListener('return-order', () => this.returnOrder);//doesnot work


			var promiseRes = this.get_sync_pos_return();
			var self = this;
			console.log("self.data->", self.data)
			setTimeout(function () { self.show(); }, 200);
		}
		// Lifecycle hooks
		back() {
			console.log("-->back")
			this.props.resolve({ confirmed: false, payload: false });
			this.trigger('close-temp-screen');
		}

		// returnOrder() {
		// 	Gui.showPopup("ErrorPopup", {
		// 		title: this.env._t('Payment Screen Custom Button Clicked'),
		// 		body: this.env._t('Welcome to OWL'),
		// 	});
		// }

		get_selected_partner() {
			var self = this;
			if (self.env.pos)
				return self.env.pos.get_order().get_client();
			// return self.pos.gui.get_current_screen_param('selected_partner_id');
			else
				return undefined;
		}

		get_sync_pos_return() {
			var self = this;
			return new Promise(function (resolve, reject) {
				rpc.query({
					model: 'pos.order',
					method: 'get_sync_pos_return',
					args: [[1]],
				}).then(function (result) {
					console.log("result: ", result);
					resolve();
					self.data = result;
					return result;
				});
			});

		}

		render_list_orders(orders, search_input) {
			console.log("render_list_orders-->Start")
			var self = this;

			var selected_partner_id = this.get_selected_partner();

			var selected_client_orders = [];
			if (selected_partner_id != undefined) {
				for (var i = 0; i < orders.length; i++) {
					if (orders[i].partner_id[0] == selected_partner_id)
						selected_client_orders = selected_client_orders.concat(orders[i]);
				}
				orders = selected_client_orders;
			}

			if (search_input != undefined && search_input != '') {
				var selected_search_orders = [];
				var search_text = search_input.toLowerCase()
				for (var i = 0; i < orders.length; i++) {
					if (orders[i].partner_id == '') {
						orders[i].partner_id = [0, '-'];
					}
					if (orders[i].partner_id[1] == false) {
						if (((orders[i].name.toLowerCase()).indexOf(search_text) != -1) || ((orders[i].state.toLowerCase()).indexOf(search_text) != -1) || ((orders[i].pos_reference.toLowerCase()).indexOf(search_text) != -1)) {
							selected_search_orders = selected_search_orders.concat(orders[i]);
						}
					}
					else {
						if (((orders[i].name.toLowerCase()).indexOf(search_text) != -1) || ((orders[i].state.toLowerCase()).indexOf(search_text) != -1) || ((orders[i].pos_reference.toLowerCase()).indexOf(search_text) != -1) || ((orders[i].partner_id[1].toLowerCase()).indexOf(search_text) != -1)) {
							selected_search_orders = selected_search_orders.concat(orders[i]);
						}
					}
				}
				orders = selected_search_orders;
			}


			var content = document.querySelector('.orders-list-contents');

			content.innerHTML = "";
			var orders = orders;
			var current_date = null;
			
			if (orders) {
				for (var i = 0, len = Math.min(orders.length, 1000); i < len; i++) {
					var order = orders[i];
					current_date = field_utils.format.datetime(moment(order.date_order), { type: 'datetime' });
					var ordersline_html = QWeb.render('OrdersLine', { widget: this, order: orders[i], selected_partner_id: orders[i].partner_id[0], current_date: current_date });
					var ordersline = document.createElement('tbody');
					// var button = '<td><button class="btn btn-primary pos-order-click" style="length: 100%; width: 100%;" name="Select" string="Select" data-id=' + orders[i].id.toString() + '>Select</button></td>'
					console.log("self.data.sync_pos_return===>>>", self.data.sync_pos_return)
					if (self.data && self.data.sync_pos_return == "true") {
						var button = `<td>
											<button class="return-order" t-att-id='` + orders[i].id.toString() + `' data-id='` + orders[i].id.toString() + `' style="cursor: pointer; color: #fff; background-color: #7F82AC;"><i class='fa fa-sign-in'></i> Return Order </button>
										 </td>`
						ordersline.innerHTML = ordersline_html.split("</tr>")[0] + button + "</tr>";
					}
					else {
						ordersline.innerHTML = ordersline_html;
					}

					ordersline = ordersline.childNodes[1];
					content.appendChild(ordersline);
				}
			}

			$('.orders-line-name', 'click', function (event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});

			console.log("FINISH-->content-------->", content)

			// $('.orders-list-contents td').on("click", function(){
			// 	console.log(".orders-list-contents td")
			// 	var o_id = $(this).data('id');
			// 	self.display_details(o_id);
			// });

			// $('.pos-order-click').on("click", function () {
			// 	console.log(".pos-order-click'-->click")
			// 	console.log("event-->", event);
			// 	var o_id = $(this).data('id');
			// 	self.display_details(o_id);
			// });

			//Return Order
			$('.return-order').on("click", function (result) {
				var order_id = parseInt(this.dataset.id)
				console.log("order_id")
				console.log(order_id)
				var selectedOrder = null;

				orders = self.env.pos.get('all_orders_list');
				for (var i = 0, len = Math.min(orders.length, 1000); i < len; i++) {
					if (orders[i] && orders[i].id == order_id) {
						selectedOrder = orders[i];
					}
				}


				var orderlines = [];
				var order_line_data = self.env.pos.get('all_orders_line_list');
				selectedOrder.lines.forEach(function (line_id) {
					console.log("line_id")
					console.log(line_id)
					for (var y = 0; y < order_line_data.length; y++) {
						if (order_line_data[y]['id'] == line_id) {
							orderlines.push(order_line_data[y]);
						}
					}
				});

				console.log(selectedOrder)
				console.log(orderlines)

				try {
					self.env.pos.last_order_id = selectedOrder;
				} catch (error) {
					
				}
				
				if ($('.bi-pos-modal').length > 0) {
					$('.bi-pos-modal')[0].style.display = "block";
				}
				Gui.showPopup('PosReturnOrderPopupWidget', {
					order: selectedOrder,
					orderlines: orderlines,
				});

				// self.gui.show_popup('pos_return_order_popup_widget', { 'orderlines': orderlines, 'order': selectedOrder });
			});
			//End Return Order



			self.orderline_click_events();


		}

		get_current_day() {
			console.log("get_current_day")
			var today = new Date();
			var dd = today.getDate();
			var mm = today.getMonth() + 1; //January is 0!

			var yyyy = today.getFullYear();
			if (dd < 10) {
				dd = '0' + dd;
			}
			if (mm < 10) {
				mm = '0' + mm;
			}
			today = yyyy + '-' + mm + '-' + dd;
			return today;
		}

		get_orders_domain() {
			console.log("get_orders_domain")
			var self = this;
			var current = self.env.pos.pos_session.id;
			if (self.env.pos.config.pos_session_limit == 'all') {
				if (self.env.pos.config.show_draft == true) {
					if (self.env.pos.config.show_posted == true) {
						pos_order_domain = [['state', 'in', ['draft', 'done']]];
						return [['state', 'in', ['draft', 'done']]];
					}
					else {
						pos_order_domain = [['state', 'in', ['draft']]];
						return [['state', 'in', ['draft']]];
					}
				}
				else if (self.env.pos.config.show_posted == true) {
					pos_order_domain = [['state', 'in', ['done']]];
					return [['state', 'in', ['done']]];
				}
				else {
					pos_order_domain = [['state', 'in', ['draft', 'done', 'paid', 'invoiced', 'cancel']]];
					return [['state', 'in', ['draft', 'done', 'paid', 'invoiced', 'cancel']]];
				}
			}
			if (self.env.pos.config.pos_session_limit == 'last3') {
				if (self.env.pos.config.show_draft == true) {
					if (self.env.pos.config.show_posted == true) {
						pos_order_domain = [['state', 'in', ['draft', 'done']], ['session_id', 'in', [current, current - 1, current - 2, current - 3]]];
						return [['state', 'in', ['draft', 'done']], ['session_id', 'in', [current, current - 1, current - 2, current - 3]]];
					}
					else {
						pos_order_domain = [['state', 'in', ['draft']], ['session_id', 'in', [current, current - 1, current - 2, current - 3]]];
						return [['state', 'in', ['draft']], ['session_id', 'in', [current, current - 1, current - 2, current - 3]]];
					}
				}
				else if (self.env.pos.config.show_posted == true) {
					pos_order_domain = [['state', 'in', ['done']], ['session_id', 'in', [current, current - 1, current - 2, current - 3]]];
					return [['state', 'in', ['done']], ['session_id', 'in', [current, current - 1, current - 2, current - 3]]];
				}
				else {
					pos_order_domain = [['session_id', 'in', [current, current - 1, current - 2, current - 3]]];
					return [['session_id', 'in', [current, current - 1, current - 2, current - 3]]];
				}
			}
			if (self.env.pos.config.pos_session_limit == 'last5') {
				if (self.env.pos.config.show_draft == true) {
					if (self.env.pos.config.show_posted == true) {
						pos_order_domain = [['state', 'in', ['draft', 'done']], ['session_id', 'in', [current, current - 1, current - 2, current - 3, current - 4, current - 5]]];
						return [['state', 'in', ['draft', 'done']], ['session_id', 'in', [current, current - 1, current - 2, current - 3, current - 4, current - 5]]];
					}
					else {
						pos_order_domain = [['state', 'in', ['draft']], ['session_id', 'in', [current, current - 1, current - 2, current - 3, current - 4, current - 5]]];
						return [['state', 'in', ['draft']], ['session_id', 'in', [current, current - 1, current - 2, current - 3, current - 4, current - 5]]];
					}
				}
				else if (self.env.pos.config.show_posted == true) {
					pos_order_domain = [['state', 'in', ['done']], ['session_id', 'in', [current, current - 1, current - 2, current - 3, current - 4, current - 5]]];
					return [['state', 'in', ['done']], ['session_id', 'in', [current, current - 1, current - 2, current - 3, current - 4, current - 5]]];
				}
				else {
					pos_order_domain = [['session_id', 'in', [current, current - 1, current - 2, current - 3, current - 4, current - 5]]];
					return [['session_id', 'in', [current, current - 1, current - 2, current - 3, current - 4, current - 5]]];
				}
			}

			if (self.env.pos.config.pos_session_limit == 'current_session') {
				if (self.env.pos.config.show_draft == true) {
					if (self.env.pos.config.show_posted == true) {
						pos_order_domain = [['state', 'in', ['draft', 'done']], ['session_id', 'in', [current]]];
						return [['state', 'in', ['draft', 'done']], ['session_id', 'in', [current]]];
					}
					else {
						pos_order_domain = [['state', 'in', ['draft']], ['session_id', 'in', [current]]];
						return [['state', 'in', ['draft']], ['session_id', 'in', [current]]];
					}
				}
				else if (self.env.pos.config.show_posted == true) {
					pos_order_domain = [['state', 'in', ['done']], ['session_id', 'in', [current]]];
					return [['state', 'in', ['done']], ['session_id', 'in', [current]]];
				}
				else {
					pos_order_domain = [['session_id', 'in', [current]]];
					return [['session_id', 'in', [current]]];
				}
			}

		}

		get_orders_fields() {
			var fields = ['name', 'id', 'date_order', 'partner_id', 'pos_reference', 'lines', 'amount_total', 'session_id', 'state', 'company_id', 'pos_order_date', 'barcode'];
			return fields;
		}

		get_pos_orders() {
			var self = this;
			var fields = self.get_orders_fields();
			var pos_domain = self.get_orders_domain();
			var load_orders = [];
			var load_orders_line = [];
			var order_ids = [];
			self.rpc({
				model: 'pos.order',
				method: 'search_read',
				args: [pos_order_domain, fields],
			}, { async: false }).then(function (output) {
				if (self.env.pos.config.pos_session_limit == 'current_day') {
					var today = self.get_current_day();
					output.forEach(function (i) {
						if (today == i.pos_order_date) {
							load_orders.push(i);
						}
					});
				}
				else {
					load_orders = output;
				}
				self.env.pos.db.get_orders_by_id = {};
				load_orders.forEach(function (order) {
					order_ids.push(order.id)
					self.env.pos.db.get_orders_by_id[order.id] = order;
				});

				var fields_domain = [['order_id', 'in', order_ids]];
				self.rpc({
					model: 'pos.order.line',
					method: 'search_read',
					args: [fields_domain],
				}, { async: false }).then(function (output1) {
					self.env.pos.db.all_orders_line_list = output1;
					load_orders_line = output1;
					self.env.pos.set({ 'all_orders_list': load_orders });
					self.env.pos.set({ 'all_orders_line_list': output1 });
					self.render_list_orders(load_orders, undefined);
					return [load_orders, load_orders_line]
				});
			});

		}

		display_details(o_id) {
			var self = this;
			var orders = self.env.pos.get('all_orders_list');
			var orders_lines = self.env.pos.get('all_orders_line_list');
			var orders1 = [];
			for (var ord = 0; ord < orders.length; ord++) {
				if (orders[ord]['id'] == o_id) {
					orders1 = orders[ord];
				}
			}
			var current_date = field_utils.format.datetime(moment(orders1.date_order), { type: 'datetime' });
			var orderline = [];
			for (var n = 0; n < orders_lines.length; n++) {
				if (orders_lines[n]['order_id'][0] == o_id) {
					orderline.push(orders_lines[n])
				}
			}
			// this.gui.show_popup('see_order_details_popup_widget', {'order': [orders1], 'orderline':orderline,'current_date':current_date});

			Gui.showPopup('SeeOrderDetailsPopupWidget', {
				title: 'Unable to create order',
				body: 'Orders cannot be created when there is no active table in restaurant mode',
				order: [orders1],
				orderline: orderline,
				current_date: current_date,
			});

		}

		orderline_click_events() {
			console.log("orderline_click_events");
			var self = this;

			//For Odoo 14
			$('.orders-line-name').on("click", function (event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});
			$('.orders-line-ref').on("click", function (event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});
			$('.orders-line-partner').on("click", function (event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});
			$('.orders-line-date').on("click", function (event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});
			$('.orders-line-tot').on("click", function (event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});
			$('.orders-line-state').on("click", function (event) {
				var o_id = $(this).data('id');
				self.display_details(o_id);
			});
		}

		show(options) {
			var self = this;
			// this._super(options);
			this.details_visible = false;
			self.get_pos_orders();
			var orders = self.env.pos.get('all_orders_list');
			var orders_lines = self.env.pos.get('all_orders_line_list');
			$('.search-order input').val('');


			console.log("render_list_orders-->")
			self.render_list_orders(orders, undefined);

			console.log("render_list_orders-->ENDSS")

			var current_date = null;

			console.log(".refresh-order-->")

			$('.refresh-order').on('click', function () {
				console.log(".refresh-order")

				$('.search-order input').val('');
				var params = self.env.pos.get_order().get_screen_data('params');
				if (params && params['selected_partner_id']) {
					params['selected_partner_id'] = undefined;
				}
				self.get_pos_orders();
			});

			//this code is for Search Orders
			$('.search-order input').keyup(function () {
				console.log("..search-order input-order-->")
				self.render_list_orders(orders, this.value);
			});


		}

		format_currency(amount, precision) {
			var currency =
				this && this.currency
					? this.currency
					: { symbol: '$', position: 'after', rounding: 0.01, decimals: 2 };

			amount = this.format_currency_no_symbol(amount, precision, currency);

			if (currency.position === 'after') {
				return amount + ' ' + (currency.symbol || '');
			} else {
				return (currency.symbol || '') + ' ' + amount;
			}
		}

		format_currency_no_symbol(amount, precision, currency) {
			if (!currency) {
				currency =
					this && this.currency
						? this.currency
						: { symbol: '$', position: 'after', rounding: 0.01, decimals: 2 };
			}
			var decimals = currency.decimals;

			if (precision && this.dp[precision] !== undefined) {
				decimals = this.dp[precision];
			}

			if (typeof amount === 'number') {
				amount = round_di(amount, decimals).toFixed(decimals);
				amount = field_utils.format.float(round_di(amount, decimals), {
					digits: [69, decimals],
				});
			}

			return amount;
		}


	}
	SeeAllOrdersScreenWidget.template = 'SeeAllOrdersScreenWidget';

	Registries.Component.add(SeeAllOrdersScreenWidget);


	// Start ClientListScreenWidget
	// gui.Gui.prototype.screen_classes.filter(function(el) { return el.name == 'clientlist'})[0].widget.include({
	// 		show: function(){
	// 			this._super();
	// 			var self = this;
	// 			this.$('.view-orders').click(function(){
	// 				self.gui.show_screen('see_all_orders_screen_widget', {});
	// 			});
	// 		$('.selected-client-orders').on("click", function() {
	// 			self.gui.show_screen('see_all_orders_screen_widget', {
	// 				'selected_partner_id': this.id
	// 			});
	// 		});

	// 	},
	// });

	// screens.ReceiptScreenWidget.include({
	// 	show: function () {
	// 		this._super(); 
	// 		var order = this.pos.get_order();                     
	// 		$("#barcode_print").barcode(
	// 			order.barcode, // Value barcode (dependent on the type of barcode)
	// 			"code128" // type (string)
	// 		);
	// 	},
	// });

	// return SeeAllOrdersScreenWidget;

	return {
		'SeeAllOrdersScreenWidget': SeeAllOrdersScreenWidget
	}

	// End SeeAllOrdersScreenWidget
});
