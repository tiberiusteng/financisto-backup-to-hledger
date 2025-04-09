#
# Expense IQ backup to Financisto backup converter
#
# expenseiq backup format is implemented with description from:
# https://github.com/vmkernel/expense-iq/tree/master
#
# usage: python expenseiq2financisto.py <input expense iq bak file> <result financisto backup file>
#
# example: python expenseiq2financisto.py "2025-04-09 04.31.00.bak" "20250409_043100_expenseiq.backup"
#
import binascii
import gzip
import json
import sqlite3
import sys

currencies_src_csv = '''\
AED,United Arab Emirates dirham,Dhs.,2,PERIOD,COMMA
AFN,Afghan afghani,؋,2,PERIOD,COMMA
ALL,Albanian lek,Lek,2,PERIOD,COMMA
AMD,Armenian dram,Դ,2,PERIOD,COMMA
ANG,Netherlands Antillean guilder,ƒ,2,COMMA,SPACE
AOA,Angolan kwanza,AOA,2,PERIOD,COMMA
ARS,Argentine peso,$,2,COMMA,SPACE
AUD,Australian dollar,$,2,PERIOD,COMMA
AWG,Aruban florin,ƒ,2,PERIOD,COMMA
AZN,Azerbaijani manat,ман,2,PERIOD,COMMA
BAM,Bosnia and Herzegovina convertible mark,KM,2,PERIOD,COMMA
BBD,Barbados dollar,$,2,COMMA,SPACE
BDT,Bangladeshi taka,৳,2,COMMA,SPACE
BGN,Bulgarian lev,лв,2,PERIOD,COMMA
BHD,Bahraini dinar,BD,3,PERIOD,COMMA
BIF,Burundian franc,FBu,0,PERIOD,COMMA
BMD,Bermudian dollar,$,2,PERIOD,COMMA
BND,Brunei dollar,$,2,PERIOD,COMMA
BOB,Boliviano,$b,2,PERIOD,COMMA
BRL,Brazilian real,R$,2,COMMA,SPACE
BSD,Bahamian dollar,$,2,PERIOD,COMMA
BTN,Bhutanese ngultrum,BTN,2,PERIOD,COMMA
BWP,Botswana pula,P,2,PERIOD,COMMA
BYR,Belarusian ruble,Br,0,PERIOD,COMMA
BZD,Belize dollar,BZ$,2,PERIOD,COMMA
CAD,Canadian dollar,$,2,PERIOD,COMMA
CDF,Congolese franc,CDF,2,PERIOD,COMMA
CHF,Swiss franc,Fr.,2,COMMA,SPACE
CLP,Chilean peso,$,0,PERIOD,COMMA
CNY,Chinese yuan,¥,2,PERIOD,COMMA
COP,Colombian peso,$,2,COMMA,SPACE
COU,Unidad de Valor Real,COU,2,PERIOD,COMMA
CRC,Costa Rican colon,₡,2,COMMA,SPACE
CUC,Cuban convertible peso,CUC,2,PERIOD,COMMA
CUP,Cuban peso,₱,2,PERIOD,COMMA
CVE,Cape Verde escudo,CVE,0,PERIOD,COMMA
CZK,Czech koruna,Kč,2,COMMA,SPACE
DJF,Djiboutian franc,Fdj,0,PERIOD,COMMA
DKK,Danish krone,kr,2,COMMA,SPACE
DOP,Dominican peso,RD$,2,COMMA,SPACE
DZD,Algerian dinar,DZD,2,PERIOD,COMMA
EGP,Egyptian pound,£,2,PERIOD,COMMA
ERN,Eritrean nakfa,ERN,2,PERIOD,COMMA
ETB,Ethiopian birr,Br,2,PERIOD,COMMA
EUR,Euro,€,2,COMMA,SPACE
FJD,Fiji dollar,$,2,PERIOD,COMMA
FKP,Falkland Islands pound,£,2,PERIOD,COMMA
GBP,Pound sterling,£,2,PERIOD,COMMA
GEL,Georgian lari,GEL,2,PERIOD,COMMA
GHS,Ghanaian cedi,GH₵,2,PERIOD,COMMA
GIP,Gibraltar pound,£,2,PERIOD,COMMA
GMD,Gambian dalasi,GMD,2,PERIOD,COMMA
GNF,Guinean franc,GNF,0,PERIOD,COMMA
GTQ,Guatemalan quetzal,Q,2,COMMA,SPACE
GYD,Guyanese dollar,$,2,PERIOD,COMMA
HKD,Hong Kong dollar,$,2,PERIOD,COMMA
HNL,Honduran lempira,L,2,COMMA,SPACE
HRK,Croatian kuna,kn,2,COMMA,SPACE
HTG,Haitian gourde,HTG,2,PERIOD,COMMA
HUF,Hungarian forint,Ft,2,COMMA,SPACE
IDR,Indonesian rupiah,Rp,0,COMMA,SPACE
ILS,Israeli new sheqel,₪,2,PERIOD,COMMA
INR,Indian rupee,IN₨,2,PERIOD,COMMA
IQD,Iraqi dinar,IQD,0,PERIOD,COMMA
IRR,Iranian rial,﷼,0,PERIOD,COMMA
ISK,Icelandic króna,kr,0,COMMA,SPACE
JMD,Jamaican dollar,J$,2,PERIOD,COMMA
JOD,Jordanian dinar,JOD,3,PERIOD,COMMA
JPY,Japanese yen,¥,0,PERIOD,COMMA
KES,Kenyan shilling,KES,2,PERIOD,COMMA
KGS,Kyrgyzstani som,KGS,2,PERIOD,COMMA
KHR,Cambodian riel,៛,2,PERIOD,COMMA
KMF,Comoro franc,CF,0,PERIOD,COMMA
KPW,North Korean won,₩,0,PERIOD,COMMA
KRW,South Korean won,₩,0,PERIOD,COMMA
KWD,Kuwaiti dinar,KWD,3,PERIOD,COMMA
KYD,Cayman Islands dollar,$,2,PERIOD,COMMA
KZT,Kazakhstani tenge,〒,2,COMMA,SPACE
LAK,Lao kip,₭,0,PERIOD,COMMA
LBP,Lebanese pound,£,0,PERIOD,COMMA
LKR,Sri Lanka rupee,₨,2,PERIOD,COMMA
LRD,Liberian dollar,$,2,PERIOD,COMMA
LSL,Lesotho loti,M,2,PERIOD,COMMA
LTL,Lithuanian litas,Lt,2,COMMA,SPACE
LVL,Latvian lats,Ls,2,COMMA,SPACE
LYD,Libyan dinar,LD,3,PERIOD,COMMA
MAD,Moroccan dirham,MD,2,PERIOD,COMMA
MDL,Moldovan leu,MDL,2,PERIOD,COMMA
MGA,Malagasy ariary,MGA,2,PERIOD,COMMA
MKD,Macedonian denar,ден,2,PERIOD,COMMA
MMK,Myanma kyat,K,0,PERIOD,COMMA
MNT,Mongolian tugrik,₮,2,PERIOD,COMMA
MOP,Macanese pataca,MOP,1,PERIOD,COMMA
MRO,Mauritanian ouguiya,MRO,2,PERIOD,COMMA
MUR,Mauritian rupee,₨,2,PERIOD,COMMA
MVR,Maldivian rufiyaa,MRf,2,PERIOD,COMMA
MWK,Malawian kwacha,MK,2,PERIOD,COMMA
MXN,Mexican peso,$,2,PERIOD,COMMA
MYR,Malaysian ringgit,RM,2,PERIOD,COMMA
MZN,Mozambican metical,MT,2,COMMA,SPACE
NAD,Namibian dollar,$,2,COMMA,SPACE
NGN,Nigerian naira,₦,2,PERIOD,COMMA
NIO,Cordoba oro,C$,2,PERIOD,COMMA
NOK,Norwegian krone,kr,2,COMMA,SPACE
NPR,Nepalese rupee,₨,2,PERIOD,COMMA
NZD,New Zealand dollar,$,2,PERIOD,COMMA
OMR,Omani rial,﷼,3,PERIOD,COMMA
PAB,Panamanian balboa,B/.,2,PERIOD,COMMA
PEN,Peruvian nuevo sol,S/.,2,PERIOD,COMMA
PGK,Papua New Guinean kina,K,2,PERIOD,COMMA
PHP,Philippine peso,Php,2,PERIOD,COMMA
PKR,Pakistani rupee,₨,2,PERIOD,COMMA
PLN,Polish złoty,zł,2,COMMA,SPACE
PYG,Paraguayan guaraní,Gs,0,PERIOD,COMMA
QAR,Qatari rial,﷼,2,PERIOD,COMMA
RON,Romanian new leu,lei,2,COMMA,SPACE
RSD,Serbian dinar,Дин.,2,PERIOD,COMMA
RUB,Russian rouble,руб,2,PERIOD,NONE
RWF,Rwandan franc,RF,0,PERIOD,COMMA
SAR,Saudi riyal,﷼,2,PERIOD,COMMA
SBD,Solomon Islands dollar,$,2,PERIOD,COMMA
SCR,Seychelles rupee,₨,2,PERIOD,COMMA
SDG,Sudanese pound,SDG,2,PERIOD,COMMA
SEK,Swedish krona/kronor,kr,2,COMMA,SPACE
SGD,Singapore dollar,S$,2,PERIOD,COMMA
SHP,Saint Helena pound,£,2,PERIOD,COMMA
SLL,Sierra Leonean leone,SLL,0,PERIOD,COMMA
SOS,Somali shilling,S,2,PERIOD,COMMA
SRD,Surinamese dollar,$,2,PERIOD,COMMA
STD,São Tomé and Príncipe dobra,STD,0,PERIOD,COMMA
SYP,Syrian pound,£,2,COMMA,SPACE
SZL,Lilangeni,E,2,COMMA,SPACE
THB,Thai baht,฿,2,PERIOD,COMMA
TJS,Tajikistani somoni,TJS,2,PERIOD,COMMA
TMT,Turkmenistani manat,TMT,2,PERIOD,COMMA
TND,Tunisian dinar,TND,3,PERIOD,COMMA
TOP,Tongan paʻanga,TOP,2,PERIOD,COMMA
TRY,Turkish lira,TL,2,COMMA,SPACE
TTD,Trinidad and Tobago dollar,TT$,2,PERIOD,COMMA
TWD,New Taiwan dollar,NT$,0,PERIOD,COMMA
TZS,Tanzanian shilling,TZS,2,PERIOD,COMMA
UAH,Ukrainian hryvnia,₴,2,COMMA,SPACE
UGX,Ugandan shilling,USh,0,PERIOD,COMMA
USD,United States dollar,$,2,PERIOD,COMMA
UYU,Uruguayan peso,$U,2,PERIOD,COMMA
UZS,Uzbekistan som,UZS,2,PERIOD,COMMA
VEF,Venezuelan bolívar fuerte,Bs,2,COMMA,SPACE
VND,Vietnamese đồng,₫,0,COMMA,SPACE
VUV,Vanuatu vatu,VUV,0,PERIOD,COMMA
WST,Samoan tala,WST,2,PERIOD,COMMA
XAF,CFA franc BEAC,FCFA,0,PERIOD,COMMA
XCD,East Caribbean dollar,$,2,PERIOD,COMMA
XDR,Special Drawing Rights,XDR,2,PERIOD,COMMA
XPF,CFP franc,F,0,PERIOD,COMMA
YER,Yemeni rial,﷼,2,PERIOD,COMMA
ZAR,South African rand,R,2,COMMA,SPACE
ZMK,Zambian kwacha,ZMK,2,PERIOD,COMMA
ZWL,Zimbabwe dollar,Z$,2,PERIOD,COMMA'''

separators = {'PERIOD': "'.'", 'COMMA': "','", 'SPACE': "' '", 'NONE': "''"}
currencies_src = {}
for l in currencies_src_csv.split('\n'):
    f = l.split(',')
    currencies_src[f[0]] = {'title': f[1], 'symbol': f[2], 'decimals': f[3],
                      'decimal_separator': separators[f[4]],
                      'group_separator': separators[f[5]]}

def create_tables():
    global db

    table_schemas = [
        'CREATE TABLE account (_id integer, name text not null, description text not null, currency text not null, start_balance real not null, monthly_budget real not null, create_date integer not null, position integer not null, default_tran_status text not null, exclude_from_total text not null, uuid text not null, updated text not null, deleted text not null, icon text, color text, hidden integer not null)',
        'CREATE TABLE tran (_id integer, account_id text, title, text, amount real, tran_date integer, remarks text, category_id text, status text, repeat_id text, photo_id text, split_id text, transfer_account_id text, project_uuid text, uuid text, updated text, deleted text)',
        'CREATE TABLE category (_id integer, name text, description text, color text, type text, parent_id text, uuid text, updated text, deleted text, icon text)',
        'CREATE TABLE category_tag (_id integer, category_id text, name text, uuid text, updated text, deleted text)',
        'CREATE TABLE category_color (_id integer, category_id text, color_code text, uuid text, updated text, deleted text)',
    ]
    c = db.cursor()
    for s in table_schemas:
        c.execute(s)

db = sqlite3.connect(':memory:', check_same_thread = False)
db.row_factory = sqlite3.Row

create_tables()

cursor = db.cursor()

out = gzip.open(sys.argv[2], 'wt', encoding='utf-8')

first_line = True
for l in open(sys.argv[1]):
    l = l.strip()

    if first_line:
        if l != '[EASYMONEY_BACKUP_V3]':
            raise Exception('Not an Expense IQ backup file')
        first_line = False
        continue

    try:
        l = binascii.a2b_hex(l[::-1].encode()).decode()
        if l.startswith('INSERT INTO user_settings'): continue
        cursor.execute(l)
    except Exception as e:
        print(repr(e))

db.commit()

out.write('''\
PACKAGE:tw.tib.financisto
VERSION_CODE:183
VERSION_NAME:2025-03-13
DATABASE_VERSION:228
#START
''')

currency = {} # TWD: 1, JPY: 2, ...
is_default = 1
_id = 1
cursor.execute('SELECT DISTINCT currency FROM account')
for r in cursor.fetchall():
    c = currencies_src.get(r['currency'], {'title': r['currency'], 
            'symbol': r['currency'], 'decimals': '2',
            'decimal_separator': "'.'",
            'group_separator': "','"})
    c['_id'] = _id
    c['name'] = r['currency']
    c['is_default'] = is_default
    out.write('''\
$ENTITY:currency
_id:{_id}
name:{name}
title:{title}
symbol:{symbol}
is_default:{is_default}
decimals:{decimals}
decimal_separator:{decimal_separator}
group_separator:{group_separator}
symbol_format:RS
updated_on:0
update_exchange_rate:1
is_active:1
$$
'''.format(**c))
    currency[r['currency']] = _id
    _id += 1
    is_default = 0

account = {}
cursor.execute('SELECT * FROM account')
_id = 1
for row in cursor.fetchall():
    r = dict(row)
    r['_id'] = _id
    r['is_include_into_totals'] = '1' if r['exclude_from_total'] == 'No' else '0'
    r['currency_id'] = currency[r['currency']]
    out.write('''\
$ENTITY:account
_id:{_id}
title:{name}
creation_date:{create_date}
currency_id:{currency_id}
type:CASH
sort_order:{position}
is_active:1
is_include_into_totals:{is_include_into_totals}
$$
'''.format(**r))
    account[r['uuid']] = _id
    _id += 1

category = {} # uuid: _id
cursor.execute('SELECT * FROM category')
_id = 1
for row in cursor.fetchall():
    r = dict(row)
    r['_id'] = _id
    r['type'] = '0' if r['type'] == 'E' else '1'
    out.write('''\
$ENTITY:category
_id:{_id}
title:{name}
type:1
is_active:1
$$
'''.format(**r))
    category[r['uuid']] = _id
    _id += 1

payee = {}
next_payee_id = 1
transfer_from = {}

status = {'C': 'RC', 'U': 'UR', 'V': 'PN', 'R': 'RS'}

cursor.execute('SELECT * FROM tran ORDER BY _id')
for row in cursor.fetchall():
    r = dict(row)

    # transfer transactions
    if r['transfer_account_id'] != '':
        if r['account_id'] == transfer_from.get('transfer_account_id'):
            # second transfer transaction
            r['from_account_id'] = account[transfer_from['account_id']]
            r['to_account_id'] = account[r['account_id']]
            r['from_amount'] = int(transfer_from['amount'] * 100)
            r['to_amount'] = int(r['amount'] * 100)
            r['status'] = status[r['status']]
            out.write('''\
$ENTITY:transactions
_id:{_id}
from_account_id:{from_account_id}
to_account_id:{to_account_id}
note:{remarks}
from_amount:{from_amount}
to_amount:{to_amount}
datetime:{tran_date}
is_template:0
status:{status}
$$
'''.format(**r))
            transfer_from = {}
        else:
            # first transfer transaction
            transfer_from = r
        continue

    # normal transactions

    if r['title']:
        payee_id = payee.get(r['title'])
        if not payee_id:
            payee_id = payee[r['title']] = next_payee_id
            next_payee_id += 1
    else:
        payee_id = -1

    r['from_account_id'] = account[r['account_id']]
    r['category_id'] = category[r['category_id']]
    r['from_amount'] = int(r['amount'] * 100)
    r['status'] = status[r['status']]
    r['payee_id'] = payee_id
    out.write('''\
$ENTITY:transactions
_id:{_id}
from_account_id:{from_account_id}
to_account_id:0
category_id:{category_id}
note:{remarks}
from_amount:{from_amount}
datetime:{tran_date}
is_template:0
status:{status}
payee_id:{payee_id}
$$
'''.format(**r))

for p in payee.items():
    out.write('''\
$ENTITY:payee
_id:{1}
title:{0}
is_active:1
$$
'''.format(*p))

out.write('#END')
