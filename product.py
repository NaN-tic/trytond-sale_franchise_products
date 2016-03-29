# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['SaleType', 'SaleTypeFranchise', 'TypeFranchiseTemplate',
    'Template', 'Franchise', 'Product']
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


class Product:
    __name__ = 'product.product'

    @classmethod
    def get_cost_sale_price_and_pvp(cls, products, quantity=0):
        pool = Pool()
        PriceList = pool.get('product.price_list')
        Party = pool.get('party.party')
        Uom = pool.get('product.uom')

        prices = cls.get_unit_sale_price(products, quantity=quantity)
        if (Transaction().context.get('price_list')
                and Transaction().context.get('customer')):
            price_list = PriceList(Transaction().context['price_list'])
            customer = Party(Transaction().context['customer'])
            context_uom = None
            if Transaction().context.get('uom'):
                context_uom = Uom(Transaction().context['uom'])
            for product in products:
                uom = context_uom or product.default_uom
                prices[product.id] = price_list.compute_all(customer, product,
                    prices[product.id], quantity, uom)
        return prices

    @staticmethod
    def get_unit_sale_price(products, quantity=0):
        '''
        Return the sale price for products and quantity.
        It uses if exists from the context:
            uom: the unit of measure
            currency: the currency id for the returned price
        '''
        pool = Pool()
        Uom = pool.get('product.uom')
        User = pool.get('res.user')
        Currency = pool.get('currency.currency')
        Date = pool.get('ir.date')

        today = Date.today()
        prices = {}

        uom = None
        if Transaction().context.get('uom'):
            uom = Uom(Transaction().context.get('uom'))

        currency = None
        if Transaction().context.get('currency'):
            currency = Currency(Transaction().context.get('currency'))

        user = User(Transaction().user)

        for product in products:
            prices[product.id] = product.list_price
            if uom:
                prices[product.id] = Uom.compute_price(
                    product.default_uom, prices[product.id], uom)
            if currency and user.company:
                if user.company.currency != currency:
                    date = Transaction().context.get('sale_date') or today
                    with Transaction().set_context(date=date):
                        prices[product.id] = Currency.compute(
                            user.company.currency, prices[product.id],
                            currency, round=False)
        return prices
