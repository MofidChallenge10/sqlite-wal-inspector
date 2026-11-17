import argparse, json, struct, sys
from pathlib import Path

def inspect_wal(path):
    data=Path(path).read_bytes()
    if len(data)<32: raise ValueError('WAL header is incomplete')
    magic,version,page_size,checkpoint,salt1,salt2,_,_=struct.unpack('>8I',data[:32])
    if magic not in (0x377f0682,0x377f0683): raise ValueError('invalid SQLite WAL magic')
    if page_size==1: page_size=65536
    if page_size<512 or page_size>65536 or page_size&(page_size-1): raise ValueError('invalid WAL page size')
    frame_size=24+page_size; payload=len(data)-32; complete,tail=divmod(payload,frame_size)
    commits=[]; invalid_salts=0; zero_page=0
    for i in range(complete):
        offset=32+i*frame_size
        page,db_size,frame_salt1,frame_salt2,_,_=struct.unpack('>6I',data[offset:offset+24])
        if page==0: zero_page+=1
        if (frame_salt1,frame_salt2)!=(salt1,salt2): invalid_salts+=1
        if db_size>0: commits.append(i+1)
    return {'path':str(path),'bytes':len(data),'magic':f'0x{magic:08x}','version':version,'page_size':page_size,'checkpoint_sequence':checkpoint,'frames':complete,'committed_transactions':len(commits),'last_commit_frame':commits[-1] if commits else None,'trailing_bytes':tail,'truncated_tail':tail!=0,'invalid_salt_frames':invalid_salts,'zero_page_frames':zero_page}

def main():
    p=argparse.ArgumentParser(description='Inspect a SQLite -wal file without checkpointing it')
    p.add_argument('database',help='database path; the adjacent -wal file is inspected'); p.add_argument('--json',action='store_true')
    a=p.parse_args(); wal=a.database+'-wal'
    try: result=inspect_wal(wal)
    except (OSError,ValueError) as e: print(f'error: {e}',file=sys.stderr); return 2
    if a.json: print(json.dumps(result,indent=2))
    else:
        print(f"WAL: {wal}\nPage size: {result['page_size']}\nFrames: {result['frames']}\nCommitted transactions: {result['committed_transactions']}\nLast commit frame: {result['last_commit_frame'] or '(none)'}\nTruncated tail: {'yes' if result['truncated_tail'] else 'no'}\nInvalid salt frames: {result['invalid_salt_frames']}")
    return 1 if result['truncated_tail'] or result['invalid_salt_frames'] or result['zero_page_frames'] else 0
if __name__=='__main__': raise SystemExit(main())
