-- disable clik2pay payment provider
UPDATE payment_provider
   SET clik2pay_user_name = NULL,
       clik2pay_user_password = NULL,
       clik2pay_api_key = NULL;
