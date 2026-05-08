-- disable clik2pay payment provider
UPDATE payment_provider
   SET globalpay_api_version = NULL,
       globalpay_app_id = NULL,