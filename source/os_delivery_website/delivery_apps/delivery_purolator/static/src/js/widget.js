odoo.define("os_delivery_website.checkout_purolator", function (require) {
  "use strict";
  const publicWidget = require("web.public.widget");
  const core = require("web.core");
  const concurrency = require("web.concurrency");
  const QWeb = core.qweb;

  const _t = core._t;
  const WebsiteSaleDeliveryWidget = publicWidget.registry.websiteSaleDelivery;
  const dp = new concurrency.DropPrevious();

  WebsiteSaleDeliveryWidget.include({
    events: {
      ...WebsiteSaleDeliveryWidget.prototype.events,

    },

    start: function () {
      this._super(...arguments);

    },
    _onCarrierClick: function (ev) {
      $('div[name="canadalator"]').html("");
      const _super = this._super.bind(this);
      const radio = $(ev.currentTarget).find('input[type="radio"]');
      radio.prop("checked", true);

      const carrier_id = parseInt(radio.val());

      dp.add(
        this._rpc({
          route: "/carrier/detail",
          params: {
            carrier_id: parseInt(radio.val()),
          },
        })
      ).then((data) => {
          debugger
        if (data.delivery_type === "purolator") {
          dp.add(
            this._rpc({
              route: "/shop/carrier_rate_shipment/purolator",
              params: {
                carrier_id: carrier_id,
              },
            })
          ).then(() => {
            console.log("Hello purolator");
            const canadalator = $("#purolator");
            dp.add(
              this._rpc({
                route: "/carrier/detail/purolator",
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

              for (const psr of result.purolator_service_rates) {
                let trow = $(`
                  <tr>
                    <td>${psr.service_id}</td>
                    <td>${psr.total_price}</td>
                    <td>
                      ${`Base Price: ${psr.base_price}<br />
                      Sur Charges: ${psr.surcharges}<br />
                      Taxes: ${psr.taxes}<br />
                      `}
                    </td>
                  </tr>
                `);

                const button = $(`
                  <button type="submit" class="btn btn-small btn-primary" name="btnCreateShipment" data-service-name="${
                    data.delivery_type
                  }" data-amount-delivery="${
                  psr.total_price
                }" data-carrier-id="${radio.val()}" id="btnCanadalatorCreateShipment">
                    Ship <i class="fa fa-chevron-right"></i>
                  </button>
                `);
                button.on(
                  "click",
                  {
                    carrier_id: parseInt(radio.val()),
                    amount_delivery: psr.total_price,
                    service_id: psr.value,
                  },
                  (event) => {
                    console.log(event.data);
                    dp.add(
                      this._rpc({
                        route: "/shop/update_carrier/purolator",
                        params: {
                          carrier_id: event.data.carrier_id,
                          amount_delivery: event.data.amount_delivery,
                          service_id: event.data.service_id,
                        },
                      })
                    ).then(this._handleCarrierUpdateResult.bind(this));
                  }
                );

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
          });
        } else if (data.delivery_type === "canadapost") {
          dp.add(
            this._rpc({
              route: "/shop/carrier_rate_shipment/canadapost",
              params: {
                carrier_id: carrier_id,
              },
            })
          ).then(() => {
            console.log("Hello canadapost");
            const canadalator = $("#canadapost");
            debugger
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
                    <td>${cpsr.service_name}</td>
                    <td>${cpsr.total_price}</td>
                    <td>
                      ${`Base Price: ${cpsr.base_price}<br />
                      Sur Charges: ${cpsr.surcharges}<br />
                      Taxes: ${cpsr.taxes}<br />
                      `}
                    </td>
                  </tr>
                `);
                const button = $(`
                  <button type="submit" class="btn btn-small btn-primary" name="btnCreateShipment" data-service-name="${
                    data.delivery_type
                  }" data-amount-delivery="${
                  cpsr.total_price
                }" data-carrier-id="${radio.val()}" id="btnCanadalatorCreateShipment">
                    Ship <i class="fa fa-chevron-right"></i>
                  </button>
                `);
                debugger
                button.on(
                  "click",
                  {
                    carrier_id: parseInt(radio.val()),
                    amount_delivery: cpsr.total_price,
                    service_name: data.delivery_type,
                    service_code:cpsr.service_code,
                    service_id:cpsr.service_id,
                  },
                  (event) => {
                    console.log(event.data);
                    dp.add(
                      this._rpc({
                        route: "/shop/update_carrier/canadapost",
                        params: {
                          carrier_id: event.data.carrier_id,
                          amount_delivery: event.data.amount_delivery,
                          service_code: event.data.service_code,
                          service_id:cpsr.service_id,
                        },
                      })
                    ).then(this._handleCarrierUpdateResult.bind(this));
                  }
                );
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
          });
        } else {
          console.log("Not purolator");
          _super(...arguments);
          $("#purolator").html("");
          $("#canadapost").html("");
        }
      });
    },
  });
});
