from django.core.management.base import BaseCommand
from api.models import PhoneProduct
from decimal import Decimal

class Command(BaseCommand):
    help = 'Populate the database with default phone products'

    def handle(self, *args, **options):
        # Define all phone products based on phons.tsx
        phone_products = [
            # Rubber cases (PhoneSettingsT)
            {
                'type': 'customed rubber case',
                'modell': 'iphone 14',
                'stock': True,
                'price': Decimal('30.00'),
                'url': '/tough/iPhone_14_t.png'
            },
            {
                'type': 'customed rubber case',
                'modell': 'iphone 14 plus',
                'stock': True,
                'price': Decimal('30.00'),
                'url': '/tough/iPhone_14_Plus_t.png'
            },
            {
                'type': 'customed rubber case',
                'modell': 'iphone 14 pro',
                'stock': True,
                'price': Decimal('30.00'),
                'url': '/tough/iPhone_14_Pro_t.png'
            },
            {
                'type': 'customed rubber case',
                'modell': 'iphone 14 pro max',
                'stock': True,
                'price': Decimal('30.00'),
                'url': '/tough/iPhone_14_Pro_Max_t.png'
            },
            {
                'type': 'customed rubber case',
                'modell': 'iphone 15',
                'stock': True,
                'price': Decimal('30.00'),
                'url': '/tough/iPhone_15_t.png'
            },
            {
                'type': 'customed rubber case',
                'modell': 'iphone 15 plus',
                'stock': True,
                'price': Decimal('30.00'),
                'url': '/tough/iPhone_15_Plus_t.png'
            },
            {
                'type': 'customed rubber case',
                'modell': 'iphone 15 pro',
                'stock': True,
                'price': Decimal('30.00'),
                'url': '/tough/iPhone_15_Pro_t.png'
            },
            {
                'type': 'customed rubber case',
                'modell': 'iphone 15 pro max',
                'stock': True,
                'price': Decimal('30.00'),
                'url': '/tough/iPhone_15_Pro_Max_t.png'
            },
            {
                'type': 'customed rubber case',
                'modell': 'iphone 16 pro',
                'stock': True,
                'price': Decimal('30.00'),
                'url': '/tough/iPhone_16_Pro_t.png'
            },
            {
                'type': 'customed rubber case',
                'modell': 'iphone 16 pro max',
                'stock': True,
                'price': Decimal('30.00'),
                'url': '/tough/iPhone_16_Pro_Max_t.png'
            },
            
            # Clear cases (PhoneSettings)
            {
                'type': 'customed clear case',
                'modell': 'iphone se',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_se.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 7',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_7_8.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 8',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_7_8.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 12',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_12.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 12 mini',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_12_mini.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 12 pro',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_12_pro.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 12 pro max',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_12_pro_max.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 13',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_13.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 13 mini',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_13_mini.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 13 pro',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_13_pro.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 13 pro max',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_13_pro_max.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 14',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_14.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 14 plus',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_14_plus.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 14 pro',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_14_pro.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'iphone 14 pro max',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/iphone_14_pro_max.png'
            },
            
            # Samsung phones
            {
                'type': 'customed clear case',
                'modell': 'samsung a34',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/samsung_a34.jpg'
            },
            {
                'type': 'customed clear case',
                'modell': 'samsung a54',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/samsung_a54.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'samsung galaxy note 8',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/samsung_galaxy_note_8.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'samsung galaxy note 12',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/samsung_galaxy_note_12.png'
            },
            {
                'type': 'customed clear case',
                'modell': 'samsung galaxy s23',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/samsung_galaxy_s23.webp'
            },
            
            # Oppo phones
            {
                'type': 'customed clear case',
                'modell': 'oppo a60',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/oppo_a60.jpg'
            },
            {
                'type': 'customed clear case',
                'modell': 'oppo reno 4z',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/oppo_reno_4z.avif'
            },
            {
                'type': 'customed clear case',
                'modell': 'oppo reno 5 lite',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/oppo_reno_5_lite.avif'
            },
            {
                'type': 'customed clear case',
                'modell': 'oppo reno 6',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/oppo_reno_6.jpg'
            },
            {
                'type': 'customed clear case',
                'modell': 'oppo reno 12',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/oppo_reno_12.jpg'
            },
            
            # Redmi phones
            {
                'type': 'customed clear case',
                'modell': 'redmi 13 pro',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/redmi_13_pro.webp'
            },
            {
                'type': 'customed clear case',
                'modell': 'redmi a3',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/redmi_a3.avif'
            },
            {
                'type': 'customed clear case',
                'modell': 'redmi note 12',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/redmi_note_12.jpg'
            },
            {
                'type': 'customed clear case',
                'modell': 'redmi note 11 pro',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/redmi_note_11_pro.avif'
            },
            {
                'type': 'customed clear case',
                'modell': 'redmi note 10',
                'stock': True,
                'price': Decimal('25.00'),
                'url': '/normal/redmi_note_10.jpg'
            },
        ]

        created_count = 0
        updated_count = 0

        for product_data in phone_products:
            product, created = PhoneProduct.objects.get_or_create(
                type=product_data['type'],
                modell=product_data['modell'],
                defaults={
                    'stock': product_data['stock'],
                    'price': product_data['price'],
                    'url': product_data['url']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {product.type} - {product.modell}')
                )
            else:
                # Update existing product with new data
                product.stock = product_data['stock']
                product.price = product_data['price']
                product.url = product_data['url']
                product.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated: {product.type} - {product.modell}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated phone products! Created: {created_count}, Updated: {updated_count}'
            )
        ) 