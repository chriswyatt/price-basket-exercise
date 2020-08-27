from itertools import repeat

import factory
from faker import Factory as FakerFactory

from product import Product
from special_offer import (
    FractionOfPrice,
    FractionOfPriceProduct,
    FractionOfPricePerQuantityProduct,
    FractionOfPricePerQuantityShared,
    FractionOfPricePerQuantity,
)


fake = FakerFactory.create('en-GB')


def create_sparse_list(items):
    """
    Create a list, indexed by an integer (key) for faster lookup.
    E.g.: {1: foo, 2: bar, 4: baz} => [None, foo, bar, None, baz]
    """
    seq = []
    for key, value in sorted(items):
        seq.extend(repeat(None, key - len(seq)))
        seq.append(value)

    return seq


class ProductFactory(factory.StubFactory):

    product_id = factory.Sequence((1).__add__)

    @factory.lazy_attribute_sequence
    def name(self, n):
        return f"{fake.word().title()}{n}"

    price = factory.Faker(
        'pydecimal',
        left_digits=3,
        right_digits=2,
        positive=True,
    )

    quantity = factory.Faker('random_int', min=1, max=9)

    @staticmethod
    def stub_to_dict(stub):
        return {
            "product_id": stub.product_id,
            "name": stub.name,
            "price": str(stub.price),
        }

    @staticmethod
    def stub_to_obj(stub):
        return Product(
            product_id=stub.product_id,
            name=stub.name,
            price=stub.price,
        )


class SpecialOfferFactory(factory.StubFactory):

    @staticmethod
    def stub_to_dict(stub):
        raise NotImplementedError

    @staticmethod
    def stub_to_obj(stub, products):
        raise NotImplementedError


class FractionOfPriceFactory(SpecialOfferFactory):
    discounted_product = factory.SubFactory(ProductFactory)

    fraction_of_price = factory.Faker(
        'pydecimal',
        left_digits=3,
        right_digits=2,
        positive=True,
    )

    @staticmethod
    def stub_to_dict(stub):
        return {
            "special_offer_type": "fraction_of_price",
            "product_matrix": [
                [stub.discounted_product.product_id],
                [str(stub.fraction_of_price)],
            ],
        }

    @staticmethod
    def stub_to_obj(stub, products):
        return FractionOfPrice(
            products,
            (
                FractionOfPriceProduct(
                    fraction_of_price=stub.fraction_of_price,
                ),
            ),
        )


class FractionOfPricePerQuantityFactory(SpecialOfferFactory):
    trigger_product = factory.SubFactory(ProductFactory)
    discounted_product = factory.SubFactory(ProductFactory)

    trigger_product_quantity = factory.Faker(
        'random_int',
        min=1,
        max=8,
    )

    discounted_product_quantity = factory.Faker(
        'random_int',
        min=1,
        max=8,
    )

    fraction_of_price = factory.Faker(
        'pydecimal',
        left_digits=3,
        right_digits=2,
        positive=True,
    )

    @staticmethod
    def stub_to_dict(stub):
        return {
            "special_offer_type": "fraction_of_price_per_quantity",
            "product_matrix": [
                [
                    stub.trigger_product.product_id,
                    stub.discounted_product.product_id,
                ],
                [
                    stub.trigger_product_quantity,
                    stub.discounted_product_quantity,
                ],
            ],
            "shared_values": [
                str(stub.fraction_of_price),
            ],
        }

    @staticmethod
    def stub_to_obj(stub, products):
        return FractionOfPricePerQuantity(
            products,
            (
                FractionOfPricePerQuantityProduct(
                    quantity=stub.trigger_product_quantity,
                ),
                FractionOfPricePerQuantityProduct(
                    quantity=stub.discounted_product_quantity,
                ),
            ),
            FractionOfPricePerQuantityShared(
                fraction_of_price=stub.fraction_of_price,
            ),
        )
