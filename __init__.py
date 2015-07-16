# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .product import *
from .sale import *


def register():
    Pool.register(
        SaleType,
        Category,
        CategoryType,
        Template,
        TemplateFranchise,
        CreateSuggestionsStart,
        Sale,
        module='sale_franchise_products', type_='model')
    Pool.register(
        CreateSuggestions,
        module='sale_franchise_products', type_='wizard')
