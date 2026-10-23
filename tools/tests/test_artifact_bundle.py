"""Cleanup bundle confinement before effects; all filesystem data is synthetic."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('artifact_bundle',Path(__file__).resolve().parents[1]/'artifact_bundle.py')
bundle=importlib.util.module_from_spec(spec);spec.loader.exec_module(bundle)


class BundleConfinement(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.root=self.base/'restored'

    def archive(self,links=None,files=None):
        archive=self.base/'bundle.tar.gz';entries={}
        with tarfile.open(archive,'w:gz') as tar:
            for name,data in (files or {}).items():
                member=tarfile.TarInfo(name);member.mode=0o644;member.size=len(data)
                tar.addfile(member,io.BytesIO(data))
                entries[name]=dict(kind='file',mode=0o644,size=len(data),sha256=hashlib.sha256(data).hexdigest())
            for name,target in (links or {}).items():
                member=tarfile.TarInfo(name);member.mode=0o777;member.type=tarfile.SYMTYPE;member.linkname=target
                tar.addfile(member);entries[name]=dict(kind='symlink',mode=0o777,target=target)
        inventory=self.base/'inventory.json';inventory.write_text(json.dumps(entries))
        descriptor=self.base/'descriptor.json';descriptor.write_text(json.dumps(dict(format=1,size=archive.stat().st_size,sha256=bundle.digest(archive),members=len(entries),inventory=inventory.name,inventory_sha256=bundle.digest(inventory))))
        return archive,descriptor,entries

    def refused(self,links):
        archive,descriptor,entries=self.archive(links)
        with self.assertRaises(ValueError):bundle.verify(archive,descriptor)
        self.assertFalse(self.root.exists())
        # Restore itself must enforce the same graph preflight, even if called
        # directly with an inventory that has not passed verify.
        with self.assertRaises(ValueError):bundle.restore(archive,self.root,entries)
        self.assertFalse(self.root.exists())

    def test_direct_escape(self):self.refused({'link':'../outside'})
    def test_chained_escape(self):self.refused({'a':'.','b':'a/../outside'})
    def test_chained_escape_reversed_inventory(self):self.refused({'b':'a/../outside','a':'.'})
    def test_nested_chained_escape(self):self.refused({'dir/a':'..','b':'dir/a/../outside'})
    def test_case_alias_chained_escape(self):self.refused({'a':'.','b':'A/../outside'})
    def test_unicode_alias_chained_escape(self):self.refused({'caf\u00e9':'.','b':'cafe\u0301/../outside'})
    def test_self_cycle(self):self.refused({'a':'a'})
    def test_two_link_cycle(self):self.refused({'a':'b','b':'a'})
    def test_expanding_cycle(self):self.refused({'a':'a/inside'})
    def test_cycle_cannot_be_hidden_by_parent_normalization(self):self.refused({'a':'a/..'})
    def test_absolute_target(self):self.refused({'link':'/outside'})
    def test_indirect_absolute_target(self):self.refused({'a':'b','b':'/outside'})
    def test_expansion_limit(self):self.refused({f'a{i}':f'a{i+1}' for i in range(41)})
    def test_ambiguous_alias_leaves(self):self.refused({'Name':'.','name':'.'})
    def test_parent_symlink_in_inventory(self):self.refused({'a':'.','a/link':'inside'})

    def test_valid_internal_dangling_chain(self):
        archive,descriptor,_=self.archive({'a':'.','b':'a/inside'})
        _,entries=bundle.verify(archive,descriptor);bundle.restore(archive,self.root,entries)
        self.assertEqual((self.root/'b').resolve(),self.root/'inside')

    def test_valid_parent_target_remains_inside(self):
        archive,descriptor,_=self.archive({'dir/link':'../data'},{'data':b'payload'})
        _,entries=bundle.verify(archive,descriptor);bundle.restore(archive,self.root,entries)
        self.assertEqual((self.root/'dir/link').read_bytes(),b'payload')

    def test_repeated_link_is_not_a_cycle(self):
        archive,descriptor,_=self.archive({'a':'dir','b':'a/../a/data'},{'dir/data':b'payload'})
        _,entries=bundle.verify(archive,descriptor);bundle.restore(archive,self.root,entries)
        self.assertEqual((self.root/'b').read_bytes(),b'payload')

    def test_runtime_style_alias_and_idempotence(self):
        archive,descriptor,_=self.archive({'bin/python3':'python3.13','bin/python':'python3'},{'bin/python3.13':b'SYNTHETIC EXECUTABLE'})
        _,entries=bundle.verify(archive,descriptor);bundle.restore(archive,self.root,entries)
        original=(self.root/'bin/python3.13').read_bytes();bundle.restore(archive,self.root,entries)
        self.assertEqual((self.root/'bin/python').read_bytes(),original)

    def test_existing_target_link_escape_refused_before_new_files(self):
        archive,descriptor,_=self.archive({'new-link':'existing/child'},{'first':b'never written'})
        _,entries=bundle.verify(archive,descriptor)
        self.root.mkdir();(self.root/'existing').symlink_to(self.base/'outside')
        with self.assertRaises(ValueError):bundle.restore(archive,self.root,entries)
        self.assertEqual([p.name for p in self.root.iterdir()],['existing'])
        self.assertFalse((self.base/'outside').exists())

    def test_existing_target_link_chain_uses_resolve_order(self):
        archive,descriptor,_=self.archive({'new-link':'existing/../outside'})
        _,entries=bundle.verify(archive,descriptor)
        self.root.mkdir();(self.root/'existing').symlink_to('.')
        with self.assertRaises(ValueError):bundle.restore(archive,self.root,entries)
        self.assertEqual([p.name for p in self.root.iterdir()],['existing'])

    def test_existing_internal_target_alias_remains_valid(self):
        archive,descriptor,_=self.archive({'new-link':'existing/data'},{'inside/data':b'payload'})
        _,entries=bundle.verify(archive,descriptor)
        self.root.mkdir();(self.root/'existing').symlink_to('inside')
        bundle.restore(archive,self.root,entries)
        self.assertEqual((self.root/'new-link').read_bytes(),b'payload')

    def test_existing_parent_symlink_refused(self):
        archive,descriptor,_=self.archive(files={'dir/data':b'payload'})
        _,entries=bundle.verify(archive,descriptor)
        self.root.mkdir();(self.root/'dir').symlink_to(self.base/'outside')
        with self.assertRaises(ValueError):bundle.restore(archive,self.root,entries)
        self.assertFalse((self.base/'outside').exists())

    def test_overwrite_refused(self):
        archive,descriptor,_=self.archive(files={'data':b'payload'})
        _,entries=bundle.verify(archive,descriptor)
        self.root.mkdir();(self.root/'data').write_bytes(b'KEEP')
        with self.assertRaises(ValueError):bundle.restore(archive,self.root,entries)
        self.assertEqual((self.root/'data').read_bytes(),b'KEEP')

    def test_traversal_member_refused(self):
        for name in ('../outside','a/../outside','a//outside','/outside','a/./outside','a\\outside'):
            with self.subTest(name=name):
                archive,descriptor,_=self.archive(files={name:b'payload'})
                with self.assertRaises(ValueError):bundle.verify(archive,descriptor)
                self.assertFalse(self.root.exists())

    def test_hash_mismatch_refused(self):
        archive,descriptor,_=self.archive(files={'data':b'payload'})
        archive.write_bytes(archive.read_bytes()+b'corrupt')
        with self.assertRaises(ValueError):bundle.verify(archive,descriptor)
        self.assertFalse(self.root.exists())


if __name__=='__main__':unittest.main()
