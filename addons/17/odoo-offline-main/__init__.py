from . import models

def post_init_hook(env):
    PublisherWarrantyContract = env['publisher_warranty.contract']
    PublisherWarrantyContract.update_notification(cron_mode=False)
