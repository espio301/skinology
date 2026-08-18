"""
Unit tests for the INCI parser and synonym resolution.
"""

from django.test import TestCase

from scraper.parsers.synonym_table import resolve_synonym, get_umbrella_names
from scraper.parsers.inci_parser import normalize_inci_name, parse_inci_list


class NormalizeInciNameTest(TestCase):
    """Tests for ``normalize_inci_name``."""

    def test_strips_whitespace(self):
        self.assertEqual(normalize_inci_name("  Retinol  "), "retinol")

    def test_collapses_internal_whitespace(self):
        self.assertEqual(
            normalize_inci_name("Salicylic   Acid"),
            "salicylic acid",
        )

    def test_lowercases(self):
        self.assertEqual(normalize_inci_name("NIACINAMIDE"), "niacinamide")

    def test_empty_string(self):
        self.assertEqual(normalize_inci_name(""), "")

    def test_single_word(self):
        self.assertEqual(normalize_inci_name("Glycerin"), "glycerin")


class ResolveSynonymTest(TestCase):
    """Tests for ``resolve_synonym``."""

    def test_known_synonym_maps_to_canonical(self):
        self.assertEqual(resolve_synonym("vitamin c"), "Ascorbic Acid")
        self.assertEqual(resolve_synonym("retinal"), "Retinaldehyde")
        self.assertEqual(resolve_synonym("vitamin b3"), "Niacinamide")

    def test_case_insensitive(self):
        self.assertEqual(resolve_synonym("VITAMIN C"), "Ascorbic Acid")
        self.assertEqual(resolve_synonym("Retinol"), "Retinol")

    def test_whitespace_handling(self):
        self.assertEqual(
            resolve_synonym("  salicylic  acid  "), "Salicylic Acid"
        )

    def test_unknown_ingredient_returns_title_cased(self):
        self.assertEqual(
            resolve_synonym("some unknown ingredient"),
            "Some Unknown Ingredient",
        )

    def test_water_synonyms(self):
        self.assertEqual(resolve_synonym("aqua"), "Water")
        self.assertEqual(resolve_synonym("eau"), "Water")
        self.assertEqual(resolve_synonym("water"), "Water")

    def test_granactive_retinoid_maps(self):
        self.assertEqual(
            resolve_synonym("granactive retinoid"),
            "Hydroxypinacolone Retinoate",
        )


class GetUmbrellaNamesTest(TestCase):
    """Tests for ``get_umbrella_names``."""

    def test_retinol_belongs_to_retinoids(self):
        umbrellas = get_umbrella_names("Retinol")
        self.assertIn("Retinoids & Alternatives", umbrellas)

    def test_ascorbic_acid_belongs_to_multiple(self):
        umbrellas = get_umbrella_names("Ascorbic Acid")
        self.assertIn("Vitamin C Derivatives", umbrellas)
        self.assertIn("Antioxidants", umbrellas)

    def test_unknown_returns_empty(self):
        self.assertEqual(get_umbrella_names("Water"), [])

    def test_salicylic_acid_belongs_to_bhas_and_acne(self):
        umbrellas = get_umbrella_names("Salicylic Acid")
        self.assertIn("BHAs", umbrellas)
        self.assertIn("Acne Fighters", umbrellas)


class ParseInciListTest(TestCase):
    """Tests for ``parse_inci_list``."""

    def test_basic_comma_separated(self):
        result = parse_inci_list("Water, Glycerin, Niacinamide")
        self.assertEqual(result, ["Water", "Glycerin", "Niacinamide"])

    def test_synonym_resolution_applied(self):
        result = parse_inci_list("Aqua, Vitamin C, Vitamin B3")
        self.assertEqual(result, ["Water", "Ascorbic Acid", "Niacinamide"])

    def test_empty_string(self):
        self.assertEqual(parse_inci_list(""), [])

    def test_whitespace_only(self):
        self.assertEqual(parse_inci_list("   "), [])

    def test_none_input(self):
        self.assertEqual(parse_inci_list(None), [])

    def test_preserves_order(self):
        result = parse_inci_list("Retinol, Niacinamide, Glycerin")
        self.assertEqual(result, ["Retinol", "Niacinamide", "Glycerin"])

    def test_strips_trailing_commas(self):
        result = parse_inci_list("Water, Glycerin, ")
        self.assertEqual(result, ["Water", "Glycerin"])

    def test_unknown_ingredients_title_cased(self):
        result = parse_inci_list("Water, xyzol mysterious compound")
        self.assertEqual(result, ["Water", "Xyzol Mysterious Compound"])


class MatchOrCreateIngredientsTest(TestCase):
    """Tests for ``match_or_create_ingredients``."""

    def test_creates_new_ingredient(self):
        from scraper.parsers.inci_parser import match_or_create_ingredients
        from api.models import Ingredient

        result = match_or_create_ingredients(["Retinol"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].inci_name, "Retinol")
        self.assertTrue(Ingredient.objects.filter(inci_name="Retinol").exists())

    def test_deduplicates_on_second_call(self):
        from scraper.parsers.inci_parser import match_or_create_ingredients
        from api.models import Ingredient

        match_or_create_ingredients(["Niacinamide"])
        match_or_create_ingredients(["Niacinamide"])
        self.assertEqual(
            Ingredient.objects.filter(inci_name__iexact="Niacinamide").count(),
            1,
        )

    def test_auto_assigns_umbrella(self):
        from scraper.parsers.inci_parser import match_or_create_ingredients

        result = match_or_create_ingredients(["Retinol"])
        umbrellas = list(result[0].umbrellas.values_list("name", flat=True))
        self.assertIn("Retinoids & Alternatives", umbrellas)

    def test_finds_by_synonym_list(self):
        from scraper.parsers.inci_parser import match_or_create_ingredients
        from api.models import Ingredient

        # Create an ingredient with a synonym
        Ingredient.objects.create(
            inci_name="Ascorbic Acid",
            common_name="Vitamin C",
            synonyms=["vitamin c", "l-ascorbic acid"],
        )

        result = match_or_create_ingredients(["Ascorbic Acid"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].inci_name, "Ascorbic Acid")
        # Should not create a duplicate
        self.assertEqual(
            Ingredient.objects.filter(inci_name="Ascorbic Acid").count(), 1
        )

    def test_multiple_ingredients_preserves_order(self):
        from scraper.parsers.inci_parser import match_or_create_ingredients

        names = ["Water", "Glycerin", "Niacinamide"]
        result = match_or_create_ingredients(names)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].inci_name, "Water")
        self.assertEqual(result[1].inci_name, "Glycerin")
        self.assertEqual(result[2].inci_name, "Niacinamide")
