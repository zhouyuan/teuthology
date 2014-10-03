import os
from fractions import gcd

class Matrix:
    def size(self): pass
    def index(self, i):
        """
        index() should return a tree represented using tuples and frozensets
        """
        pass
    def minscanlen(self):
        """
        min run require to get a good sample
        """
        pass

    def cyclicity(self):
        return self.size() / self.minscanlen()

class Cycle(Matrix):
    """
    Run a matrix multiple times
    """
    def __init__(self, num, mat):
        self.mat = mat
        self.num = num
    def size(self):
        return self.mat.size() * self.num
    def index(self, i):
        return self.mat.index(i % self.mat.size())
    def minscanlen(self):
        return self.mat.minscanlen()

class Base(Matrix):
    """
    Just a single item.
    """
    def __init__(self, item):
        self.item = item
    def size(self):
        return 1
    def index(self, i):
        return self.item
    def minscanlen(self):
        return 1

class Product(Matrix):
    """
    Builds items by taking one item from each submatrix.  Contiguous subsequences
    should move through all dimensions.
    """
    def __init__(self, item, _submats):
        assert len(_submats) > 0
        self.item = item

        submats = sorted(
            [((i.size(), ind), i) for (i, ind) in \
             zip(_submats, range(len(_submats)))], reverse=True)
        self.submats = []
        self._size = 1
        for ((size, _), submat) in submats:
            self.submats.append((self._size, submat))
            self._size *= size
        self.submats.reverse()

        self._minscanlen = max([i.minscanlen() for i in _submats])

    def minscanlen(self):
        return self._minscanlen

    def size(self):
        return self._size

    def _index(self, i, submats):
        """
        We recursively reduce the N dimension problem to a two dimension problem.

        index(i) = (lmat.index(i % lmat.size()), rmat.index(i % rmat.size()))
        would simply work if lmat.size() and rmat.size() are relatively prime.

        In general, if the gcd(lmat.size(), rmat.size()) == N, index(i) would be
        periodic on the interval (lmat.size() * rmat.size()) / N.  To adjust, we
        increment the lmat index number on each repeat.  Each of the N repeats
        must therefore be distinct from the previous ones resulting in
        lmat.size() * rmat.size() combinations.
        """
        assert len(submats) > 0
        if len(submats) == 1:
            return submats[0][1].index(i)

        lmat = submats[0][1]
        lsize = lmat.size()

        rsize = submats[0][0]

        cycles = gcd(rsize, lsize)
        clen = (rsize * lsize) / cycles
        off = (i / clen) % cycles

        def combine(r, s=frozenset()):
            if type(r) is frozenset:
                return s | r
            return s | frozenset([r])

        litems = lmat.index(i + off)
        ritems = self._index(i, submats[1:])
        return combine(litems, combine(ritems))

    def index(self, i):
        items = self._index(i, self.submats)
        return (self.item, items)

class Sum(Matrix):
    """
    We want to mix the subsequences proportionately to their size.
    """
    def __init__(self, item, _submats):
        assert len(_submats) > 0
        self.item = item

        submats = sorted(
            [((i.size(), ind), i) for (i, ind) in \
             zip(_submats, range(len(_submats)))], reverse=True)
        self.submats = []
        self._size = 0
        for ((size, ind), submat) in submats:
            self.submats.append((self._size, submat))
            self._size += size
        self.submats.reverse()

        self._minscanlen = max(
            [(self._size / i.size()) * \
             i.minscanlen() for i in _submats])

    def minscanlen(self):
        return self._minscanlen

    def size(self):
        return self._size

    def _index(self, _i, submats):
        """
        We reduce the N sequence problem to a two sequence problem recursively.

        If we have two sequences M and N of length m and n (n > m wlog), we
        want to mix an M item into the stream every N / M items.  Once we run
        out of N, we want to simply finish the M stream.
        """
        assert len(submats) > 0
        if len(submats) == 1:
            return submats[0][1].index(_i)
        lmat = submats[0][1]
        lsize = lmat.size()

        rsize = submats[0][0]

        mult = rsize / lsize
        clen = mult + 1
        thresh = lsize * clen
        i = _i % (rsize + lsize)
        base = (_i / (rsize + lsize))
        #print _i, mult, clen, thresh, i, base
        if i < thresh:
            if i % clen == 0:
                return lmat.index((i / clen) + (base * lsize))
            else:
                return self._index(((i / clen) * mult + ((i % clen) - 1)) + \
                                   (base * rsize),
                                   submats[1:])
        else:
            return self._index(i - lsize, submats[1:])
    def index(self, i):
        return (self.item, self._index(i, self.submats))

def generate_lists(result):
    if type(result) is frozenset:
        ret = []
        for i in result:
            ret.extend(generate_lists(i))
        return frozenset(ret)
    elif type(result) is tuple:
        ret = []
        (item, children) = result
        for f in generate_lists(children):
            nf = [item]
            nf.extend(f)
            ret.append(tuple(nf))
        return frozenset(ret)
    else:
        return frozenset([(result,)])

def generate_paths(path, result, joinf=os.path.join):
    return sorted([reduce(joinf, i, path) for i in generate_lists(result)])

def generate_desc(joinf, result):
    if type(result) is frozenset:
        ret = []
        for i in result:
            ret.append(generate_desc(joinf, i))
        if len(ret) > 1:
            return '{' + ' '.join(sorted(ret)) + '}'
        else:
            return ret[0]
    elif type(result) is tuple:
        (item, children) = result
        cdesc = generate_desc(joinf, children)
        return joinf(str(item), cdesc)
    else:
        return str(result)

def _test():
    def test(res):
        sz = res.size()
        s = frozenset([generate_lists(res.index(i)) for i in range(sz)])
        print sz, len(s)
        if True:#sz != len(s):
            print sz
            for i in range(res.size()):
                print sorted([j for j in generate_lists(res.index(i))])
    def mbs(num, l): return Sum(num*10, [Base(i + (100*num)) for i in l])

    test(mbs(1, range(6)))
    test(mbs(1, range(5)))
    test(Product(1, [mbs(1, range(6)), mbs(2, range(2))]))
    test(Product(1, [
        mbs(1, range(6)),
        mbs(2, range(2)),
        mbs(3, range(3)),
    ]))
    test(Product(1, [
        mbs(1, range(2)),
        mbs(2, range(5)),
        mbs(4, range(4)),
    ]))
    test(Sum(1, [
        mbs(1, range(6)),
        mbs(3, range(3)),
        mbs(2, range(2)),
        mbs(4, range(9)),
    ]))
    test(Sum(1, [
        mbs(1, range(2)),
        mbs(2, range(5)),
    ]))
    test(Sum(
        9,
        [
            mbs(10, range(6)),
            Product(1, [
                mbs(1, range(2)),
                mbs(2, range(5)),
                mbs(4, range(4))]),
            Product(8, [
                mbs(7, range(2)),
                mbs(6, range(5)),
                mbs(5, range(4))])
        ]
    ))
#_test()
