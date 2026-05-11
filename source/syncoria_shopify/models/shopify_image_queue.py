# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import base64
import json
import logging
import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ShopifyImageQueue(models.Model):
    _name = 'shopify.image.queue'
    _description = 'Shopify Image Queue'
    _order = 'create_date desc, id desc'

    shopify_instance_id = fields.Many2one(
        'marketplace.instance',
        string='Shopify Instance',
        required=True,
        ondelete='cascade',
    )
    # Shopify image fields
    shopify_image_id = fields.Char(string='Image ID')
    product_id = fields.Char(string='Product ID')
    position = fields.Integer(string='Position', default=1)
    src = fields.Char(string='Source URL')
    variant_ids = fields.Char(string='Variant IDs', help='JSON array of variant IDs')

    # Processing fields
    state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], string='State', default='pending', required=True, index=True)

    @api.model
    def process_image_queue_cron(self, batch_size=100, commit_after=100):
        """Cron job to process all pending images, committing after every commit_after records."""
        processed_count = 0
        total_processed = 0

        while True:
            pending_images = self.search([('state', '=', 'pending')], limit=batch_size)
            if not pending_images:
                break

            _logger.info("Processing batch of %d images", len(pending_images))

            for image in pending_images:
                try:
                    image._process_single_image()
                    processed_count += 1
                    total_processed += 1

                    if processed_count >= commit_after:
                        self.env.cr.commit()
                        _logger.info("Committed %d images, total processed: %d", processed_count, total_processed)
                        processed_count = 0

                except Exception as e:
                    _logger.error("Error processing image queue %s: %s", image.id, str(e))
                    image.write({'state': 'failed'})

        # Final commit for remaining records
        if processed_count > 0:
            self.env.cr.commit()
            _logger.info("Final commit: %d images, total processed: %d", processed_count, total_processed)

        _logger.info("Image queue processing complete. Total: %d", total_processed)

    def _process_single_image(self):
        """Process a single image queue record."""
        self.ensure_one()

        # Find product mapping
        mapping = self.env['shopify.product.mappings'].search([
            ('shopify_parent_id', '=', self.product_id),
            ('shopify_instance_id', '=', self.shopify_instance_id.id)
        ], limit=1)

        if not mapping or not mapping.product_tmpl_id:
            _logger.warning("No product mapping found for Shopify product %s", self.product_id)
            self.write({'state': 'failed'})
            return

        product_tmpl = mapping.product_tmpl_id

        # Download image
        image_data = self._download_image(self.src)
        if not image_data:
            self.write({'state': 'failed'})
            return

        # Set main image or create extra image
        if self.position == 1:
            product_tmpl.write({'image_1920': image_data})
        else:
            self.env['product.image'].create({
                'name': self.src,
                'image_1920': image_data,
                'product_tmpl_id': product_tmpl.id
            })

        # Set variant images
        if self.variant_ids:
            variant_id_list = json.loads(self.variant_ids)
            for variant_id in variant_id_list:
                variant_mapping = self.env['shopify.product.mappings'].search([
                    ('shopify_id', '=', str(variant_id)),
                    ('shopify_instance_id', '=', self.shopify_instance_id.id)
                ], limit=1)
                if variant_mapping and variant_mapping.product_id:
                    variant_mapping.product_id.write({'image_1920': image_data})

        self.write({'state': 'done'})

    def _download_image(self, image_url):
        """Download image from URL and return base64 encoded data."""
        if not image_url:
            return False
        try:
            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                return base64.b64encode(response.content)
            _logger.warning("Failed to download image: HTTP %s", response.status_code)
            return False
        except Exception as e:
            _logger.warning("Exception downloading image: %s", str(e))
            return False
