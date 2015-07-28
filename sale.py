# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from collections import defaultdict
from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
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
        Sale = pool.get('sale.sale')
        SaleLine = pool.get('sale.line')

        sale = Sale()
        sale.party = franchise.company.party
        sale.franchise = franchise
        sale.type = self.start.sale_type
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
        for product in products:
            line = SaleLine()
            for field in SaleLine.product.on_change:
                if not hasattr(sale, field):
                    setattr(sale, field, None)
            line.type = 'line'
            line.quantity = 0.0
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
        if self.franchise:
            party = self.franchise.company.party
            changes['party'] = party.id
            changes['party.rec_name'] = party.rec_name
            self.party = party
            changes.update(self.on_change_party())
        return changes
