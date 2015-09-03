# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.wizard import Wizard, StateView, StateAction, Button

__all__ = ['SaleType', 'SaleTypeFranchise', 'TypeFranchiseTemplate',
    'Template', 'Franchise', 'CreateFranchisesStart', 'CreateFranchises']
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
    templates = fields.Function(fields.Many2Many('product.template', None,
            None, 'Product Templates'),
        'get_templates')
    types = fields.Many2Many('sale.type-sale.franchise', 'franchise',
        'type', 'Sale Types')

    def get_templates(self, name):
        pool = Pool()
        Template = pool.get('product.template')
        return [x.id for x in Template.search([
                    ('franchises', '=', self.id),
                    ('types', 'in', [x.id for x in self.types]),
                    ])]


class SaleTypeFranchise(ModelSQL, ModelView):
    'SaleType - Franchise'
    __name__ = 'sale.type-sale.franchise'
    type = fields.Many2One('sale.type', 'Type', required=True, select=True,
        ondelete='CASCADE')
    franchise = fields.Many2One('sale.franchise', 'Franchise', required=True,
        select=True, ondelete='CASCADE',
        domain=[
            ('types', '=', Eval('type')),
            ],
        depends=['type'])
    templates = fields.Many2Many('sale.type-sale.franchise-product.template',
        'type_franchise', 'template', 'Templates')

    @classmethod
    def __setup__(cls):
        super(SaleTypeFranchise, cls).__setup__()
        cls._sql_constraints += [
            ('invoice_type_franchise', 'UNIQUE(type, franchise)',
                'The Type and Franchise must be unique.'),
            ]


class TypeFranchiseTemplate(ModelSQL, ModelView):
    'Type per Franchise - Type'
    __name__ = 'sale.type-sale.franchise-product.template'
    type_franchise = fields.Many2One('sale.type-sale.franchise',
        'Type per Franchise', required=True, select=True, ondelete='CASCADE')
    template = fields.Many2One('product.template', 'Template', required=True,
        select=True, ondelete='CASCADE')


class Template:
    __name__ = 'product.template'
    type_franchises = fields.Many2Many(
        'sale.type-sale.franchise-product.template', 'template',
        'type_franchise', 'Type per Franchise')
    franchises = fields.Function(fields.Many2Many(
            'sale.franchise', None, None, 'Franchises',
            states={
                'invisible': ~Eval('salable', False),
                },
            depends=['salable']),
        'get_franchises', searcher='search_franchises')
    types = fields.Function(fields.Many2Many('sale.type', None, None,
            'Sale Types',
            states={
                'invisible': ~Eval('salable', False),
                },
            depends=['salable']),
        'get_types', searcher='search_types')

    def get_franchises(self, name):
        return list(set(r.franchise.id for r in self.type_franchises))

    @classmethod
    def search_franchises(cls, name, clause):
        return [tuple(('type_franchises.franchise',)) + tuple(clause[1:])]

    def get_types(self, name):
        return list(set(r.type.id for r in self.type_franchises))

    @classmethod
    def search_types(cls, name, clause):
        return [tuple(('type_franchises.type',)) + tuple(clause[1:])]


class CreateFranchisesStart(ModelView):
    'Create Franchises Start'
    __name__ = 'sale_type.create_franchises.start'
    sale_type = fields.Many2One('sale.type', 'Sale Type', required=True)


class CreateFranchises(Wizard):
    'Create Franchises'
    __name__ = 'sale_type.create_franchises'
    start = StateView('sale_type.create_franchises.start',
        'sale_franchise_products.create_franchises_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create', 'result', 'tryton-ok', default=True),
            ])
    result = StateAction('sale_franchise_products.act_sale_type_franchise')

    def _get_relation_domain(self):
        return [('type', '=', self.start.sale_type.id)]

    def _get_franchises_domain(self):
        return []

    def get_relation(self, franchise):
        pool = Pool()
        Relation = pool.get('sale.type-sale.franchise')
        relation = Relation()
        relation.type = self.start.sale_type
        relation.franchise = franchise
        return relation

    def do_result(self, action):
        pool = Pool()
        Franchise = pool.get('sale.franchise')
        Relation = pool.get('sale.type-sale.franchise')

        franchises = set(Franchise.search(self._get_franchises_domain()))
        existing = set((x.franchise for x in Relation.search(
                self._get_relation_domain())))
        to_create = []
        for missing in franchises - existing:
            to_create.append(self.get_relation(missing)._save_values)

        Relation.create(to_create)
        created = Relation.search([
                ('type', '=', self.start.sale_type.id),
                ])
        data = {'res_id': [s.id for s in created]}
        if len(franchises) == 1:
            action['views'].reverse()
        return action, data
