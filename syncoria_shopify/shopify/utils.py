# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import pprint
import re
import json
import base64
from sys import api_version
import requests
from odoo import models, api, fields, tools, exceptions, _
from odoo import exceptions
import logging

_logger = logging.getLogger(__name__)

def to_shopify_gid(resource, numeric_id):
    if not resource or not numeric_id:
        return False
    # Some DB fields may already contain a full GID string.
    if isinstance(numeric_id, str) and numeric_id.startswith("gid://shopify/"):
        return numeric_id
    return "gid://shopify/%s/%s" % (resource, numeric_id)


def from_shopify_gid(gid):
    if not gid or '/' not in str(gid):
        return False
    return str(gid).rsplit('/', 1)[-1]


def graphql_page_info(response):
    page_info = (response or {}).get('pageInfo') or {}
    return {
        'has_next_page': bool(page_info.get('hasNextPage')),
        'end_cursor': page_info.get('endCursor'),
    }


def build_graphql_pagination_variables(limit=250, cursor=False, base_variables=None):
    variables = dict(base_variables or {})
    variables.update({'first': limit})
    if cursor:
        variables.update({'after': cursor})
    return variables


def parse_gql_nodes(payload, path=None):
    """
    Extract GraphQL items consistently from either:
    - a connection: {"edges": [{"node": {...}}]}
    - a nodes list: {"nodes": [{...}]}
    - or a plain list
    """
    data = payload
    if path:
        keys = path.split(".") if isinstance(path, str) else list(path)
        for key in keys:
            data = (data or {}).get(key)
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    if isinstance(data.get("nodes"), list):
        return data.get("nodes") or []
    if isinstance(data.get("edges"), list):
        return [((edge or {}).get("node") or {}) for edge in (data.get("edges") or []) if (edge or {}).get("node")]
    return []


def _customer_addr_from_gql(address):
    if not address:
        return {}
    return {
        "id": from_shopify_gid(address.get("id")),
        "address1": address.get("address1"),
        "address2": address.get("address2"),
        "city": address.get("city"),
        "company": address.get("company"),
        "first_name": address.get("firstName"),
        "last_name": address.get("lastName"),
        "phone": address.get("phone"),
        "province": address.get("province"),
        "country": address.get("country"),
        "zip": address.get("zip"),
        "name": address.get("name"),
        "province_code": address.get("provinceCode"),
        "country_code": address.get("countryCodeV2"),
        "country_name": address.get("country"),
        "default": bool(address.get("default")),
    }


def _address_input_from_rest(data):
    address = (data or {}).get("address") or {}
    return {
        "address1": address.get("address1"),
        "address2": address.get("address2"),
        "city": address.get("city"),
        "company": address.get("company"),
        "firstName": address.get("first_name"),
        "lastName": address.get("last_name"),
        "phone": address.get("phone"),
        "province": address.get("province"),
        "country": address.get("country"),
        "zip": address.get("zip"),
    }


def _normalize_customer_node(node):
    customer_id = from_shopify_gid((node or {}).get("id"))
    addresses = [_customer_addr_from_gql(a) for a in parse_gql_nodes(node or {}, ("addresses",))]
    default_address = _customer_addr_from_gql((node or {}).get("defaultAddress"))
    if default_address and not default_address.get("id"):
        default_address["id"] = next((a.get("id") for a in addresses if a.get("default")), None)
    return {
        "id": customer_id,
        "first_name": (node or {}).get("firstName"),
        "last_name": (node or {}).get("lastName"),
        "email": (node or {}).get("email"),
        "phone": (node or {}).get("phone"),
        "state": ((node or {}).get("state") or "").lower() or None,
        "note": (node or {}).get("note"),
        "orders_count": (node or {}).get("numberOfOrders"),
        "verified_email": (node or {}).get("verifiedEmail"),
        "tax_exempt": (node or {}).get("taxExempt"),
        "tags": ",".join((node or {}).get("tags") or []),
        "default_address": default_address if default_address else None,
        "addresses": addresses,
    }


def _gql_product_status(status):
    """Map our Odoo product status to Shopify GraphQL ProductStatus enum."""
    if not status:
        return "ACTIVE"
    status = str(status).lower()
    return {
        "draft": "DRAFT",
        "active": "ACTIVE",
        "archived": "ARCHIVED",
    }.get(status, "ACTIVE")


def _tags_to_list(tags):
    """Convert Odoo tags string -> Shopify GraphQL tags list."""
    if not tags:
        return []
    if isinstance(tags, list):
        return [t for t in tags if t]
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    return []


def _variant_option_values(variant, product_options):
    """
    Convert REST-like variant option1/option2/option3 into GraphQL optionValues.

    product_options is a list of dicts like: {"name": "...", "values": [...]}.
    """
    if not product_options:
        return []
    option_values = []
    for idx in range(min(3, len(product_options))):
        opt_def = product_options[idx] or {}
        opt_name = opt_def.get("name")
        val = variant.get(f"option{idx+1}")
        if opt_name and val is not None and val != "":
            option_values.append({"optionName": opt_name, "name": val})
    return option_values


def _inventory_item_input_from_variant(variant):
    # We rely on Shopify's defaults for most inventory fields; only tracked and requiresShipping matter for shipping behavior.
    tracked = str(variant.get("inventory_management") or "").lower() == "shopify"
    requires_shipping = bool(variant.get("requires_shipping")) if "requires_shipping" in variant else None
    inventory_item = {"tracked": tracked}
    if requires_shipping is not None:
        inventory_item["requiresShipping"] = requires_shipping
    if variant.get("sku"):
        inventory_item["sku"] = variant.get("sku")
    return inventory_item


def _gql_inventory_policy(policy):
    if not policy:
        return "DENY"
    policy = str(policy).upper()
    # REST values often come as "deny"/"continue"
    return {"DENY": "DENY", "CONTINUE": "CONTINUE"}.get(policy, "DENY")


def _money_to_gql(value):
    """
    Shopify GraphQL expects money fields (price/compareAtPrice) as strings.
    Accept floats/ints/strings and normalize to a string without scientific notation.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        # Keep up to 2 decimals (Shopify money), strip trailing zeros for readability
        return ("%.2f" % float(value)).rstrip("0").rstrip(".")
    return str(value)


def _rest_variant_to_gql_bulk_input(variant, product_options, for_update=False):
    """
    Build ProductVariantsBulkInput payload (create/update) from our internal REST-like variant shape.
    """
    option_values = _variant_option_values(variant, product_options)
    payload = {
        "optionValues": option_values,
        "price": _money_to_gql(variant.get("price")),
        "compareAtPrice": _money_to_gql(variant.get("compare_at_price") or variant.get("compareAtPrice")),
        "barcode": variant.get("barcode"),
        "taxable": variant.get("taxable"),
        "inventoryPolicy": _gql_inventory_policy(variant.get("inventory_policy")),
        "inventoryItem": _inventory_item_input_from_variant(variant),
    }
    # For create, id must not be sent. For update, id is required.
    if for_update and variant.get("id"):
        payload["id"] = to_shopify_gid("ProductVariant", variant.get("id"))

    # prune nulls to keep Shopify validation errors readable
    return {k: v for k, v in payload.items() if v is not None and v != ""}


def get_provar_vals(record, values):
    data = {}
    product = {
        'id': record.shopify_id,
        # 'product_id': 6929081696441,
        'title': record.name,
        'price': record.list_price,
        'sku': record.default_code,
        # 'position': 1,
        # 'inventory_policy': 'deny',
        'compare_at_price': record.shopify_compare_price,
        # 'fulfillment_service': 'manual',
        # 'inventory_management': None,
        # 'option1': 'Default Title',
        # 'option2': None,
        # 'option3': None,
        'taxable': record.shopify_charge_tax,
        'status': record.shopify_product_status,
        'barcode': record.barcode,
        # 'grams': 0,
        # 'image_id': None,
        'weight': record.weight,
        'weight_unit': record.uom_id.name,
        # 'inventory_item_id': 42940912238777,
        'inventory_quantity': record.qty_available,
        # 'old_inventory_quantity': 0,
        'requires_shipping': True if record.type == 'product' else False
    }
    if record.qty_available:
        product['inventory_quantity'] = int(record.qty_available)

    product = {k: v for k, v in product.items() if v}
    data["product"] = product
    return data


def get_protmpl_vals(record, action, mapping, instance, images=False):
    data = {}
    product = {}

    if 'product.template' in str(record):
        product.update({
            "title": record.name,
            "body_html": record.description_sale or '',
            "vendor": record.shopify_vendor or "",
            "product_type": record.categ_id.name or "",
            "status": record.shopify_product_status,
            "tags": record.shopify_tags or '',
        })
        if action == 'update':
            product.update({'id': mapping.shopify_parent_id})
        variants = []
        variants_rec = record.product_variant_ids
        instance_id = instance
        if instance_id.compute_pricelist_price:
            record.compute_shopify_price(instance_id)
        for var in variants_rec:
            variant_mapping = record.env['shopify.product.mappings'].search([('product_id', '=', var.id),('shopify_instance_id', '=', instance.id)], limit=1)
            exclude_variant = False
            for attrib in var.product_template_attribute_value_ids:
                if attrib.product_attribute_value_id in record.attribute_line_ids.shopify_value_ids:
                    _logger.info("EXCLUDE VARIANT")
                    _logger.info(attrib.product_attribute_value_id.display_name)
                    exclude_variant = True or exclude_variant
            if exclude_variant:
                continue
            variant = {}
            price_list_price = var.get_shopify_price(instance_id)
            shopify_price = False
            if not price_list_price:
                record.message_post(
                    body=f"Product Price won't be updated because no price found in pricelist {instance_id.pricelist_id.name}")
            else:
                variant["price"] = price_list_price
            # var.compute_shopify_price(instance_id)
                shopify_price = price_list_price
            count = 1
            _logger.info("Variant Name ===>>>{}".format(var.name))
            # _logger.info("Variant Price ===>>>{}".format(shopify_price))

            if var.product_template_attribute_value_ids:
                for attrib in var.product_template_attribute_value_ids:
                    _logger.info(attrib.attribute_id.name)
                    _logger.info(attrib.name)

                    variant["option" + str(count)] = attrib.name
                    count += 1
                    variant.update({
                        'title': var.name,
                        'sku': var.default_code or '',
                        'inventory_management': 'shopify',
                        'barcode': var.barcode or '',
                        'weight': var.weight,
                        'weight_unit': var.weight_uom_name,
                        'compare_at_price': var.product_tmpl_id.shopify_compare_price
                    })
                    if shopify_price:
                        variant['price'] = shopify_price
                    if action == 'update' and variant_mapping:
                        variant.update({'id': variant_mapping.shopify_id})
                    variant = {k: v for k, v in variant.items()}
            else:
                variant = {
                    'title': var.name,
                    'sku': var.default_code or '',
                    'barcode': var.barcode or '',
                    'weight': var.weight,
                    'weight_unit': var.weight_uom_name,
                    'inventory_management': 'shopify',
                    'compare_at_price': var.product_tmpl_id.shopify_compare_price
                }
                if shopify_price:
                    variant['price'] = shopify_price
                if action == 'update':
                    variant.update({'id': variant_mapping.shopify_id})
            if len(variant) > 0:
                variants.append(variant)

        product["variants"] = variants
        options = []
        for att_line in record.attribute_line_ids.filtered(lambda att_line: att_line.attribute_id.create_variant != 'no_variant'):
            option = {"name": att_line.attribute_id.name, "values": []}
            for value_id in att_line.value_ids:
                if value_id.id not in att_line.shopify_value_ids.ids:
                    option["values"].append(value_id.name)
            options.append(option)
        if options:
            product["options"] = options
        product['images'] = []
        """ LEGACY """
        # try:
        #     product['images'] = []
        #     if record.image_1920 and instance_id.set_image:
        #         product.update({
        #             "images": [{
        #                 "attachment": record.image_1920.decode(),
        #             }]
        #         })
        #         product_image = image_data_uri(record.image_1920)
        #     for image in record.product_template_image_ids:
        #         product['images'] += [{
        #             "attachment": image.image_1920.decode()
        #         }]
        # except Exception as e:
        #     _logger.info("Exception In Decoding Images-%s", e.args)

        # if instance_id.set_image and images:
        #     try:
        #         product['images'] = []
        #         product.update({
        #             "images": [{"src": image} for image in images]
        #         })
        #     except Exception as e:
        #         _logger.info("Exception In Decoding Images-%s", e.args)

        product = {k: v for k, v in product.items()}
        data["product"] = product
        _logger.info("\nDATA===>>>\n" + pprint.pformat(data))
    elif 'product.product' in str(record):
        mapping_tmpl = record.env['shopify.product.mappings'].search([('product_tmpl_id', '=', record.product_tmpl_id.id), ('shopify_instance_id', '=', instance.id)], limit=1)
        variant = {"product_id": mapping_tmpl.shopify_parent_id, "sku": record.default_code or '',
                   'weight': record.weight,
                   'weight_unit': record.weight_uom_name,
                   "barcode": record.barcode or ''}
        if action == 'update':
            del variant['product_id']
            variant['id'] = mapping.shopify_id
        if mapping.shopify_instance_id.compute_pricelist_price:
            record.compute_shopify_price(mapping.shopify_instance_id)
        if mapping.shopify_instance_id.set_price:
            price_list_price = record.get_shopify_price(mapping.shopify_instance_id)
            if not price_list_price:
                record.message_post(body=f"Product Price won't be updated because no price found in pricelist {mapping.shopify_instance_id.pricelist_id.name}")
            else:
                variant["price"] = price_list_price
        position = 1
        for att in record.product_template_variant_value_ids.sorted():
            value = record.env['product.attribute.value'].browse(att.product_attribute_value_id.id)
            variant['option' + str(position)] = value.name
            position += 1
        data['variant'] = variant
        _logger.info("\nDATA===>>>\n" + pprint.pformat(data))
    return data


def get_marketplace(record):
    """Resolve marketplace.instance for Shopify calls from record or system default."""
    instance = getattr(record, 'shopify_instance_id', False) or getattr(
        record, 'marketplace_instance_id', False)
    if instance:
        return instance
    tmpl = getattr(record, 'product_tmpl_id', False)
    if tmpl:
        instance = getattr(tmpl, 'shopify_instance_id', False) or getattr(
            tmpl, 'marketplace_instance_id', False)
        if instance:
            return instance
    ICPSudo = record.env['ir.config_parameter'].sudo()
    try:
        raw = ICPSudo.get_param('syncoria_base_marketplace.marketplace_instance_id') or ''
        ids_found = [int(s) for s in re.findall(r'\b\d+\b', raw)]
    except (TypeError, ValueError):
        ids_found = []
    if ids_found:
        return record.env['marketplace.instance'].sudo().search(
            [('id', '=', ids_found[0])], limit=1)
    return record.env['marketplace.instance']


# def update_product_images(record, product_data, req_type):
#     """_summary_
#
#     Args:
#         record (_type_): _description_
#         product_data (_type_): _description_
#         req_type (_type_): _description_
#     """
#     _logger.info("[START]-Upload Product Images.....")
#     import datetime
#     start_time = datetime.datetime.now()
#     time_lag = 0.5  # 0.5seconds
#     _logger.info("start_time-{}".format(start_time))
#
#     data = {}
#     attachments = [record.image_1920.decode()] if record.image_1920 else []
#     if not record.shopify_image_id:
#         req_type = 'create'
#
#     for attachment in attachments:
#         _logger.info("attachment-{}".format(attachment))
#         while True:
#             current_time = datetime.datetime.now()
#             if (current_time - start_time).seconds > time_lag:
#                 start_time = datetime.datetime.now()
#                 data = {
#                     "image":
#                         {
#                             "variant_ids": [record.shopify_id],
#                             "attachment": attachment
#                         }
#                 }
#                 marketplace_instance_id = record.shopify_instance_id or get_marketplace(record)
#                 version = marketplace_instance_id.marketplace_api_version or '2021-01'
#                 url = marketplace_instance_id.marketplace_host
#                 if req_type == 'create':
#                     type_req = 'POST'
#                     url += '/admin/api/%s/products/%s/images.json' % (
#                         version, product_data.shopify_id)
#                 if req_type == 'update':
#                     type_req = 'PUT'
#                     url += '/admin/api/%s/products/%s/images/%s.json' % (
#                         version, product_data.shopify_id, record.shopify_image_id)
#                 headers = {
#                     'X-Service-Key': marketplace_instance_id.token,
#                     'Content-Type': 'application/json'
#                 }
#                 updated_products, next_link = shopify_api_call(
#                     headers=headers,
#                     url=url,
#                     type=type_req,
#                     marketplace_instance_id=marketplace_instance_id,
#                     data=data
#                 )
#                 if "errors" not in updated_products:
#                     var = record.write({
#                         "shopify_image_id": updated_products["image"]["id"]
#                     })
#
#                 break
#
#     _logger.info("[END]-Upload Product Images.....")

def update_image_shopify(marketplace_instance_id, image, product_id, variant_id=False):
    try:
        if not getattr(marketplace_instance_id, "use_graphql", False):
            raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
        if image:
            # Upload media via stagedUploadsCreate -> upload to staged url -> productCreateMedia
            connector = product_id.env["marketplace.connector"]
            mapping = product_id.env["shopify.product.mappings"].search(
                [
                    ("product_tmpl_id", "=", product_id.id),
                    ("shopify_instance_id", "=", marketplace_instance_id.id),
                ],
                limit=1,
            )
            if not mapping or not mapping.shopify_parent_id:
                return

            product_gid = to_shopify_gid("Product", mapping.shopify_parent_id)

            # Our `image` is base64-encoded bytes; staged uploads require the raw binary.
            image_bytes = base64.b64decode(image) if isinstance(image, (bytes, str)) else image
            filename = f"shopify-product-{mapping.shopify_parent_id}.jpg"
            mime_type = "image/jpeg"

            staged_query = """
            mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
              stagedUploadsCreate(input: $input) {
                stagedTargets {
                  url
                  resourceUrl
                  parameters { name value }
                }
                userErrors { field message }
              }
            }
            """
            staged_vars = {
                "input": [
                    {
                        "filename": filename,
                        "mimeType": mime_type,
                        "httpMethod": "POST",
                        "resource": "PRODUCT_IMAGE",
                    }
                ]
            }
            staged_res, _next = connector.shopify_graphql_call(
                headers={"X-Service-Key": marketplace_instance_id.token},
                url="/graphql.json",
                query=staged_query,
                variables=staged_vars,
                type="POST",
                marketplace_instance_id=marketplace_instance_id,
            )
            if staged_res.get("errors"):
                raise exceptions.UserError(_("GraphQL stagedUploadsCreate failed: %s") % staged_res.get("errors"))

            staged_payload = (staged_res.get("data") or {}).get("stagedUploadsCreate") or {}
            staged_targets = staged_payload.get("stagedTargets") or []
            if not staged_targets:
                return
            target = staged_targets[0]

            upload_url = target.get("url")
            resource_url = target.get("resourceUrl")
            params_list = target.get("parameters") or []
            params = {p.get("name"): p.get("value") for p in params_list if p.get("name")}
            if not upload_url or not resource_url:
                return

            # Upload file to staged url using returned auth parameters.
            # Shopify's staged upload targets are typically S3 POST-form targets.
            upload_resp = requests.post(
                upload_url,
                data=params,
                files={"file": (filename, image_bytes, mime_type)},
                timeout=60,
            )
            if upload_resp.status_code >= 400:
                raise exceptions.UserError(_("Staged upload failed with HTTP %s") % upload_resp.status_code)

            product_media_query = """
            mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
              productCreateMedia(media: $media, productId: $productId) {
                media { id status alt mediaContentType }
                mediaUserErrors { field message }
              }
            }
            """
            create_media_vars = {
                "productId": product_gid,
                "media": [
                    {
                        "originalSource": resource_url,
                        "mediaContentType": "IMAGE",
                        "alt": getattr(product_id, "name", "Image"),
                    }
                ],
            }
            media_res, _next = connector.shopify_graphql_call(
                headers={"X-Service-Key": marketplace_instance_id.token},
                url="/graphql.json",
                query=product_media_query,
                variables=create_media_vars,
                type="POST",
                marketplace_instance_id=marketplace_instance_id,
            )
            if media_res.get("errors"):
                raise exceptions.UserError(_("GraphQL productCreateMedia failed: %s") % media_res.get("errors"))
            _logger.info("GraphQL media upload response: %s", media_res)
            return
    except Exception as e:
        _logger.info(e)

        # if variant_images and variant_images.get(var_id.id):
        #     data = {"image": {"src": variant_images.get(var_id.id), "variant_ids": [int(var_id.shopify_id)]}}
        #     created_images, next_link = record.env['marketplace.connector'].shopify_api_call(
        #         headers=headers,
        #         url='/products/%s/images.json' % var_id.shopify_parent_id,
        #         type='POST',
        #         marketplace_instance_id=marketplace_instance_id,
        #         data=data
        #     )
        #     _logger.info(created_images)

def shopify_pt_request(record, data, req_type, mapping, instance, attachment_ids=False, variant_images=False):
    marketplace_instance_id = instance
    use_graphql = getattr(marketplace_instance_id, "use_graphql", False)

    # ---------------------------
    # GraphQL path (Day 3)
    # ---------------------------
    if use_graphql:
        # Build a REST-like response payload so the existing mapping logic below can remain unchanged.
        if "product.template" in str(record):
            product_data = data.get("product") or {}
            product_options = product_data.get("options") or []
            variants = product_data.get("variants") or []
            product_type = product_data.get("product_type")

            if req_type == "create":
                product_create_input = {
                    "title": product_data.get("title"),
                    "descriptionHtml": product_data.get("body_html"),
                    "vendor": product_data.get("vendor"),
                    "productType": product_type,
                    "status": _gql_product_status(product_data.get("status")),
                    "tags": _tags_to_list(product_data.get("tags")),
                    "productOptions": [
                        {"name": opt.get("name"), "values": opt.get("values") or []}
                        for opt in product_options
                        if opt.get("name")
                    ],
                }
                product_create_query = """
                mutation productCreate($input: ProductInput!) {
                  productCreate(input: $input) {
                    product { id }
                    userErrors { field message }
                  }
                }
                """
                connector = record.env["marketplace.connector"]
                product_create_res, _next = connector.shopify_graphql_call(
                    headers={"X-Service-Key": marketplace_instance_id.token},
                    url="/graphql.json",
                    query=product_create_query,
                    variables={"input": product_create_input},
                    type="POST",
                    marketplace_instance_id=marketplace_instance_id,
                )
                if product_create_res.get("errors"):
                    created_products = {"errors": product_create_res.get("errors")}
                else:
                    gql_product = (product_create_res.get("data") or {}).get("productCreate") or {}
                    product_gid = (gql_product.get("product") or {}).get("id")
                    if not product_gid:
                        created_products = {"errors": _("ProductCreate returned no product id")}
                    else:
                        product_id_numeric = from_shopify_gid(product_gid)

                        variants_bulk_input = [
                            _rest_variant_to_gql_bulk_input(v, product_options, for_update=False) for v in variants
                        ]
                        variant_create_query = """
                        mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                          productVariantsBulkCreate(productId: $productId, variants: $variants) {
                            productVariants {
                              id
                              sku
                              inventoryItem { id }
                              image { id }
                              selectedOptions { name value }
                            }
                            userErrors { field message }
                          }
                        }
                        """
                        gql_variants_res, _next = connector.shopify_graphql_call(
                            headers={"X-Service-Key": marketplace_instance_id.token},
                            url="/graphql.json",
                            query=variant_create_query,
                            variables={
                                "productId": product_gid,
                                "variants": variants_bulk_input,
                            },
                            type="POST",
                            marketplace_instance_id=marketplace_instance_id,
                        )
                        if gql_variants_res.get("errors"):
                            created_products = {"errors": gql_variants_res.get("errors")}
                        else:
                            gql_variants_payload = (gql_variants_res.get("data") or {}).get("productVariantsBulkCreate") or {}
                            gql_variants = gql_variants_payload.get("productVariants") or []

                            options_list = [
                                {"position": idx + 1, "name": opt.get("name")}
                                for idx, opt in enumerate(product_options)
                                if opt.get("name")
                            ]

                            selected_options_by_name = {}
                            normalized_variants = []
                            for gv in gql_variants:
                                selected = {}
                                for so in gv.get("selectedOptions") or []:
                                    selected[so.get("name")] = so.get("value")
                                v_dict = {
                                    "id": from_shopify_gid(gv.get("id")),
                                    "sku": gv.get("sku"),
                                    "product_id": product_id_numeric,
                                    "inventory_item_id": from_shopify_gid((gv.get("inventoryItem") or {}).get("id")),
                                    "image_id": from_shopify_gid((gv.get("image") or {}).get("id")),
                                }
                                # REST-like option1/2/3 mapping for downstream attribute linking
                                for idx, opt in enumerate(options_list[:3], start=1):
                                    opt_name = opt.get("name")
                                    opt_val = selected.get(opt_name)
                                    if opt_val is not None and opt_val != "":
                                        v_dict[f"option{idx}"] = opt_val
                                normalized_variants.append(v_dict)

                            created_products = {
                                "product": {
                                    "id": product_id_numeric,
                                    "variants": normalized_variants,
                                    "options": options_list,
                                }
                            }

            elif req_type == "update":
                # Update product base fields then variants via productVariantsBulkUpdate.
                product_id_numeric = product_data.get("id") or mapping.shopify_parent_id
                product_gid = to_shopify_gid("Product", product_id_numeric)

                product_update_input = {
                    "id": product_gid,
                    "title": product_data.get("title"),
                    "descriptionHtml": product_data.get("body_html"),
                    "vendor": product_data.get("vendor"),
                    "productType": product_type,
                    "status": _gql_product_status(product_data.get("status")),
                    "tags": _tags_to_list(product_data.get("tags")),
                }
                # Shopify Admin GraphQL expects ProductInput for productUpdate.
                product_update_query = """
                mutation productUpdate($input: ProductInput!) {
                  productUpdate(input: $input) {
                    product { id }
                    userErrors { field message }
                  }
                }
                """
                connector = record.env["marketplace.connector"]
                product_update_res, _next = connector.shopify_graphql_call(
                    headers={"X-Service-Key": marketplace_instance_id.token},
                    url="/graphql.json",
                    query=product_update_query,
                    variables={"input": product_update_input},
                    type="POST",
                    marketplace_instance_id=marketplace_instance_id,
                )
                if product_update_res.get("errors"):
                    raise exceptions.UserError(_("Shopify productUpdate failed: %s") % (product_update_res.get("errors")))
                product_update_payload = (product_update_res.get("data") or {}).get("productUpdate") or {}
                product_update_user_errors = product_update_payload.get("userErrors") or []
                if product_update_user_errors:
                    msgs = "; ".join([ue.get("message") for ue in product_update_user_errors if ue.get("message")])
                    raise exceptions.UserError(_("Shopify productUpdate validation error: %s") % (msgs or product_update_user_errors))

                variants_bulk_input = [
                    _rest_variant_to_gql_bulk_input(v, product_options, for_update=True) for v in variants
                ]
                variant_update_query = """
                mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    productVariants {
                      id
                      sku
                      inventoryItem { id }
                      image { id }
                      selectedOptions { name value }
                    }
                    userErrors { field message }
                  }
                }
                """
                gql_variants_res, _next = connector.shopify_graphql_call(
                    headers={"X-Service-Key": marketplace_instance_id.token},
                    url="/graphql.json",
                    query=variant_update_query,
                    variables={
                        "productId": product_gid,
                        "variants": variants_bulk_input,
                    },
                    type="POST",
                    marketplace_instance_id=marketplace_instance_id,
                )
                if gql_variants_res.get("errors"):
                    created_products = {"errors": gql_variants_res.get("errors")}
                else:
                    gql_variants_payload = (gql_variants_res.get("data") or {}).get("productVariantsBulkUpdate") or {}
                    gql_variant_user_errors = gql_variants_payload.get("userErrors") or []
                    if gql_variant_user_errors:
                        msgs = "; ".join([ue.get("message") for ue in gql_variant_user_errors if ue.get("message")])
                        raise exceptions.UserError(_("Shopify productVariantsBulkUpdate validation error: %s") % (msgs or gql_variant_user_errors))
                    gql_variants = gql_variants_payload.get("productVariants") or []

                    options_list = [
                        {"position": idx + 1, "name": opt.get("name")}
                        for idx, opt in enumerate(product_options)
                        if opt.get("name")
                    ]
                    normalized_variants = []
                    for gv in gql_variants:
                        selected = {}
                        for so in gv.get("selectedOptions") or []:
                            selected[so.get("name")] = so.get("value")
                        v_dict = {
                            "id": from_shopify_gid(gv.get("id")),
                            "sku": gv.get("sku"),
                            "product_id": product_id_numeric,
                            "inventory_item_id": from_shopify_gid((gv.get("inventoryItem") or {}).get("id")),
                            "image_id": from_shopify_gid((gv.get("image") or {}).get("id")),
                        }
                        for idx, opt in enumerate(options_list[:3], start=1):
                            opt_name = opt.get("name")
                            opt_val = selected.get(opt_name)
                            if opt_val is not None and opt_val != "":
                                v_dict[f"option{idx}"] = opt_val
                        normalized_variants.append(v_dict)

                    created_products = {
                        "product": {
                            "id": product_id_numeric,
                            "variants": normalized_variants,
                            "options": options_list,
                        }
                    }
            else:
                created_products = {"errors": _("Unsupported req_type for GraphQL product template: %s") % req_type}

        elif "product.product" in str(record):
            variant_data = data.get("variant") or {}
            connector = record.env["marketplace.connector"]

            # Find parent product id from the template mapping
            tmpl_mapping = record.env["shopify.product.mappings"].search(
                [("product_tmpl_id", "=", record.product_tmpl_id.id), ("shopify_instance_id", "=", marketplace_instance_id.id)],
                limit=1,
            )
            if not tmpl_mapping or not tmpl_mapping.shopify_parent_id:
                created_products = {"errors": _("Missing Shopify parent mapping for variant creation/update")}
            else:
                product_gid = to_shopify_gid("Product", tmpl_mapping.shopify_parent_id)

                # Derive option names from template attribute lines (order => option1/2/3)
                product_option_defs = []
                for att_line in record.product_tmpl_id.attribute_line_ids.filtered(
                    lambda l: l.attribute_id.create_variant != "no_variant"
                ):
                    product_option_defs.append({"name": att_line.attribute_id.name, "values": []})

                variants_list = [variant_data]
                if req_type == "create":
                    variants_bulk_input = [
                        _rest_variant_to_gql_bulk_input(v, product_option_defs, for_update=False) for v in variants_list
                    ]
                    variant_create_query = """
                    mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                      productVariantsBulkCreate(productId: $productId, variants: $variants) {
                        productVariants {
                          id
                          sku
                          inventoryItem { id }
                          image { id }
                          selectedOptions { name value }
                        }
                      }
                    }
                    """
                    gql_variants_res, _next = connector.shopify_graphql_call(
                        headers={"X-Service-Key": marketplace_instance_id.token},
                        url="/graphql.json",
                        query=variant_create_query,
                        variables={"productId": product_gid, "variants": variants_bulk_input},
                        type="POST",
                        marketplace_instance_id=marketplace_instance_id,
                    )
                else:
                    variants_bulk_input = [
                        _rest_variant_to_gql_bulk_input(v, product_option_defs, for_update=True) for v in variants_list
                    ]
                    variant_update_query = """
                    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                        productVariants {
                          id
                          sku
                          inventoryItem { id }
                          image { id }
                          selectedOptions { name value }
                        }
                      }
                    }
                    """
                    gql_variants_res, _next = connector.shopify_graphql_call(
                        headers={"X-Service-Key": marketplace_instance_id.token},
                        url="/graphql.json",
                        query=variant_update_query,
                        variables={"productId": product_gid, "variants": variants_bulk_input},
                        type="POST",
                        marketplace_instance_id=marketplace_instance_id,
                    )

                if gql_variants_res.get("errors"):
                    created_products = {"errors": gql_variants_res.get("errors")}
                else:
                    payload = (gql_variants_res.get("data") or {}).get(
                        "productVariantsBulkCreate" if req_type == "create" else "productVariantsBulkUpdate"
                    ) or {}
                    gql_variants = payload.get("productVariants") or []
                    gv = (gql_variants or [None])[0] or {}
                    created_products = {
                        "variant": {
                            "id": from_shopify_gid(gv.get("id")),
                            "sku": gv.get("sku"),
                            "product_id": tmpl_mapping.shopify_parent_id,
                            "inventory_item_id": from_shopify_gid((gv.get("inventoryItem") or {}).get("id")),
                        }
                    }
        else:
            created_products = {"errors": _("Unsupported record type for GraphQL product request: %s") % record}

    else:
        raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
    _logger.info("\ncreated_products--->\n" + pprint.pformat(created_products))

    if created_products.get('errors'):
        raise exceptions.UserError(_(created_products.get('errors')))
    elif created_products.get('product', {}).get("id"):
        # if not record.shopify_id:
        #     shopify_id = created_products.get("product", {}).get("id")
        #     product_vals = {
        #         'shopify_id': shopify_id,
        #         'marketplace_instance_id': marketplace_instance_id.id,
        #     }
        #     record.write(product_vals)
        if record.image_1920:
            update_image_shopify(marketplace_instance_id, record.image_1920, record)
        if 'product_template_image_ids' in record:
            for image in record.product_template_image_ids:
                update_image_shopify(marketplace_instance_id, image.image_1920, record)
        if created_products.get('product', {}).get("variants"):
            if len(created_products.get('product', {}).get("variants")) == 1:
                variant = created_products.get('product', {}).get("variants")[0]
                product_ids = record.env['product.product'].sudo().search(
                    [('product_tmpl_id', '=', record.id)])
                if len(product_ids) == 1:
                    val_dict = {
                        'name': variant.get('sku'),
                        'shopify_instance_id': marketplace_instance_id.id,
                        'product_id': product_ids.id,
                        'shopify_id': variant.get('id'),
                        'shopify_parent_id': variant.get('product_id'),
                        'shopify_inventory_id': variant.get('inventory_item_id')
                    }
                    if not mapping:
                        prod_mapping = record.env['shopify.product.mappings'].sudo().create(val_dict)
                else:
                    _logger.warning('There is something wrong')
            if len(created_products.get('product', {}).get("variants")) > 1:
                """Update Variants for the Products"""
                variants = created_products.get('product', {}).get("variants")
                options = created_products.get('product', {}).get("options")
                options_dict = {}
                for opt in options:
                    options_dict['option' + str(opt['position'])] = opt['name']
                for var in variants:
                    fields = list([key for key, value in var.items()])
                    pro_domain = []
                    ptav_ids = []
                    for key, value in options_dict.items():
                        if key in fields:
                            attribute_id = record.env['product.attribute'].sudo().search([('name', '=', value)],
                                                                                         limit=1).id
                            domain = [('attribute_id', '=', attribute_id)]
                            domain += [('name', '=', var[key]), ('product_tmpl_id', '=', record.id)]
                            ptav = record.env['product.template.attribute.value'].sudo().search(domain, limit=1)
                            ptav_ids += ptav.ids
                    pro_domain += [('product_tmpl_id', '=', record.id)]
                    if len(ptav_ids) > 1:
                        for ptav_id in ptav_ids:
                            pro_domain += [('product_template_attribute_value_ids', '=', ptav_id)]
                    elif len(ptav_ids) == 1:
                        pro_domain += [('product_template_attribute_value_ids', 'in', ptav_ids)]

                    var_id = record.env['product.product'].sudo().search(pro_domain, limit=1)
                    _logger.info("pro_domain-->%s", pro_domain)

                    if var_id:
                        val_dict = {
                            'name': var.get('sku'),
                            'shopify_instance_id': marketplace_instance_id.id,
                            'product_id': var_id.id,
                            'shopify_id': var.get('id'),
                            'shopify_parent_id': var.get('product_id'),
                            'shopify_inventory_id': var.get('inventory_item_id')
                        }
                        variant_mapping = record.env['shopify.product.mappings'].search([('product_id', '=', var_id.id),('shopify_instance_id', '=', marketplace_instance_id.id)], limit=1)
                        if not variant_mapping:
                            prod_mapping = record.env['shopify.product.mappings'].sudo().create(val_dict)
                        try:
                            var_id.env.cr.commit()
                            if var_id.image_1920:
                                update_image_shopify(marketplace_instance_id, var_id.image_1920, record, var_id)
                        except Exception as e:
                            _logger.info("Exception===>>>{}".format(e.args))
            # Update cost
            record.action_update_shopify_cost_product(marketplace_instance_id)

        body = _("Shopify Product " + req_type + " with Shopify ID: " + str(created_products.get("product").get("id")))
        _logger.info(body)
        record.message_post(body=body)

    elif created_products.get('variant', {}).get("id"):
        if not mapping:
            # shopify_id = created_products.get("variant", {}).get("id")
            # product_vals = {
            #     'shopify_id': shopify_id,
            #     'marketplace_instance_id': marketplace_instance_id.id,
            #     'shopify_inventory_id': created_products.get("variant", {}).get("inventory_item_id"),
            #     'shopify_parent_id': created_products.get("variant", {}).get("product_id")
            # }
            # record.write(product_vals)
            val_dict = {
                'name': created_products.get("variant", {}).get("sku"),
                'shopify_instance_id': marketplace_instance_id.id,
                'product_id': record.id,
                'shopify_id': created_products.get("variant", {}).get("id"),
                'shopify_parent_id': created_products.get("variant", {}).get("product_id"),
                'shopify_inventory_id': created_products.get("variant", {}).get("inventory_item_id")
            }
            prod_mapping = record.env['shopify.product.mappings'].sudo().create(val_dict)
            body = _(
                "Shopify Product Variant" + req_type + " with Shopify ID: " + str(
                    created_products.get("variant").get("id")))
            _logger.info(body)
            record.message_post(body=body)
        # Sync Image
        if marketplace_instance_id.set_image and record.image_1920:
            update_image_shopify(marketplace_instance_id, record.image_1920, record.product_tmpl_id, record)

        # Sync Cost
        record.action_update_shopify_cost_product(marketplace_instance_id)


# --------------------------------------------------------------------------------------------------------
# --------------------------------------Shopify Customer Functions----------------------------------------
# --------------------------------------------------------------------------------------------------------

def shopify_address_values(record):
    address = {}
    first_name = record.name.split(' ', 1)[1] if len(
        record.name.split(' ', 1)[1]) > 0 else ''
    last_name = record.name.split(' ', 1)[1] if len(
        record.name.split(' ', 1)) > 1 else ''

    address = {
        "address": {
            "address1": record.street or '',
            "address2": record.street2 or '',
            "city": record.city or '',
            "company": "Fancy Co.",
            "first_name": first_name,
            "last_name": first_name,
            "phone": record.phone,
            "province": record.state_id.name if record.state_id else '',
            "country": record.country_id.name if record.country_id else '',
            "zip": record.zip,
            "name": record.name,
            "province_code": record.state_id.code if record.state_id else '',
            "country_code": record.country_id.code if record.country_id else '',
            "country_name": record.country_id.name if record.country_id else '',
        }
    }

    address = {k: v for k, v in address.items() if v}

    return address


def shopify_customer_values(record):
    first_name = record.name.split(' ')[0] if len(
        record.name.split(' ', 1)) > 0 else ''
    last_name = record.name.split(' ', 1)[1] if len(
        record.name.split(' ', 1)) > 1 else ''
    customer = {
        "customer": {
            "first_name": first_name,
            "last_name": last_name,
            "email": record.email or '',
            "phone": record.phone or '',
            # Fields can be added
            'note': record.comment,
            'accepts_marketing': record.shopify_accepts_marketing,
            'currency': record.currency_id.name,
            # 'marketing_opt_in_level' : record.currency_id.name,
        }
    }

    customer = {k: v for k, v in customer.items() if v}
    customer["customer"]["default_address"] = shopify_address_values(record)
    pprint.pprint(customer)
    return customer


def shopify_cus_req(self, data, req_type):
    """This function call SHopify Api to get Customer Informations

    Args:
        data (dict): A dict of Customer Information
        req_type (['search','create','update']): Request Type

    Returns:
        dict: Dict containing customer response
    """
    marketplace_instance_id = get_marketplace(self)
    if getattr(marketplace_instance_id, "use_graphql", False):
        connector = self.env['marketplace.connector']
        headers = {'X-Service-Key': marketplace_instance_id.token}
        if req_type == 'search':
            query = """
            query SyncoriaCustomerSearch($query: String!) {
              customers(first: 5, query: $query) {
                nodes { id email }
              }
            }
            """
            res, _next = connector.shopify_graphql_call(
                headers=headers,
                url='/graphql.json',
                query=query,
                variables={"query": "email:%s" % (self.email or "")},
                type='POST',
                marketplace_instance_id=marketplace_instance_id,
            )
            customers = []
            for node in parse_gql_nodes((res.get("data") or {}), ("customers",)):
                customers.append({
                    "id": from_shopify_gid(node.get("id")),
                    "email": node.get("email"),
                })
            return json.dumps({"customers": customers, "errors": res.get("errors")})

        customer_payload = (data or {}).get("customer") or {}
        customer_input = {
            "id": to_shopify_gid("Customer", self.shopify_id) if self.shopify_id else None,
            "firstName": customer_payload.get("first_name"),
            "lastName": customer_payload.get("last_name"),
            "email": customer_payload.get("email"),
            "phone": customer_payload.get("phone"),
            "note": customer_payload.get("note"),
            "acceptsMarketing": customer_payload.get("accepts_marketing"),
            "tags": [t.strip() for t in str(customer_payload.get("tags") or "").split(",") if t.strip()],
        }
        customer_input = {k: v for k, v in customer_input.items() if v is not None and v != ""}

        if req_type == 'create':
            query = """
            mutation SyncoriaCustomerCreate($input: CustomerInput!) {
              customerCreate(input: $input) {
                customer {
                  id firstName lastName email phone state note numberOfOrders verifiedEmail taxExempt tags
                  defaultAddress { id address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2 }
                  addresses { id address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2 }
                }
                userErrors { field message }
              }
            }
            """
            res, _next = connector.shopify_graphql_call(
                headers=headers, url='/graphql.json', query=query, variables={"input": customer_input},
                type='POST', marketplace_instance_id=marketplace_instance_id
            )
            node = (((res.get("data") or {}).get("customerCreate") or {}).get("customer") or {})
            return json.dumps({"customer": _normalize_customer_node(node), "errors": res.get("errors")})

        if req_type == 'update':
            query = """
            mutation SyncoriaCustomerUpdate($input: CustomerInput!) {
              customerUpdate(input: $input) {
                customer {
                  id firstName lastName email phone state note numberOfOrders verifiedEmail taxExempt tags
                  defaultAddress { id address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2 }
                  addresses { id address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2 }
                }
                userErrors { field message }
              }
            }
            """
            res, _next = connector.shopify_graphql_call(
                headers=headers, url='/graphql.json', query=query, variables={"input": customer_input},
                type='POST', marketplace_instance_id=marketplace_instance_id
            )
            node = (((res.get("data") or {}).get("customerUpdate") or {}).get("customer") or {})
            return json.dumps({"customer": _normalize_customer_node(node), "errors": res.get("errors")})

        if req_type == 'delete':
            query = """
            mutation SyncoriaCustomerDelete($input: CustomerDeleteInput!) {
              customerDelete(input: $input) {
                deletedCustomerId
                userErrors { field message }
              }
            }
            """
            res, _next = connector.shopify_graphql_call(
                headers=headers, url='/graphql.json', query=query,
                variables={"input": {"id": to_shopify_gid("Customer", self.shopify_id)}},
                type='POST', marketplace_instance_id=marketplace_instance_id
            )
            deleted_id = (((res.get("data") or {}).get("customerDelete") or {}).get("deletedCustomerId"))
            return json.dumps({"deleted_customer_id": from_shopify_gid(deleted_id), "errors": res.get("errors")})
    raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))


def shopify_add_req(self, data, req_type):
    """This function call Shopify Api to get Address Informations

    Args:
        data (dict): A dict of Address Information
        req_type (['search','create','update']): Request Type

    Returns:
        dict: Address Response
    """
    marketplace_instance_id = get_marketplace(self)
    if getattr(marketplace_instance_id, "use_graphql", False):
        connector = self.env['marketplace.connector']
        headers = {'X-Service-Key': marketplace_instance_id.token}
        customer_gid = to_shopify_gid("Customer", self.shopify_id)
        address_gid = to_shopify_gid("MailingAddress", self.shopify_add_id) if self.shopify_add_id else None

        if req_type == 'create':
            query = """
            mutation SyncoriaCustomerAddressCreate($customerId: ID!, $address: MailingAddressInput!) {
              customerAddressCreate(customerId: $customerId, address: $address) {
                customerAddress { id address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2 }
                userErrors { field message }
              }
            }
            """
            res, _next = connector.shopify_graphql_call(
                headers=headers, url='/graphql.json', query=query,
                variables={"customerId": customer_gid, "address": _address_input_from_rest(data)},
                type='POST', marketplace_instance_id=marketplace_instance_id
            )
            addr = (((res.get("data") or {}).get("customerAddressCreate") or {}).get("customerAddress") or {})
            return json.dumps({"customer_address": _customer_addr_from_gql(addr), "errors": res.get("errors")})

        if req_type == 'update':
            query = """
            mutation SyncoriaCustomerAddressUpdate($customerId: ID!, $id: ID!, $address: MailingAddressInput!) {
              customerAddressUpdate(customerId: $customerId, id: $id, address: $address) {
                customerAddress { id address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2 }
                userErrors { field message }
              }
            }
            """
            res, _next = connector.shopify_graphql_call(
                headers=headers, url='/graphql.json', query=query,
                variables={"customerId": customer_gid, "id": address_gid, "address": _address_input_from_rest(data)},
                type='POST', marketplace_instance_id=marketplace_instance_id
            )
            addr = (((res.get("data") or {}).get("customerAddressUpdate") or {}).get("customerAddress") or {})
            return json.dumps({"customer_address": _customer_addr_from_gql(addr), "errors": res.get("errors")})

        if req_type == 'delete':
            query = """
            mutation SyncoriaCustomerAddressDelete($customerId: ID!, $id: ID!) {
              customerAddressDelete(customerId: $customerId, id: $id) {
                deletedCustomerAddressId
                userErrors { field message }
              }
            }
            """
            res, _next = connector.shopify_graphql_call(
                headers=headers, url='/graphql.json', query=query,
                variables={"customerId": customer_gid, "id": address_gid},
                type='POST', marketplace_instance_id=marketplace_instance_id
            )
            deleted_id = (((res.get("data") or {}).get("customerAddressDelete") or {}).get("deletedCustomerAddressId"))
            return json.dumps({"id": from_shopify_gid(deleted_id), "errors": res.get("errors")})

        if req_type == 'search':
            query = """
            query SyncoriaCustomerAddresses($id: ID!) {
              customer(id: $id) {
                addresses(first: 250) {
                  nodes { id address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2 }
                }
              }
            }
            """
            res, _next = connector.shopify_graphql_call(
                headers=headers, url='/graphql.json', query=query, variables={"id": customer_gid},
                type='POST', marketplace_instance_id=marketplace_instance_id
            )
            addresses = [_customer_addr_from_gql(a) for a in parse_gql_nodes((res.get("data") or {}).get("customer") or {}, ("addresses",))]
            if self.shopify_add_id:
                addresses = [a for a in addresses if str(a.get("id")) == str(self.shopify_add_id)]
                return json.dumps({"customer_address": (addresses[0] if addresses else {}), "errors": res.get("errors")})
            return json.dumps({"addresses": addresses, "errors": res.get("errors")})
    raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))


def shopify_inventory_request(record, data, req_type, marketplace_instance_id=None):
    marketplace_instance_id = marketplace_instance_id or get_marketplace(record)
    if getattr(marketplace_instance_id, "use_graphql", False):
        inventory_item = (data or {}).get("inventory_item") or {}
        mutation = """
        mutation SyncoriaInventoryItemUpdate($id: ID!, $input: InventoryItemInput!) {
          inventoryItemUpdate(id: $id, input: $input) {
            inventoryItem { id sku tracked requiresShipping harmonizedSystemCode countryCodeOfOrigin provinceCodeOfOrigin }
            userErrors { field message }
          }
        }
        """
        item_id = inventory_item.get("id") or getattr(record, "shopify_inventory_id", False)
        input_data = {
            "sku": inventory_item.get("sku"),
            "cost": inventory_item.get("cost"),
            "harmonizedSystemCode": inventory_item.get("harmonized_system_code"),
            "requiresShipping": inventory_item.get("requires_shipping"),
            "countryCodeOfOrigin": inventory_item.get("country_code_of_origin"),
            "provinceCodeOfOrigin": inventory_item.get("province_code_of_origin"),
        }
        input_data = {k: v for k, v in input_data.items() if v is not None and v != ""}
        inventory_items, next_link = record.env['marketplace.connector'].shopify_graphql_call(
            headers={'X-Service-Key': marketplace_instance_id.token},
            url='/graphql.json',
            query=mutation,
            variables={
                "id": to_shopify_gid("InventoryItem", item_id),
                "input": input_data,
            },
            type='POST',
            marketplace_instance_id=marketplace_instance_id,
        )
        _logger.info("inventory_items--->\n%s", pprint.pformat(inventory_items))
        if inventory_items.get('errors'):
            body = "Variant Updated Error for Id-%s" % (inventory_items.get('errors'))
            record.message_post(body=body)
        else:
            updated = ((inventory_items.get("data") or {}).get("inventoryItemUpdate") or {}).get("inventoryItem") or {}
            if updated.get("id"):
                body = "Variant Updated for Id-%s" % from_shopify_gid(updated.get("id"))
                record.message_post(body=body)
        return
    raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
