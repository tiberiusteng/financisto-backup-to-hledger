import datetime
import re

src = open('easycard.csv', 'r', encoding='utf-8')

payee = {
    '統一超商': 3,
    '全家': 4,
    'OK': 5,
    '萊爾富': 51,
    '美廉社': 301
}

payee_pattern = {
    '麥當勞': 52,
    '鬍鬚張': 87
}

transit_pattern = ['客運', '捷運', '大都會']

# category
# 1: 食
# 19: 交通

for line in src:
    f = line.strip().split(',')
    ts = int(datetime.datetime.strptime(f[0], '%Y-%m-%d %H:%M').timestamp() * 1000)
    if f[1] == '加值': continue

    unsure = True
    category_id = 0
    payee_id = 0
    amount = int(f[3]) * -100
    note = ''

    if amount == 0: continue

    if f[2] in payee:
        category_id = 1
        payee_id = payee[f[2]]
        unsure = False

    if unsure:
        for p in payee_pattern:
            if p in f[2]:
                category_id = 1
                payee_id = payee_pattern[p]
                unsure = False

    if unsure:
        for p in transit_pattern:
            if p in f[2]:
                category_id = 19
                note = f[2]
                unsure = False

    if unsure:
        print('Unsure: ' + repr([f, ts]))
        break

    print(f'''\
$ENTITY:transactions
from_account_id:19
to_account_id:0
category_id:{category_id}
from_amount:{amount}
datetime:{ts}
status:UR
note:{note}
payee_id:{payee_id}
$$''')
