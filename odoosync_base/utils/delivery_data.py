from odoo.http import request


class DataUtils:
    """
        This class is used for demo data creations for services while fetching relevant service.
    """
    @staticmethod
    def delivery_product_data():
        return [
            {
                "name": "Purolator CN",
                "default_code": "Purolator_001",
                "type": "service",
                "categ_id": request.env.ref("delivery.product_category_deliveries").id,
                "sale_ok": False,
                "purchase_ok": False,
                "list_price": 0.00,
            },
            {
                "name": "Purolator US",
                "default_code": "Purolator_002",
                "type": "service",
                "categ_id": request.env.ref("delivery.product_category_deliveries").id,
                "sale_ok": False,
                "purchase_ok": False,
                "list_price": 0.00,
            },
            {
                "name": "Purolator Int.",
                "default_code": "Purolator_003",
                "type": "service",
                "categ_id": request.env.ref("delivery.product_category_deliveries").id,
                "sale_ok": False,
                "purchase_ok": False,
                "list_price": 0.00,
            },
            {
                "name": "Purolator Int.",
                "default_code": "Purolator_003",
                "type": "service",
                "categ_id": request.env.ref("delivery.product_category_deliveries").id,
                "sale_ok": False,
                "purchase_ok": False,
                "list_price": 0.00,
            },
            {
                "name": "Canada Post",
                "default_code": "DeliveryCNPOST",
                "type": "service",
                "categ_id": request.env.ref("delivery.product_category_deliveries").id,
                "sale_ok": False,
                "purchase_ok": False,
                "list_price": 0.00,
            },

        ]
