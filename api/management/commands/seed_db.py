from django.core.management.base import BaseCommand
from api.models import Product, SkinConcern, Retailer, RetailerListing

class Command(BaseCommand):
    help = 'Seeds the database with initial mock skincare products'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding data...')
        
        # Concerns
        pores, _ = SkinConcern.objects.get_or_create(label='Clogged Pores', internal_key='pores')
        acne, _ = SkinConcern.objects.get_or_create(label='Blemish-Prone Skin', internal_key='acne')
        dryness, _ = SkinConcern.objects.get_or_create(label='Severe Dryness', internal_key='dryness')
        pigment, _ = SkinConcern.objects.get_or_create(label='Uneven Skin Tone', internal_key='pigmentation')
        redness, _ = SkinConcern.objects.get_or_create(label='Easily Irritated Skin', internal_key='redness')
        
        # Retailer
        sephora, _ = Retailer.objects.get_or_create(
            name='Sephora', 
            base_url='https://www.sephora.com', 
            affiliate_network='sovrn'
        )

        products_data = [
            {
                'brand': 'GlowRecipe', 'name': 'Watermelon Glow AHA Night Treatment',
                'type': 'serum', 'concerns': [pores, acne], 'price': 40.00,
                'image': 'https://www.sephora.com/productimages/sku/s2530467-main-zoom.jpg'
            },
            {
                'brand': "Paula's Choice", 'name': '2% BHA Liquid Exfoliant',
                'type': 'exfoliant', 'concerns': [acne, pores], 'price': 34.00,
                'image': 'https://www.sephora.com/productimages/sku/s2362168-main-zoom.jpg'
            },
            {
                'brand': 'Supergoop!', 'name': 'Unseen Sunscreen SPF 40',
                'type': 'sunscreen', 'concerns': [], 'price': 38.00,
                'image': 'https://www.sephora.com/productimages/sku/s2357226-main-zoom.jpg'
            },
            {
                'brand': 'LANEIGE', 'name': 'Cream Skin Toner & Moisturizer',
                'type': 'toner', 'concerns': [dryness], 'price': 36.00,
                'image': 'https://www.sephora.com/productimages/product/p504044-av-05-zoom.jpg'
            },
            {
                'brand': 'The Ordinary', 'name': 'Niacinamide 10% + Zinc 1%',
                'type': 'serum', 'concerns': [acne, pores], 'price': 6.00,
                'image': 'https://www.sephora.com/productimages/sku/s2031391-main-zoom.jpg'
            },
            {
                'brand': 'COSRX', 'name': 'Advanced Snail 96 Mucin Power Essence',
                'type': 'serum', 'concerns': [dryness, redness], 'price': 25.00,
                'image': 'https://www.ulta.com/pim/master/2561917.jpg'
            },
        ]

        for data in products_data:
            prod, created = Product.objects.get_or_create(
                brand=data['brand'], 
                name=data['name'], 
                defaults={
                    'product_type': data['type'],
                    'image_url': data['image'],
                }
            )
            prod.concerns.set(data['concerns'])

            RetailerListing.objects.get_or_create(
                product=prod, retailer=sephora,
                defaults={'price': data['price'], 'product_url': 'https://example.com'}
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded DB.'))
