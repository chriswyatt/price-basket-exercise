import io
import json
import unittest
from collections import Counter
from decimal import Decimal
from functools import partial
from itertools import chain, repeat
from operator import is_not, attrgetter, itemgetter
from random import shuffle

import factory
from parameterized import parameterized

from factories import (
    FractionOfPriceFactory,
    FractionOfPricePerQuantityFactory,
    ProductFactory,
    create_sparse_list,
    fake,
)
from product import Product
from special_offer import (
    FractionOfPrice,
    FractionOfPriceProduct,
    FractionOfPricePerQuantity,
    FractionOfPricePerQuantityProduct,
    FractionOfPricePerQuantityShared,
    SpecialOfferType,
    get_special_offers_from_json,
)


class TestFractionOfPriceFromJson(unittest.TestCase):

    def setUp(self):
        product_stub_seq = ProductFactory.stub_batch(
            fake.random_int(min=2, max=8),
        )

        self.product_by_id = create_sparse_list(
            (
                s.product_id,
                Product(
                    product_id=s.product_id,
                    name=s.name,
                    price=s.price,
                ),
            )
            for s in product_stub_seq)

    def test_one_special_offer(self):
        discounted_product = fake.random_element(tuple(filter(
            partial(is_not, None),
            self.product_by_id,
        )))

        fraction_of_price_str = f"0.{fake.random_int(min=1, max=99):02d}"
        fraction_of_price = Decimal(fraction_of_price_str)

        with io.StringIO() as file_obj:
            special_offer_obj = {
                "special_offer_type": "fraction_of_price",
                "product_matrix": [
                    [discounted_product.product_id],
                    [fraction_of_price_str],
                ],
            }
            json.dump([special_offer_obj], file_obj)
            file_obj.seek(0)

            special_offer, = get_special_offers_from_json(
                file_obj,
                self.product_by_id,
            )

        self.assertEqual(
            discounted_product,
            special_offer.discounted_product,
        )
        self.assertEqual(
            fraction_of_price,
            special_offer.fraction_of_price,
        )


class TestFractionOfPricePerQuantityFromJson(unittest.TestCase):

    def setUp(self):
        product_stub_seq = ProductFactory.stub_batch(
            fake.random_int(min=2, max=8),
        )

        self.product_by_id = create_sparse_list(
            (
                s.product_id,
                Product(
                    product_id=s.product_id,
                    name=s.name,
                    price=s.price,
                ),
            )
            for s in product_stub_seq)

    def test_one_special_offer(self):
        trigger_product = fake.random_element(tuple(filter(
            partial(is_not, None),
            self.product_by_id,
        )))

        trigger_product_quota = fake.random_int(min=1, max=4)

        discounted_product = fake.random_element(tuple(filter(
            partial(is_not, None),
            self.product_by_id,
        )))

        discounted_product_quota = fake.random_int(min=1, max=4)

        fraction_of_price_str = f"0.{fake.random_int(min=1, max=99):02d}"
        fraction_of_price = Decimal(fraction_of_price_str)

        with io.StringIO() as file_obj:
            special_offer_obj = {
                "special_offer_type": "fraction_of_price_per_quantity",
                "product_matrix": [
                    [
                        trigger_product.product_id,
                        discounted_product.product_id,
                    ],
                    [
                        trigger_product_quota,
                        discounted_product_quota,
                    ],
                ],
                "shared_values": [fraction_of_price_str]
            }
            json.dump([special_offer_obj], file_obj)
            file_obj.seek(0)

            special_offer, = get_special_offers_from_json(
                file_obj,
                self.product_by_id,
            )

        self.assertEqual(trigger_product, special_offer.trigger_product)

        self.assertEqual(
            trigger_product_quota,
            special_offer.trigger_product_quantity,
        )

        self.assertEqual(
            discounted_product,
            special_offer.discounted_product,
        )

        self.assertEqual(
            discounted_product_quota,
            special_offer.discounted_product_quantity,
        )

        self.assertEqual(
            fraction_of_price,
            special_offer.fraction_of_price,
        )


class TestFractionOfPriceGetDiscount(unittest.TestCase):

    def setUp(self):
        product_stub_seq = ProductFactory.stub_batch(
            fake.random_int(min=2, max=8),
        )

        self.quantity_by_product = Counter(
            chain.from_iterable(
                repeat(
                    Product(s.product_id, s.name, s.price),
                    s.quantity,
                )
                for s in product_stub_seq))

    def test_success(self):
        (discounted_product,
         discounted_product_quantity) = fake.random_element(
            self.quantity_by_product.items(),
        )

        fraction_of_price_str = f"0.{fake.random_int(min=1, max=99):02d}"
        fraction_of_price = Decimal(fraction_of_price_str)
        product_seq = (discounted_product,)
        value_matrix = (
            FractionOfPriceProduct(
                fraction_of_price=fraction_of_price,
            ),
        )
        special_offer = FractionOfPrice(product_seq, value_matrix)

        actual = special_offer.get_discount(self.quantity_by_product)

        expected_value = (
            discounted_product.price *
            discounted_product_quantity *
            (Decimal('1.00') - fraction_of_price))

        self.assertEqual(expected_value, actual.value)


class TestFractionOfPricePerQuantityGetDiscount(unittest.TestCase):

    @parameterized.expand([
        # 1 discounted product for 1 trigger product
        (1, 1, 1, 1, 1),

        # 1 discounted product for 1 trigger product (twice)
        (1, 2, 1, 2, 2),

        # 2 discounted products for 1 trigger product (twice)
        (1, 2, 2, 4, 4),

        # 2 discounted products for 1 trigger product (twice); however 3 discountable products were requested,
        # even though another product could have been discounted
        (1, 2, 2, 3, 3),

        # 2 discounted products for 1 trigger product (twice); however 5 products were requested, so
        # one discountable product was not discounted
        (1, 2, 2, 5, 4),

        # The same thing with bigger numbers
        (2, 8, 4, 16, 16),
        (2, 8, 4, 12, 12),
        (2, 8, 4, 20, 16),

        # No trigger products or discountable products requested
        (2, 0, 2, 0, 0),

        # Discountable products requested, but no trigger products
        (2, 0, 2, 2, 0),

        # Not quite enough trigger products requested
        (4, 3, 1, 1, 0),

        # Not quite enough trigger products requested for second trigger
        (4, 7, 1, 1, 1),

        # Bad data. Not expected in actual usage.
        (0, 0, 0, 0, 0),
    ])
    def test_success(
            self,
            trigger_product_quota,
            trigger_product_quantity,
            discountable_product_quota,
            discountable_product_quantity,
            expected_num_discounts,
    ):
        quantity_seq = (
            fake.random_int(min=1, max=8),
            trigger_product_quantity,
            discountable_product_quantity,
            fake.random_int(min=1, max=8),
        )

        product_stub_seq = ProductFactory.stub_batch(
            4,
            quantity=factory.Iterator(quantity_seq,  cycle=False),
        )
        product_seq = tuple(
            Product(s.product_id, s.name, s.price)
            for s in product_stub_seq)

        quantity_by_product = Counter(
            chain.from_iterable(
                repeat(p, s.quantity)
                for p, s in zip(product_seq, product_stub_seq)))

        trigger_product = product_seq[1]
        discounted_product = product_seq[2]

        fraction_of_price_str = f"0.{fake.random_int(min=1, max=99):02d}"
        fraction_of_price = Decimal(fraction_of_price_str)

        product_seq = (trigger_product, discounted_product)

        value_matrix = (
            FractionOfPricePerQuantityProduct(
                quantity=trigger_product_quota,
            ),
            FractionOfPricePerQuantityProduct(
                quantity=discountable_product_quota,
            ),
        )

        shared_values = FractionOfPricePerQuantityShared(
            fraction_of_price=fraction_of_price,
        )

        special_offer = FractionOfPricePerQuantity(
            product_seq,
            value_matrix,
            shared_values,
        )

        actual = special_offer.get_discount(quantity_by_product)

        expected_value = (
            expected_num_discounts *
            discounted_product.price *
            (Decimal('1.00') - fraction_of_price))

        self.assertEqual(expected_value, actual.value)


class TestFromJson(unittest.TestCase):

    def setUp(self):
        self.product_stub_seq = ProductFactory.stub_batch(8)

        self.product_seq = tuple(map(
            ProductFactory.stub_to_obj,
            self.product_stub_seq,
        ))

        class LocalFractionOfPriceFactory(
            FractionOfPriceFactory,
        ):
            discounted_product = factory.Faker(
                'random_element',
                elements=self.product_seq,
            )

        class LocalFractionOfPricePerQuantityFactory(
            FractionOfPricePerQuantityFactory,
        ):
            trigger_product = factory.Faker(
                'random_element',
                elements=self.product_seq,
            )
            discounted_product = factory.Faker(
                'random_element',
                elements=self.product_seq,
            )

        self.special_offer_factory_cls_by_type = {
            SpecialOfferType.FRACTION_OF_PRICE:
                LocalFractionOfPriceFactory,
            SpecialOfferType.FRACTION_OF_PRICE_PER_QUANTITY:
                LocalFractionOfPricePerQuantityFactory,
        }

        self.special_offer_stub_seq_by_type = {
            t: f.stub_batch(4)
            for t, f in self.special_offer_factory_cls_by_type.items()}

        self.special_offer_dict_seq_by_type = {
            t: map(
                f.stub_to_dict,
                self.special_offer_stub_seq_by_type[t],
            )
            for t, f in self.special_offer_factory_cls_by_type.items()}

        self.product_id_getter_by_special_offer_type = {
            SpecialOfferType.FRACTION_OF_PRICE:
                attrgetter(
                    "discounted_product.product_id",
                ),
            SpecialOfferType.FRACTION_OF_PRICE_PER_QUANTITY:
                attrgetter(
                    "trigger_product.product_id",
                    "discounted_product.product_id",
                ),
        }

    def test_many(self):
        data = [
            (t, s, d)
            for t in self.special_offer_factory_cls_by_type.keys()
            for s, d in zip(
                self.special_offer_stub_seq_by_type[t],
                self.special_offer_dict_seq_by_type[t],
            )]

        shuffle(data)

        product_by_id = create_sparse_list(
            ((p.product_id, p) for p in self.product_seq))

        with io.StringIO() as file_obj:
            special_offer_seq = list(map(itemgetter(2), data))
            json.dump(special_offer_seq, file_obj)
            file_obj.seek(0)

            special_offer_seq = tuple(get_special_offers_from_json(
                file_obj,
                product_by_id,
            ))

        self.assertEqual(
            tuple(map(itemgetter(0), data)),
            tuple(s.SPECIAL_OFFER_TYPE for s in special_offer_seq),
        )

        getter_dict = self.product_id_getter_by_special_offer_type

        self.assertEqual(
            tuple(
                (
                    t,
                    getter_dict[t](s),
                )
                for t, s, _ in data),
            tuple(
                (
                    s.SPECIAL_OFFER_TYPE,
                    getter_dict[s.SPECIAL_OFFER_TYPE](s),
                )
                for s in special_offer_seq),
        )

    def test_empty(self):
        with io.StringIO() as file_obj:
            json.dump([], file_obj)
            file_obj.seek(0)

            special_offer_seq = tuple(get_special_offers_from_json(
                file_obj,
                (),
            ))

        self.assertEqual((), special_offer_seq)
