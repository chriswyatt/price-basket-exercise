import io
import json
import unittest
from itertools import chain, repeat
from operator import attrgetter
from random import sample
from unittest.mock import patch, sentinel

import factory

from factories import ProductFactory, fake
from product import Product, get_products_from_json


class TestProductFromJson(unittest.TestCase):

    def test_one_product(self):
        stub = ProductFactory.stub(product_id=fake.random_int())

        with io.StringIO() as file_obj:
            product_obj = {
                "product_id": stub.product_id,
                "name": stub.name,
                "price": str(stub.price)
            }
            json.dump([product_obj], file_obj)
            file_obj.seek(0)

            product, = Product.from_json(file_obj)

        self.assertEqual(stub.product_id, product.product_id)
        self.assertEqual(stub.name, product.name)
        self.assertEqual(stub.price, product.price)

    def test_many_products(self):
        stub_seq = ProductFactory.stub_batch(fake.random_int(2, 8))

        with io.StringIO() as file_obj:
            product_obj_seq = [
                {
                    "product_id": stub.product_id,
                    "name": stub.name,
                    "price": str(stub.price)
                }
                for stub in stub_seq
            ]
            json.dump(product_obj_seq, file_obj)
            file_obj.seek(0)

            products = tuple(Product.from_json(file_obj))

        expected = tuple(map(
            attrgetter("product_id", "name", "price"),
            stub_seq,
        ))

        actual = tuple(map(
            attrgetter("product_id", "name", "price"),
            products,
        ))

        self.assertEqual(expected, actual)


class TestGetProductsFromJson(unittest.TestCase):

    @patch("product.Product")
    def test_success(self, product_cls):
        file_obj = sentinel.file_obj

        product_id_seq = range(1, 9)

        stub_seq = ProductFactory.stub_batch(
            len(product_id_seq),
            product_id=factory.Iterator(product_id_seq, cycle=False),
        )

        product_seq = tuple(
            Product(s.product_id, s.name, s.price)
            for s in stub_seq)

        from_json = product_cls.from_json
        from_json.return_value.__iter__.return_value = product_seq

        expected = (None, ) + product_seq

        actual = get_products_from_json(file_obj)

        self.assertEqual(expected, actual)

    @patch("product.Product")
    def test_id_unconsecutive_and_unordered(self, product_cls):
        file_obj = sentinel.file_obj

        product_id_seq = (3, 6, 10, 15)

        stub_seq = ProductFactory.stub_batch(
            len(product_id_seq),
            product_id=factory.Iterator(product_id_seq, cycle=False),
        )

        product_seq = tuple(
            Product(s.product_id, s.name, s.price)
            for s in stub_seq)

        from_json = product_cls.from_json

        from_json.return_value.__iter__.return_value = sample(
            product_seq,
            k=len(product_id_seq),
        )

        expected = tuple(chain(
            repeat(None, 3),
            (product_seq[0],),
            repeat(None, 2),
            (product_seq[1],),
            repeat(None, 3),
            (product_seq[2],),
            repeat(None, 4),
            (product_seq[3],),
        ))

        actual = get_products_from_json(file_obj)

        self.assertEqual(expected, actual)
