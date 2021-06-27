from __future__ import print_function
import json
import enum

_srz_classes = {}

class DumpMode(enum.Enum):
  BASE = 1
  DERIVED = 2

def _cls_register( name, cls ): _srz_classes.update (**{name:cls})

class LookupError (RuntimeError):
    pass

def _cls_rvslookup( cls ):
    result = [n for n,c in _srz_classes.items() if c is cls]
    if error_if_missing:
        if not result: raise LookupError('Class {} could not be found. use @register or @register_custom'.format(cls.__name__))
    return result[0]

def _cls_lookup( name, error_if_missing=False ):
    x = _srz_classes.get(name)
    if error_if_missing:
        if x is None: raise LookupError('Class name of {!r} could not be found. use @register or @register_custom'.format(name))
    return x


#===  API

def deep_factory (obj):
    if isinstance(obj, dict): return factory(obj,deep=True)
    elif isinstance(obj, (list,tuple)): return memb.__class__ ( deep_factory(o) for o in obj )
    else: return obj

def factory (obj, deep=False):
    xform = lambda o :deep_factory (o) if deep else o
    if type(obj) is dict:
        cls = None
        if len(obj) == 1:
            clsname,inst_info = obj.items()[0]
            cls = _cls_lookup( clsname )
        if cls is None:
            return {k:xform(v) for k,v in obj.items()} # should expand normal dicts without
                                                       # endless recursion
        else:
            return cls.ctor(xform( inst_info ))
    return obj


def deep_dumper (self):
    dmp = self._dump()
    dct = dmp.values()[0]   # instance dictionary for iteration
    dct_ = dct.copy()       # dct_ into which sub-objects can be serialized if not JSON-dump compatible
    for x,y in dct.items():
	if not isinstance(y,(int,str,float,tuple,list,dict)): dct_[x] = deep_dumper(y)
    rv = { dmp.keys()[0] : dct_ }
    return rv


def register (cls, name = None, dump_mode = DumpMode.BASE):
    def _dump(self,name = name):
        return { name or self.__class__.__name__ : self.__dict__ }
    cls._dump = _dump
    if dump_mode == DumpMode.BASE:
        cls.dump = cls._dump
    elif callable( dump_mode ):
        cls.dump = dump_mode
#-->else depend on derived method to implement dump()
    def ctor(cls,dct):
        return cls(**dct)
    cls.ctor = classmethod( ctor )
    _cls_register(name or cls.__name__, cls)
    return cls

class register_custom:
  def __init__(self, name = None, dump_mode = DumpMode.BASE):
      self.name = name
      self.dump_mode = dump_mode
  def __call__(self, cls):
      return register(cls, name = self.name,
                           dump_mode = self.dump_mode)

class Base(object):
    def __init__(self,**kw):
        for k,v in kw.items(): setattr(self,k,v)
    def __repr__(self): return '<{} {}>'.format(self.__class__.__name__,self.__dict__)


if __name__ == '__main__':


    @register_custom( dump_mode = DumpMode.DERIVED )
    class Derived_0(Base):
        def __init__(self,i=3,**kw):
            self.i = i
            super(Derived_0,self).__init__(**kw)
            try:
                self.i = factory(self.i)
            except: pass

        def dump( self ):
            dmp = self._dump()
            dct = dmp.values()[0]   # instance dictionary for iteration
            dct_ = dct.copy()       # dct_ into which sub-objects can be serialized if not JSON-dump compatible
            for x,y in dct.items():
                if not isinstance(y,(int,str,float,tuple,list,dict)): dct_[x] = y.dump()
            rv = { dmp.keys()[0] : dct_ }
            return rv

        def __repr__(self): # --> to show virtual methods are honored, shatnerize the base class repr
            return super(Derived_0,self).__repr__().replace(' ', ' ... ')


    @register_custom(name = '__Bag_')
    class Bag(Base):
      pass

    @register
    class OtherClass(Base): pass

    derived = Derived_0(i=OtherClass())
    dd = derived.dump()
    print( 'json.dump of derived ==> ',json.dumps(dd) )
    print('Derived_0 object dump() output:',dd)

    dcopy = factory(dd)
    print('Reconstituted object: (note __repr__ has custom derived behavior', dcopy)

    b = Bag()
    b.attr1 = {'a':3}
    b.attr2 = [ 'hello','world' ]

    s = b.dump()
    print ('bag dump ->', s)
    print('************',factory(s).__class__,b.__class__)

#----+----+----+

    @register_custom( dump_mode = deep_dumper )
    class Abc:
       i = 3
       def __init__(self, x=123 ): self.x=x
    
    i0 = Abc()
    xxx=(i0.dump())
    i1 = deep_factory (xxx)
    print (i0, i0.x, i1, i1.x)
