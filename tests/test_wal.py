import pathlib, struct, tempfile, unittest, sys
sys.path.insert(0,'src')
from sqlite_wal_inspector.__main__ import inspect_wal
class TestWal(unittest.TestCase):
 def make_wal(self,path,tail=b''):
  page=512; salt1,salt2=11,22
  header=struct.pack('>8I',0x377f0682,3007000,page,0,salt1,salt2,0,0)
  def frame(page_no,db_size): return struct.pack('>6I',page_no,db_size,salt1,salt2,0,0)+b'X'*page
  path.write_bytes(header+frame(1,0)+frame(2,2)+tail)
 def test_frames_and_commit(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'x-wal'; self.make_wal(p); r=inspect_wal(p)
   self.assertEqual(r['frames'],2); self.assertEqual(r['committed_transactions'],1); self.assertEqual(r['last_commit_frame'],2)
 def test_truncated_tail(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'x-wal'; self.make_wal(p,b'bad'); self.assertTrue(inspect_wal(p)['truncated_tail'])
 def test_real_sqlite_wal(self):
  import sqlite3
  with tempfile.TemporaryDirectory() as d:
   database=pathlib.Path(d)/'live.db'; connection=sqlite3.connect(database)
   try:
    connection.execute('PRAGMA journal_mode=WAL'); connection.execute('PRAGMA wal_autocheckpoint=0')
    connection.execute('CREATE TABLE events(value TEXT)'); connection.execute('INSERT INTO events VALUES (?)',('created',)); connection.commit()
    result=inspect_wal(str(database)+'-wal')
    self.assertGreaterEqual(result['frames'],1); self.assertEqual(result['invalid_salt_frames'],0)
   finally: connection.close()
 def test_bad_magic(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'x-wal'; p.write_bytes(b'0'*40)
   with self.assertRaises(ValueError): inspect_wal(p)
if __name__=='__main__': unittest.main()
