#
# usage: python invoice-match.py invoice.csv 20200818_005305_256.backup
#
import datetime
import gzip
import json
import pprint
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')

invoices = {}
current_invoice = {}
current_lineitems = []

invoice_csv = open(sys.argv[1], 'r', encoding='utf-8')

payee_check = {
    3: re.compile('統一超商'),
    4: re.compile('全家便利商店'),
    51: re.compile('萊爾富'),
    301: re.compile('三商家購'),
}

def save_invoice():
    global invoices, current_invoice, current_lineitems
    if not current_invoice: return
    invoices[current_invoice['id']] = [current_invoice['date'], current_invoice['total'], current_lineitems,
        current_invoice['carrier'], current_invoice['issuer']]
    current_invoice = {}
    current_lineitems = []

for l in invoice_csv:
    f = l.strip().split('|')
    if f[0] == 'M':
        save_invoice()
        current_invoice['id'] = f[6]
        current_invoice['date'] = datetime.datetime.strptime(f[3] + ' +0800', '%Y%m%d %z').timestamp()
        current_invoice['total'] = int(f[7])
        current_invoice['carrier'] = f[1]
        current_invoice['issuer'] = f[5]
    elif f[0] == 'D':
        current_lineitems.append((f[3], f[2]))
save_invoice()

bak = gzip.open(sys.argv[2], 'rt', encoding='utf-8')
out = gzip.open(sys.argv[2].replace('.backup', '-invoice.backup'), 'wt', encoding='utf-8')

entity_type = ''
entity = {}
start = False

for line in bak:
    if not start:
        out.write(line)
        if line == '#START\n':
            print('started')
            start = True

    if line.startswith('#END'):
        out.write(line)
        break

    if line == '$$\n':
        # match invoice
        if entity_type == 'transactions':
            amount = int(entity['from_amount']) / -100
            ts = int(entity['datetime']) / 1000

            matched = False
            for invoice_id, i in invoices.items():

                if (abs(ts - i[0]) < 93600 and (amount == i[1] or amount == (i[1] + 5) or amount == (i[1] + 2) or amount == (i[1] + 1) or amount == (i[1] - 5)) and
                    (entity['from_account_id'] == '19' if i[3] == '悠遊卡' else True)):

                    payee_id = int(entity['payee_id'])
                    if payee_id in payee_check:
                        if not payee_check[payee_id].search(i[4]):
                            print('payee check %d != %s' % (payee_id, i[4]))
                            continue

                    if amount == i[1] + 5:
                        i[2].append(('兩用袋', '5'))
                    elif amount == i[1] + 2:
                        i[2].append(('兩用袋', '2'))
                    elif amount == i[1] + 1:
                        i[2].append(('兩用袋', '1'))
                    elif amount == i[1] - 5:
                        i[2].append(('自帶杯', '-5'))
                    print('Matched ' + invoice_id)
                    matched = True
                    new_note = unicodedata.normalize('NFKC', ', '.join((' '.join(x) for x in i[2])))
                    if not entity.get('note'):
                        entity['note'] = new_note
                        print('    + ' + new_note)
                    else:
                        print('      ' + entity['note'])
                        print('    ! ' + new_note)
                    break

            if matched:
                del invoices[invoice_id]

        # output entity
        out.write('$ENTITY:' + entity_type + '\n')
        for k, v in entity.items():
            out.write(f'{k}:{v}\n')
        out.write('$$\n')
        entity_type = ''
        entity = {}

    if line.startswith('$ENTITY:'):
        entity_type = line[8:-1]

    elif entity_type:
        f = line.strip().split(':', 1)
        entity[f[0]] = f[1]

print()
print('Remaining invoices (%s):' % len(invoices))
print()

for invoice_id, invoice in invoices.items():
    invoice[0] = datetime.datetime.fromtimestamp(invoice[0],
        datetime.timezone(datetime.timedelta(hours=8))
        ).strftime('%Y-%m-%d %H:%M:%S')

pprint.pprint(invoices)
