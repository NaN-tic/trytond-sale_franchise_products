# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from collections import defaultdict
from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.i18n import gettext
from trytond.exceptions import UserError
import logging


__all__ = ['CreateSuggestionsStart', 'CreateSuggestions', 'Sale']


class CreateSuggestionsStart(ModelView):
    'Create Suggestions Start'
    __name__ = 'sale.create_suggestions.start'
    sale_type = fields.Many2One('sale.type', 'Sale Type', required=True)
    date = fields.Date('Date', required=True)
    notes = fields.Text('Notes')
    franchises = fields.One2Many('sale.franchise', None, 'Franchises')

    @staticmethod
    def default_date():
        pool = Pool()
        Date = pool.get('ir.date')
        return Date.today()

    @fields.depends('sale_type', 'notes')
    def on_change_sale_type(self):
        if self.sale_type and not self.notes:
            self.notes = self.sale_type.notes

    @fields.depends('sale_type')
    def on_change_with_franchises(self, name=None):
        if not self.sale_type:
            return []
        pool = Pool()
        Product = pool.get('product.product')
        products = Product.search([
            ('template.salable', '=', True),
            ('template.types', '=', self.sale_type.id),
        ])
        return [
            type_franchise.franchise.id
            for product in products
            for type_franchise in product.template.type_franchises
            if type_franchise.type == self.sale_type
        ]


class CreateSuggestions(Wizard):
    'Create Suggestions'
    __name__ = 'sale.create_suggestions'
    _logger = logging.getLogger(__name__)

    start = StateView(
        'sale.create_suggestions.start',
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

        if not franchise.company_party:
            raise UserError(gettext(
                'sale_franchise_products.msg_missing_franchise_company',
                franchise=franchise.rec_name))

        values = Sale.default_get(Sale._fields.keys(), with_rec_name=False)
        sale = Sale(**values)
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
            getattr(sale, method)()

        lines = []
        uom2products = {}
        product2lines = {}
        for product in products:
            line = SaleLine()
            line.sale = sale
            for field in SaleLine.product.on_change:
                if not hasattr(sale, field):
                    setattr(sale, field, None)
            line.type = 'line'
            line.quantity = 0.0
            line.product = product
            line.unit = product.sale_uom.id
            uom2products.setdefault(line.unit.id, []).append(product)
            product2lines.setdefault(product.id, []).append(line)
            line.on_change_product()
            lines.append(line)
        for uom_id, products in uom2products.items():
            with Transaction().set_context(
                    currency=(
                        sale.currency.id
                        if getattr(sale, 'currency', None)
                        else sale.default_currency()),
                    customer=sale.party.id,
                    sale_date=sale.sale_date,
                    uom=uom_id,
                    price_list=(
                        sale.price_list.id
                        if sale.price_list else None)):
                product_prices = Product.get_cost_sale_price_and_pvp(
                    products, 0)
            for product_id, list_price in product_prices.items():

                for line in product2lines[product_id]:
                    line.cost_price = list_price[0]
                    line.gross_unit_price = list_price[1]
                    line.unit_price = list_price[1]
                    line.public_price = list_price[2]
        sale.lines = lines
        return sale

    def get_franchises(self):
        pool = Pool()
        Product = pool.get('product.product')
        products = Product.search(self._get_products_domain())
        franchises = defaultdict(list)
        for product in products:
            for type_franchise in product.template.type_franchises:
                if type_franchise.type != self.start.sale_type or \
                        type_franchise.franchise not in \
                        self.start.franchises:
                    continue
                franchises[type_franchise.franchise].append(product)
        return franchises

    def do_result(self, action):
        pool = Pool()
        Sale = pool.get('sale.sale')

        self._logger.info("Get franchises")
        franchises = self.get_franchises()
        self._logger.info("Get sales...")
        sales = [self.get_sale(f, p) for f, p in franchises.items()]
        self._logger.info("Saving sales...")
        suggestions = Sale.create([s._save_values for s in sales])
        self._logger.info("Sales Created")
        data = {'res_id': [s.id for s in suggestions]}
        if len(suggestions) == 1:
            action['views'].reverse()
        return action, data


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    type = fields.Many2One('sale.type', 'Type',
        states={
        'readonly': Eval('state') != 'draft',
        },
        depends=['state'])

    @fields.depends('type', 'notes')
    def on_change_type(self):
        if self.type and not self.notes:
            self.comment = self.type.notes

    @fields.depends('franchise', methods=['on_change_party'])
    def on_change_franchise(self):
        super(Sale, self).on_change_franchise()
        if self.franchise and self.franchise.company_party:
            self.party = self.franchise.company_party
            self.on_change_party()
            self.shipment_address = self.franchise.address
