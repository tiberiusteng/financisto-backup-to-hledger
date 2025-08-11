#
# usage: python easycard-import.py easycard.csv 20200818_005305_256.backup
#
import datetime
import dateutil.tz
import gzip
import re
import sys

src = open(sys.argv[1], 'r', encoding='utf-8')

payee = {
    '統一超商': 3,
    '全家': 4,
    'OK': 5,
    'COMEBUY長沂國際': 29,
    '萊爾富': 51,
    '全聯福利中心': 55,
    '美廉社': 301,
    '寶雅國際股份有限公司': 333,
    '康是美': 1112,
}

payee_pattern = {
    '八方雲集': 45,
    '麥當勞': 52,
    '50嵐': 62,
    '鬍鬚張': 87,
    '約翰紅茶': 221,
    '摩斯漢堡': 47,
    '小北百貨': 968
}

transit_pattern = ['客運', '捷運', '大都會']

def local_ts_str(ts):
    return datetime.datetime \
        .fromtimestamp(ts / 1000, dateutil.tz.gettz('Asia/Taipei')) \
        .strftime('%Y-%m-%d %H:%M')

# category
# 1: 食
# 19: 交通

card_tx = []

for line in src:
    f = line.strip().split(',')
    ts = int(datetime.datetime.strptime(f[0] + ' +0800', '%Y-%m-%d %H:%M %z').timestamp() * 1000)
    card_tx.append([ts, f[1], f[2], f[3]])

bak = gzip.open(sys.argv[2], 'rt', encoding='utf-8')
out = gzip.open(sys.argv[2].replace('.backup', '-easycard.backup'), 'wt', encoding='utf-8')

entity_type = ''
entity = {}
start = False
unsures = []

for line in bak:
    if not start:
        out.write(line)
        if line == '#START\n':
            print('started')
            start = True

    elif line.startswith('#END'):
        break

    elif line.startswith('$ENTITY:'):
        entity_type = line[8:-1]

    elif line == '$$\n':
        # match charge transaction
        if entity_type == 'transactions' and \
            entity['to_account_id'] == '19' and \
            entity['to_amount'] == '50000':

            ts = int(entity['datetime'])

            # find the nearest charge transaction
            nearest_timediff = -1
            nearest_tx = -1

            for i, tx in enumerate(card_tx):
                if tx[1] != '自動加值': continue

                timediff = abs(tx[0] - ts)
                if timediff < 86400000 and (nearest_timediff == -1 or timediff < nearest_timediff):
                    nearest_timediff = timediff
                    nearest_tx = i

            if nearest_tx != -1:
                bak_ts = local_ts_str(ts)
                charge_ts = local_ts_str(card_tx[nearest_tx][0])

                print(f'matched charge {bak_ts} -> {charge_ts}')

                entity['datetime'] = card_tx[nearest_tx][0]

                card_tx[nearest_tx][1] = None

        # output entity
        out.write('$ENTITY:' + entity_type + '\n')
        for k, v in entity.items():
            out.write(f'{k}:{v}\n')
        out.write('$$\n')
        entity_type = ''
        entity = {}

    elif entity_type:
        f = line.strip().split(':', 1)
        entity[f[0]] = f[1]

for tx in card_tx:
    ts = tx[0]

    if tx[1] == '加值':
        ts_str = local_ts_str(ts)
        amount = int(tx[3]) * 100
        neg_amount = amount * -1
        note = tx[2]

        print(f'{ts_str} {tx[1]} {tx[2]} {int(amount/100)}')

        out.write(f'''\
$ENTITY:transactions
from_account_id:27
to_account_id:19
from_amount:{neg_amount}
to_amount:{amount}
datetime:{ts}
status:UR
note:{note}
$$\n''')
        continue

    if tx[1] != '扣款': continue
    ts += 100

    unsure = True
    category_id = 0
    payee_id = 0
    amount = int(tx[3]) * -100
    note = ''

    if amount == 0: continue

    if tx[2] in payee:
        category_id = 1
        payee_id = payee[tx[2]]
        unsure = False

    if unsure:
        for p in payee_pattern:
            if p in tx[2]:
                category_id = 1
                payee_id = payee_pattern[p]
                unsure = False

    if unsure:
        for p in transit_pattern:
            if p in tx[2]:
                category_id = 19
                note = tx[2]
                unsure = False

    if unsure:
        unsures.append('Unsure: ' + repr([tx, local_ts_str(ts)]))

    ts_str = local_ts_str(ts)

    print(f'{ts_str} {tx[2]} {int(amount/100)} {note}')

    out.write(f'''\
$ENTITY:transactions
from_account_id:19
to_account_id:0
category_id:{category_id}
from_amount:{amount}
datetime:{ts}
status:UR
note:{note}
payee_id:{payee_id}
$$\n''')

out.write('#END')

if unsures:
    for u in unsures:
        print(u)
