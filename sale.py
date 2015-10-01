# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from collections import defaultdict
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, StateAction, Button

__all__ = ['CreateSuggestionsStart', 'CreateSuggestions', 'Sale']


class CreateSuggestionsStart(ModelView):
    'Create Suggestions Start'
    __name__ = 'sale.create_suggestions.start'
    sale_type = fields.Many2One('sale.type', 'Sale Type', required=True)
    date = fields.Date('Date', required=True)
    notes = fields.Text('Notes')

    @staticmethod
    def default_date():
        pool = Pool()
        Date = pool.get('ir.date')
        return Date.today()

    @fields.depends('sale_type', 'notes')
    def on_change_sale_type(self):
        changes = {}
        if self.sale_type and not self.notes:
            changes['notes'] = self.sale_type.notes
        return changes


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
            ('template.types', '=', self.start.sale_type.id),
            ]

    def get_sale(self, franchise, products):
        pool = Pool()
        Product = pool.get('product.product')
        Sale = pool.get('sale.sale')
        SaleLine = pool.get('sale.line')

        sale = Sale()
        sale.party = franchise.company_party
        sale.franchise = franchise
        sale.type = self.start.sale_type
        sale.price_list = franchise.price_list
        sale.sale_date = self.start.date
        sale.comment = self.start.notes
        for name in ('party', 'franchise'):
            for field in getattr(Sale, name).on_change:
                if not hasattr(sale, field):
                    setattr(sale, field, None)
            method = 'on_change_%s' % name
            for k, v in getattr(sale, method)().iteritems():
                setattr(sale, k, v)

        lines = []
        uom2products = {}
        product2lines = {}
        for product in products:
            line = SaleLine()
            for field in SaleLine.product.on_change:
                if not hasattr(sale, field):
                    setattr(sale, field, None)
            line.type = 'line'
            line.quantity = 0.0
            line.product = product
            line.unit = product.sale_uom.id
            uom2products.setdefault(line.unit.id, []).append(product)
            product2lines.setdefault(product.id, []).append(line)
            for k, v in line.on_change_product().iteritems():
                setattr(line, k, v)
            lines.append(line)
        for uom_id, products in uom2products.iteritems():
            with Transaction().set_context(
                    currency=(sale.currency.id
                        if getattr(sale, 'currency', None)
                        else sale.default_currency()),
                    customer=sale.party.id,
                    sale_date=sale.sale_date,
                    uom=uom_id,
                    price_list=(sale.price_list.id
                        if sale.price_list else None)):
                product_prices = Product.get_sale_price(products, 0)
            for product_id, list_price in product_prices.iteritems():
                for line in product2lines[product_id]:
                    line.gross_unit_price = list_price
                    line.unit_price = list_price
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
                if self.start.sale_type not in franchise.types:
                    continue
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
    type = fields.Many2One('sale.type', 'Type',
        states={
            'readonly': Eval('state') != 'draft',
            },
        depends=['state'])

    @fields.depends('type', 'notes')
    def on_change_type(self):
        changes = {}
        if self.type and not self.notes:
            changes['comment'] = self.type.notes
        return changes

    @fields.depends('franchise', methods=['party'])
    def on_change_franchise(self):
        changes = super(Sale, self).on_change_franchise()
        if self.franchise and self.franchise.company_party:
            party = self.franchise.company_party
            changes['party'] = party.id
            changes['party.rec_name'] = party.rec_name
            self.party = party
            changes.update(self.on_change_party())
        return changes
