odoo.define('odoo_moneris_cloud.pos_models.extend', function (require) {
   "use strict";
    var {PosGlobalState} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const MonerisPosGlobalState = (PosGlobalState) => class MonerisPosGlobalState extends PosGlobalState {
        async _processData(loadedData) {

            await super._processData(...arguments);

            this.moneris_pos_orders = loadedData['pos.order'];

        }
    }
    Registries.Model.extend(PosGlobalState, MonerisPosGlobalState);
});

