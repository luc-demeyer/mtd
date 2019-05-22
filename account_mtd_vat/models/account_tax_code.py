# -*- coding = utf-8 -*-
import logging

from openerp import models, fields, api, _
from openerp.osv import fields, osv
from openerp.tools.translate import _


class mtd_account_tax_code(osv.osv):
    _inherit = "account.tax.code"

    def _sum_year(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        move_state = ('posted',)
        if context.get('state', 'all') == 'all':
            move_state = ('draft', 'posted',)
        if context.get('fiscalyear_id', False):
            if len(context['fiscalyear_id']) > 1:
                fiscalyear_id = context['fiscalyear_id']
            else:
                fiscalyear_id = [context['fiscalyear_id']]
        else:
            fiscalyear_id = self.pool.get('account.fiscalyear').finds(cr, uid, exception=False)

        vat = ''
        if 'vat' in context.keys() and context['vat'] != "":
            vat = False
            if context['vat'] == 'True':
                vat = True
        date_from = None
        date_to = None
        company_id = None
        if 'date_from' in context.keys():
            date_from = context['date_from']
        if 'date_to' in context.keys():
            date_to = context['date_to']
        if 'company_id' in context.keys():
            company_id = context['company_id']

        where = ''
        where_params = ()
        if fiscalyear_id:
            pids = []
            for fy in fiscalyear_id:
                pids += map(lambda x: str(x.id), self.pool.get('account.fiscalyear').browse(cr, uid, fy).period_ids)
            if pids:
                if vat == '':
                    where = ' AND line.date >= %s AND line.date <= %s AND move.state IN %s  AND line.company_id = %s'
                    where_params = (date_from, date_to, move_state, company_id)
                else:
                    where = ' AND line.date >= %s AND line.date <= %s AND move.state IN %s AND line.vat = %s  AND line.company_id = %s'
                    where_params = (date_from, date_to, move_state, vat, company_id)

        return self._sum(
            cr,
            uid,
            ids,
            name,
            args,
            context,
            where=where,
            where_params=where_params
        )

    def _sum(self, cr, uid, ids, name, args, context, where='', where_params=()):
        parent_ids = tuple(self.search(cr, uid, [('parent_id', 'child_of', ids)]))
        if context.get('based_on', 'invoices') == 'payments':
            cr.execute('SELECT line.tax_code_id, sum(line.tax_amount) \
                    FROM account_move_line AS line, \
                        account_move AS move \
                        LEFT JOIN account_invoice invoice ON \
                            (invoice.move_id = move.id) \
                    WHERE line.tax_code_id IN %s '+where+' \
                        AND move.id = line.move_id \
                        AND ((invoice.state = \'paid\') \
                        OR (invoice.id IS NULL)) \
                        GROUP BY line.tax_code_id',
                        (parent_ids,) + where_params)
        else:
            cr.execute('SELECT line.tax_code_id, sum(line.tax_amount) \
                    FROM account_move_line AS line, \
                    account_move AS move \
                    WHERE line.tax_code_id IN %s '+where+' \
                    AND move.id = line.move_id \
                    GROUP BY line.tax_code_id',
                       (parent_ids,) + where_params)
        res = dict(cr.fetchall())
        obj_precision = self.pool.get('decimal.precision')
        res2 = {}
        for record in self.browse(cr, uid, ids, context=context):
            def _rec_get(record):
                amount = res.get(record.id) or 0.0
                for rec in record.child_ids:
                    amount += _rec_get(rec) * rec.sign
                return amount
            res2[record.id] = round(_rec_get(record), obj_precision.precision_get(cr, uid, 'Account'))

        if 'calculate_vat' in context.keys():
            if context.get('based_on', 'invoices') == 'payments':
                cr.execute('SELECT line.tax_code_id, sum(line.tax_amount) as amount, \
                        sum(line.mtd_tax_amount) as mtd_amount FROM account_move_line AS line, \
                            account_move AS move \
                            LEFT JOIN account_invoice invoice ON \
                                (invoice.move_id = move.id) \
                        WHERE line.tax_code_id IN %s ' + where + ' \
                            AND move.id = line.move_id \
                            AND ((invoice.state = \'paid\') \
                                OR (invoice.id IS NULL)) \
                                GROUP BY line.tax_code_id',
                           (parent_ids,) + where_params)
            else:
                cr.execute('SELECT line.tax_code_id, sum(line.tax_amount), \
                    sum(mtd_tax_amount) as mtd_sum  \
                    FROM account_move_line AS line, \
                    account_move as move \
                    WHERE line.tax_code_id IN %s '+where+' \
                    AND move.id = line.move_id \
                    GROUP BY line.tax_code_id',
                    (parent_ids,) + where_params)
            compare_dict = {}
            for row in cr.fetchall():

                compare_dict[row[0]]=[row[1], row[2]]
            return res2, compare_dict
        return res2

    def _sum_period(self, cr, uid, ids, name, args, context):
        if context is None:
            context = {}
        move_state = ('posted',)
        if context.get('state', False) == 'all':
            move_state = ('draft', 'posted',)
        if context.get('period_id', False):
            period_id = context['period_id']
        else:
            period_id = self.pool.get('account.period').find(cr, uid, context=context)
            if not period_id:
                return dict.fromkeys(ids, 0.0)
            period_id = [period_id[0]]
        vat = ''
        if 'vat' in context.keys() and context['vat'] != "":
            vat = False
            if context['vat'] == 'True':
                vat = True
        date_from = None
        date_to = None
        company_id = None
        if 'date_from' in context.keys():
            date_from = context['date_from']
        if 'date_to' in context.keys():
            date_to = context['date_to']
        if 'company_id' in context.keys():
            company_id = context['company_id']
        if vat == "":
            return self._sum(
                cr,
                uid,
                ids,
                name,
                args,
                context,
                where=' AND line.date >= %s AND line.date <= %s AND move.state IN %s AND line.company_id = %s',
                where_params=(date_from, date_to, move_state, company_id)
            )
        else:
            return self._sum(
                cr,
                uid,
                ids,
                name,
                args,
                context,
                where=' AND line.date >= %s AND line.date <= %s AND move.state IN %s AND line.vat = %s AND line.company_id = %s',
                where_params=(date_from, date_to, move_state, vat, company_id)
            )

    _columns = {
        'sum': fields.function(_sum_year, string="Year Sum"),
        'sum_period': fields.function(_sum_period, string="Period Sum")
    }
