# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from collections import defaultdict
from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.wizard import Wizard, StateView, StateAction, Button

__all__ = ['CreateSuggestionsStart', 'CreateSuggestions', 'Sale']


class CreateSuggestionsStart(ModelView):
    'Create Suggestions Start'
    __name__ = 'sale.create_suggestions.start'
    sale_type = fields.Many2One('sale.type', 'Sale Type', required=True)


class CreateSuggestions(Wizard):
    'Create Suggestions'
    __name__ = 'sale.create_suggestions'
    start = StateView('sale.create_suggestions.start',
        'sale_franchise_products.create_suggestions_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create', 'result', 'tryton-ok', default=True),
            ])
    result = StateAction('sale.act_sale_form')

    def _get_products_domain(self):
        return [
            ('template.salable', '=', True),
            ('template.category.types', '=', self.start.sale_type.id),
            ]

    def get_sale(self, franchise, products):
        pool = Pool()
        Sale = pool.get('sale.sale')
        SaleLine = pool.get('sale.line')

        sale = Sale()
        sale.party = franchise.company.party
        sale.franchise = franchise
        sale.type = self.start.sale_type
        for name in ('party', 'franchise'):
            for field in getattr(Sale, name).on_change:
                if not hasattr(sale, field):
                    setattr(sale, field, None)
            method = 'on_change_%s' % name
            for k, v in getattr(sale, method)().iteritems():
                setattr(sale, k, v)

        lines = []
        for product in products:
            line = SaleLine()
            for field in SaleLine.product.on_change:
                if not hasattr(sale, field):
                    setattr(sale, field, None)
            line.type = 'line'
            line.quantity = 1.0
            line.product = product
            for k, v in line.on_change_product().iteritems():
                setattr(line, k, v)
            lines.append(line)
        sale.lines = lines
        return sale

    def do_result(self, action):
        pool = Pool()
        Sale = pool.get('sale.sale')
        Product = pool.get('product.product')
        products = Product.search(self._get_products_domain())

        franchises = defaultdict(list)
        for product in products:
            for franchise in product.template.franchises:
                franchises[franchise].append(product)

        sales = [self.get_sale(f, p) for f, p in franchises.iteritems()]
        suggestions = Sale.create([s._save_values for s in sales])
        data = {'res_id': [s.id for s in suggestions]}
        if len(suggestions) == 1:
            action['views'].reverse()
        return action, data


class Sale:
    __name__ = 'sale.sale'
    __metaclass__ = PoolMeta
    type = fields.Many2One('sale.type', 'Type')
