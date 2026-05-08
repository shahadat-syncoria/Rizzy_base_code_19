import base64
import json
import logging

import requests

from odoo import fields, models, SUPERUSER_ID

_logger = logging.getLogger(__name__)


class ShopifyProductMappings(models.Model):
    _name = 'shopify.product.mappings'

    name = fields.Char('Name')
    shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID", required=True, )
    product_id = fields.Many2one("product.product", string="Product", )
    product_tmpl_id = fields.Many2one("product.template", string="Product Template", related='product_id.product_tmpl_id',)
    shopify_id = fields.Char(string="Shopify Variant Id", copy=False, required=True, )
    shopify_parent_id = fields.Char(string="Shopify Product Id", copy=False, )
    shopify_inventory_id = fields.Char(string="Shopify Inventory Id", copy=False, required=True, )
    default_code = fields.Char(string="SKU", related='product_id.default_code', store=True)

    _sql_constraints = [
        (
            'unique_shopifyinstance_byshopifyid',
            'UNIQUE(shopify_instance_id, shopify_id)',
            'Only one instance exist only one shopify id.',
        )
    ]

    def fetch_images_from_shopify(self):
        for shopify_mapping_id in self:
            _logger.info("Fetching images for shopify mapping: {}".format(shopify_mapping_id.product_tmpl_id.display_name))
            if not shopify_mapping_id:
                continue
            if shopify_mapping_id.shopify_instance_id:
                marketplace_instance_id = shopify_mapping_id.shopify_instance_id
            if not marketplace_instance_id:
                raise ValueError('Can not find marketplace_instance_id for product id:' + str(shopify_mapping_id.product_id.id))
            if getattr(marketplace_instance_id, "use_graphql", False):
                query = """
                query SyncoriaProductMedia($id: ID!) {
                  product(id: $id) {
                    media(first: 50) {
                      nodes {
                        __typename
                        ... on MediaImage {
                          image { url }
                        }
                      }
                    }
                  }
                }
                """
                res, _next = self.env['marketplace.connector'].shopify_graphql_call(
                    headers={'X-Service-Key': marketplace_instance_id.token},
                    url='/graphql.json',
                    query=query,
                    variables={"id": "gid://shopify/Product/%s" % shopify_mapping_id.shopify_parent_id},
                    type='POST',
                    marketplace_instance_id=marketplace_instance_id,
                )
                if res.get("errors"):
                    _logger.info("Shopify GraphQL media fetch errors: %s", res.get("errors"))
                    continue
                product = (res.get("data") or {}).get("product") or {}
                nodes = ((product.get("media") or {}).get("nodes") or [])
                image_urls = []
                for n in nodes:
                    img = (n.get("image") or {})
                    if img.get("url"):
                        image_urls.append(img.get("url"))
                if image_urls:
                    shopify_mapping_id.product_tmpl_id.with_user(SUPERUSER_ID).write({'product_template_image_ids': [(5, 0, 0)]})
                    # first image becomes main
                    shopify_mapping_id.product_tmpl_id.with_user(SUPERUSER_ID).write({'image_1920': self.shopify_image_processing(image_urls[0])})
                    for im in image_urls[1:]:
                        self.env['product.image'].create({
                            'name': im,
                            'image_1920': self.shopify_image_processing(im),
                            'product_tmpl_id': shopify_mapping_id.product_tmpl_id.id
                        })
                continue
            raise ValueError("GraphQL-only: enable 'Use GraphQL' on the Shopify instance.")

    def shopify_image_processing(self, image_url):
        if image_url:
            image = False
            if requests.get(image_url).status_code == 200:
                image = base64.b64encode(requests.get(image_url).content)
            return image
        else:
            return False