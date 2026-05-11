odoo.define("os_delivery_website.checkout_canadapost", function (require) {
  "use strict";
  const publicWidget = require("web.public.widget");
  const core = require("web.core");
  const concurrency = require("web.concurrency");
  const QWeb = core.qweb;

  const _t = core._t;
  const WebsiteSaleDeliveryWidget = publicWidget.registry.websiteSaleDelivery;
  const dp = new concurrency.DropPrevious();

  console.log(WebsiteSaleDeliveryWidget.prototype);

  WebsiteSaleDeliveryWidget.extend({
    events: {
      ...WebsiteSaleDeliveryWidget.prototype.events,
      // 'change select[name="shipping_id"]': "_onSetAddress",
      // "click #delivery_carrier .o_delivery_carrier_select": "_onCarrierClick",
      // "change #services_id": "_onServiceClick",
      // "click .showHideLink": "_onshowHideLink",
      "click #btnCanadalatorCreateShipment": "_updateShippingDetails",
    },
    _updateShippingDetails: function (ev) {
      const carrier_id = ev.target.dataset.carrierId;
      const amount_delivery = ev.target.dataset.amountDelivery;
      const service_name = ev.target.dataset.serviceName;
      const _super = this._super.bind(this);
      const radio = $(ev.currentTarget).find('input[type="radio"]');
      radio.prop("checked", true);
      // console.log(parseInt(radio.val()));
      let self = this;
      console.log({ carrier_id, amount_delivery, service_name });
      // dp.add(
      //   this._rpc({
      //     route: "/shop/update_carrier",
      //     params: {
      //       carrier_id,
      //       canadalator_amount_delivery: amount_delivery,
      //     },
      //   })
      // ).then(this._handleCarrierUpdateResult.bind(this));
    },
  });

  WebsiteSaleDeliveryWidget.include({
    events: {
      ...WebsiteSaleDeliveryWidget.prototype.events,
      // 'change select[name="shipping_id"]': "_onSetAddress",
      // "click #delivery_carrier .o_delivery_carrier_select": "_onCarrierClick",
      // "change #services_id": "_onServiceClick",
      // "click .showHideLink": "_onshowHideLink",
      // "click #btnCanadalatorCreateShipment": "_updateShippingDetails",
    },

    start: function () {
      // const _super = this._super.bind(this);
      // dp.add(
      //   this._rpc({
      //     route: "/carrier/detail",
      //     params: {
      //       carrier_id: parseInt(radio.val()),
      //     },
      //   })
      // ).then((data) => {
      //   if (data.delivery_type !== "purolator") {
      //     _super(...arguments);
      //   }
      // });
      // var $carriers = $(
      //   '#delivery_carrier input[name="delivery_type[]"]:checked:enabled'
      // );
      // console.log($carriers.val());
      // this._rpc({
      //   route: "/carrier/detail",
      //   params: {
      //     carrier_id: 4,
      //   },
      // }).then((data) => console.log(data));
    },
    _onCarrierClick: function (ev) {
      $('div[name="canadalator"]').html("");
      const _super = this._super.bind(this);
      const radio = $(ev.currentTarget).find('input[type="radio"]');
      radio.prop("checked", true);
      const carrier_id = parseInt(radio.val());
      dp.app(
        this._rpc({
          route: "/shop/carrier_rate_shipment",
          params: {
            carrier_id: carrier_id,
          },
        })
      ).then(() => {
        dp.add(
          this._rpc({
            route: "/carrier/detail",
            params: {
              carrier_id: parseInt(radio.val()),
            },
          })
        ).then((data) => {
          debugger;
          if (data.delivery_type === "canadapost") {
            console.log("Hello canadapost");
            const canadalator = $("#canadapost");
            dp.add(
              this._rpc({
                route: "/carrier/detail/canadapost",
                params: {
                  carrier_id: parseInt(radio.val()),
                },
              })
            ).then((result) => {
              const tableHead = $(`
                <thead>
                  <tr>
                    <th align="left" scope="col">Delivery Service</th>
                    <th align="right" scope="col">Estimated Cost</th>
                    <th align="center" scope="col">Cost Breakdown</th>
                    <th align="center" scope="col"></th>
                  </tr>
                </thead>
              `);
              const tableBody = $("<tbody></tbody>");
              for (const cpsr of result.cnpost_service_rates) {
                let trow = $(`
                  <tr>
                    <td>${cpsr.service_id}</td>
                    <td>${cpsr.total_price}</td>
                    <td>
                      ${`Base Price: ${cpsr.base_price}<br />
                      Sur Charges: ${cpsr.surcharges}<br />
                      Taxes: ${cpsr.taxes}<br />
                      `}
                    </td>
                  </tr>
                `);
                // const updateShippingCost = (ev) => {
                //   this._updateShippingCost(ev.data.amount);
                // };
                const button = $(`
                  <button type="submit" class="btn btn-small btn-primary" name="btnCreateShipment" data-service-name="${
                    data.delivery_type
                  }" data-amount-delivery="${
                  cpsr.total_price
                }" data-carrier-id="${radio.val()}" id="btnCanadalatorCreateShipment">
                    Ship <i class="fa fa-chevron-right"></i>
                  </button>
                `);
                button.on(
                  "click",
                  {
                    carrier_id: parseInt(radio.val()),
                    amount_delivery: cpsr.total_price,
                    service_name: data.delivery_type,
                  },
                  (event) => {
                    console.log(event.data);
                    dp.add(
                      this._rpc({
                        route: "/shop/update_carrier/canadapost",
                        params: {
                          carrier_id: event.data.carrier_id,
                          amount_delivery: event.data.amount_delivery,
                        },
                      })
                    ).then(this._handleCarrierUpdateResult.bind(this));
                  }
                );
                // button.data("carrierid", radio.val());
                // .on(
                //   "click",
                //   {
                //     amount: psr.total_price,
                //   },
                //   updateShippingCost
                // );
                const actionColumn = $("<td></td>");
                actionColumn.append(button);
                trow.append(actionColumn);
                tableBody.append(trow);
              }

              const table = $(`
            <table id="estimate_table" class="table">
            </table>
          `);
              table.append(tableHead);
              table.append(tableBody);
              if (!$(canadalator).has("table[id='estimate_table']")) {
                $(canadalator).html(table);
              } else {
                $(canadalator).html(table);
              }
            });
          } else {
            console.log("Not canadapost");
            _super(...arguments);
            $("#canadapost").html("");
          }
        });
      });
      // console.log(parseInt(radio.val()));
      // let self = this;
    },
    /**
     * @private
     * @param {Event} ev
     */
    _updateShippingDetails: function (ev) {
      const carrier_id = ev.target.dataset.carrierId;
      const amount_delivery = ev.target.dataset.amountDelivery;
      const service_name = ev.target.dataset.serviceName;
      const _super = this._super.bind(this);
      const radio = $(ev.currentTarget).find('input[type="radio"]');
      radio.prop("checked", true);
      // console.log(parseInt(radio.val()));
      let self = this;
      console.log({ carrier_id, amount_delivery, service_name });
      // dp.add(
      //   this._rpc({
      //     route: "/shop/update_carrier",
      //     params: {
      //       carrier_id,
      //       canadalator_amount_delivery: amount_delivery,
      //     },
      //   })
      // ).then(this._handleCarrierUpdateResult.bind(this));
    },
  });
});
