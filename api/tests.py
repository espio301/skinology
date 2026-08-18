from django.test import TestCase
from api.models import Ingredient, SkinConcern, Product, ProductIngredient, IngredientConcernEvidence
from api.services.pubmed_client import build_query, CONTRAINDICATED_PAIRS, _is_contraindicated
from api.serializers import ProductDetailSerializer


class PubMedClientTests(TestCase):
    def setUp(self):
        self.retinol, _ = Ingredient.objects.get_or_create(inci_name='Retinol')
        self.retinol.pubmed_terms = [{'term': 'Retinol', 'field': 'Mesh'}, {'term': 'retinol', 'field': 'ti'}]
        self.retinol.save()

        self.glycolic, _ = Ingredient.objects.get_or_create(inci_name='Glycolic Acid')
        self.glycolic.pubmed_terms = [{'term': 'glycolic acid', 'field': 'ti'}]
        self.glycolic.save()

        self.niacinamide, _ = Ingredient.objects.get_or_create(inci_name='Niacinamide')
        self.niacinamide.pubmed_terms = [{'term': 'Niacinamide', 'field': 'Mesh'}, {'term': 'niacinamide', 'field': 'ti'}]
        self.niacinamide.save()

        self.sun_protection, _ = SkinConcern.objects.get_or_create(internal_key='sun-protection', defaults={'label': 'Sun Protection'})
        self.sun_protection.pubmed_terms = [{'term': 'sunscreen', 'field': 'tiab'}]
        self.sun_protection.pubmed_excluders = [{'term': 'photosensitiv*', 'field': 'tiab'}, {'term': 'phototoxic*', 'field': 'tiab'}]
        self.sun_protection.save()

        self.dryness, _ = SkinConcern.objects.get_or_create(internal_key='dryness', defaults={'label': 'Dryness'})
        self.dryness.pubmed_terms = [{'term': 'dry skin', 'field': 'tiab'}]
        self.dryness.save()

        self.acne, _ = SkinConcern.objects.get_or_create(internal_key='acne', defaults={'label': 'Acne'})
        self.acne.pubmed_terms = [{'term': 'acne', 'field': 'tiab'}]
        self.acne.save()


    def test_contraindicated_pairs_blocked(self):
        """Retinol x sun-protection and Retinol x dryness should return empty query string."""
        self.assertTrue(_is_contraindicated(self.retinol, self.sun_protection))
        self.assertEqual(build_query(self.retinol, self.sun_protection), '')

        self.assertTrue(_is_contraindicated(self.retinol, self.dryness))
        self.assertEqual(build_query(self.retinol, self.dryness), '')

        self.assertTrue(_is_contraindicated(self.glycolic, self.sun_protection))
        self.assertEqual(build_query(self.glycolic, self.sun_protection), '')

    def test_valid_pair_builds_query(self):
        """Niacinamide x acne should return a valid non-empty query string including excluders if any."""
        self.assertFalse(_is_contraindicated(self.niacinamide, self.acne))
        query = build_query(self.niacinamide, self.acne)
        self.assertIn('Niacinamide', query)
        self.assertIn('acne', query)

    def test_excluders_included_in_query(self):
        """Valid pair with concern excluders should include NOT clause with excluders."""
        query = build_query(self.niacinamide, self.sun_protection)
        self.assertIn('NOT', query)
        self.assertIn('photosensitiv*', query)
        self.assertIn('phototoxic*', query)


class SerializerTests(TestCase):
    def test_product_detail_serializer_includes_query_used(self):
        ingredient, _ = Ingredient.objects.get_or_create(inci_name='Niacinamide')
        concern, _ = SkinConcern.objects.get_or_create(internal_key='acne', defaults={'label': 'Acne'})
        product = Product.objects.create(name='Test Serum', brand='Brand', slug='test-serum')
        product.concerns.add(concern)
        ProductIngredient.objects.create(product=product, ingredient=ingredient, order=1)

        IngredientConcernEvidence.objects.create(
            ingredient=ingredient,
            concern=concern,
            evidence_tier='well_founded',
            pubmed_count=150,
            query_used='("Niacinamide"[Mesh]) AND ("Acne Vulgaris"[Mesh])',
            top_articles=[{'pmid': '12345', 'title': 'Study on Niacinamide', 'year': 2023}]
        )

        serializer = ProductDetailSerializer(product)
        breakdown = serializer.data['concern_breakdown']
        self.assertEqual(len(breakdown), 1)
        sub_concerns = breakdown[0]['sub_concerns']
        self.assertEqual(len(sub_concerns), 1)
        ing_data = sub_concerns[0]['ingredients'][0]
        self.assertEqual(ing_data['query_used'], '("Niacinamide"[Mesh]) AND ("Acne Vulgaris"[Mesh])')
        self.assertEqual(ing_data['articles'][0]['pmid'], '12345')


