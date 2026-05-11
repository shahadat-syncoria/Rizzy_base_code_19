odoo.define('odoo_clover_cloud.pos_models.extend', function (require) {
    "use strict";
    var {PosGlobalState} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const CloverPosGlobalState = (PosGlobalState) => class CloverPosGlobalState extends PosGlobalState {
        async _processData(loadedData) {

            await super._processData(...arguments);
            debugger

            this.clover_pos_orders = loadedData['pos.order'];

        }
    }
    Registries.Model.extend(PosGlobalState, CloverPosGlobalState);


});

    