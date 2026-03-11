#!/usr/bin/env python3
"""watchfile - Watch files for changes. Zero deps."""
import sys,os,time,hashlib
def fhash(p):
    try:return hashlib.md5(open(p,'rb').read()).hexdigest()
    except:return None
def main():
    paths=sys.argv[1:] or ['.']
    state={}
    for p in paths:
        if os.path.isdir(p):
            for r,_,fs in os.walk(p):
                for f in fs:fp=os.path.join(r,f);state[fp]=fhash(fp)
        else:state[p]=fhash(p)
    print(f'Watching {len(state)} files...')
    try:
        while True:
            time.sleep(1)
            for fp in list(state):
                h=fhash(fp)
                if h!=state[fp]:print(f'CHANGED: {fp}');state[fp]=h
    except KeyboardInterrupt:pass
if __name__=='__main__':main()
