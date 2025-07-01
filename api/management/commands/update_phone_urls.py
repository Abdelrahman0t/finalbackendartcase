from django.core.management.base import BaseCommand
from api.models import PhoneProduct

class Command(BaseCommand):
    help = 'Updates URLs for all phone products based on their model names and types'

    # Manual mapping of model names to their exact URLs
    URL_MAPPING = {
        # Rubber cases
        'iphone 14': 'tough/iPhone_14_t.png',
        'iphone 14 plus': 'tough/iPhone_14_Plus_t.png',
        'iphone 14 pro': 'tough/iPhone_14_Pro_t.png',
        'iphone 14 pro max': 'tough/iPhone_14_Pro_Max_t.png',
        'iphone 15': 'tough/iPhone_15_t.png',
        'iphone 15 plus': 'tough/iPhone_15_Plus_t.png',
        'iphone 15 pro': 'tough/iPhone_15_Pro_t.png',
        'iphone 15 pro max': 'tough/iPhone_15_Pro_Max_t.png',
        'iphone 16 pro': 'tough/iPhone_16_Pro_t.png',
        'iphone 16 max': 'tough/iPhone_16_Pro_Max_t.png',
        
        # Clear cases
        'iphone se': 'normal/iphone_se.png',
        'iphone 7': 'normal/iphone_7_8.png',
        'iphone 8': 'normal/iphone_7_8.png',
        'iphone 12': 'normal/iphone_12.png',
        'iphone 12 mini': 'normal/iphone_12_mini.png',
        'iphone 12 pro': 'normal/iphone_12_pro.png',
        'iphone 12 pro max': 'normal/iphone_12_pro_max.png',
        'iphone 13': 'normal/iphone_13.png',
        'iphone 13 mini': 'normal/iphone_13_mini.png',
        'iphone 13 pro': 'normal/iphone_13_pro.png',
        'iphone 13 pro max': 'normal/iphone_13_pro_max.png',
        'iphone 14': 'normal/iphone_14.png',
        'iphone 14 plus': 'normal/iphone_14_plus.png',
        'iphone 14 pro': 'normal/iphone_14_pro.png',
        'iphone 14 pro max': 'normal/iphone_14_pro_max.png',
        'samsung a34': 'normal/samsung_a34.jpg',
        'samsung a54': 'normal/samsung_a54.png',
        'samsung galaxy note 8': 'normal/samsung_galaxy_note_8.png',
        'samsung galaxy note 12': 'normal/samsung_galaxy_note_12.png',
        'samsung galaxy s23': 'normal/samsung_galaxy_s23.webp',
        'oppo a60': 'normal/oppo_a60.jpg',
        'oppo reno 4z': 'normal/oppo_reno_4z.avif',
        'oppo reno 5 lite': 'normal/oppo_reno_5_lite.avif',
        'oppo reno 6': 'normal/oppo_reno_6.jpg',
        'oppo reno 12': 'normal/oppo_reno_12.jpg',
        'redmi 13 pro': 'normal/redmi_13_pro.webp',
        'redmi a3': 'normal/redmi_a3.avif',
        'redmi note 12': 'normal/redmi_note_12.jpg',
        'redmi note 11 pro': 'normal/redmi_note_11_pro.avif',
        'redmi note 10': 'normal/redmi_note_10.jpg'
    }

    def handle(self, *args, **kwargs):
        products = PhoneProduct.objects.all()
        updated_count = 0

        for product in products:
            # Get the URL from our mapping
            url = self.URL_MAPPING.get(product.modell.lower())
            if url:
                product.url = url
                product.save()
                updated_count += 1
            else:
                self.stdout.write(self.style.WARNING(f'No URL mapping found for {product.modell}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} products')) 