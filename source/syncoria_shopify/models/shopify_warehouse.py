from odoo import api, fields, models
from odoo.exceptions import UserError,ValidationError


class ShopifyWarehouse(models.Model):
    _name = 'shopify.warehouse'
    _description = 'Shopify Warehouse'
    _rec_name = 'shopify_loc_name'

    shopify_invent_id = fields.Char("Inventory Id", )
    shopify_loc_name = fields.Char('Location Name')
    marketplace_type = fields.Selection(selection=[('shopify', 'Shopify')], default='shopify')
    shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID")
    shopify_loc_add_one = fields.Char(string="Location Address1", )
    shopify_loc_add_two = fields.Char(string="Location Address2", )
    shopify_loc_city = fields.Char(string="Location City", )
    shopify_loc_zip = fields.Char(string="Location Zip", )
    shopify_loc_province = fields.Char(string="Location Province", )
    shopify_loc_country = fields.Char(string="Location Country", )
    shopify_loc_phone = fields.Char(string="Location Phone Number", )
    shopify_loc_created_at = fields.Char(string="Location Created", )
    shopify_loc_updated_at = fields.Char(string="Location Updated", )
    shopify_loc_country_code = fields.Char(string="Location Country Code", )
    shopify_loc_country_name = fields.Char(string="Location Country Name", )
    shopify_loc_country_province_code = fields.Char(string="Location Province Code", )
    shopify_loc_legacy = fields.Boolean(string="Location Leagacy", help="Can this location fulfil order?")
    shopify_loc_active = fields.Boolean(string="Active", )
    shopify_loc_localized_country_name = fields.Char(string="Localized Country Name", )
    shopify_loc_localized_province_name = fields.Char(string="Localized Province Name", )
    partner_id = fields.Many2one('res.partner',readonly=True,store=True)


    def _shopify_create_partner(self,record):
        res_partners = self.env['res.partner']
        res_country = self.env['res.country']
        country_id = res_country.search([("name", "=", record.shopify_loc_country_name)], limit=1)
        country_state_id = country_id.state_ids.search([("name", "=", record.shopify_loc_province)], limit=1)
        exists_partner = res_partners.search([("shopify_warehouse_id", "=", record.shopify_invent_id)], limit=1)

        if not exists_partner:
            res_vals = {
                'company_type': 'company',
                'name': record.shopify_loc_name,
                'street': record.shopify_loc_add_one,
                'street2': record.shopify_loc_add_two,
                'city': record.shopify_loc_city,
                'state_id': country_state_id.id,
                'zip': record.shopify_loc_zip,
                'country_id': country_id.id,
                'phone': record.shopify_loc_phone,
                'marketplace_type': 'shopify',
                'shopify_warehouse_id': record.shopify_invent_id,
                'shopify_warehouse_active': record.shopify_loc_active

            }
            partner = res_partners.create(res_vals)
        else:
            res_vals = {
                'name': record.shopify_loc_name,
                'street': record.shopify_loc_add_one,
                'street2': record.shopify_loc_add_two,
                'phone': record.shopify_loc_phone,
                'shopify_warehouse_id': record.shopify_invent_id,
                'shopify_warehouse_active': record.shopify_loc_active
            }
            exists_partner.update(res_vals)
            partner = exists_partner

        return partner

    def create_update_warehouse_to_odoo(self):
        try:
            for record in self:
                partner_id = self._shopify_create_partner(record)
                record.partner_id = partner_id.id
        except Exception as e:
            raise ValidationError("%s" % e)
