# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['SaleType', 'Category', 'CategoryType', 'TemplateFranchise',
    'Template', 'Franchise']
__metaclass__ = PoolMeta


class SaleType(ModelSQL, ModelView):
    'Sale Type'
    __name__ = 'sale.type'
    name = fields.Char('Name', required=True)
    notes = fields.Text('Notes')
    accepts_new_products = fields.Boolean('Accepts new products',
        help=('If left blank it will not be possible to create new lines on '
            'sales'))
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
    types = fields.Function(fields.Many2Many('sale.type', None, None,
            'Sale Types',
            states={
                'invisible': ~Eval('salable', False),
                },
            depends=['salable']),
        'get_types', searcher='search_types')

    def get_types(self, name):
        if self.category:
            return [x.id for x in self.category.types]
        return []

    @classmethod
    def search_types(cls, name, clause):
        return [tuple(('category.types',)) + tuple(clause[1:])]


class Franchise:
    __name__ = 'sale.franchise'
    templates = fields.Many2Many('sale.franchise-product.template',
        'franchise', 'template', 'Product Templates')
    categories = fields.Function(fields.Many2Many('product.category', None,
            None, 'Categories'),
        'get_categories', searcher='search_categories')
    types = fields.Function(fields.Many2Many('sale.type', None, None,
            'Sale Types'),
        'get_types', searcher='search_types')

    def get_categories(self, name):
        return list(set([t.id for t in self.templates]))

    @classmethod
    def search_categories(cls, name, clause):
        return [tuple(('templates.category',)) + tuple(clause[1:])]

    def get_types(self, name):
        return list(set([t.id for c in self.categories for t in c.types]))

    @classmethod
    def search_types(cls, name, clause):
        return [tuple(('templates.category.types',)) + tuple(clause[1:])]
