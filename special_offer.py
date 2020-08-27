"""
special_offer.py
===

Parse special offer JSON and calculate each discount.

For details of the JSON format, check the docstring for each
_SpecialOffer subclass.
"""

import json
import logging
from collections import namedtuple

from decimal import Decimal
from enum import Enum

from utils import format_currency_gbp


logger = logging.getLogger(__name__)


class SpecialOfferType(Enum):
    FRACTION_OF_PRICE = "fraction_of_price"
    FRACTION_OF_PRICE_PER_QUANTITY = "fraction_of_price_per_quantity"


FractionOfPriceProduct = namedtuple(
    "FractionOfPriceProduct",
    ("fraction_of_price",),
)

FractionOfPricePerQuantityProduct = namedtuple(
    "FractionOfPricePerQuantityProduct",
    ("quantity",),
)

FractionOfPricePerQuantityShared = namedtuple(
    "FractionOfPricePerQuantityShared",
    ("fraction_of_price",),
)

Discount = namedtuple(
    "Discount",
    ("value", "description"),
)


class SpecialOffer:

    SPECIAL_OFFER_TYPE = NotImplemented
    ProductValues = NotImplemented
    SharedValues = NotImplemented

    def __init__(self, products, value_matrix, shared_values=()):
        self._products = products
        self._value_matrix = value_matrix
        self._shared_values = shared_values

    def __repr__(self):
        return (
            f"SpecialOffer(type={self.SPECIAL_OFFER_TYPE!r}) at "
            f"{hash(self)}")

    @staticmethod
    def _parse_special_offer_type(special_offer_obj):
        value = special_offer_obj["special_offer_type"]

        if type(value) is not str:
            raise TypeError

        return SpecialOfferType(value)

    @staticmethod
    def _parse_product_matrix_products(col, product_by_id):
        for product_id in col:
            try:
                product = product_by_id[product_id]
            except IndexError:
                logger.exception("Product not found")
                raise
            else:
                if product is None:
                    logger.exception("Product not found")
                    raise ValueError
                else:
                    yield product

    @staticmethod
    def _parse_product_matrix_values(cols):
        raise NotImplementedError

    @classmethod
    def _parse_product_matrix(cls, special_offer_obj, product_by_id):
        cols = special_offer_obj["product_matrix"]

        products = cls._parse_product_matrix_products(
            cols[0],
            product_by_id,
        )

        value_matrix = cls._parse_product_matrix_values(cols[1:])
        return products, value_matrix

    @staticmethod
    def _parse_shared_values(special_offer_obj):
        return ()

    @classmethod
    def _parse(cls, special_offer_obj, product_by_id):
        try:
            products, value_matrix = cls._parse_product_matrix(
                special_offer_obj,
                product_by_id,
            )
        except ValueError:
            logger.exception("'product_matrix' field is invalid")
            raise

        try:
            shared_values = cls._parse_shared_values(special_offer_obj)
        except ValueError:
            logger.exception("'shared_values' field is invalid")
            raise

        return {
            "products": tuple(products),
            "value_matrix": tuple(value_matrix),
            "shared_values": shared_values,
        }

    @classmethod
    def from_json(cls, file_obj, product_by_id):
        special_offer_obj_seq = json.load(file_obj)

        for special_offer_obj in special_offer_obj_seq:
            try:
                special_offer_type = cls._parse_special_offer_type(
                    special_offer_obj,
                )
            except ValueError:
                logger.exception(
                    "'special_offer_type' field is invalid",
                )
                continue

            sub_cls = _CLS_BY_TYPE[special_offer_type]
            kwargs = sub_cls._parse(special_offer_obj, product_by_id)
            yield sub_cls(**kwargs)

    def _get_quantities(self, quantity_by_product):
        for product in self._products:
            yield quantity_by_product.get(product, 0)

    def _get_discount_description(self, value):
        raise NotImplementedError

    def get_discount(self, quantity_by_product):
        raise NotImplementedError


class FractionOfPrice(SpecialOffer):
    """
    Sell a product at a fraction of its price

    JSON format:

    {
        "special_offer_type": "fraction_of_price",
        "product_matrix": [[PRODUCT_ID], [FRACTION_OF_PRICE]]
    }

    PRODUCT_ID: the product's identifier (integer)
    FRACTION_OF_PRICE: ratio between 0 and 1 (decimal string)

    FRACTION_OF_PRICE is the surcharge rather than the discount, e.g.,
    0.75 means 25% is taken off the original price

    For example, if a product costs £10.00 and FRACTION_OF_PRICE is
    "0.75", £2.50 will be discounted.
    """

    SPECIAL_OFFER_TYPE = SpecialOfferType.FRACTION_OF_PRICE
    ProductValues = FractionOfPriceProduct

    # Product matrix row indices
    _ROW_IX_DISCOUNTED_PRODUCT = 0

    @property
    def discounted_product(self):
        return self._products[self._ROW_IX_DISCOUNTED_PRODUCT]

    @property
    def fraction_of_price(self):
        row_ix = self._ROW_IX_DISCOUNTED_PRODUCT
        return self._value_matrix[row_ix].fraction_of_price

    @classmethod
    def _parse_product_matrix_values(cls, cols):
        col, = cols

        for value in col:
            if type(value) is not str:
                logger.exception("'product_matrix' field is invalid")
                raise ValueError

            yield cls.ProductValues(fraction_of_price=Decimal(value))

    def _get_discount_description(self, value):
        return (
            f"{self.discounted_product.name} "
            f"{(1 - self.fraction_of_price):.0%} off: "
            f"{format_currency_gbp(value * -1)}")

    def get_discount(self, quantity_by_product):
        quantity, = self._get_quantities(quantity_by_product)

        value = (
            quantity *
            self.discounted_product.price *
            (1 - self.fraction_of_price))

        description = self._get_discount_description(value)

        return Discount(value=value, description=description)


class FractionOfPricePerQuantity(SpecialOffer):
    """
    Buy X units of one product, and get Y units of another product
    discounted

    JSON format:

    {
        "special_offer_type": "fraction_of_price_per_quantity",
        "product_matrix": [
            [TRIGGER_PRODUCT_ID, DISCOUNTABLE_PRODUCT_ID],
            [TRIGGER_PRODUCT_QUOTA, DISCOUNTABLE_PRODUCT_QUOTA]
        ],
        "shared_values": [FRACTION_OF_PRICE]
    }

    TRIGGER_PRODUCT_ID:         Product that will trigger the discount
                                of another product (integer)
    TRIGGER_PRODUCT_QUOTA:      Quantity (integer)
    DISCOUNTABLE_PRODUCT_ID:    Product that will be discounted
    DISCOUNTABLE_PRODUCT_QUOTA: Quantity (integer)
    FRACTION_OF_PRICE:          Ratio between 0 and 1 (decimal string)

    FRACTION_OF_PRICE is the surcharge rather than the discount, e.g.,
    0.75 means 25% is taken off the original price

    For every TRIGGER_PRODUCT_QUOTA of the trigger product,
    DISCOUNTABLE_PRODUCT_QUOTA products can be discounted

    For example:

    Apple has product ID: 1 and a price of £0.50
    Banana has product ID: 2 and a price of £1.00

    For each 2 apples, 4 bananas are discounted at 75% of the original
    cost (i.e., 25% off):

    JSON:

    {
        "special_offer_type": "fraction_of_price_per_quantity",
        "product_matrix": [
            [1, 2], # Apple ID, Banana ID
            [2, 4], # Apple quota, Banana quota
        ],
        "shared_values": ["0.75"]  # fraction of banana's price
    }

    If 2 apples and 4 bananas are requested, 0.25 x 4 will be discounted
    If 2 apples and 3 bananas are requested, 0.25 x 3 will be discounted
    If 1 apple and 3 bananas are requested 0.25 x 2 will be discounted
    If 0 apples and 10 bananas are requested, nothing will be discounted
    """

    SPECIAL_OFFER_TYPE = SpecialOfferType.FRACTION_OF_PRICE_PER_QUANTITY
    ProductValues = FractionOfPricePerQuantityProduct
    SharedValues = FractionOfPricePerQuantityShared

    # Product matrix row indices
    _ROW_IX_TRIGGER_PRODUCT = 0
    _ROW_IX_DISCOUNTED_PRODUCT = 1

    @property
    def trigger_product(self):
        return self._products[self._ROW_IX_TRIGGER_PRODUCT]

    @property
    def trigger_product_quantity(self):
        row_ix = self._ROW_IX_TRIGGER_PRODUCT
        return self._value_matrix[row_ix].quantity

    @property
    def discounted_product(self):
        return self._products[self._ROW_IX_DISCOUNTED_PRODUCT]

    @property
    def discounted_product_quantity(self):
        row_ix = self._ROW_IX_DISCOUNTED_PRODUCT
        return self._value_matrix[row_ix].quantity

    @property
    def fraction_of_price(self):
        return self._shared_values.fraction_of_price

    @classmethod
    def _parse_product_matrix_values(cls, cols):
        col, = cols

        for value in col:
            if type(value) is not int:
                logger.exception("'product_matrix' field is invalid")
                raise ValueError

            yield cls.ProductValues(quantity=value)

    @classmethod
    def _parse_shared_values(cls, special_offer_obj):
        shared_values = special_offer_obj['shared_values']

        if type(shared_values) != list:
            raise TypeError

        fraction_of_price_str, = shared_values

        if type(fraction_of_price_str) != str:
            raise TypeError

        return cls.SharedValues(
            fraction_of_price=Decimal(fraction_of_price_str),
        )

    def _get_discount_description(self, value):
        return (
            f"{self.discounted_product.name} "
            f"{(1 - self.fraction_of_price):.0%} off: "
            f"{format_currency_gbp(value * -1)}")

    def get_discount(self, quantity_by_product):
        """
        Trigger product (T)
        Discountable product (D)

        For every X products (T), discount Y products (D). If the
        quantity of products (D) in the basket is less than Y, then the
        quantity in the basket is used instead.

        Example:

        For each 4 apples (A), discount 2 bananas (B). D will represent
        1 discount from a banana.

        4A + 2B => 2D
        8A + 4B => 4D
        8A + 3B => 3D
        """

        # Quantity of trigger products (A)
        tq = self.trigger_product_quantity

        # Number of products (B) to discount, for each quantity of
        # trigger products (A)
        dq_per_tq = self.discounted_product_quantity

        # Actual quantities requested
        (trigger_product_quantity,
         discounted_product_quantity) = self._get_quantities(
            quantity_by_product,
        )

        # Ratio of discounted cost to original cost
        # (e.g. 0.75 would be 75% of original cost)
        fraction_of_price = self.fraction_of_price

        # The maximum number of products (B) that can be discounted,
        # based on the number of trigger products requested
        if trigger_product_quantity > 0:
            max_num_discountable = (
                (trigger_product_quantity // tq) * dq_per_tq)
        else:
            max_num_discountable = 0

        # The actual number of products (B) that can be discounted,
        # taking into account the quantity requested
        num_discountable = min(
            max_num_discountable,
            discounted_product_quantity,
        )

        # The discount
        value = (
            num_discountable *
            self.discounted_product.price *
            (1 - fraction_of_price))

        description = self._get_discount_description(value)

        return Discount(value=value, description=description)


_CLS_BY_TYPE = {
    cls.SPECIAL_OFFER_TYPE: cls
    for cls in (
        FractionOfPrice,
        FractionOfPricePerQuantity,
    )}


get_special_offers_from_json = SpecialOffer.from_json
