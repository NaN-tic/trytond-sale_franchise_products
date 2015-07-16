# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['SaleType', 'Category', 'CategoryType', 'TemplateFranchise',
    'Template']
__metaclass__ = PoolMeta


class SaleType(ModelSQL, ModelView):
    'Sale Type'
    __name__ = 'sale.type'
    name = fields.Char('Name', required=True)
    categories = fields.Many2Many('sale.type-product.category', 'type',
        'category', 'Categories')


class Category:
    __name__ = 'product.category'
    types = fields.Many2Many('sale.type-product.category', 'category',
        'type', 'Type')


class CategoryType(ModelSQL):
    'Product Template - Franchise'
    __name__ = 'sale.type-product.category'
    type = fields.Many2One('sale.type', 'Type', required=True, select=True)
    category = fields.Many2One('product.category', 'Category', required=True,
        select=True)


class TemplateFranchise(ModelSQL):
    'Product Template - Franchise'
    __name__ = 'sale.franchise-product.template'
    template = fields.Many2One('product.template', 'Template', required=True,
        select=True)
    franchise = fields.Many2One('sale.franchise', 'Franchise', required=True,
        select=True)


class Template:
    __name__ = 'product.template'
    franchises = fields.Many2Many('sale.franchise-product.template',
        'template', 'franchise', 'Franchises',
        states={
            'invisible': ~Eval('salable', False),
            },
        depends=['salable'])
