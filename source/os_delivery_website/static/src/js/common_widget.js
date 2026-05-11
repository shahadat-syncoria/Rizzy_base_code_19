/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { KeepLast } from "@web/core/utils/concurrency";

import WebsiteSaleCheckout from '@website_sale/js/checkout'


//  const Dialog = require("web.Dialog");


//const WebsiteSaleCheckout = publicWidget.registry.WebsiteSaleCheckout;


WebsiteSaleCheckout.include({

    events: {
      ...WebsiteSaleCheckout.prototype.events,
    },

    start: async function () {
    debugger;
      await this._super(...arguments);
      this.keepLast = new KeepLast();
      var self = this;
      self.keepLast = new KeepLast();
      // var agmts = { ...arguments };
      // const _super = this._super.bind(this);
      var $carriers = $('#o_delivery_methods input[name="delivery_type"]');
      // var $payButton = $('button[name="o_payment_submit_button"]');
      // var tototo = "";
      // Workaround to:
      // - update the amount/error on the label at first rendering
      // - prevent clicking on 'Pay Now' if the shipper rating fails
      // if ($carriers.length > 0) {
      //   if ($carriers.filter(":checked").length === 0) {
      //     $payButton.prop("disabled", true);
      //     var disabledReasons = $payButton.data("disabled_reasons") || {};
      //     disabledReasons.carrier_selection = true;
      //     $payButton.data("disabled_reasons", disabledReasons);
      //   }
      //   $carriers.filter(":checked").click();
      // }

      // console.log($carriers);

      // Asynchronously retrieve every carrier price
      $.each($carriers, function (k, carrierInput) {
        console.log($(carrierInput).val());

        self.keepLast.add(
          self.rpc("/carrier/detail",
            {
              carrier_id:parseInt(carrierInput.value),
            },
          )
        ).then(function (data) {
            console.log("================", data);

            // console.log("=>>>>>>>>>>>>>>>>>>", data);
            if (
              data.delivery_type === "purolator" ||
              data.delivery_type === "canadapost"
            ) {
              // self._showLoading($(carrierInput));
//              $(carrierInput).siblings(".o_wsale_delivery_badge_price").empty();
//              $(carrierInput)
//                .siblings(".o_wsale_delivery_badge_price")
//                .append("Select to compute delivery rate");
              // return "";
            }

            // console.log("hello");
            // return self
            //   ._rpc({
            //     route: "/shop/carrier_rate_shipment",
            //     params: {
            //       carrier_id: carrierInput.value,
            //     },
            //   })
            //   .then(self._handleCarrierUpdateResultBadge.bind(self));
            // else {
            // return this._super.apply(this, arguments);
            // return _super(...arguments);
            // }
            // else {
            // $carrierInput.siblings(".o_wsale_delivery_badge_price").empty();
            // self._showLoading($(carrierInput));
            // self
            //   ._rpc({
            //     route: "/shop/carrier_rate_shipment",
            //     params: {
            //       carrier_id: carrierInput.value,
            //     },
            //   })
            //   .then(self._handleCarrierUpdateResultBadge.bind(self));
            // self._super.apply(this, arguments);
            // _super(...arguments);
            // }
          })
          .catch((error) => {
            console.log(error);
//            $(carrierInput).siblings(".o_wsale_delivery_badge_price").empty();
//            $(carrierInput)
//              .siblings(".o_wsale_delivery_badge_price")
//              .append("Select to compute delivery rate");
          });
      });

      // _.each($carriers, function (carrierInput, k) {
      //   console.log($(carrierInput).val());

      //   dp.add(
      //     self._rpc({
      //       route: "/carrier/detail",
      //       params: {
      //         carrier_id: parseInt(carrierInput.value),
      //       },
      //     })
      //   ).then(function (data) {
      //     console.log("=>>>>>>>>>>>>>>>>>>", data);
      //     if (data.delivery_type === "purolator") {
      //       // self._showLoading($(carrierInput));
      //       tototo = data.delivery_type;
      //       console.log(tototo);
      //       $(carrierInput).siblings(".o_wsale_delivery_badge_price").empty();
      //       $(carrierInput)
      //         .siblings(".o_wsale_delivery_badge_price")
      //         .append("Select to compute delivery rate");
      //       return "";
      //     }

      //     console.log("hello");
      //     return self
      //       ._rpc({
      //         route: "/shop/carrier_rate_shipment",
      //         params: {
      //           carrier_id: carrierInput.value,
      //         },
      //       })
      //       .then(self._handleCarrierUpdateResultBadge.bind(self));
      //     // else {
      //     // return this._super.apply(this, arguments);
      //     // return _super(...arguments);
      //     // }
      //     // else {
      //     // $carrierInput.siblings(".o_wsale_delivery_badge_price").empty();
      //     // self._showLoading($(carrierInput));
      //     // self
      //     //   ._rpc({
      //     //     route: "/shop/carrier_rate_shipment",
      //     //     params: {
      //     //       carrier_id: carrierInput.value,
      //     //     },
      //     //   })
      //     //   .then(self._handleCarrierUpdateResultBadge.bind(self));
      //     // self._super.apply(this, arguments);
      //     // _super(...arguments);
      //     // }
      //   });
      // });
      // return this;
      // if (turnOfLoading) {
      //   alert("yes");

      // } else {
      //   return this._super.apply(this, arguments);
      // }
    },
    _onCarrierClick: async function (ev) {
    debugger;
      $('div[name="canadalator"]').html("");
      const _super = this._super.bind(this);
//      const radio = $(ev.currentTarget).find('input[type="radio"]');
      const radio = ev.currentTarget.closest('.o_delivery_carrier_select').querySelector(
            'input[type="radio"]'
        );
        this._disablePayButton();
//        this._showLoading(radio);
//      radio.prop("checked", true);
      radio.checked = true

      const carrier_id = parseInt(radio.value);

      await this.keepLast.add(
        this.rpc("/carrier/detail",
          {
            carrier_id: parseInt(radio.value),
          },
       )
      ).then((data) => {
        if (data.delivery_type === "purolator") {
          this.keepLast.add(
            this.rpc("/shop/get_delivery_rate/purolator",
              {
                carrier_id: carrier_id,
              },
            )
          ).then((data) => {
              console.log("Hello purolator");
              if (data.status === false) {
                const errorData = { ...data };
                errorData.error_message = "Error";
                this._handleCarrierUpdateResult(errorData);
                this.displayNotification({
                  message: data.error_message,
                  type: "danger",
                  sticky: true,
                });
                throw new Error(errorData.error_message);
                // return;
              }
              const canadalator = $("#purolator");
              this.keepLast.add(
                this.rpc("/carrier/detail/purolator",{
                    carrier_id: parseInt(radio.value),
                  },
                )
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
                  }" data-carrier-id="${radio.value}" id="btnCanadalatorCreateShipment">
                    Ship <i class="fa fa-chevron-right"></i>
                  </button>
                `);
                  button.on(
                    "click",
                    {
                      carrier_id: parseInt(radio.value),
                      amount_delivery: psr.total_price,
                      service_id: psr.value,
                    },
                    (event) => {
//                      console.log(radio, this._showLoading);
                      console.log(event.data);
//                      this._showLoading(radio);
                      this.keepLast.add(
                        this.rpc("/shop/update_carrier/purolator",
                           {
                            carrier_id: event.data.carrier_id,
                            amount_delivery: event.data.amount_delivery,
                            service_id: event.data.service_id,
                          },
                        )
                      )
                        .then((carrier_data) => {
                          console.log(carrier_data);
                          if (!carrier_data.status) {
                          }
                          return this._handleCarrierUpdateResult(radio);
                        })
                        .catch((error) => {
                          console.log(error);
                        });
//                      radio.siblings(".o_wsale_delivery_badge_price").empty();
//                      radio
//                        .siblings(".o_wsale_delivery_badge_price")
//                        .append("Select to compute delivery rate");
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
//                radio.siblings(".o_wsale_delivery_badge_price").empty();
//                radio
//                  .siblings(".o_wsale_delivery_badge_price")
//                  .append("Select to compute delivery rate");
              });
            })
            .catch((error) => {
              console.log(error);
            });
        } else if (data.delivery_type === "canadapost") {
          this.keepLast.add(
            this.rpc("/shop/carrier_rate_shipment/canadapost",
             {
                carrier_id: carrier_id,
              },
            )
          ).then((resdata) => {
            if (resdata.status === false) {
              const errorData = { ...resdata };
              errorData.error_message = "Error";

              this._handleCarrierUpdateResult(errorData);

              this.displayNotification({
                message: resdata.error_message,
                type: "danger",
                sticky: true,
              });
              throw resdata.error_message;
              // return;
            }
            console.log("Hello canadapost");
            if (data.status === false) {
              console.log(data);
//              Dialog.alert(this, { $content: data.error_message });
              this._handleCarrierUpdateResult(data);
            }
            const canadalator = $("#canadapost");
            this.keepLast.add(
              this.rpc("/carrier/detail/canadapost",
                {
                  carrier_id: parseInt(radio.value),
                },
              )
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
                }" data-carrier-id="${radio.value}" id="btnCanadalatorCreateShipment">
                    Ship <i class="fa fa-chevron-right"></i>
                  </button>
                `);
                button.on(
                  "click",
                  {
                    carrier_id: parseInt(radio.value),
                    amount_delivery: cpsr.total_price,
                    service_name: data.delivery_type,
                    service_code: cpsr.service_code,
                    service_id: cpsr.service_id,
                  },
                  (event) => {
                    console.log(event.data);
                    this.keepLast.add(
                      this.rpc( "/shop/update_carrier/canadapost",
                         {
                          carrier_id: event.data.carrier_id,
                          amount_delivery: event.data.amount_delivery,
                          service_code: event.data.service_code,
                          service_id: cpsr.service_id,
                        },
                      )
                    ).then((carrier_data) => {
                          console.log(carrier_data);
                          if (!carrier_data.status) {
                          }
                          return this._handleCarrierUpdateResult(radio);
                        })
                        .catch((error) => {
                          console.log(error);
                        });
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
//              radio.siblings(".o_wsale_delivery_badge_price").empty();
//              radio
//                .siblings(".o_wsale_delivery_badge_price")
//                .append("Select to compute delivery rate");
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
