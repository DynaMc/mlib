import struct
from copy import deepcopy
chunks = lambda l, n: [l[x: x+n] for x in xrange(0, len(l), n)]

from Crypto.PublicKey import RSA

class RSAKEY(object):

    def __init__(self,d):
        self.bin = d
        self.off = 0 
        self.bits = 0
    def get_int(self,b):
        r=long(self.bin[self.off:self.off+self.bits/b][::-1].encode('hex'),16)
        self.off += self.bits/b
        return r

    def unpack(self):

        if self.bin[0] not in ["\x06","\x07"]:
            return None

        if self.bin[8:12] not in ['RSA1','RSA2']:
            return None
        key = {}
        priv = self.bin[0] == "\x07"
        self.bits,key['e'] = struct.unpack('II',self.bin[12:20])
        self.off = 20
        key['n']= self.get_int(8)
        if priv:
            key['p1'] = self.get_int(16)
            key['p2'] = self.get_int(16)
            key['exp1'] = self.get_int(16)
            key['exp2'] = self.get_int(16)
            key['coeff'] = self.get_int(16)
            key['d'] = self.get_int(8)
            ko = RSA.construct((key['n'],long(key['e']),key['d']))
        else:
            ko = RSA.construct((key['n'],long(key['e'])))
        return ko,key


def parse_pubkey_rsa(rsa_bin, ignore_len=False):
    r = RSAKEY(rsa_bin).unpack()
    if not r:
        return rsa_bin.encode('hex')
    return r[1]

def parse_key_ecc(ecc_bin):
    s, = struct.unpack('I',ecc_bin[:4])
    ecc_bin = ecc_bin[4:4+s]
    keys, = struct.unpack('I',ecc_bin[4:8])
    t = {'ECS3':'ecdsa_pub_p384','ECS4':'ecdsa_priv_p384'}[ecc_bin[0:4]]
    x = ecc_bin[8:8+keys]
    y = ecc_bin[8+keys:keys*2+8]
    return {'t':t,'x': str(int(x.encode('hex'),16)),'y':str(int(y.encode('hex'),16))}

def parse_asn1_pubkey(asn1):
    import bitarray
    from pyasn1.codec.der.decoder import decode
    bs = decode(asn1)[0][1] ## frist is some oid
    b=bitarray.bitarray(str(bs).replace(',','').replace(' ','')[1:-1])
    v = decode(b.tobytes())[0]
    return {'n': str(v[0]), 'e': int(str(v[1]))}



def generic_unparse(data,do_rest=False):
    cfg = deepcopy(data)
    r = ['INJECTS']
    r.append('='*80)
    for inj in cfg['injects']:

        r.append('Target: '+inj['target'])
        inj['injects']
        for i in inj['injects']:
            if 'pre' in i:
                r.append('<data_before>')
                r.append(i['pre'])
                r.append('<data_end>')
            if 'post' in i:
                r.append('<data_after>')
                r.append(i['post'])
                r.append('<data_end>')
            if 'inj' in i:
                r.append('<data_inject>')
                r.append(i['inj'])
                r.append('<data_end>')

    r.append('\n\nACTIONS')
    r.append('='*80)
    for a  in cfg.get('actions',[]):
        r.append('Target: %s | Action: %s | Type: %s'%(a['target'],a['action'],a['type']))
    r.append("\n")
    if do_rest:
        for el in cfg:
            if el in ['injects','actions']: continue
            
            r.append(el.upper())
            r.append('='*80)
            for e in cfg[el]:
                r.append(str(e))
        r.append("\n")
    return "\n".join(r)


def generic_parse(_data):
            
    if not _data:
        return None

    off = _data.find('set_url')
    off2 = 0
    ret = []
    while off < len(_data):
        off2 = _data.find('set_url',off+7)
        if off2 == -1:
            ret.append(_process_ent(_data[off:]))
            break
        else:
            ret.append(_process_ent(_data[off:off2]))
        off = off2
    #print off
    return ret
        
def _process_ent(d):
    try:
        ret = {}
        __process_ent(d,ret)
    except Exception as e:
        import traceback
        print '-'*20
        print d
        print '#'*20
        print ret
        print '-'*20
        traceback.print_exc()
    return ret

    
def __process_ent(d,ret):
    TRNSL ={'data_before':'pre','data_after':'post','data_inject':'inj','data_count':'cnt'}
    d = d.strip()

#    try:
    trgt,rest = d.split("\n",1)
#    except:
#        print '#'*20
#        print rest
#        raise Exception('e1')

    try:
        _,url,fl = trgt.strip().split(' ')
    except ValueError:
        if trgt.strip() == 'set_url':
            #huh target url in new line?
            url, rest = rest.split("\n",1)
        else:
            _,url =  trgt.strip().split(' ')

        fl = ''
    ret['flags']=fl
    ret['target']=url
    ret['injects']=[]
    
    r = {}
    
    while rest:
        ## skip comments?
        if rest.startswith(';') or rest.startswith('#'):
            o=rest.find("\n")
            if o == -1:
                return ret

            rest = rest[o+1:]
            continue
        

#        try:
        tag, rest2 = rest.split("\n",1)
        # except:
        #     print '#'*20
        #     print `rest`
        #     raise Exception('e2')
        
        rest = rest2
        tag = tag.strip()
        if not tag:
            continue

        if tag == 'data_end':
            log.error('fucked up config... skip it...')
            continue
        
        _end = rest.find('data_end')
        r[TRNSL[tag]]= rest[:_end].strip().decode('unicode-escape')

        if tag == 'data_after':
            ret['injects'].append(r)
            r = {}
        rest = rest[_end+8:].strip()
    
