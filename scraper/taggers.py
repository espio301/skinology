"""
Concern auto-tagger.

Assigns ``SkinConcern`` records to ``Product`` instances based on the
concerns linked to the product's ingredients.  A product "addresses" a
concern if at least one of its ingredients has that concern in its
``concerns_supported`` M2M.
"""

import logging

from django.db.models import QuerySet

logger = logging.getLogger(__name__)


def auto_tag_product(product) -> None:
    """
    Look at every ingredient linked to *product*, collect all
    ``concerns_supported`` as well as evidence-supported concerns from those ingredients,
    and set ``product.concerns`` to the union of top-level parent concerns.

    This is idempotent — calling it multiple times on the same product
    will always produce the same result.
    """
    from api.models import SkinConcern, IngredientConcernEvidence  # deferred import

    concern_ids: set[int] = set()
    ingredient_ids = [pi.ingredient_id for pi in product.product_ingredients.all()]

    if ingredient_ids:
        # Collect explicitly supported concerns
        for pi in product.product_ingredients.select_related("ingredient").all():
            for concern in pi.ingredient.concerns_supported.all():
                parent = concern.parent if concern.parent else concern
                concern_ids.add(parent.pk)

        # Collect evidence-backed concerns (pubmed_count > 0)
        evidence_qs = IngredientConcernEvidence.objects.filter(
            ingredient_id__in=ingredient_ids,
            pubmed_count__gt=0,
        ).select_related('concern__parent')

        for ev in evidence_qs:
            parent = ev.concern.parent if ev.concern.parent else ev.concern
            concern_ids.add(parent.pk)

    if concern_ids:
        concerns = SkinConcern.objects.filter(pk__in=concern_ids)
        product.concerns.set(concerns)
        logger.debug(
            "Tagged '%s' with %d concerns: %s",
            product,
            len(concern_ids),
            [c.label for c in concerns],
        )
    else:
        product.concerns.clear()
        logger.debug("'%s' has no matching concerns — cleared.", product)


def auto_tag_all_products() -> int:
    """
    Bulk-tag every product that has at least one ``ProductIngredient``.

    Returns:
        Number of products that were updated.
    """
    from api.models import Product  # deferred import

    updated = 0
    products: QuerySet = Product.objects.prefetch_related(
        "product_ingredients__ingredient__concerns_supported",
    ).all()

    for product in products:
        auto_tag_product(product)
        updated += 1

    logger.info("Auto-tagged %d products with skin concerns.", updated)
    return updated
