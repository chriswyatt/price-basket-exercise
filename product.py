import json
import logging

from decimal import Decimal


logger = logging.getLogger(__name__)


class Product:

    def __init__(self, product_id, name, price):
        self.product_id = product_id
        self.name = name
        self.price = price

    def __repr__(self):
        return f"Product(id={self.product_id!r}, name={self.name!r})"

    @staticmethod
    def _parse_product_id(product_obj):
        value = product_obj['product_id']

        if type(value) is not int:
            raise TypeError

        return value

    @staticmethod
    def _parse_name(product_obj):
        value = product_obj['name']

        if type(value) is not str:
            raise TypeError

        return value

    @staticmethod
    def _parse_price(product_obj):
        value = product_obj['price']
        if type(value) is not str:
            raise ValueError

        return Decimal(value)

    @classmethod
    def from_json(cls, file_obj):
        product_obj_seq = json.load(file_obj)

        product_id_set = set()
        name_set = set()

        for product_obj in product_obj_seq:

            try:
                product_id = cls._parse_product_id(product_obj)
            except ValueError:
                logger.exception("'product_id' field is invalid")
                continue

            if product_id in product_id_set:
                logger.error("Product IDs are not unique")
                continue

            try:
                name = cls._parse_name(product_obj)
            except ValueError:
                logger.exception("'name' field is invalid")
                continue

            if name in name_set:
                logger.error("Product names are not unique")
                continue

            name_set.add(name)

            try:
                price = cls._parse_price(product_obj)
            except ValueError:
                logger.exception("'price' field is invalid")
                continue

            yield cls(product_id=product_id, name=name, price=price)


def get_products_from_json(file_obj):
    product_by_id = {
        p.product_id: p for p in Product.from_json(file_obj)}

    if len(product_by_id) == 0:
        return ()

    max_product_id = max(product_by_id.keys())

    return tuple(
        product_by_id.get(ix) for ix in range(max_product_id + 1))
