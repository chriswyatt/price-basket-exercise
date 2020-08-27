#!/usr/bin/env python3

import argparse
from collections import Counter
from pathlib import Path

from product import get_products_from_json
from special_offer import get_special_offers_from_json
from utils import format_currency_gbp


_MODULE_DIR_PATH = Path(__file__).parent.resolve()

with (_MODULE_DIR_PATH / 'products.json').open('rb') as file_obj:
    _PRODUCTS_BY_ID = tuple(get_products_from_json(file_obj))

with (_MODULE_DIR_PATH / 'special_offers.json').open('rb') as file_obj:
    _SPECIAL_OFFERS = tuple(get_special_offers_from_json(
        file_obj,
        _PRODUCTS_BY_ID,
    ))


def _parse_args(products_by_id):
    product_by_name = {
        p.name: p for p in products_by_id if p is not None}

    parser = argparse.ArgumentParser(
        description=(
            "Price a basket of goods, accounting for special offers"),
    )

    parser.add_argument(
        "products",
        metavar="PRODUCT",
        type=product_by_name.__getitem__,
        nargs="+",
        help="Name of product",
    )

    args = parser.parse_args()
    return Counter(args.products)


def _get_original_total(quantity_by_product):
    return sum(
        quantity * product.price
        for product, quantity in quantity_by_product.items())


def _get_discounts(special_offers, quantity_by_product):
    for special_offer in special_offers:
        discount = special_offer.get_discount(quantity_by_product)
        if discount.value > 0:
            yield discount


def get_original_total_and_discounts(
        quantity_by_product,
        special_offers,
):
    original_total = _get_original_total(quantity_by_product)
    discounts = _get_discounts(special_offers, quantity_by_product)

    return original_total, discounts


def _print_summary(original_total, discounts):
    subtotal = original_total

    for discount in discounts:
        print(f"Subtotal: {format_currency_gbp(subtotal)}")
        print(f"{discount.description}")
        subtotal -= discount.value

    print(f"Total: {format_currency_gbp(subtotal)}")


def main():
    quantity_by_product = _parse_args(_PRODUCTS_BY_ID)

    original_total, discounts = get_original_total_and_discounts(
        quantity_by_product,
        _SPECIAL_OFFERS,
    )

    _print_summary(original_total, discounts)


if __name__ == '__main__':
    main()
