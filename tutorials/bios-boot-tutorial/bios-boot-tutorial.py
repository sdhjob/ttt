#!/usr/bin/env python3

import argparse
import json
import numpy
import os
import random
import re
import subprocess
import sys
import time

args = None
logFile = None

unlockTimeout = 999999999
fastUnstakeSystem = './fast.refund/sou.system/sou.system.wasm'

systemAccounts = [
    'sou.bpay',
    'sou.msig',
    'sou.names',
    'sou.ram',
    'sou.ramfee',
    'sou.saving',
    'sou.stake',
    'sou.token',
    'sou.vpay',
    'sou.rex',
]

def jsonArg(a):
    return " '" + json.dumps(a) + "' "

def run(args):
    print('bios-boot-tutorial.py:', args)
    logFile.write(args + '\n')
    if subprocess.call(args, shell=True):
        print('bios-boot-tutorial.py: exiting because of error')
        sys.exit(1)

def retry(args):
    while True:
        print('bios-boot-tutorial.py: ', args)
        logFile.write(args + '\n')
        if subprocess.call(args, shell=True):
            print('*** Retry')
            sleep(2)
        else:
            break

def background(args):
    print('bios-boot-tutorial.py:', args)
    logFile.write(args + '\n')
    return subprocess.Popen(args, shell=True)

def getOutput(args):
    print('bios-boot-tutorial.py:', args)
    logFile.write(args + '\n')
    proc = subprocess.Popen(args, shell=True, stdout=subprocess.PIPE)
    return proc.communicate()[0].decode('utf-8')

def getJsonOutput(args):
    return json.loads(getOutput(args))

def sleep(t):
    print('sleep', t, '...')
    time.sleep(t)
    print('resume')

def startWallet():
    run('rm -rf ' + os.path.abspath(args.wallet_dir))
    run('mkdir -p ' + os.path.abspath(args.wallet_dir))
    background(args.ksoud + ' --unlock-timeout %d --http-server-address 127.0.0.1:6666 --wallet-dir %s' % (unlockTimeout, os.path.abspath(args.wallet_dir)))
    sleep(.4)
    run(args.clsou + 'wallet create -f %s/default_pwd' % (os.path.abspath(args.wallet_dir)))

def importKeys():
    run(args.clsou + 'wallet import --private-key ' + args.private_key)
    keys = {}
    for a in accounts:
        key = a['pvt']
        if not key in keys:
            if len(keys) >= args.max_user_keys:
                break
            keys[key] = True
            run(args.clsou + 'wallet import --private-key ' + key)
    for i in range(firstProducer, firstProducer + numProducers):
        a = accounts[i]
        key = a['pvt']
        if not key in keys:
            keys[key] = True
            run(args.clsou + 'wallet import --private-key ' + key)

def startNode(nodeIndex, account):
    dir = args.nodes_dir + ('%02d-' % nodeIndex) + account['name'] + '/'
    run('rm -rf ' + dir)
    run('mkdir -p ' + dir)
    otherOpts = ''.join(list(map(lambda i: '    --p2p-peer-address localhost:' + str(9000 + i), range(nodeIndex))))
    if not nodeIndex: otherOpts += (
        '    --plugin sou::history_plugin'
        '    --plugin sou::history_api_plugin'
    )
    cmd = (
            args.nodesou +
            '    --max-irreversible-block-age -1'
            '    --contracts-console'
            '    --genesis-json ' + os.path.abspath(args.genesis) +
            '    --blocks-dir ' + os.path.abspath(dir) + '/blocks'
                                                         '    --config-dir ' + os.path.abspath(dir) +
            '    --data-dir ' + os.path.abspath(dir) +
            '    --chain-state-db-size-mb 1024'
            '    --http-server-address 0.0.0.0:' + str(8000 + nodeIndex) +
            '    --p2p-listen-endpoint 0.0.0.0:' + str(9000 + nodeIndex) +
            '    --max-clients ' + str(maxClients) +
            '    --p2p-max-nodes-per-host ' + str(maxClients) +
            '    --enable-stale-production'
            '    --max-transaction-time 200000'
            '    --http-max-response-time-ms 90000'
            '    --producer-name ' + account['name'] +
            '    --private-key \'["' + account['pub'] + '","' + account['pvt'] + '"]\''
                                                                                 '    --plugin sou::http_plugin'
                                                                                 '    --plugin sou::chain_plugin'
                                                                                 '    --plugin sou::chain_api_plugin'
                                                                                 '    --plugin sou::producer_plugin'
                                                                                 '    --plugin sou::producer_api_plugin' +
            otherOpts)
    with open(dir + 'stderr', mode='w') as f:
        f.write(cmd + '\n\n')
    background(cmd + '    2>>' + dir + 'stderr')

def startProducers(b, e):
    for i in range(b, e):
        startNode(i - b + 1, accounts[i])

def createSystemAccounts():
    for a in systemAccounts:
        run(args.clsou + 'create account sou ' + a + ' ' + args.public_key)

def intToCurrency(i):
    return '%d.%04d %s' % (i // 10000, i % 10000, args.symbol)

def allocateFunds(b, e):
    # dist = numpy.random.pareto(1.161, e - b).tolist() # 1.161 = 80/20 rule
    # dist.sort()
    # dist.reverse()
    factor = 2100 / (e - 1)
    total = 0
    for i in range(b, e):
        if i==0 :
            funds = 500_0000_0000
        else:
            funds = round(factor * 10000)
        if i >= firstProducer and i < firstProducer + numProducers:
            funds = max(funds, round(args.min_producer_funds * 10000))
        total += funds
        accounts[i]['funds'] = funds
    return total

def createStakedAccounts(b, e):
    ramFunds = round(args.ram_funds * 10000)
    configuredMinStake = round(args.min_stake * 10000)
    maxUnstaked = round(args.max_unstaked * 10000)
    for i in range(b, e):
        a = accounts[i]
        funds = a['funds']
        print('#' * 80)
        print('# %d/%d %s %s' % (i, e, a['name'], intToCurrency(funds)))
        print('#' * 80)
        if funds < ramFunds:
            print('skipping %s: not enough funds to cover ram' % a['name'])
            continue
        minStake = min(funds - ramFunds, configuredMinStake)
        unstaked = min(funds - ramFunds - minStake, maxUnstaked)
        stake = funds - ramFunds - unstaked
        stakeNet = round(stake / 2)
        stakeCpu = stake - stakeNet
        print('%s: total funds=%s, ram=%s, net=%s, cpu=%s, unstaked=%s' % (a['name'], intToCurrency(a['funds']), intToCurrency(ramFunds), intToCurrency(stakeNet), intToCurrency(stakeCpu), intToCurrency(unstaked)))
        assert(funds == ramFunds + stakeNet + stakeCpu + unstaked)
        retry(args.clsou + 'system newaccount --transfer sou %s %s --stake-net "%s" --stake-cpu "%s" --buy-ram "%s"   ' %
              (a['name'], a['pub'], intToCurrency(stakeNet), intToCurrency(stakeCpu), intToCurrency(ramFunds)))
        if unstaked:
            retry(args.clsou + 'transfer sou %s "%s"' % (a['name'], intToCurrency(unstaked)))

def regProducers(b, e):
    for i in range(b, e):
        a = accounts[i]
        retry(args.clsou + 'system regproducer %s "%s" "%s" "%s"' %
              (a['name'], a['pub'], a['url'], a['location']))

def listProducers():
    run(args.clsou + 'system listproducers')

def vote(b, e):
    for i in range(b, e):
        voter = accounts[i]['name']
        k = args.num_producers_vote
        if k > numProducers:
            k = numProducers - 1
        prods = random.sample(range(firstProducer, firstProducer + numProducers), k)
        prods = ' '.join(map(lambda x: accounts[x]['name'], prods))
        retry(args.clsou + 'system voteproducer prods ' + voter + ' ' + prods)

def claimRewards():
    table = getJsonOutput(args.clsou + 'get table sou sou producers -l 100')
    times = []
    for row in table['rows']:
        if row['unpaid_blocks'] and not row['last_claim_time']:
            times.append(getJsonOutput(args.clsou + 'system claimrewards -j ' + row['owner'])['processed']['elapsed'])
    print('Elapsed time for claimrewards:', times)

def proxyVotes(b, e):
    vote(firstProducer, firstProducer + 1)
    proxy = accounts[firstProducer]['name']
    retry(args.clsou + 'system regproxy ' + proxy)
    sleep(1.0)
    for i in range(b, e):
        voter = accounts[i]['name']
        retry(args.clsou + 'system voteproducer proxy ' + voter + ' ' + proxy)

def updateAuth(account, permission, parent, controller):
    run(args.clsou + 'push action sou updateauth' + jsonArg({
        'account': account,
        'permission': permission,
        'parent': parent,
        'auth': {
            'threshold': 1, 'keys': [], 'waits': [],
            'accounts': [{
                'weight': 1,
                'permission': {'actor': controller, 'permission': 'active'}
            }]
        }
    }) + '-p ' + account + '@' + permission)

def resign(account, controller):
    updateAuth(account, 'owner', '', controller)
    updateAuth(account, 'active', 'owner', controller)
    sleep(1)
    run(args.clsou + 'get account ' + account)

def randomTransfer(b, e):
    for j in range(20):
        src = accounts[random.randint(b, e - 1)]['name']
        dest = src
        while dest == src:
            dest = accounts[random.randint(b, e - 1)]['name']
        run(args.clsou + 'transfer -f ' + src + ' ' + dest + ' "0.0001 ' + args.symbol + '"' + ' || true')

def msigProposeReplaceSystem(proposer, proposalName):
    requestedPermissions = []
    for i in range(firstProducer, firstProducer + numProducers):
        requestedPermissions.append({'actor': accounts[i]['name'], 'permission': 'active'})
    trxPermissions = [{'actor': 'sou', 'permission': 'active'}]
    with open(fastUnstakeSystem, mode='rb') as f:
        setcode = {'account': 'sou', 'vmtype': 0, 'vmversion': 0, 'code': f.read().hex()}
    run(args.clsou + 'multisig propose ' + proposalName + jsonArg(requestedPermissions) +
        jsonArg(trxPermissions) + 'sou setcode' + jsonArg(setcode) + ' -p ' + proposer)

def msigApproveReplaceSystem(proposer, proposalName):
    for i in range(firstProducer, firstProducer + numProducers):
        run(args.clsou + 'multisig approve ' + proposer + ' ' + proposalName +
            jsonArg({'actor': accounts[i]['name'], 'permission': 'active'}) +
            '-p ' + accounts[i]['name'])

def msigExecReplaceSystem(proposer, proposalName):
    retry(args.clsou + 'multisig exec ' + proposer + ' ' + proposalName + ' -p ' + proposer)

def msigReplaceSystem():
    run(args.clsou + 'push action sou buyrambytes' + jsonArg(['sou', accounts[0]['name'], 200000]) + '-p sou')
    sleep(1)
    msigProposeReplaceSystem(accounts[0]['name'], 'fast.unstake')
    sleep(1)
    msigApproveReplaceSystem(accounts[0]['name'], 'fast.unstake')
    msigExecReplaceSystem(accounts[0]['name'], 'fast.unstake')

def produceNewAccounts():
    with open('newusers', 'w') as f:
        for i in range(120_000, 200_000):
            x = getOutput(args.clsou + 'create key --to-console')
            r = re.match('Private key: *([^ \n]*)\nPublic key: *([^ \n]*)', x, re.DOTALL | re.MULTILINE)
            name = 'user'
            for j in range(7, -1, -1):
                name += chr(ord('a') + ((i >> (j * 4)) & 15))
            print(i, name)
            f.write('        {"name":"%s", "pvt":"%s", "pub":"%s"},\n' % (name, r[1], r[2]))

def stepKillAll():
    run('killall ksoud nodesou || true')
    sleep(1.5)
def stepStartWallet():
    startWallet()
    importKeys()
def stepStartBoot():
    startNode(0, {'name': 'sou', 'pvt': args.private_key, 'pub': args.public_key})
    sleep(8)
def stepInstallSystemContracts():
    run(args.clsou + 'set contract sou.token ' + args.contracts_dir + '/sou.token/')
    run(args.clsou + 'set contract sou.msig ' + args.contracts_dir + '/sou.msig/')
    sleep(8)
def stepCreateTokens():
    retry(args.clsou + 'push action sou.token create \'["sou", "10000000000.0000 %s"]\' -p sou.token' % (args.symbol))
    totalAllocation = allocateFunds(0, len(accounts))
    run(args.clsou + 'push action sou.token issue \'["sou", "%s", "init"]\' -p sou' % intToCurrency(totalAllocation))
    sleep(8)
def stepSetSystemContract():
    # All of the protocol upgrade features introduced in v1.8 first require a special protocol
    # feature (codename PREACTIVATE_FEATURE) to be activated and for an updated version of the system
    # contract that makes use of the functionality introduced by that feature to be deployed.

    # activate PREACTIVATE_FEATURE before installing sou.system
    retry('curl -X POST http://127.0.0.1:%d' % args.http_port +
          '/v1/producer/schedule_protocol_feature_activations ' +
          '-d \'{"protocol_features_to_activate": ["0ec7e080177b2c02b278d5088611686b49d739925a92d9bfcacd7fc6b74053bd"]}\'')
    sleep(8)

    # install sou.system the older version first
    retry(args.clsou + 'set contract sou ' + args.old_contracts_dir + '/sou.system/ -x 90')
    sleep(8)

    # activate remaining features
    # GET_SENDER
    retry(args.clsou + 'push action sou activate \'["f0af56d2c5a48d60a4a5b5c903edfb7db3a736a94ed589d0b797df33ff9d3e1d"]\' -p sou')
    # FORWARD_SETCODE
    retry(args.clsou + 'push action sou activate \'["2652f5f96006294109b3dd0bbde63693f55324af452b799ee137a81a905eed25"]\' -p sou')
    # ONLY_BILL_FIRST_AUTHORIZER
    retry(args.clsou + 'push action sou activate \'["8ba52fe7a3956c5cd3a656a3174b931d3bb2abb45578befc59f283ecd816a405"]\' -p sou')
    # RESTRICT_ACTION_TO_SELF
    retry(args.clsou + 'push action sou activate \'["ad9e3d8f650687709fd68f4b90b41f7d825a365b02c23a636cef88ac2ac00c43"]\' -p sou@active')
    # DISALLOW_EMPTY_PRODUCER_SCHEDULE
    retry(args.clsou + 'push action sou activate \'["68dcaa34c0517d19666e6b33add67351d8c5f69e999ca1e37931bc410a297428"]\' -p sou@active')
    # FIX_LINKAUTH_RESTRICTION
    retry(args.clsou + 'push action sou activate \'["e0fb64b1085cc5538970158d05a009c24e276fb94e1a0bf6a528b48fbc4ff526"]\' -p sou@active')
    # REPLACE_DEFERRED
    retry(args.clsou + 'push action sou activate \'["ef43112c6543b88db2283a2e077278c315ae2c84719a8b25f25cc88565fbea99"]\' -p sou@active')
    # NO_DUPLICATE_DEFERRED_ID
    retry(args.clsou + 'push action sou activate \'["4a90c00d55454dc5b059055ca213579c6ea856967712a56017487886a4d4cc0f"]\' -p sou@active')
    # ONLY_LINK_TO_EXISTING_PERMISSION
    retry(args.clsou + 'push action sou activate \'["1a99a59d87e06e09ec5b028a9cbb7749b4a5ad8819004365d02dc4379a8b7241"]\' -p sou@active')
    # RAM_RESTRICTIONS
    retry(args.clsou + 'push action sou activate \'["4e7bf348da00a945489b2a681749eb56f5de00b900014e137ddae39f48f69d67"]\' -p sou@active')
    # WEBAUTHN_KEY
    retry(args.clsou + 'push action sou activate \'["4fca8bd82bbd181e714e283f83e1b45d95ca5af40fb89ad3977b653c448f78c2"]\' -p sou@active')
    # WTMSIG_BLOCK_SIGNATURES
    retry(args.clsou + 'push action sou activate \'["299dcb6af692324b899b39f16d5a530a33062804e41f09dc97e9f156b4476707"]\' -p sou@active')
    sleep(8)

    retry(args.clsou + 'push action sou setpriv' + jsonArg(['sou.msig', 1]) + '-p sou@active')

    # install sou.system latest version
    retry(args.clsou + 'set abi sou ' + args.contracts_dir + '/sou.system/sou.system.abi -x 90')
    retry(args.clsou + 'set code sou ' + args.contracts_dir + '/sou.system/sou.system.wasm -x 90')
    sleep(8)

def stepInitSystemContract():
    run(args.clsou + 'push action sou init' + jsonArg(['0', '4,' + args.symbol]) + '-p sou@active')
    sleep(8)
def stepCreateStakedAccounts():
    createStakedAccounts(0, len(accounts))
def stepRegProducers():
    regProducers(firstProducer, firstProducer + numProducers)
    sleep(8)
    listProducers()
def stepStartProducers():
    startProducers(firstProducer, firstProducer + numProducers)
    sleep(args.producer_sync_delay)
def stepVote():
    vote(0, 0 + args.num_voters)
    sleep(8)
    listProducers()
    sleep(8)
def stepProxyVotes():
    proxyVotes(0, 0 + args.num_voters)
def stepResign():
    resign('sou', 'sou.prods')
    for a in systemAccounts:
        resign(a, 'sou')
def stepTransfer():
    while True:
        randomTransfer(0, args.num_senders)
def stepLog():
    run('tail -n 60 ' + args.nodes_dir + '00-sou/stderr')

# Command Line Arguments

parser = argparse.ArgumentParser()

commands = [
    ('k', 'kill',               stepKillAll,                True,    "Kill all nodesou and ksoud processes"),
    ('w', 'wallet',             stepStartWallet,            True,    "Start ksoud, create wallet, fill with keys"),
    ('b', 'boot',               stepStartBoot,              True,    "Start boot node"),
    ('s', 'sys',                createSystemAccounts,       True,    "Create system accounts (sou.*)"),
    ('c', 'contracts',          stepInstallSystemContracts, True,    "Install system contracts (token, msig)"),
    ('t', 'tokens',             stepCreateTokens,           True,    "Create tokens"),
    ('S', 'sys-contract',       stepSetSystemContract,      True,    "Set system contract"),
    ('I', 'init-sys-contract',  stepInitSystemContract,     True,    "Initialiaze system contract"),
    ('T', 'stake',              stepCreateStakedAccounts,   True,    "Create staked accounts"),
    ('p', 'reg-prod',           stepRegProducers,           True,    "Register producers"),
    ('P', 'start-prod',         stepStartProducers,         True,    "Start producers"),
    ('v', 'vote',               stepVote,                   True,    "Vote for producers"),
    ('R', 'claim',              claimRewards,               True,    "Claim rewards"),
    ('x', 'proxy',              stepProxyVotes,             True,    "Proxy votes"),
    ('q', 'resign',             stepResign,                 True,    "Resign sou"),
    ('m', 'msg-replace',        msigReplaceSystem,          False,   "Replace system contract using msig"),
    ('X', 'xfer',               stepTransfer,               False,   "Random transfer tokens (infinite loop)"),
    ('l', 'log',                stepLog,                    True,    "Show tail of node's log"),
]

parser.add_argument('--public-key', metavar='', help="SOU Public Key", default='SOU8Znrtgwt8TfpmbVpTKvA2oB8Nqey625CLN8bCN3TEbgx86Dsvr', dest="public_key")
parser.add_argument('--private-key', metavar='', help="SOU Private Key", default='5K463ynhZoCDDa4RDcr63cUwWLTnKqmdcoTKTHBjqoKfv4u5V7p', dest="private_key")
parser.add_argument('--clsou', metavar='', help="clsou command", default='../../build/programs/clsou/clsou --wallet-url http://127.0.0.1:6666 ')
parser.add_argument('--nodesou', metavar='', help="Path to nodesou binary", default='../../build/programs/nodesou/nodesou')
parser.add_argument('--ksoud', metavar='', help="Path to ksoud binary", default='../../build/programs/ksoud/ksoud')
parser.add_argument('--contracts-dir', metavar='', help="Path to latest contracts directory", default='../../build/contracts/')
parser.add_argument('--old-contracts-dir', metavar='', help="Path to 1.8.x contracts directory", default='../../build/contracts/')
parser.add_argument('--nodes-dir', metavar='', help="Path to nodes directory", default='./nodes/')
parser.add_argument('--genesis', metavar='', help="Path to genesis.json", default="./genesis.json")
parser.add_argument('--wallet-dir', metavar='', help="Path to wallet directory", default='./wallet/')
parser.add_argument('--log-path', metavar='', help="Path to log file", default='./output.log')
parser.add_argument('--symbol', metavar='', help="The sou.system symbol", default='SOU')
parser.add_argument('--user-limit', metavar='', help="Max number of users. (0 = no limit)", type=int, default=3000)
parser.add_argument('--max-user-keys', metavar='', help="Maximum user keys to import into wallet", type=int, default=100)
parser.add_argument('--ram-funds', metavar='', help="How much funds for each user to spend on ram", type=float, default=0.1)
parser.add_argument('--min-stake', metavar='', help="Minimum stake before allocating unstaked funds", type=float, default=0.9)
parser.add_argument('--max-unstaked', metavar='', help="Maximum unstaked funds", type=float, default=0)
parser.add_argument('--producer-limit', metavar='', help="Maximum number of producers. (0 = no limit)", type=int, default=21)
parser.add_argument('--min-producer-funds', metavar='', help="Minimum producer funds", type=float, default=100.0000)
parser.add_argument('--num-producers-vote', metavar='', help="Number of producers for which each user votes", type=int, default=21)
parser.add_argument('--num-voters', metavar='', help="Number of voters", type=int, default=1)
parser.add_argument('--num-senders', metavar='', help="Number of users to transfer funds randomly", type=int, default=0)
parser.add_argument('--producer-sync-delay', metavar='', help="Time (s) to sleep to allow producers to sync", type=int, default=80)
parser.add_argument('-a', '--all', action='store_true', help="Do everything marked with (*)")
parser.add_argument('-H', '--http-port', type=int, default=8000, metavar='', help='HTTP port for clsou')

for (flag, command, function, inAll, help) in commands:
    prefix = ''
    if inAll: prefix += '*'
    if prefix: help = '(' + prefix + ') ' + help
    if flag:
        parser.add_argument('-' + flag, '--' + command, action='store_true', help=help, dest=command)
    else:
        parser.add_argument('--' + command, action='store_true', help=help, dest=command)

args = parser.parse_args()

args.clsou += ' --url http://127.0.0.1:%d ' % args.http_port

logFile = open(args.log_path, 'a')

logFile.write('\n\n' + '*' * 80 + '\n\n\n')

with open('accounts.json') as f:
    a = json.load(f)
    if args.user_limit:
        del a['users'][args.user_limit:]
    if args.producer_limit:
        del a['producers'][args.producer_limit:]
    firstProducer = len(a['users'])
    numProducers = len(a['producers'])
    accounts = a['users'] + a['producers']

maxClients = numProducers + 10

haveCommand = False
for (flag, command, function, inAll, help) in commands:
    if getattr(args, command) or inAll and args.all:
        if function:
            haveCommand = True
            function()
if not haveCommand:
    print('bios-boot-tutorial.py: Tell me what to do. -a does almost everything. -h shows options.')
