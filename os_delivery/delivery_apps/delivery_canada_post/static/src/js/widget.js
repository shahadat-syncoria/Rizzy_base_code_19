odoo.define('delivery_canada_post.checkout', function (require) {
    'use strict';
    
    var core = require('web.core');
    var publicWidget = require('web.public.widget');    
    var _t = core._t;
    var concurrency = require('web.concurrency');
    var dp = new concurrency.DropPrevious();

    publicWidget.registry.websiteSaleDelivery = publicWidget.Widget.extend({
        selector: '.oe_website_sale',
        events: {
            'change select[name="shipping_id"]': '_onSetAddress',
            'click #delivery_carrier .o_delivery_carrier_select': '_onCarrierClick',
            'change #services_id': '_onServiceClick',
            'click .showHideLink': '_onshowHideLink',
            'click .button': '_onButtonClick',
        },
    
        /**
         * @override
         */
        start: function () {
            var self = this;
            var $carriers = $('#delivery_carrier input[name="delivery_type"]');
            var $payButton = $('#o_payment_form_pay');

            if ($carriers.length > 0) {
                if ($carriers.filter(':checked').length === 0) {
                    $payButton.prop('disabled', true);
                    var disabledReasons = $payButton.data('disabled_reasons') || {};
                    disabledReasons.carrier_selection = true;
                    $payButton.data('disabled_reasons', disabledReasons);
                }
                $carriers.filter(':checked').click();
            }
    
            _.each($carriers, function (carrierInput, k) {
                self._showLoading($(carrierInput));
                self._rpc({
                    route: '/shop/carrier_rate_shipment',
                    params: {
                        'carrier_id': carrierInput.value,
                    },
                }).then(self._handleCarrierUpdateResultBadge.bind(self));
            });
            var services_id = document.getElementById('services_id');
            var services_name = document.getElementById('services_name');
            var cnpost_table = document.getElementById('cnpost_table');
            if(services_id != null){
                if(services_id.innerHTML == ""){
                    services_id.style.display = "none";
                    services_name.style.display = "none";
                    cnpost_table.style.display = "none";
                }
                else{
                    cnpost_table.style.display = "cnpost_table";
                }
            }

            function toggle(className, displayState){
                var elements = document.getElementsByClassName(className)
                for (var i = 0; i < elements.length; i++){
                    elements[i].style.display = displayState;
                }
            }
            var showhideink = document.getElementById('showHideLink');
            if (showhideink) {
                showhideink.src = '/delivery_canada_post/static/src/images/ln-plus.png.png'
            }
            return this._super.apply(this, arguments);
        },
    
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
    
        /**
         * @private
         * @param {jQuery} $carrierInput
         */
        _showLoading: function ($carrierInput) {
            $carrierInput.siblings('.o_wsale_delivery_badge_price').html('<span class="fa fa-spinner fa-spin"/>');
        },
        /**
         * @private
         * @param {Object} result
         */
        _handleCarrierUpdateResult: function (result) {
            this._handleCarrierUpdateResultBadge(result);
            var $payButton = $('#o_payment_form_pay');
            var $amountDelivery = $('#order_delivery .monetary_field');
            var $amountUntaxed = $('#order_total_untaxed .monetary_field');
            var $amountTax = $('#order_total_taxes .monetary_field');
            var $amountTotal = $('#order_total .monetary_field');
            var services_id = document.getElementById('services_id');
            var services_name = document.getElementById('services_name');
            var cnpost_table = document.getElementById('cnpost_table');

            if(services_id.value == ""){
                services_name.style.display = "none";
                services_id.style.display = "none";
            }
            console.log(result);
            if (result.status === true) {
                $amountDelivery.html(result.new_amount_delivery);
                $amountUntaxed.html(result.new_amount_untaxed);
                $amountTax.html(result.new_amount_tax);
                $amountTotal.html(result.new_amount_total);

                var disabledReasons = $payButton.data('disabled_reasons') || {};
                disabledReasons.carrier_selection = false;
                $payButton.data('disabled_reasons', disabledReasons);
                $payButton.prop('disabled', _.contains($payButton.data('disabled_reasons'), true));

                // $payButton.data('disabled_reasons').carrier_selection = false;
                // $payButton.prop('disabled', _.contains($payButton.data('disabled_reasons'), true));


                var length = services_id.options.length;
                for (var i = length-1; i >= 0; i--) {
                    services_id.options[i] = null;
                }    
                var rates = result.cnpost_service_rates;
                var cnpost_service_rates  = result.cnpost_service_rates;
                // var cnpost_service_rates = rates.filter(rec => rec.service_code === 'PurolatorExpress' || rec.service_code === 'PurolatorExpressU.S.' 
                //         || rec.service_code === 'PurolatorExpressInternational' 
                //         || rec.service_code === 'PurolatorGround');

                var minRate = 0, services_id_value =false;
                var rate_array = [];
                cnpost_service_rates.forEach(function(rec, index){
                    rate_array.push(rec.total_price);
                    var opt = document.createElement('option');
                    opt.appendChild(document.createTextNode(rec.name));
                    opt.value = rec.value; 
                    services_id.appendChild(opt); 
                });  
                if (rate_array.length > 0) {
                    minRate = Math.min.apply(null,rate_array);
                    cnpost_service_rates.forEach(function(rec, index){
                        if (minRate === rec.total_price) {
                            services_id_value = rec.value;
                        }
                    });  
                }
                if(cnpost_service_rates.length > 0){
                    services_name.style.display = "block";
                    cnpost_table.style.display = "block";
                    table_load.style.display = "none";
                }
                if (services_id_value != false) {
                    services_id.value=services_id_value;                    
                }
                if(services_id.value== ""){
                    services_id.style.display = "none";
                    services_name.style.display = "none";
                    cnpost_table.style.display = "none";
                }
                else{
                    services_name.style.display = "block";
                    cnpost_table.style.display = "block";
                    table_load.style.display = "none";
                }
                function popoulate_table(datas) {
                    var tableRef = document.getElementById('cn_estimate_table').getElementsByTagName('tbody')[0];
                    for (let index = tableRef.childElementCount-1; index > 0; index--) {
                        tableRef.deleteRow(index);                        
                    }
                    console.log(datas);
                    console.log("----------------------")
                    datas.forEach(function(rec, index){
                        // rec.service_code = rec.service_code.replace(/([a-z])([A-Z])/g, '$1 $2');
                        // rec.service_code = rec.service_code.replace(/([a-z])([0-9])/g, '$1 $2');
                        var data_arr = rec.service_code.split(" ")
                        var expected_time = rec.expected_delivery_date;
                        var expected_time = "";
                        // if ((rec.service_code.slice(Math.max(rec.service_code.length - 2, 0)) == "PM") || (rec.service_code.slice(Math.max(rec.service_code.length - 2, 0)) == "AM")){
                        //     var expected_time = data_arr[data_arr.length -1].replace(/([0-9])([A-Z])/g, '$1 $2');
                        // }else{
                        //     var expected_time = ""
                        // }
                        // rec.service_code = rec.service_code.replace(/([0-9])([A-Z])/g, '$1 $2');
                        // if (rec.service_code.includes('Express')){
                        //     var guaranteed = `Guaranteed<sup>✝</sup>`
                        // }
                        // else{var guaranteed = "       "
                        // }
                        var newRow = tableRef.insertRow(tableRef.rows.length);
                        var myHtmlContent =   `                               
                       <tr style="border-bottom:1pt solid black;" class="border_bottom">
                            <td align="left" valign="top" style="height:20px;">
                                <span id="lblArrivalDate"
                                    class="StaticText">${rec.expected_delivery_date}<br>${expected_time}</br></span>
                            </td>
                            <td align="left" valign="top" style="white-space:nowrap;">
                                <span id="lblService"
                                    class="StaticText">${rec.service_name}</span>
                            </td>
                            <td align="center" style="width:350px;white-space:nowrap;">
                                <div class="iw_component">
                                    <div class="rate-details" id="rate-details" style="overflow: hidden; padding-left: 2.3em;display:none;" groupname="TotalCostCollapseGroup">
                                        <table border="0" cellspacing="0" cellpadding="0">
                                            <tbody>
                                                <tr>
                                                    <td style="border-bottom: solid 1px white; width: 75px; white-space: nowrap;"
                                                        align="left" valign="middle">
                                                        <span id="BaseCost"
                                                            class="StaticText">Base Cost</span>
                                                    </td>
                                                    <td style="border-bottom: solid 1px white; width: 50px; white-space: nowrap;"
                                                        align="right" valign="top">
                                                        <span
                                                            id="lblBaseCostValue"
                                                            class="StaticText">$${rec.base_price.toFixed(2)}</span>
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td style="border-bottom: solid 1px white; width: 75px; white-space: nowrap;"
                                                        align="left" valign="middle">
                                                        <span
                                                            id="lblCostName"
                                                            class="StaticText">Fuel Surcharge</span>
                                                    </td>
                                                    <td style="border-bottom: solid 1px white; width: 50px; white-space: nowrap;"
                                                        align="right" valign="middle">
                                                        <span
                                                            id="lblCostValue"
                                                            class="StaticText">$${rec.surcharges.toFixed(2)}</span>
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td style="border-bottom: solid 1px white; width: 75px; white-space: nowrap;"
                                                        align="left" valign="middle">
                                                        <span
                                                            id="lblCostName"
                                                            class="StaticText">GST/HST</span>
                                                    </td>
                                                    <td style="border-bottom: solid 1px white; width: 50px; white-space: nowrap;"
                                                        align="right" valign="middle">
                                                        <span
                                                            id="lblCostValue"
                                                            class="StaticText">$${rec.taxes.toFixed(2)}</span>
                                                    </td>
        
                                                </tr>
                                                <tr>
                                                    <td style="border-bottom: solid 1px white; width: 75px; white-space: nowrap;"
                                                        align="left" valign="middle">
                                                    </td>
                                                    <td valign="top" style="border-bottom: solid 1px white; width: 50px;">
                                                    </td>
                                                    <td style="border-bottom: solid 1px white; white-space: nowrap"
                                                        valign="middle" align="right" rowspan="99">
                                                           
                                                            <input type="submit"
                                                            name="btnCreateShipment"
                                                            value="Ship"
                                                            id="btnCreateShipment"
                                                            class="button button-primary" title="Ship"/>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                                <div class="iw_component">
                                    <div id="lTotalCost">
                                        <table style="width: 200px;" border="0" cellspacing="0" cellpadding="0">
                                            <tbody>
                                                <tr>
                                                    <td style="border-bottom: solid 1px white; min-width:75px;  width:75px; white-space: nowrap;"
                                                        align="right" valign="bottom">
                                                    </td>
                                                    <td style="border-bottom: solid 1px white; width: 50px; white-space: nowrap; vertical-align: bottom;"
                                                        align="right" valign="bottom">
                                                        <span
                                                            id="txtGrandTotal1"
                                                            class="StaticText">${rec.total_price.toFixed(2)}</span>
                                                    </td>
                                                    <td style="border-bottom: solid 1px white; width: 75px; white-space: nowrap;"
                                                        align="right" valign="bottom">
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </td>
                            <td style="display:none" class="service_code_name" id="service_code_name">
                                    ${rec.value}
                            </td>
                            <td align="left" style="width:20px;white-space:nowrap;">
                                <div id="showHideLink-div" style="padding-top:0.5em">
                                    <a id="showHideLink" class="showHideLink" >
                                        <img src="/delivery_canada_post/static/src/images/ln-plus.png" tooltip="Expand" alt="Expand"/>
                                    </a>
                                </div>
                            </td>
                        </tr>
                        `
                        newRow.innerHTML = myHtmlContent;
                    });   
                }
                popoulate_table(cnpost_service_rates);
                var tableRef = document.getElementById('cn_estimate_table').getElementsByTagName('tbody')[0];
                for(var index=1;index<tableRef.childElementCount;index++){
                    if(tableRef.children[index].children[2].innerText.replace(/\s/g, '') == minRate){
                        tableRef.children[index].children[4].children[0].children[0].click()
                    }
                  }
                if (cnpost_service_rates.length > 0) {
                    cnpost_table.style.display = "block";
                }
            } else {
                $amountDelivery.html(result.new_amount_delivery);
                $amountUntaxed.html(result.new_amount_untaxed);
                $amountTax.html(result.new_amount_tax);
                $amountTotal.html(result.new_amount_total);
            }
        },

        /**
         * @private
         * @param {Object} result
         */
        _handleCarrierUpdateResultBadge: function (result) {
            var $carrierBadge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .o_wsale_delivery_badge_price');
            if (result.status === true) {
                 if (result.is_free_delivery) {
                     $carrierBadge.text(_t('Free'));
                 } else {
                     $carrierBadge.html(result.new_amount_delivery);
                 }
                 $carrierBadge.removeClass('o_wsale_delivery_carrier_error');
            } else {
                $carrierBadge.addClass('o_wsale_delivery_carrier_error');
                $carrierBadge.text(result.error_message);
            }
        },

        /**
         * @private
         * @param {Object} result
         */
        _handleCarrierUpdateResultBadgeExtend: function (result) {  
            var $carriers = $('#delivery_carrier input[name="delivery_type"]');         
            if ($carriers.length > 0) {
                var carrier = $carriers.filter(':checked');
                if(carrier.length == 1){
                    var $carrierBadge = $('#delivery_carrier input[name="delivery_type"][value=' + carrier[0].value + '] ~ .o_wsale_delivery_badge_price');
                    $carrierBadge.html(result.new_amount_delivery);
                    var $amountUntaxed = $('#order_total_untaxed .monetary_field');
                    var $amountTax = $('#order_total_taxes .monetary_field');
                    var $amountTotal = $('#order_total .monetary_field');
                    var $amountDelivery = $('#order_delivery .monetary_field');
                    if (result.status === true) {
                        $amountDelivery.html(result.new_amount_delivery);
                        $amountUntaxed.html(result.new_amount_untaxed);
                        $amountTax.html(result.new_amount_tax);
                        $amountTotal.html(result.new_amount_total); 
                    }
                }                       
            } 
        },
        
        // --------------------------------------------------------------------------
        // Handlers
        // --------------------------------------------------------------------------
        /**
         * @private
         * @param {Event} ev
         */
        _onServiceClick: function (ev) {    
            var self = this;
            var selectElement = ev.target;
            var service_code = selectElement.value;
            
            var $carriers = $('#delivery_carrier input[name="delivery_type"]');
            var carrier_id = $carriers.filter(':checked')[0].value
            console.log(service_code)
            console.log(carrier_id)
            self._rpc({
                route: '/shop/update_carrier_service',
                params: {
                    'service_code': service_code,
                    'carrier_id': carrier_id,
                },
            }).then(self._handleCarrierUpdateResultBadgeExtend.bind(self));
        },
    
        /**
         * @private
         * @param {Event} ev
         */
        _onCarrierClick: function (ev) {
            var $radio = $(ev.currentTarget).find('input[type="radio"]');
            this._showLoading($radio);
            $radio.prop("checked", true);
            var $payButton = $('#o_payment_form_pay');
            $payButton.prop('disabled', true);
            var disabledReasons = $payButton.data('disabled_reasons') || {};
            // $payButton.data('disabled_reasons', $payButton.data('disabled_reasons') || {});
            // $payButton.data('disabled_reasons').carrier_selection = true;
            disabledReasons.carrier_selection = true;
            $payButton.data('disabled_reasons', disabledReasons);
            
            dp.add(this._rpc({
                route: '/shop/update_carrier',
                params: {
                    carrier_id: $radio.val(),
                },
            })).then(this._handleCarrierUpdateResult.bind(this));
        },
        /**
         * @private
         * @param {Event} ev
         */
        _onSetAddress: function (ev) {
            var value = $(ev.currentTarget).val();
            var $providerFree = $('select[name="country_id"]:not(.o_provider_restricted), select[name="state_id"]:not(.o_provider_restricted)');
            var $providerRestricted = $('select[name="country_id"].o_provider_restricted, select[name="state_id"].o_provider_restricted');
            if (value === 0) {
                $providerFree.hide().attr('disabled', true);
                $providerRestricted.show().attr('disabled', false).change();
            } else {
                $providerFree.show().attr('disabled', false).change();
                $providerRestricted.hide().attr('disabled', true);
            }
        },

       /**
         * @private
         * @param {Event} ev
         */
        _onshowHideLink: function (ev) {    
            var src = ev.currentTarget.firstElementChild.src.split("/");
            if (src[src.length - 1] == 'ln-plus.png'){
                ev.currentTarget.firstElementChild.src = '/delivery_canada_post/static/src/images/ln-minus.png';
                ev.currentTarget.parentElement.parentElement.parentElement.children[2].children[0].firstElementChild.style.display = 'block';
            }
            else if  (src[src.length - 1] == 'ln-minus.png'){
                ev.currentTarget.firstElementChild.src = '/delivery_canada_post/static/src/images/ln-plus.png';
                ev.currentTarget.parentElement.parentElement.parentElement.children[2].children[0].firstElementChild.style.display = 'none';
            }
        },


           /**
         * @private
         * @param {Event} ev
         */
        _onButtonClick: function (ev) {
            var self = this;    
            var row =  ev.target.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement;
            var service_code = row.cells[3].innerText.replace(/[^0-9]/g,'');
            var $carriers = $('#delivery_carrier input[name="delivery_type"]');
            var carrier_id = $carriers.filter(':checked')[0].value
            self._rpc({
                route: '/shop/update_carrier_service',
                params: {
                    'service_code': service_code,
                    'carrier_id': carrier_id,
                },
            }).then(self._handleCarrierUpdateResultBadgeExtend.bind(self));
        },
    });

});
    

