# coding: utf-8

import glob
import gzip
import re
import sqlite3
import time
import wcwidth

financisto_backup_file = sorted(glob.glob(r'../應用程式/Financisto 1 Legacy Test/*.backup'))[-1]
ledger_file = 'tib.journal'

tables = {}
balances = {}
currencies = {}

def create_db():
    table_schemas = [
        '''CREATE TABLE account ( _id integer primary key autoincrement, title text not null, creation_date long not null, currency_id integer not null, total_amount integer not null default 0 , type text not null default 'CASH', issuer text, number text, sort_order integer not null default 0, is_active boolean not null default 1, is_include_into_totals boolean not null default 1, last_category_id long not null default 0, last_account_id long not null default 0, total_limit integer not null default 0, card_issuer text, closing_day integer not null default 0, payment_day integer not null default 0, note text, last_transaction_date long not null default 0, updated_on long not null)''',
        '''CREATE TABLE category ( _id integer primary key autoincrement, title text not null, left integer not null default 0, right integer not null default 0 , last_location_id long not null default 0, last_project_id long not null default 0, sort_order integer not null default 0, type integer not null default 0, updated_on long not null)''',
        '''CREATE TABLE currency_exchange_rate ( from_currency_id integer not null, to_currency_id integer not null, rate_date long not null, rate float not null, updated_on long not null, PRIMARY KEY (from_currency_id, to_currency_id, rate_date) )''',
        '''CREATE TABLE locations ( _id integer primary key autoincrement, name text not null, datetime long not null, provider text, title text, accuracy float, latitude double, longitude double, is_payee integer not null default 0, resolved_address text , count integer not null default 0, updated_on long not null)''',
        '''CREATE TABLE transactions ( _id integer primary key autoincrement, from_account_id long not null, to_account_id long not null default 0, category_id long not null default 0, project_id long not null default 0, location_id long not null default 0, note text, from_amount integer not null default 0, to_amount integer not null default 0, datetime long not null, provider text, accuracy float, latitude double, longitude double , payee text, is_template integer not null default 0, template_name text, recurrence text, notification_options text, status text not null default 'UR', attached_picture text, is_ccard_payment integer not null default 0, last_recurrence long not null default 0, payee_id long, parent_id long not null default 0, original_currency_id long not null default 0, original_from_amount long not null default 0, updated_on long not null)''',
        '''CREATE TABLE project ( _id integer primary key autoincrement, title text , is_active boolean not null default 1, updated_on long not null)''',
        '''CREATE TABLE currency ( _id integer primary key autoincrement, name text not null, title text not null, symbol text not null , is_default integer not null default 0, decimals integer not null default 2, decimal_separator text, group_separator text, symbol_format text not null default 'RS', updated_on long not null)''',
        '''CREATE TABLE payee ( _id integer primary key autoincrement, title text not null, last_category_id long not null default 0, updated_on long not null)''',
    ]
    c = db.cursor()
    for s in table_schemas:
        c.execute(s)

def import_backup():
    global db

    c = db.cursor()

    f = gzip.open(financisto_backup_file, 'rt', encoding='utf-8')

    for l in f:
        if l == '#START\n': break
    
    # read entities
    p_entity = re.compile(r'\$ENTITY:([^\n]+)\n')
    p_id = re.compile(r'_id:(\d+)\n')
    
    ENTITY_TYPE = 0
    ENTITY_ID = 1
    ENTITY_FIELDS = 2

    state = ENTITY_TYPE

    entity_type = None
    entity_id = None
    fields = {}

    while 1:
        l = f.readline()
        if   not l: break
        elif l == '#END\n': break
        elif l == '$$\n':
            # dirty auto increment for currency exchange rate
            if not entity_id:
                if entity_type not in tables:
                    entity_id = 1
                else:
                    entity_id = max(tables[entity_type].keys()) + 1
            
            tables.setdefault(entity_type, {})[entity_id] = fields

            if entity_type != 'currency_exchange_rate':
                fields['_id'] = entity_id

            #for k in fields:
            #    if type(fields[k]) == str:
            #        fields[k] = fields[k].decode('utf8')
            #print(entity_type, list(fields.keys()))
            c.execute(
                'INSERT INTO %s (%s) VALUES (%s)' % (
                    entity_type,
                    ','.join(list(fields.keys())),
                    ','.join([':%s' % x for x in list(fields.keys())])
                ),
                fields)

            entity_type = None
            entity_id = None
            fields = {}
            state = ENTITY_TYPE

        elif state == ENTITY_TYPE:
            m = p_entity.match(l)
            if m:
                entity_type = m.group(1)
                if entity_type == 'currency_exchange_rate':
                    state = ENTITY_FIELDS
                else:
                    state = ENTITY_ID
        
        elif state == ENTITY_ID:
            m = p_id.match(l)
            if m:
                entity_id = m.group(1)
                state = ENTITY_FIELDS
        
        elif state == ENTITY_FIELDS:
            k, v = l.strip().split(':', 1)
            fields[k] = v

    db.commit()

db = sqlite3.connect(':memory:', check_same_thread = False)
db.row_factory = sqlite3.Row

create_db()
import_backup()

c = db.cursor()

account_type_map = {
    'ASSET': 'Assets',
    'CASH': 'Assets',
    'BANK': 'Assets',
    'CREDIT_CARD': 'Liabilities',
    'LIABILITY': 'Liabilities'
}

def get_category_title(parent_category_id, parent_category, category_type, category):
    if parent_category_id == None and parent_category == None and category_type == None and category == None:
        return '[Split]'

    title = []

    if category_type == 1:
        title.append('Income')
    else:
        title.append('Expense')

    if parent_category_id and parent_category:
        title.append(parent_category)

    title.append(category)
    title = ':'.join(title)

    return title + (' ' * (40 - wcwidth.wcswidth(title)))

def get_account_title(account_type, account):
    title = account_type_map[account_type] + ':' + account
    return title + (' ' * (40 - wcwidth.wcswidth(title)))

digits = re.compile('[0123456789]')
def get_currency(currency):
    if digits.search(currency):
        return '"' + currency + '"'
    else:
        return currency

def get_amount(amount, currency):
    global currencies
    amount = amount / 100
    c = currencies[currency]
    return ('{0:,.%sf}' % c['decimals']).format(amount)

ledger = open(ledger_file, 'w', encoding='utf-8')

c.execute('SELECT * FROM currency')
for r in c.fetchall():
    #if r['decimals'] == 0:
    #    decimals = ''
    #else:
    decimals = '.' + '0' * int(r['decimals'])
    currencies[r['name']] = dict(r)
    ledger.write('commodity 1,000{0} {1}\n'.format(decimals, get_currency(r['name'])))
ledger.write('\n')

c.execute("""
SELECT
	t.datetime, t.note, t.status,
	oc.name original_currency, t.original_from_amount,
	fc.name from_currency, t.from_amount, 
	tc.name to_currency, t.to_amount,
	p.title payee, fa.type from_account_type, fa.title from_account, 
	ta.type to_account_type, ta.title to_account, 
	pc._id parent_category_id, pc.title parent_category, c.type category_type, c.title category
FROM 'transactions' t
LEFT JOIN payee p ON t.payee_id = p._id
LEFT JOIN account fa ON t.from_account_id = fa._id
LEFT JOIN account ta ON t.to_account_id = ta._id
LEFT JOIN category pc ON (SELECT parent._id FROM category node, category parent WHERE node.left BETWEEN parent.left AND parent.right AND node._id = t.category_id AND parent._id != t.category_id ORDER BY parent.left DESC) = pc._id
LEFT JOIN category c ON t.category_id = c._id
LEFT JOIN currency oc ON t.original_currency_id = oc._id
LEFT JOIN currency fc ON fa.currency_id = fc._id
LEFT JOIN currency tc ON ta.currency_id = tc._id
ORDER BY t.datetime ASC
""")

for r in c.fetchall():
    if r['status'] == 'RC':
        flag = ' *'
    else:
        flag = ''
    date = time.strftime('%Y-%m-%d', time.localtime(r['datetime'] / 1000))
    note = r['note'] or ''
    if r['payee']:
        note = r['payee'] + ' | ' + note

    transaction_header = '{0}{1} {2}\n'.format(date, flag, note)
    from_account_title = get_account_title(r['from_account_type'], r['from_account'])

    if r['to_account_type'] == None:
        from_currency = r['from_currency']
        from_amount   = get_amount(r['from_amount'], r['from_currency'])
        category_title = get_category_title(r['parent_category_id'], r['parent_category'], r['category_type'], r['category'])

        if category_title == '[Split]':
            split_tag = ';'
            from_account_balance = balances.get(r['from_account'], 0) + int(r['from_amount'])
            ledger.write(';' + transaction_header)
        else:
            split_tag = ' '
            from_account_balance = balances[r['from_account']] = balances.get(r['from_account'], 0) + int(r['from_amount'])
            ledger.write(transaction_header)

        ledger.write('{0} {1} {2:>12} {3} = {4:>12} {5}\n'.format(
            split_tag,
            from_account_title, from_amount, get_currency(from_currency),
            get_amount(from_account_balance, r['from_currency']), get_currency(from_currency)))

        if r['original_currency']:
            ledger.write('{0} {1} {2:>12} {3} ; {4:12.4f} {5}\n'.format(
                split_tag, category_title,
                get_amount(-r['original_from_amount'], r['original_currency']), get_currency(r['original_currency']),
                int(r['from_amount']) / int(r['original_from_amount']), get_currency(r['from_currency'])))
        else:
            ledger.write('{0} {1}\n'.format(split_tag, category_title.strip()))
    else:
        ledger.write(transaction_header)

        balances[r['from_account']] = balances.get(r['from_account'], 0) + int(r['from_amount'])
        balances[r['to_account']] = balances.get(r['to_account'], 0) + int(r['to_amount'])

        to_account_title = get_account_title(r['to_account_type'], r['to_account'])

        if r['from_currency'] != r['to_currency']:
            ledger.write('  ; {0:.4f} {1} / {2:.4f} {3}\n'.format(
                -int(r['from_amount']) / int(r['to_amount']), get_currency(r['from_currency']),
                -int(r['to_amount']) / int(r['from_amount']), get_currency(r['to_currency'])))

        ledger.write('  {0} {1:>12} {2} = {3:>12} {4}\n'.format(
            from_account_title, get_amount(r['from_amount'], r['from_currency']), get_currency(r['from_currency']),
            get_amount(balances[r['from_account']], r['from_currency']), get_currency(r['from_currency'])))

        ledger.write('  {0} {1:>12} {2} = {3:>12} {4}\n'.format(
            to_account_title, get_amount(r['to_amount'], r['to_currency']), get_currency(r['to_currency']),
            get_amount(balances[r['to_account']], r['to_currency']), get_currency(r['to_currency'])))
        #else:
        #    ledger.write('  {0} {1:>10} {2} @ {3:10f} {4} = {5:>10} {6}\n'.format(
        #        to_account_title, get_amount(r['to_amount'], r['to_currency']), get_currency(r['to_currency']),
        #        -int(r['from_amount']) / int(r['to_amount']), get_currency(r['from_currency']),
        #        get_amount(balances[r['to_account']], r['to_currency']), get_currency(r['to_currency'])))

    ledger.write('\n')

ledger.close()
