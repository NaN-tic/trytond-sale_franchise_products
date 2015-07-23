# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['SaleType', 'SaleTypeFranchise', 'TemplateFranchise', 'Template',
    'Franchise']
__metaclass__ = PoolMeta


class SaleType(ModelSQL, ModelView):
    'Sale Type'
    __name__ = 'sale.type'
    name = fields.Char('Name', required=True)
    notes = fields.Text('Notes')
    accepts_new_products = fields.Boolean('Accepts new products',
        help=('If left blank it will not be possible to create new lines on '
            'sales'))
    franchises = fields.Many2Many('sale.type-sale.franchise', 'type',
        'franchise', 'Franchises')


class Franchise:
    __name__ = 'sale.franchise'
    templates = fields.Many2Many('sale.franchise-product.template',
        'franchise', 'template', 'Product Templates', readonly=True)
    types = fields.Many2Many('sale.type-sale.franchise', 'franchise',
        'type', 'Sale Types')


class SaleTypeFranchise(ModelSQL):
    'SaleType - Franchise'
    __name__ = 'sale.type-sale.franchise'
    type = fields.Many2One('sale.type', 'Type', required=True, select=True,
        ondelete='CASCADE')
    franchise = fields.Many2One('sale.franchise', 'Franchise', required=True,
        select=True, ondelete='CASCADE')


class TemplateFranchise(ModelSQL, ModelView):
    'Product Template - Franchise'
    __name__ = 'sale.franchise-product.template'
    franchise = fields.Many2One('sale.franchise', 'Franchise', required=True,
        select=True, ondelete='CASCADE')
    template = fields.Many2One('product.template', 'Template', required=True,
        select=True, ondelete='CASCADE')


class Template:
    __name__ = 'product.template'
    franchises = fields.Many2Many('sale.franchise-product.template',
        'template', 'franchise', 'Franchises', readonly=True,
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
        return list(set(t.id for f in self.franchises for t in f.types))

    @classmethod
    def search_types(cls, name, clause):
        return [tuple(('franchises.types',)) + tuple(clause[1:])]
