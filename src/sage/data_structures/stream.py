r"""
Streams

This module provides lazy implementations of basic operators on
streams. The classes implemented in this module can be used to build
up more complex streams for different kinds of series (Laurent,
Dirichlet, etc.).

EXAMPLES:

Streams can be used as data structure for lazy Laurent series::

    sage: L.<z> = LazyLaurentSeriesRing(ZZ)
    sage: f = L(lambda n: n, valuation=0)
    sage: f
    z + 2*z^2 + 3*z^3 + 4*z^4 + 5*z^5 + 6*z^6 + O(z^7)
    sage: type(f._coeff_stream)
    <class 'sage.data_structures.stream.Stream_function'>

There are basic unary and binary operators available for streams. For
example, we can add two streams::

    sage: from sage.data_structures.stream import *
    sage: f = Stream_function(lambda n: n, True, 0)
    sage: [f[i] for i in range(10)]
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    sage: g = Stream_function(lambda n: 1, True, 0)
    sage: [g[i] for i in range(10)]
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    sage: h = Stream_add(f, g, True)
    sage: [h[i] for i in range(10)]
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

We can subtract one stream from another::

    sage: h = Stream_sub(f, g, True)
    sage: [h[i] for i in range(10)]
    [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8]

There is a Cauchy product on streams::

    sage: h = Stream_cauchy_mul(f, g, True)
    sage: [h[i] for i in range(10)]
    [0, 1, 3, 6, 10, 15, 21, 28, 36, 45]

We can compute the inverse corresponding to the Cauchy product::

    sage: ginv = Stream_cauchy_invert(g)
    sage: h = Stream_cauchy_mul(f, ginv, True)
    sage: [h[i] for i in range(10)]
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1]

Two streams can be composed::

    sage: g = Stream_function(lambda n: n, True, 1)
    sage: h = Stream_cauchy_compose(f, g, True)
    sage: [h[i] for i in range(10)]
    [0, 1, 4, 14, 46, 145, 444, 1331, 3926, 11434]

There is a unary negation operator::

    sage: h = Stream_neg(f, True)
    sage: [h[i] for i in range(10)]
    [0, -1, -2, -3, -4, -5, -6, -7, -8, -9]

More generally, we can multiply by a scalar::

    sage: h = Stream_lmul(f, 2, True)
    sage: [h[i] for i in range(10)]
    [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

Finally, we can apply an arbitrary functions to the elements of a stream::

    sage: h = Stream_map_coefficients(f, lambda n: n^2, True)
    sage: [h[i] for i in range(10)]
    [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

AUTHORS:

- Kwankyu Lee (2019-02-24): initial version
- Tejasvi Chebrolu, Martin Rubey, Travis Scrimshaw (2021-08):
  refactored and expanded functionality
"""

# ****************************************************************************
#       Copyright (C) 2019 Kwankyu Lee <ekwankyu@gmail.com>
#                     2022 Martin Rubey <martin.rubey at tuwien.ac.at>
#                     2022 Travis Scrimshaw <tcscrims at gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#                  https://www.gnu.org/licenses/
# ****************************************************************************

from sage.rings.integer_ring import ZZ
from sage.rings.infinity import infinity
from sage.arith.misc import divisors
from sage.misc.misc_c import prod
from sage.misc.lazy_attribute import lazy_attribute
from sage.misc.lazy_import import lazy_import
from sage.combinat.integer_vector_weighted import iterator_fast as wt_int_vec_iter
from sage.categories.hopf_algebras_with_basis import HopfAlgebrasWithBasis
from sage.misc.cachefunc import cached_method

lazy_import('sage.combinat.sf.sfa', ['_variables_recursive', '_raise_variables'])


class Stream():
    """
    Abstract base class for all streams.

    INPUT:

    - ``true_order`` -- boolean; if the approximate order is the actual order

    .. NOTE::

        An implementation of a stream class depending on other stream
        classes must not access coefficients or the approximate order
        of these, in order not to interfere with lazy definitions for
        :class:`Stream_uninitialized`.

        If an approximate order or even the true order is known, it
        must be set after calling ``super().__init__``.

        Otherwise, a lazy attribute ``_approximate_order`` has to be
        defined.  Any initialization code depending on the
        approximate orders of input streams can be put into this
        definition.

        However, keep in mind that (trivially) this initialization
        code is not executed if ``_approximate_order`` is set to a
        value before it is accessed.

    """
    def __init__(self, true_order):
        """
        Initialize ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream
            sage: CS = Stream(1)
        """
        self._true_order = true_order

    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact
            sage: f = Stream_exact([0,3])
            sage: f._approximate_order
            1
        """
        raise NotImplementedError

    def __ne__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be different.

        The default is to always return ``False`` as it usually
        cannot be decided whether they are equal.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream
            sage: CS = Stream(1)
            sage: CS != CS
            False
            sage: CS != Stream(-2)
            False
        """
        return False

    def is_nonzero(self):
        r"""
        Return ``True`` if and only if this stream is known
        to be non-zero.

        The default implementation is ``False``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream
            sage: CS = Stream(1)
            sage: CS.is_nonzero()
            False
        """
        return False

    def is_uninitialized(self):
        r"""
        Return ``True`` if ``self`` is an uninitialized stream.

        The default implementation is ``False``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_zero
            sage: zero = Stream_zero()
            sage: zero.is_uninitialized()
            False
        """
        return False


class Stream_inexact(Stream):
    """
    An abstract base class for the stream when we do not know it is
    eventually constant.

    In particular, a cache is provided.

    INPUT:

    - ``is_sparse`` -- boolean; whether the implementation of the stream is sparse
    - ``true_order`` -- boolean; if the approximate order is the actual order

    If the cache is dense, it begins with the first non-zero term.
    """
    def __init__(self, is_sparse, true_order):
        """
        Initialize the stream class for a stream whose
        coefficients are not necessarily eventually constant.

        TESTS::

            sage: from sage.data_structures.stream import Stream_inexact
            sage: from sage.data_structures.stream import Stream_function
            sage: g = Stream_function(lambda n: n, False, 0)
            sage: isinstance(g, Stream_inexact)
            True
        """
        super().__init__(true_order)
        self._is_sparse = is_sparse
        if self._is_sparse:
            self._cache = dict()  # cache of known coefficients
        else:
            self._cache = list()
            self._iter = self.iterate_coefficients()

    def is_nonzero(self):
        r"""
        Return ``True`` if and only if the cache contains a non-zero element.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function
            sage: CS = Stream_function(lambda n: 1/n, False, 1)
            sage: CS.is_nonzero()
            False
            sage: CS[1]
            1
            sage: CS.is_nonzero()
            True
        """
        if self._is_sparse:
            return any(self._cache.values())
        return any(self._cache)

    def __getstate__(self):
        """
        Build the dictionary for pickling ``self``.

        We remove the cache from the pickle information when it is a dense
        implementation as iterators cannot be pickled.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact
            sage: from sage.data_structures.stream import Stream_cauchy_mul
            sage: h = Stream_exact([1])
            sage: g = Stream_exact([1, -1, -1])
            sage: u = Stream_cauchy_mul(h, g, True)
            sage: [u[i] for i in range(10)]
            [1, -1, -1, 0, 0, 0, 0, 0, 0, 0]
            sage: u._cache
            {0: 1, 1: -1, 2: -1, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0}
            sage: m = loads(dumps(u))
            sage: m._cache
            {0: 1, 1: -1, 2: -1, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0}
            sage: [m[i] for i in range(10)]
            [1, -1, -1, 0, 0, 0, 0, 0, 0, 0]

            sage: h = Stream_exact([1])
            sage: g = Stream_exact([1, -1, -1])
            sage: u = Stream_cauchy_mul(h, g, False)
            sage: [u[i] for i in range(10)]
            [1, -1, -1, 0, 0, 0, 0, 0, 0, 0]
            sage: u._cache
            [1, -1, -1, 0, 0, 0, 0, 0, 0, 0]
            sage: m = loads(dumps(u))
            sage: m._cache
            []
            sage: [m[i] for i in range(10)]
            [1, -1, -1, 0, 0, 0, 0, 0, 0, 0]
        """
        d = dict(self.__dict__)
        if not self._is_sparse:
            # We cannot pickle a generator object, so we remove it
            # and the cache from the pickle information.
            del d["_iter"]
            del d["_cache"]
        return d

    def __setstate__(self, d):
        """
        Build an object from ``d``.

        INPUT:

        - ``d`` -- a dictionary that needs to be unpickled

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact
            sage: h = Stream_exact([-1])
            sage: g = Stream_exact([1, -1])
            sage: from sage.data_structures.stream import Stream_cauchy_mul
            sage: u = Stream_cauchy_mul(h, g, True)
            sage: [u[i] for i in range(10)]
            [-1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
            sage: loads(dumps(u)) == u
            True
        """
        self.__dict__ = d
        if not self._is_sparse:
            self._iter = self.iterate_coefficients()
            self._cache = []

    def __getitem__(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the index

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function
            sage: f = Stream_function(lambda n: n^2, True, 0)
            sage: f[3]
            9
            sage: f._cache
            {3: 9}
            sage: [f[i] for i in range(10)]
            [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
            sage: f._cache
            {1: 1, 2: 4, 3: 9, 4: 16, 5: 25, 6: 36, 7: 49, 8: 64, 9: 81}

            sage: f = Stream_function(lambda n: n^2, False, 0)
            sage: f[3]
            9
            sage: f._cache
            [1, 4, 9]
            sage: [f[i] for i in range(10)]
            [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
            sage: f._cache
            [1, 4, 9, 16, 25, 36, 49, 64, 81]
        """
        if n < self._approximate_order:
            return ZZ.zero()

        if self._is_sparse:
            try:
                return self._cache[n]
            except KeyError:
                pass

            c = self.get_coefficient(n)
            if self._true_order or n > self._approximate_order:
                self._cache[n] = c
                return c

            if c:
                self._true_order = True
                self._cache[n] = c
                return c

            # self._approximate_order is not in self._cache if
            # self._true_order is False
            ao = self._approximate_order + 1
            while ao in self._cache:
                if self._cache[ao]:
                    self._true_order = True
                    break
                ao += 1
            self._approximate_order = ao
            return c

        # Dense implementation
        while not self._true_order and n >= self._approximate_order:
            c = next(self._iter)
            if c:
                self._true_order = True
                self._cache.append(c)
            else:
                self._approximate_order += 1

        if self._true_order:
            # It is important to extend by generator:
            # self._iter might recurse, and thereby extend the
            # cache itself, too.
            i = n - self._approximate_order
            self._cache.extend(next(self._iter)
                               for _ in range(i - len(self._cache) + 1))
            return self._cache[i]

        return ZZ.zero()

    def iterate_coefficients(self):
        """
        A generator for the coefficients of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_cauchy_compose
            sage: f = Stream_function(lambda n: 1, False, 1)
            sage: g = Stream_function(lambda n: n^3, False, 1)
            sage: h = Stream_cauchy_compose(f, g, True)
            sage: n = h.iterate_coefficients()
            sage: [next(n) for i in range(10)]
            [1, 9, 44, 207, 991, 4752, 22769, 109089, 522676, 2504295]
        """
        n = self._approximate_order
        while True:
            yield self.get_coefficient(n)
            n += 1

    def order(self):
        r"""
        Return the order of ``self``, which is the minimum index ``n`` such
        that ``self[n]`` is non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function
            sage: f = Stream_function(lambda n: n, True, 0)
            sage: f.order()
            1

        TESTS::

            sage: f = Stream_function(lambda n: n*(n+1), False, -1)
            sage: f.order()
            1
            sage: f._true_order
            True

            sage: f = Stream_function(lambda n: n*(n+1), True, -1)
            sage: f.order()
            1
            sage: f._true_order
            True
        """
        if self._true_order:
            return self._approximate_order
        n = self._approximate_order
        while not self[n]:
            n += 1
        return n

    def __ne__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be different.

        Only the elements in the caches are considered.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function
            sage: f = Stream_function(lambda n: n, True, 0)
            sage: g = Stream_function(lambda n: n^2, True, 0)
            sage: f != g
            False
            sage: f[1], g[1]
            (1, 1)
            sage: f != g
            False
            sage: f[3], g[4]
            (3, 16)
            sage: f != g
            False
            sage: f[2], g[2]
            (2, 4)
            sage: f != g
            True

        Checking the dense implementation::

            sage: f = Stream_function(lambda n: n if n > 0 else 0, False, -3)
            sage: g = Stream_function(lambda n: n^2, False, 0)
            sage: f != g
            False
            sage: g != f
            False
            sage: _ = f[1], g[1]
            sage: f != g
            False
            sage: g != f
            False
            sage: _ = f[2], g[2]
            sage: f != g
            True
            sage: g != f
            True

            sage: f = Stream_function(lambda n: n if n > 0 else 0, False, -3)
            sage: g = Stream_function(lambda n: n^2, False, 0)
            sage: _ = f[5], g[1]
            sage: f != g
            False
            sage: g != f
            False
            sage: _ = g[2]
            sage: f != g
            True
            sage: g != f
            True

            sage: f = Stream_function(lambda n: n if n > 0 else 0, False, -3)
            sage: g = Stream_function(lambda n: n^2, False, 0)
            sage: _ = g[5], f[1]
            sage: f != g
            False
            sage: g != f
            False
            sage: _ = f[2]
            sage: f != g
            True
            sage: g != f
            True

        """
        # TODO: more cases, in particular mixed implementations,
        # could be detected
        if not isinstance(other, Stream_inexact):
            return (other != self)

        if self.is_uninitialized() != other.is_uninitialized():
            return True

        if self._is_sparse and other._is_sparse:
            for i in self._cache:
                if i in other._cache and other._cache[i] != self._cache[i]:
                    return True

        elif not self._is_sparse and not other._is_sparse:
            if ((self._true_order
                 and other._approximate_order > self._approximate_order)
                or (other._true_order
                    and self._approximate_order > other._approximate_order)):
                return True

            if not self._true_order or not other._true_order:
                return False

            if any(i != j for i, j in zip(self._cache, other._cache)):
                return True

        return False


class Stream_exact(Stream):
    r"""
    A stream of eventually constant coefficients.

    INPUT:

    - ``initial_values`` -- a list of initial values
    - ``is_sparse`` -- boolean; specifies whether the stream is sparse
    - ``order`` -- integer (default: 0); determining the degree
      of the first element of ``initial_values``
    - ``degree`` -- integer (optional); determining the degree
      of the first element which is known to be equal to ``constant``
    - ``constant`` -- integer (default: 0); the coefficient
      of every index larger than or equal to ``degree``

    .. WARNING::

        The convention for ``order`` is different to the one in
        :class:`sage.rings.lazy_series_ring.LazySeriesRing`, where
        the input is shifted to have the prescribed order.

    """
    def __init__(self, initial_coefficients, constant=None, degree=None, order=None):
        """
        Initialize a stream with eventually constant coefficients.

        TESTS::

            sage: from sage.data_structures.stream import Stream_exact
            sage: Stream_exact([])
            Traceback (most recent call last):
            ...
            AssertionError: Stream_exact should only be used for non-zero streams

            sage: s = Stream_exact([0, 0, 1, 0, 0])
            sage: s._initial_coefficients, s._approximate_order, s._degree, s._true_order
            ((1,), 2, 3, True)

            sage: s = Stream_exact([0, 0, 1, 0, 0], constant=0)
            sage: s._initial_coefficients, s._approximate_order, s._degree, s._true_order
            ((1,), 2, 3, True)

            sage: s = Stream_exact([0, 0, 1, 0, 0], constant=0, degree=10)
            sage: s._initial_coefficients, s._approximate_order, s._degree, s._true_order
            ((1,), 2, 3, True)

            sage: s = Stream_exact([0, 0, 1, 0, 0], constant=1)
            sage: s._initial_coefficients, s._approximate_order, s._degree, s._true_order
            ((1,), 2, 5, True)

            sage: s = Stream_exact([0, 0, 1, 0, 1], constant=1, degree=10)
            sage: s._initial_coefficients, s._approximate_order, s._degree, s._true_order
            ((1, 0, 1), 2, 10, True)

            sage: s = Stream_exact([0, 0, 1, 0, 1], constant=1, degree=5)
            sage: s._initial_coefficients, s._approximate_order, s._degree, s._true_order
            ((1,), 2, 4, True)

            sage: s = Stream_exact([0, 0, 1, 2, 0, 1], constant=1)
            sage: s._initial_coefficients, s._approximate_order, s._degree, s._true_order
            ((1, 2), 2, 5, True)

            sage: s = Stream_exact([0, 0, 1, 2, 1, 1], constant=1)
            sage: s._initial_coefficients, s._approximate_order, s._degree, s._true_order
            ((1, 2), 2, 4, True)

            sage: s = Stream_exact([0, 0, 1, 2, 1, 1], constant=1, order=-2)
            sage: s._initial_coefficients, s._approximate_order, s._degree, s._true_order
            ((1, 2), 0, 2, True)
        """
        if constant is None:
            self._constant = ZZ.zero()
        else:
            self._constant = constant

        if order is None:
            order = 0
        if (degree is None
            or (not self._constant
                and degree > order + len(initial_coefficients))):
            self._degree = order + len(initial_coefficients)
        else:
            self._degree = degree
        assert order + len(initial_coefficients) <= self._degree

        # we remove leading and trailing zeros from
        # initial_coefficients

        # if the degree is order + len(initial_coefficients), we also
        # insist that the last entry of initial_coefficients is
        # different from constant, because __eq__ below would become
        # complicated otherwise
        for i, v in enumerate(initial_coefficients):
            if v:
                # We have found the first non-zero coefficient
                order += i
                initial_coefficients = initial_coefficients[i:]
                if order + len(initial_coefficients) == self._degree:
                    # Strip off the constant values at the end
                    for w in reversed(initial_coefficients):
                        if not (w == self._constant):
                            break
                        initial_coefficients.pop()
                        self._degree -= 1
                # Strip off all remaining zeros at the end
                for w in reversed(initial_coefficients):
                    if w:
                        break
                    initial_coefficients.pop()
                self._initial_coefficients = tuple(initial_coefficients)
                break
        else:
            order = self._degree
            self._initial_coefficients = tuple()

        assert self._initial_coefficients or self._constant, "Stream_exact should only be used for non-zero streams"

        super().__init__(True)
        self._approximate_order = order

    def __getitem__(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the index

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact
            sage: s = Stream_exact([1])
            sage: [s[i] for i in range(-2, 5)]
            [0, 0, 1, 0, 0, 0, 0]

            sage: s = Stream_exact([], constant=1)
            sage: [s[i] for i in range(-2, 5)]
            [0, 0, 1, 1, 1, 1, 1]

            sage: s = Stream_exact([2], constant=1)
            sage: [s[i] for i in range(-2, 5)]
            [0, 0, 2, 1, 1, 1, 1]

            sage: s = Stream_exact([2], order=-1, constant=1)
            sage: [s[i] for i in range(-2, 5)]
            [0, 2, 1, 1, 1, 1, 1]

            sage: s = Stream_exact([2], order=-1, degree=2, constant=1)
            sage: [s[i] for i in range(-2, 5)]
            [0, 2, 0, 0, 1, 1, 1]

            sage: t = Stream_exact([0, 2, 0], order=-2, degree=2, constant=1)
            sage: t == s
            True

            sage: s = Stream_exact([0,1,2,1,0,0,1,1], constant=1)
            sage: [s[i] for i in range(10)]
            [0, 1, 2, 1, 0, 0, 1, 1, 1, 1]

            sage: t = Stream_exact([0,1,2,1,0,0], constant=1)
            sage: s == t
            True
        """
        if n >= self._degree:
            return self._constant
        i = n - self._approximate_order
        if i < 0 or i >= len(self._initial_coefficients):
            return ZZ.zero()
        return self._initial_coefficients[i]

    def order(self):
        r"""
        Return the order of ``self``, which is the minimum index
        ``n`` such that ``self[n]`` is non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact
            sage: s = Stream_exact([1])
            sage: s.order()
            0
        """
        return self._approximate_order

    def __hash__(self):
        """
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact
            sage: s = Stream_exact([1])
            sage: hash(s) == hash(s)
            True
        """
        return hash((self._initial_coefficients, self._degree, self._constant))

    def __eq__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be equal.

        If ``other`` is also exact, equality is computable.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact
            sage: s = Stream_exact([2], order=-1, degree=2, constant=1)
            sage: t = Stream_exact([0, 2, 0], 1, 2, -2)
            sage: [s[i] for i in range(10)]
            [0, 0, 1, 1, 1, 1, 1, 1, 1, 1]
            sage: [t[i] for i in range(10)]
            [0, 0, 1, 1, 1, 1, 1, 1, 1, 1]
            sage: s == t
            True
            sage: s = Stream_exact([2], constant=1)
            sage: t = Stream_exact([2], order=-1, constant=1)
            sage: [s[i] for i in range(10)]
            [2, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            sage: [t[i] for i in range(10)]
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            sage: s == t
            False
            sage: t == t
            True

            sage: s = Stream_exact([2], order=0, degree=5, constant=1)
            sage: t = Stream_exact([2], order=-1, degree=5, constant=1)
            sage: s == t
            False

        """
        return (isinstance(other, type(self))
                and self._degree == other._degree
                and self._approximate_order == other._approximate_order
                and self._initial_coefficients == other._initial_coefficients
                and self._constant == other._constant)

    def __ne__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be different.

        The argument ``other`` may be exact or inexact, but is
        assumed to be non-zero.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact
            sage: s = Stream_exact([2], order=-1, degree=2, constant=1)
            sage: t = Stream_exact([0, 2, 0], 1, 2, -2)
            sage: s != t
            False
            sage: s = Stream_exact([2], constant=1)
            sage: t = Stream_exact([2], order=-1, constant=1)
            sage: s != t
            True

        When it is not known, then both equality and inequality
        return ``False``::

            sage: from sage.data_structures.stream import Stream_function
            sage: f = Stream_function(lambda n: 2 if n == 0 else 1, False, 0)
            sage: s == f
            False
            sage: s != f
            False
            sage: [s[i] for i in range(-3, 5)]
            [0, 0, 0, 2, 1, 1, 1, 1]
            sage: [f[i] for i in range(-3, 5)]
            [0, 0, 0, 2, 1, 1, 1, 1]
        """
        if isinstance(other, type(self)):
            return (self._degree != other._degree
                    or self._approximate_order != other._approximate_order
                    or self._initial_coefficients != other._initial_coefficients
                    or self._constant != other._constant)
        if other.is_uninitialized():
            return True
        if isinstance(other, Stream_zero):
            # We are assumed to be nonzero
            return True
        # if other is not exact, we can at least compare with the
        # elements in its cache
        if other._is_sparse:
            for i in other._cache:
                if self[i] != other._cache[i]:
                    return True
        else:
            if other._true_order:
                return any(self[i] != c
                           for i, c in enumerate(other._cache,
                                                 other._approximate_order))
            if other._approximate_order > self._approximate_order:
                return True

        return False

    def is_nonzero(self):
        r"""
        Return ``True`` if and only if this stream is known
        to be non-zero.

        An assumption of this class is that it is non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact
            sage: s = Stream_exact([2], order=-1, degree=2, constant=1)
            sage: s.is_nonzero()
            True
        """
        return True

    def _polynomial_part(self, R):
        """
        Return the initial part of ``self`` as a Laurent polynomial in ``R``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact
            sage: s = Stream_exact([2], order=-1, degree=2, constant=1)
            sage: L.<z> = LazyLaurentSeriesRing(ZZ)
            sage: s._polynomial_part(L._laurent_poly_ring)
            2*z^-1
        """
        v = self._approximate_order
        return R(self._initial_coefficients).shift(v)


class Stream_iterator(Stream_inexact):
    r"""
    Class that creates a stream from an iterator.

    INPUT:

    - ``iter`` -- a function that generates the coefficients of the
      stream
    - ``approximate_order`` -- integer; a lower bound for the order
      of the stream

    Instances of this class are always dense.

    EXAMPLES::

        sage: from sage.data_structures.stream import Stream_iterator
        sage: f = Stream_iterator(iter(NonNegativeIntegers()), 0)
        sage: [f[i] for i in range(10)]
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        sage: f = Stream_iterator(iter(NonNegativeIntegers()), 1)
        sage: [f[i] for i in range(10)]
        [0, 0, 1, 2, 3, 4, 5, 6, 7, 8]
    """
    def __init__(self, iter, approximate_order, true_order=False):
        """
        Initialize.

        TESTS::

            sage: from sage.data_structures.stream import Stream_iterator
            sage: f = Stream_iterator(iter(NonNegativeIntegers()), 0)
            sage: TestSuite(f).run(skip="_test_pickling")
        """
        self.iterate_coefficients = lambda: iter
        super().__init__(False, true_order)
        self._approximate_order = approximate_order


class Stream_function(Stream_inexact):
    r"""
    Class that creates a stream from a function on the integers.

    INPUT:

    - ``function`` -- a function that generates the
      coefficients of the stream
    - ``is_sparse`` -- boolean; specifies whether the stream is sparse
    - ``approximate_order`` -- integer; a lower bound for the order
      of the stream

    .. NOTE::

        We assume for equality that ``function`` is a function in the
        mathematical sense.

    EXAMPLES::

        sage: from sage.data_structures.stream import Stream_function
        sage: f = Stream_function(lambda n: n^2, False, 1)
        sage: f[3]
        9
        sage: [f[i] for i in range(10)]
        [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

        sage: f = Stream_function(lambda n: 1, False, 0)
        sage: n = f.iterate_coefficients()
        sage: [next(n) for _ in range(10)]
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

        sage: f = Stream_function(lambda n: n, True, 0)
        sage: f[4]
        4
    """
    def __init__(self, function, is_sparse, approximate_order, true_order=False):
        """
        Initialize.

        TESTS::

            sage: from sage.data_structures.stream import Stream_function
            sage: f = Stream_function(lambda n: 1, False, 1)
            sage: TestSuite(f).run(skip="_test_pickling")
        """
        self.get_coefficient = function
        super().__init__(is_sparse, true_order)
        self._approximate_order = approximate_order

    def __hash__(self):
        """
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function
            sage: f = Stream_function(lambda n: n, True, 0)
            sage: g = Stream_function(lambda n: 1, False, 1)
            sage: hash(f) == hash(g)
            True
        """
        # We don't hash the function as it might not be hashable.
        return hash(type(self))

    def __eq__(self, other):
        r"""
        Return whether ``self`` and ``other`` are known to be equal.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function
            sage: fun = lambda n: n
            sage: f = Stream_function(fun, True, 0)
            sage: g = Stream_function(fun, False, 0)
            sage: h = Stream_function(lambda n: n, False, 0)
            sage: f == g
            True
            sage: f == h
            False
        """
        return isinstance(other, type(self)) and self.get_coefficient == other.get_coefficient


class Stream_uninitialized(Stream_inexact):
    r"""
    Coefficient stream for an uninitialized series.

    INPUT:

    - ``approximate_order`` -- integer; a lower bound for the order
      of the stream

    Instances of this class are always dense.

    .. TODO::

        shouldn't instances of this class share the cache with its
        ``_target``?

    EXAMPLES::

        sage: from sage.data_structures.stream import Stream_uninitialized
        sage: from sage.data_structures.stream import Stream_exact
        sage: one = Stream_exact([1])
        sage: C = Stream_uninitialized(0)
        sage: C._target
        sage: C._target = one
        sage: C[4]
        0
    """
    def __init__(self, approximate_order, true_order=False):
        """
        Initialize ``self``.

        TESTS::

            sage: from sage.data_structures.stream import Stream_uninitialized
            sage: C = Stream_uninitialized(0)
            sage: TestSuite(C).run(skip="_test_pickling")
        """
        self._target = None
        if approximate_order is None:
            raise ValueError("the valuation must be specified for undefined series")
        super().__init__(False, true_order)
        self._approximate_order = approximate_order
        self._initializing = False

    def iterate_coefficients(self):
        """
        A generator for the coefficients of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_uninitialized
            sage: from sage.data_structures.stream import Stream_exact
            sage: z = Stream_exact([1], order=1)
            sage: C = Stream_uninitialized(0)
            sage: C._target
            sage: C._target = z
            sage: n = C.iterate_coefficients()
            sage: [next(n) for _ in range(10)]
            [0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        """
        n = self._approximate_order
        while True:
            yield self._target[n]
            n += 1

    def is_uninitialized(self):
        """
        Return ``True`` if ``self`` is an uninitialized stream.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_uninitialized
            sage: C = Stream_uninitialized(0)
            sage: C.is_uninitialized()
            True

        A more subtle uninitialized series::

            sage: L.<z> = LazyPowerSeriesRing(QQ)
            sage: T = L.undefined(1)
            sage: D = L.undefined(0)
            sage: T.define(z * exp(T) * D)
            sage: T._coeff_stream.is_uninitialized()
            True
        """
        if self._target is None:
            return True
        if self._initializing:
            return False
        # We implement semaphore-like behavior for coupled (undefined) series
        self._initializing = True
        result = self._target.is_uninitialized()
        self._initializing = False
        return result


class Stream_unary(Stream_inexact):
    r"""
    Base class for unary operators on coefficient streams.

    INPUT:

    - ``series`` -- :class:`Stream` the operator acts on
    - ``is_sparse`` -- boolean
    - ``true_order`` -- boolean (default: ``False``) if the approximate order
      is the actual order

    EXAMPLES::

        sage: from sage.data_structures.stream import (Stream_function, Stream_cauchy_invert, Stream_lmul)
        sage: f = Stream_function(lambda n: 2*n, False, 1)
        sage: g = Stream_cauchy_invert(f)
        sage: [g[i] for i in range(10)]
        [-1, 1/2, 0, 0, 0, 0, 0, 0, 0, 0]
        sage: g = Stream_lmul(f, 2, True)
        sage: [g[i] for i in range(10)]
        [0, 4, 8, 12, 16, 20, 24, 28, 32, 36]
    """
    def __init__(self, series, is_sparse, true_order=False):
        """
        Initialize ``self``.

        TESTS::

            sage: from sage.data_structures.stream import Stream_unary
            sage: from sage.data_structures.stream import (Stream_cauchy_invert, Stream_exact)
            sage: f = Stream_exact([1, -1])
            sage: g = Stream_cauchy_invert(f)
            sage: isinstance(g, Stream_unary)
            True
            sage: TestSuite(g).run()
        """
        self._series = series
        super().__init__(is_sparse, true_order)

    def __hash__(self):
        """
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_unary
            sage: from sage.data_structures.stream import Stream_function
            sage: M = Stream_unary(Stream_function(lambda n: 1, False, 1), True)
            sage: hash(M) == hash(M)
            True
        """
        return hash((type(self), self._series))

    def __eq__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be equal.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_function, Stream_rmul)
            sage: f = Stream_function(lambda n: 2*n, False, 1)
            sage: g = Stream_function(lambda n: n, False, 1)
            sage: h = Stream_rmul(f, 2, True)
            sage: n = Stream_rmul(g, 2, True)
            sage: h == n
            False
            sage: n == n
            True
            sage: h == h
            True
        """
        return isinstance(other, type(self)) and self._series == other._series

    def is_uninitialized(self):
        """
        Return ``True`` if ``self`` is an uninitialized stream.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_uninitialized, Stream_unary
            sage: C = Stream_uninitialized(0)
            sage: M = Stream_unary(C, True)
            sage: M.is_uninitialized()
            True
        """
        return self._series.is_uninitialized()


class Stream_binary(Stream_inexact):
    """
    Base class for binary operators on coefficient streams.

    INPUT:

    - ``left`` -- :class:`Stream` for the left side of the operator
    - ``right`` -- :class:`Stream` for the right side of the operator

    EXAMPLES::

        sage: from sage.data_structures.stream import (Stream_function, Stream_add, Stream_sub)
        sage: f = Stream_function(lambda n: 2*n, True, 0)
        sage: g = Stream_function(lambda n: n, True, 1)
        sage: h = Stream_add(f, g, True)
        sage: [h[i] for i in range(10)]
        [0, 3, 6, 9, 12, 15, 18, 21, 24, 27]
        sage: h = Stream_sub(f, g, True)
        sage: [h[i] for i in range(10)]
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    """

    def __init__(self, left, right, is_sparse):
        """
        Initialize ``self``.

        TESTS::

            sage: from sage.data_structures.stream import Stream_binary
            sage: from sage.data_structures.stream import (Stream_add, Stream_cauchy_invert, Stream_exact)
            sage: f1 = Stream_exact([1, -1])
            sage: g1 = Stream_cauchy_invert(f1)
            sage: f2 = Stream_exact([1, 1])
            sage: g2 = Stream_cauchy_invert(f2)
            sage: O = Stream_add(g1, g2, True)
            sage: isinstance(O, Stream_binary)
            True
            sage: TestSuite(O).run()
        """
        self._left = left
        self._right = right
        super().__init__(is_sparse, False)

    def __hash__(self):
        """
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_binary
            sage: from sage.data_structures.stream import Stream_function
            sage: M = Stream_function(lambda n: n, True, 0)
            sage: N = Stream_function(lambda n: -2*n, True, 0)
            sage: O = Stream_binary(M, N, True)
            sage: hash(O) == hash(O)
            True
        """
        return hash((type(self), self._left, self._right))

    def __eq__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be equal.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_function, Stream_cauchy_mul)
            sage: f = Stream_function(lambda n: 2*n, False, 1)
            sage: g = Stream_function(lambda n: n, False, 1)
            sage: h = Stream_function(lambda n: 1, False, 1)
            sage: t = Stream_cauchy_mul(f, g, True)
            sage: u = Stream_cauchy_mul(g, h, True)
            sage: v = Stream_cauchy_mul(h, f, True)
            sage: t == u
            False
            sage: t == t
            True
            sage: u == v
            False
        """
        if not isinstance(other, type(self)):
            return False
        return self._left == other._left and self._right == other._right

    def is_uninitialized(self):
        """
        Return ``True`` if ``self`` is an uninitialized stream.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_uninitialized, Stream_sub, Stream_function
            sage: C = Stream_uninitialized(0)
            sage: F = Stream_function(lambda n: n, True, 0)
            sage: B = Stream_sub(F, C, True)
            sage: B.is_uninitialized()
            True
            sage: Bp = Stream_sub(F, F, True)
            sage: Bp.is_uninitialized()
            False
        """
        return self._left.is_uninitialized() or self._right.is_uninitialized()


class Stream_binaryCommutative(Stream_binary):
    r"""
    Base class for commutative binary operators on coefficient streams.

    EXAMPLES::

        sage: from sage.data_structures.stream import (Stream_function, Stream_add)
        sage: f = Stream_function(lambda n: 2*n, True, 0)
        sage: g = Stream_function(lambda n: n, True, 1)
        sage: h = Stream_add(f, g, True)
        sage: [h[i] for i in range(10)]
        [0, 3, 6, 9, 12, 15, 18, 21, 24, 27]
        sage: u = Stream_add(g, f, True)
        sage: [u[i] for i in range(10)]
        [0, 3, 6, 9, 12, 15, 18, 21, 24, 27]
        sage: h == u
        True
    """
    def __hash__(self):
        """
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_function, Stream_add)
            sage: f = Stream_function(lambda n: 2*n, True, 0)
            sage: g = Stream_function(lambda n: n, True, 1)
            sage: h = Stream_add(f, g, True)
            sage: u = Stream_add(g, f, True)
            sage: hash(h) == hash(u)
            True
        """
        return hash((type(self), frozenset([self._left, self._right])))

    def __eq__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be equal.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_function, Stream_add)
            sage: f = Stream_function(lambda n: 2*n, True, 0)
            sage: g = Stream_function(lambda n: n, True, 1)
            sage: h = Stream_add(f, g, True)
            sage: [h[i] for i in range(10)]
            [0, 3, 6, 9, 12, 15, 18, 21, 24, 27]
            sage: u = Stream_add(g, f, True)
            sage: [u[i] for i in range(10)]
            [0, 3, 6, 9, 12, 15, 18, 21, 24, 27]
            sage: h == u
            True
        """
        if not isinstance(other, type(self)):
            return False
        if self._left == other._left and self._right == other._right:
            return True
        if self._left == other._right and self._right == other._left:
            return True
        return False


class Stream_zero(Stream):
    """
    A coefficient stream that is exactly equal to zero.

    EXAMPLES::

        sage: from sage.data_structures.stream import Stream_zero
        sage: s = Stream_zero()
        sage: s[5]
        0
    """
    def __init__(self):
        """
        Initialize ``self``.

        TESTS::

            sage: from sage.data_structures.stream import Stream_zero
            sage: s = Stream_zero()
            sage: TestSuite(s).run()
        """
        super().__init__(True)
        self._approximate_order = infinity

    def __getitem__(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the index

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_zero
            sage: s = Stream_zero()
            sage: s[1]
            0
            sage: sum([s[i] for i in range(10)])
            0
        """
        return ZZ.zero()

    def order(self):
        r"""
        Return the order of ``self``, which is ``infinity``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_zero
            sage: s = Stream_zero()
            sage: s.order()
            +Infinity
        """
        return self._approximate_order # == infinity

    def __eq__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be equal.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_zero
            sage: Stream_zero() == Stream_zero()
            True
        """
        return self is other or isinstance(other, Stream_zero)

    def __ne__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be different.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_zero, Stream_function
            sage: Stream_zero() != Stream_zero()
            False
            sage: f = Stream_function(lambda n: 2*n, True, 0)
            sage: Stream_zero() != f
            False
            sage: f[0]
            0
            sage: Stream_zero() != f
            False
            sage: f[1]
            2
            sage: Stream_zero() != f
            True
        """
        return self is not other and not isinstance(other, Stream_zero) and other.is_nonzero()

    def __hash__(self):
        """
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_zero
            sage: s = Stream_zero()
            sage: hash(s)
            0
        """
        return 0


#####################################################################
# Binary operations

class Stream_add(Stream_binaryCommutative):
    """
    Operator for addition of two coefficient streams.

    INPUT:

    - ``left`` -- :class:`Stream` of coefficients on the left side of the operator
    - ``right`` -- :class:`Stream` of coefficients on the right side of the operator

    EXAMPLES::

        sage: from sage.data_structures.stream import (Stream_add, Stream_function)
        sage: f = Stream_function(lambda n: n, True, 0)
        sage: g = Stream_function(lambda n: 1, True, 0)
        sage: h = Stream_add(f, g, True)
        sage: [h[i] for i in range(10)]
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        sage: u = Stream_add(g, f, True)
        sage: [u[i] for i in range(10)]
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    """
    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact
            sage: h = Stream_exact([0,3])
            sage: h._approximate_order
            1
        """
        # this is not the true order, because we may have cancellation
        return min(self._left._approximate_order, self._right._approximate_order)

    def get_coefficient(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the degree for the coefficient

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_function, Stream_add)
            sage: f = Stream_function(lambda n: n, True, 0)
            sage: g = Stream_function(lambda n: n^2, True, 0)
            sage: h = Stream_add(f, g, True)
            sage: h.get_coefficient(5)
            30
            sage: [h.get_coefficient(i) for i in range(10)]
            [0, 2, 6, 12, 20, 30, 42, 56, 72, 90]
        """
        return self._left[n] + self._right[n]


class Stream_sub(Stream_binary):
    """
    Operator for subtraction of two coefficient streams.

    INPUT:

    - ``left`` -- :class:`Stream` of coefficients on the left side of the operator
    - ``right`` -- :class:`Stream` of coefficients on the right side of the operator

    EXAMPLES::

        sage: from sage.data_structures.stream import (Stream_sub, Stream_function)
        sage: f = Stream_function(lambda n: n, True, 0)
        sage: g = Stream_function(lambda n: 1, True, 0)
        sage: h = Stream_sub(f, g, True)
        sage: [h[i] for i in range(10)]
        [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8]
        sage: u = Stream_sub(g, f, True)
        sage: [u[i] for i in range(10)]
        [1, 0, -1, -2, -3, -4, -5, -6, -7, -8]
    """
    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact, Stream_function, Stream_add
            sage: f = Stream_exact([0,3])
            sage: g = Stream_function(lambda n: -3*n, True, 1)
            sage: h = Stream_add(f, g, True)
            sage: h._approximate_order
            1
            sage: [h[i] for i in range(5)]
            [0, 0, -6, -9, -12]
        """
        # this is not the true order, because we may have cancellation
        return min(self._left._approximate_order, self._right._approximate_order)

    def get_coefficient(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the degree for the coefficient

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_function, Stream_sub)
            sage: f = Stream_function(lambda n: n, True, 0)
            sage: g = Stream_function(lambda n: n^2, True, 0)
            sage: h = Stream_sub(f, g, True)
            sage: h.get_coefficient(5)
            -20
            sage: [h.get_coefficient(i) for i in range(10)]
            [0, 0, -2, -6, -12, -20, -30, -42, -56, -72]
        """
        return self._left[n] - self._right[n]


class Stream_cauchy_mul(Stream_binary):
    """
    Operator for multiplication of two coefficient streams using the
    Cauchy product.

    We are *not* assuming commutativity of the coefficient ring here,
    only that the coefficient ring commutes with the (implicit) variable.

    INPUT:

    - ``left`` -- :class:`Stream` of coefficients on the left side of the operator
    - ``right`` -- :class:`Stream` of coefficients on the right side of the operator

    EXAMPLES::

        sage: from sage.data_structures.stream import (Stream_cauchy_mul, Stream_function)
        sage: f = Stream_function(lambda n: n, True, 0)
        sage: g = Stream_function(lambda n: 1, True, 0)
        sage: h = Stream_cauchy_mul(f, g, True)
        sage: [h[i] for i in range(10)]
        [0, 1, 3, 6, 10, 15, 21, 28, 36, 45]
        sage: u = Stream_cauchy_mul(g, f, True)
        sage: [u[i] for i in range(10)]
        [0, 1, 3, 6, 10, 15, 21, 28, 36, 45]
    """
    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact, Stream_function, Stream_cauchy_mul
            sage: f = Stream_exact([0, Zmod(6)(2)])
            sage: g = Stream_function(lambda n: Zmod(6)(3*n), True, 1)
            sage: h = Stream_cauchy_mul(f, g, True)
            sage: h._approximate_order
            2
            sage: [h[i] for i in range(5)]
            [0, 0, 0, 0, 0]
        """
        # this is not the true order, unless we have an integral domain
        return self._left._approximate_order + self._right._approximate_order

    def get_coefficient(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the degree for the coefficient

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_function, Stream_cauchy_mul)
            sage: f = Stream_function(lambda n: n, True, 0)
            sage: g = Stream_function(lambda n: n^2, True, 0)
            sage: h = Stream_cauchy_mul(f, g, True)
            sage: h.get_coefficient(5)
            50
            sage: [h.get_coefficient(i) for i in range(10)]
            [0, 0, 1, 6, 20, 50, 105, 196, 336, 540]
        """
        return sum(l * self._right[n - k]
                   for k in range(self._left._approximate_order,
                                  n - self._right._approximate_order + 1)
                   if (l := self._left[k]))

    def is_nonzero(self):
        r"""
        Return ``True`` if and only if this stream is known
        to be non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_function,
            ....:     Stream_cauchy_mul, Stream_cauchy_invert)
            sage: f = Stream_function(lambda n: n, True, 1)
            sage: g = Stream_cauchy_mul(f, f, True)
            sage: g.is_nonzero()
            False
            sage: fi = Stream_cauchy_invert(f)
            sage: h = Stream_cauchy_mul(fi, fi, True)
            sage: h.is_nonzero()
            True
        """
        return self._left.is_nonzero() and self._right.is_nonzero()


class Stream_cauchy_mul_commutative(Stream_cauchy_mul, Stream_binaryCommutative):
    """
    Operator for multiplication of two coefficient streams using the
    Cauchy product for commutative multiplication of coefficients.
    """
    pass


class Stream_dirichlet_convolve(Stream_binary):
    r"""
    Operator for the Dirichlet convolution of two streams.

    INPUT:

    - ``left`` -- :class:`Stream` of coefficients on the left side of the operator
    - ``right`` -- :class:`Stream` of coefficients on the right side of the operator

    The coefficient of `n^{-s}` in the convolution of `l` and `r`
    equals `\sum_{k | n} l_k r_{n/k}`.

    EXAMPLES::

        sage: from sage.data_structures.stream import (Stream_dirichlet_convolve, Stream_function, Stream_exact)
        sage: f = Stream_function(lambda n: n, True, 1)
        sage: g = Stream_exact([0], constant=1)
        sage: h = Stream_dirichlet_convolve(f, g, True)
        sage: [h[i] for i in range(1, 10)]
        [1, 3, 4, 7, 6, 12, 8, 15, 13]
        sage: [sigma(n) for n in range(1, 10)]
        [1, 3, 4, 7, 6, 12, 8, 15, 13]

        sage: u = Stream_dirichlet_convolve(g, f, True)
        sage: [u[i] for i in range(1, 10)]
        [1, 3, 4, 7, 6, 12, 8, 15, 13]
    """
    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact, Stream_function, Stream_dirichlet_convolve
            sage: f = Stream_exact([0, 2])
            sage: g = Stream_function(lambda n: 3*n, True, 1)
            sage: h = Stream_dirichlet_convolve(f, g, True)
            sage: h._approximate_order
            1
            sage: [h[i] for i in range(5)]
            [0, 6, 12, 18, 24]
        """
        # this is not the true order, unless we have an integral domain
        if (self._left._approximate_order <= 0
            or self._right._approximate_order <= 0):
            raise ValueError("Dirichlet convolution is only defined for "
                             "coefficient streams with minimal index of "
                             "non-zero coefficient at least 1")
        return self._left._approximate_order * self._right._approximate_order

    def get_coefficient(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the degree for the coefficient

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_dirichlet_convolve, Stream_function, Stream_exact)
            sage: f = Stream_function(lambda n: n, True, 1)
            sage: g = Stream_exact([0], constant=1)
            sage: h = Stream_dirichlet_convolve(f, g, True)
            sage: h.get_coefficient(7)
            8
            sage: [h[i] for i in range(1, 10)]
            [1, 3, 4, 7, 6, 12, 8, 15, 13]
        """
        return sum(l * self._right[n//k] for k in divisors(n)
                   if (k >= self._left._approximate_order
                       and n // k >= self._right._approximate_order
                       and (l := self._left[k])))


class Stream_cauchy_compose(Stream_binary):
    r"""
    Return ``f`` composed by ``g``.

    This is the composition `(f \circ g)(z) = f(g(z))`.

    INPUT:

    - ``f`` -- a :class:`Stream`
    - ``g`` -- a :class:`Stream` with positive order

    EXAMPLES::

        sage: from sage.data_structures.stream import Stream_cauchy_compose, Stream_function
        sage: f = Stream_function(lambda n: n, True, 1)
        sage: g = Stream_function(lambda n: 1, True, 1)
        sage: h = Stream_cauchy_compose(f, g, True)
        sage: [h[i] for i in range(10)]
        [0, 1, 3, 8, 20, 48, 112, 256, 576, 1280]
        sage: u = Stream_cauchy_compose(g, f, True)
        sage: [u[i] for i in range(10)]
        [0, 1, 3, 8, 21, 55, 144, 377, 987, 2584]
    """
    def __init__(self, f, g, is_sparse):
        """
        Initialize ``self``.

        TESTS::

            sage: from sage.data_structures.stream import Stream_function, Stream_cauchy_compose
            sage: f = Stream_function(lambda n: 1, True, 1)
            sage: g = Stream_function(lambda n: n^2, True, 1)
            sage: h = Stream_cauchy_compose(f, g, True)
        """
        if g._true_order and g._approximate_order <= 0:
            raise ValueError("can only compose with a series of positive valuation")
        super().__init__(f, g, is_sparse)

    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_cauchy_compose
            sage: f = Stream_function(lambda n: n, True, 1)
            sage: g = Stream_function(lambda n: n^2, True, 1)
            sage: h = Stream_cauchy_compose(f, g, True)
            sage: h._approximate_order
            1
            sage: [h[i] for i in range(5)]
            [0, 1, 6, 28, 124]

        .. TODO::

            check similarities with :class:`Stream_plethysm`
        """
        # this is very likely not the true order
        if self._right._approximate_order <= 0:
            raise ValueError("can only compose with a series of positive valuation")

        if self._left._approximate_order < 0:
            ginv = Stream_cauchy_invert(self._right)
            # The constant part makes no contribution to the negative.
            # We need this for the case so self._neg_powers[0][n] => 0.
            self._neg_powers = [Stream_zero(), ginv]
            for i in range(1, -self._left._approximate_order):
                # TODO: possibly we always want a dense cache here?
                self._neg_powers.append(Stream_cauchy_mul(self._neg_powers[-1], ginv, self._is_sparse))
        # placeholder None to make this 1-based.
        self._pos_powers = [None, self._right]

        return self._left._approximate_order * self._right._approximate_order

    def get_coefficient(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the degree for the coefficient

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_cauchy_compose
            sage: f = Stream_function(lambda n: n, True, 1)
            sage: g = Stream_function(lambda n: n^2, True, 1)
            sage: h = Stream_cauchy_compose(f, g, True)
            sage: h[5] # indirect doctest
            527
            sage: [h[i] for i in range(10)] # indirect doctest
            [0, 1, 6, 28, 124, 527, 2172, 8755, 34704, 135772]
        """
        fv = self._left._approximate_order
        gv = self._right._approximate_order
        if n < 0:
            return sum(l * self._neg_powers[-k][n]
                       for k in range(fv, n // gv + 1)
                       if (l := self._left[k]))
        # n > 0
        while len(self._pos_powers) <= n // gv:
            # TODO: possibly we always want a dense cache here?
            self._pos_powers.append(Stream_cauchy_mul(self._pos_powers[-1],
                                                      self._right,
                                                      self._is_sparse))
        ret = sum(l * self._neg_powers[-k][n] for k in range(fv, 0)
                  if (l := self._left[k]))

        if not n:
            ret += self._left[0]

        return ret + sum(l * self._pos_powers[k][n] for k in range(1, n // gv + 1)
                         if (l := self._left[k]))


class Stream_plethysm(Stream_binary):
    r"""
    Return the plethysm of ``f`` composed by ``g``.

    This is the plethysm `f \circ g = f(g)` when `g` is an element of
    a ring of symmetric functions.

    INPUT:

    - ``f`` -- a :class:`Stream`
    - ``g`` -- a :class:`Stream` with positive order, unless ``f`` is
      of :class:`Stream_exact`.
    - ``p`` -- the ring of powersum symmetric functions containing ``g``
    - ``ring`` (optional, default ``None``) -- the ring the result
      should be in, by default ``p``
    - ``include`` -- a list of variables to be treated as degree one
      elements instead of the default degree one elements
    - ``exclude`` -- a list of variables to be excluded from the
      default degree one elements

    EXAMPLES::

        sage: # needs sage.modules
        sage: from sage.data_structures.stream import Stream_function, Stream_plethysm
        sage: s = SymmetricFunctions(QQ).s()
        sage: p = SymmetricFunctions(QQ).p()
        sage: f = Stream_function(lambda n: s[n], True, 1)
        sage: g = Stream_function(lambda n: s[[1]*n], True, 1)
        sage: h = Stream_plethysm(f, g, True, p, s)
        sage: [h[i] for i in range(5)]
        [0,
         s[1],
         s[1, 1] + s[2],
         2*s[1, 1, 1] + s[2, 1] + s[3],
         3*s[1, 1, 1, 1] + 2*s[2, 1, 1] + s[2, 2] + s[3, 1] + s[4]]
        sage: u = Stream_plethysm(g, f, True, p, s)
        sage: [u[i] for i in range(5)]
        [0,
         s[1],
         s[1, 1] + s[2],
         s[1, 1, 1] + s[2, 1] + 2*s[3],
         s[1, 1, 1, 1] + s[2, 1, 1] + 3*s[3, 1] + 2*s[4]]

    This class also handles the plethysm of an exact stream with a
    stream of order `0`::

        sage: # needs sage.modules
        sage: from sage.data_structures.stream import Stream_exact
        sage: f = Stream_exact([s[1]], order=1)
        sage: g = Stream_function(lambda n: s[n], True, 0)
        sage: r = Stream_plethysm(f, g, True, p, s)
        sage: [r[n] for n in range(3)]
        [s[], s[1], s[2]]

    TESTS:

    Check corner cases::

        sage: # needs sage.modules
        sage: f0 = Stream_exact([p([])])
        sage: f1 = Stream_exact([p[1]], order=1)
        sage: f2 = Stream_exact([p[2]], order=2 )
        sage: f11 = Stream_exact([p[1,1]], order=2 )
        sage: r = Stream_plethysm(f0, f1, True, p); [r[n] for n in range(3)]
        [p[], 0, 0]
        sage: r = Stream_plethysm(f0, f2, True, p); [r[n] for n in range(3)]
        [p[], 0, 0]
        sage: r = Stream_plethysm(f0, f11, True, p); [r[n] for n in range(3)]
        [p[], 0, 0]

    Check that degree one elements are treated in the correct way::

        sage: # needs sage.modules
        sage: R.<a1,a2,a11,b1,b21,b111> = QQ[]; p = SymmetricFunctions(R).p()
        sage: f_s = a1*p[1] + a2*p[2] + a11*p[1,1]
        sage: g_s = b1*p[1] + b21*p[2,1] + b111*p[1,1,1]
        sage: r_s = f_s(g_s)
        sage: f = Stream_exact([f_s.restrict_degree(k)
        ....:                   for k in range(f_s.degree()+1)])
        sage: g = Stream_exact([g_s.restrict_degree(k)
        ....:                   for k in range(g_s.degree()+1)])
        sage: r = Stream_plethysm(f, g, True, p)
        sage: r_s == sum(r[n] for n in range(2*(r_s.degree()+1)))
        True

        sage: r_s - f_s(g_s, include=[])                                                # needs sage.modules
        (a2*b1^2-a2*b1)*p[2] + (a2*b111^2-a2*b111)*p[2, 2, 2] + (a2*b21^2-a2*b21)*p[4, 2]

        sage: r2 = Stream_plethysm(f, g, True, p, include=[])                           # needs sage.modules
        sage: r_s - sum(r2[n] for n in range(2*(r_s.degree()+1)))                       # needs sage.modules
        (a2*b1^2-a2*b1)*p[2] + (a2*b111^2-a2*b111)*p[2, 2, 2] + (a2*b21^2-a2*b21)*p[4, 2]

    """
    def __init__(self, f, g, is_sparse, p, ring=None, include=None, exclude=None):
        r"""
        Initialize ``self``.

        TESTS::

            sage: # needs sage.modules
            sage: from sage.data_structures.stream import Stream_function, Stream_plethysm
            sage: s = SymmetricFunctions(QQ).s()
            sage: p = SymmetricFunctions(QQ).p()
            sage: f = Stream_function(lambda n: s[n], True, 1)
            sage: g = Stream_function(lambda n: s[n-1,1], True, 2)
            sage: h = Stream_plethysm(f, g, True, p)
        """
        if isinstance(f, Stream_exact):
            self._degree_f = f._degree
        else:
            self._degree_f = None

        if g._true_order and g._approximate_order == 0 and self._degree_f is None:
            raise ValueError("can only compute plethysm with a series of valuation 0 for symmetric functions of finite support")

        if ring is None:
            self._basis = p
        else:
            self._basis = ring
        self._p = p
        g = Stream_map_coefficients(g, lambda x: p(x), is_sparse)
        self._powers = [g]  # a cache for the powers of g in the powersum basis
        R = self._basis.base_ring()
        self._degree_one = _variables_recursive(R, include=include, exclude=exclude)

        if HopfAlgebrasWithBasis(R).TensorProducts() in p.categories():
            self._tensor_power = len(p._sets)
            p_f = p._sets[0]
            f = Stream_map_coefficients(f, lambda x: p_f(x), is_sparse)
        else:
            self._tensor_power = None
            f = Stream_map_coefficients(f, lambda x: p(x), is_sparse)
        super().__init__(f, g, is_sparse)

    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: # needs sage.modules
            sage: from sage.data_structures.stream import Stream_function, Stream_plethysm
            sage: p = SymmetricFunctions(QQ).p()
            sage: f = Stream_function(lambda n: p[n], True, 1)
            sage: h = Stream_plethysm(f, f, True, p)
            sage: h._approximate_order
            1
            sage: [h[i] for i in range(5)]
            [0, p[1], 2*p[2], 2*p[3], 3*p[4]]
        """
        # this is very likely not the true order
#        if self._right._approximate_order == 0 and self._degree_f is None:
#            raise ValueError("can only compute plethysm with a series of "
#                             " valuation 0 for symmetric functions of finite "
#                             " support")
        return self._left._approximate_order * self._right._approximate_order

    def get_coefficient(self, n):
        r"""
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the degree for the coefficient

        EXAMPLES::

            sage: # needs sage.modules
            sage: from sage.data_structures.stream import Stream_function, Stream_plethysm
            sage: s = SymmetricFunctions(QQ).s()
            sage: p = SymmetricFunctions(QQ).p()
            sage: f = Stream_function(lambda n: s[n], True, 1)
            sage: g = Stream_function(lambda n: s[[1]*n], True, 1)
            sage: h = Stream_plethysm(f, g, True, p)
            sage: s(h.get_coefficient(5))
            4*s[1, 1, 1, 1, 1] + 4*s[2, 1, 1, 1] + 2*s[2, 2, 1] + 2*s[3, 1, 1] + s[3, 2] + s[4, 1] + s[5]
            sage: [s(h.get_coefficient(i)) for i in range(6)]
            [0,
             s[1],
             s[1, 1] + s[2],
             2*s[1, 1, 1] + s[2, 1] + s[3],
             3*s[1, 1, 1, 1] + 2*s[2, 1, 1] + s[2, 2] + s[3, 1] + s[4],
             4*s[1, 1, 1, 1, 1] + 4*s[2, 1, 1, 1] + 2*s[2, 2, 1] + 2*s[3, 1, 1] + s[3, 2] + s[4, 1] + s[5]]
        """
        if not n:  # special case of 0
            if self._right[0]:
                assert self._degree_f is not None, "the plethysm with a lazy symmetric function of valuation 0 is defined only for symmetric functions of finite support"
                K = self._degree_f
            else:
                K = 1
        else:
            K = n + 1

        return sum((c * self.compute_product(n, la)
                    for k in range(self._left._approximate_order, K)
                    if self._left[k] # necessary, because it might be int(0)
                    for la, c in self._left[k]),
                   self._basis.zero())

    def compute_product(self, n, la):
        r"""
        Compute the product ``p[la](self._right)`` in degree ``n``.

        EXAMPLES::

            sage: # needs sage.modules
            sage: from sage.data_structures.stream import Stream_plethysm, Stream_exact, Stream_function, Stream_zero
            sage: s = SymmetricFunctions(QQ).s()
            sage: p = SymmetricFunctions(QQ).p()
            sage: f = Stream_exact([1]) # irrelevant for this test
            sage: g = Stream_exact([s[2], s[3]], 0, 4, 2)
            sage: h = Stream_plethysm(f, g, True, p)
            sage: A = h.compute_product(7, Partition([2, 1])); A
            1/12*p[2, 2, 1, 1, 1] + 1/4*p[2, 2, 2, 1] + 1/6*p[3, 2, 2]
             + 1/12*p[4, 1, 1, 1] + 1/4*p[4, 2, 1] + 1/6*p[4, 3]
            sage: A == p[2, 1](s[2] + s[3]).homogeneous_component(7)
            True

            sage: # needs sage.modules
            sage: p2 = tensor([p, p])
            sage: f = Stream_exact([1]) # irrelevant for this test
            sage: g = Stream_function(lambda n: sum(tensor([p[k], p[n-k]])
            ....:                                   for k in range(n+1)), True, 1)
            sage: h = Stream_plethysm(f, g, True, p2)
            sage: A = h.compute_product(7, Partition([2, 1]))
            sage: B = p[2, 1](sum(g[n] for n in range(7)))
            sage: B = p2.element_class(p2, {m: c for m, c in B
            ....:                           if sum(mu.size() for mu in m) == 7})
            sage: A == B
            True

            sage: # needs sage.modules
            sage: f = Stream_exact([1]) # irrelevant for this test
            sage: g = Stream_function(lambda n: s[n], True, 0)
            sage: h = Stream_plethysm(f, g, True, p)
            sage: B = p[2, 2, 1](sum(p(s[i]) for i in range(7)))
            sage: all(h.compute_product(k, Partition([2, 2, 1]))
            ....:      == B.restrict_degree(k) for k in range(7))
            True
        """
        # This is the approximate order of the result
        rao = self._right._approximate_order
        ret_approx_order = rao * sum(la)
        ret = self._basis.zero()
        if n < ret_approx_order:
            return ret

        la_exp = la.to_exp()
        wgt = [i for i, m in enumerate(la_exp, 1) if m]
        exp = [m for m in la_exp if m]
        # the docstring of wt_int_vec_iter, i.e., iterator_fast,
        # states that the weights should be weakly decreasing
        wgt.reverse()
        exp.reverse()
        for k in wt_int_vec_iter(n - ret_approx_order, wgt):
            # prod does not short-cut zero, therefore
            # ret += prod(self.stretched_power_restrict_degree(i, m, rao * m + d)
            #             for i, m, d in zip(wgt, exp, k))
            # is expensive
            lf = []
            for i, m, d in zip(wgt, exp, k):
                f = self.stretched_power_restrict_degree(i, m, rao * m + d)
                if not f:
                    break
                lf.append(f)
            else:
                ret += prod(lf)

        return ret

    @cached_method
    def stretched_power_restrict_degree(self, i, m, d):
        r"""
        Return the degree ``d*i`` part of ``p([i]*m)(g)`` in
        terms of ``self._basis``.

        INPUT:

        - ``i``, ``m`` -- positive integers
        - ``d`` -- integer

        EXAMPLES::

            sage: # needs sage.modules
            sage: from sage.data_structures.stream import Stream_plethysm, Stream_exact, Stream_function, Stream_zero
            sage: s = SymmetricFunctions(QQ).s()
            sage: p = SymmetricFunctions(QQ).p()
            sage: f = Stream_exact([1]) # irrelevant for this test
            sage: g = Stream_exact([s[2], s[3]], 0, 4, 2)
            sage: h = Stream_plethysm(f, g, True, p)
            sage: A = h.stretched_power_restrict_degree(2, 3, 6)
            sage: A == p[2,2,2](s[2] + s[3]).homogeneous_component(12)
            True

            sage: # needs sage.modules
            sage: p2 = tensor([p, p])
            sage: f = Stream_exact([1]) # irrelevant for this test
            sage: g = Stream_function(lambda n: sum(tensor([p[k], p[n-k]])
            ....:                                   for k in range(n+1)), True, 1)
            sage: h = Stream_plethysm(f, g, True, p2)
            sage: A = h.stretched_power_restrict_degree(2, 3, 6)
            sage: B = p[2,2,2](sum(g[n] for n in range(7)))     # long time
            sage: B = p2.element_class(p2, {m: c for m, c in B  # long time
            ....:                           if sum(mu.size() for mu in m) == 12})
            sage: A == B                        # long time
            True

        """
        # TODO: we should do lazy binary powering here
        while len(self._powers) < m:
            # TODO: possibly we always want a dense cache here?
            self._powers.append(Stream_cauchy_mul(self._powers[-1],
                                                  self._powers[0],
                                                  self._is_sparse))
        power_d = self._powers[m-1][d]
        # we have to check power_d for zero because it might be an
        # integer and not a symmetric function
        if power_d:
            # _raise_variables(c, i, self._degree_one) cannot vanish
            # because i is positive and c is non-zero
            if self._tensor_power is None:
                terms = {mon.stretch(i):
                         _raise_variables(c, i, self._degree_one)
                         for mon, c in power_d}
            else:
                terms = {tuple((mu.stretch(i) for mu in mon)):
                         _raise_variables(c, i, self._degree_one)
                         for mon, c in power_d}
            return self._basis(self._p.element_class(self._p, terms))

        return self._basis.zero()


#####################################################################
# Unary operations

class Stream_scalar(Stream_unary):
    """
    Base class for operators multiplying a coefficient stream by a
    scalar.

    INPUT:

    - ``series`` -- a :class:`Stream`
    - ``scalar`` -- a non-zero, non-one scalar
    - ``is_sparse`` -- boolean
    """
    def __init__(self, series, scalar, is_sparse):
        """
        Initialize ``self``.

        TESTS::

            sage: from sage.data_structures.stream import (Stream_rmul, Stream_function)
            sage: f = Stream_function(lambda n: -1, True, 0)
            sage: g = Stream_rmul(f, 3, True)
        """
        self._scalar = scalar
        assert scalar, "the scalar must not be equal to 0"
        assert scalar != 1, "the scalar must not be equal to 1"
        super().__init__(series, is_sparse, series._true_order)

    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_rmul
            sage: f = Stream_function(lambda n: Zmod(6)(n), True, 2)
            sage: h = Stream_rmul(f, 3, True) # indirect doctest
            sage: h._approximate_order
            2
            sage: [h[i] for i in range(5)]
            [0, 0, 0, 3, 0]
        """
        # this is not the true order, unless we have an integral domain
        return self._series._approximate_order

    def __hash__(self):
        """
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function
            sage: from sage.data_structures.stream import Stream_rmul
            sage: a = Stream_function(lambda n: 2*n, False, 1)
            sage: f = Stream_rmul(a, 2, True)
            sage: hash(f) == hash(f)
            True
        """
        return hash((type(self), self._series, self._scalar))

    def __eq__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be equal.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function
            sage: from sage.data_structures.stream import Stream_rmul, Stream_lmul
            sage: a = Stream_function(lambda n: 2*n, False, 1)
            sage: b = Stream_function(lambda n: n, False, 1)
            sage: f = Stream_rmul(a, 2, True)
            sage: f == Stream_rmul(b, 2, True)
            False
            sage: f == Stream_rmul(a, 2, False)
            True
            sage: f == Stream_rmul(a, 3, True)
            False
            sage: f == Stream_lmul(a, 3, True)
            False
        """
        return (isinstance(other, type(self)) and self._series == other._series
                and self._scalar == other._scalar)

    def is_nonzero(self):
        r"""
        Return ``True`` if and only if this stream is known
        to be non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_rmul, Stream_function)
            sage: f = Stream_function(lambda n: n, True, 1)
            sage: g = Stream_rmul(f, 2, True)
            sage: g.is_nonzero()
            False

            sage: from sage.data_structures.stream import Stream_cauchy_invert
            sage: fi = Stream_cauchy_invert(f)
            sage: g = Stream_rmul(fi, 2, True)
            sage: g.is_nonzero()
            True
        """
        return self._series.is_nonzero()


class Stream_rmul(Stream_scalar):
    """
    Operator for multiplying a coefficient stream with a scalar
    as ``scalar * self``.

    INPUT:

    - ``series`` -- a :class:`Stream`
    - ``scalar`` -- a non-zero, non-one scalar

    EXAMPLES::

        sage: # needs sage.modules
        sage: from sage.data_structures.stream import (Stream_rmul, Stream_function)
        sage: W = algebras.DifferentialWeyl(QQ, names=('x',))
        sage: x, dx = W.gens()
        sage: f = Stream_function(lambda n: x^n, True, 1)
        sage: g = Stream_rmul(f, dx, True)
        sage: [g[i] for i in range(5)]
        [0, x*dx + 1, x^2*dx + 2*x, x^3*dx + 3*x^2, x^4*dx + 4*x^3]
    """
    def get_coefficient(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the degree for the coefficient

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_rmul, Stream_function)
            sage: f = Stream_function(lambda n: n, True, 1)
            sage: g = Stream_rmul(f, 3, True)
            sage: g.get_coefficient(5)
            15
            sage: [g.get_coefficient(i) for i in range(10)]
            [0, 3, 6, 9, 12, 15, 18, 21, 24, 27]
        """
        return self._scalar * self._series[n]


class Stream_lmul(Stream_scalar):
    """
    Operator for multiplying a coefficient stream with a scalar
    as ``self * scalar``.

    INPUT:

    - ``series`` -- a :class:`Stream`
    - ``scalar`` -- a non-zero, non-one scalar

    EXAMPLES::

        sage: # needs sage.modules
        sage: from sage.data_structures.stream import (Stream_lmul, Stream_function)
        sage: W = algebras.DifferentialWeyl(QQ, names=('x',))
        sage: x, dx = W.gens()
        sage: f = Stream_function(lambda n: x^n, True, 1)
        sage: g = Stream_lmul(f, dx, True)
        sage: [g[i] for i in range(5)]
        [0, x*dx, x^2*dx, x^3*dx, x^4*dx]
    """
    def get_coefficient(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the degree for the coefficient

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_lmul, Stream_function)
            sage: f = Stream_function(lambda n: n, True, 1)
            sage: g = Stream_lmul(f, 3, True)
            sage: g.get_coefficient(5)
            15
            sage: [g.get_coefficient(i) for i in range(10)]
            [0, 3, 6, 9, 12, 15, 18, 21, 24, 27]
        """
        return self._series[n] * self._scalar


class Stream_neg(Stream_unary):
    """
    Operator for negative of the stream.

    INPUT:

    - ``series`` -- a :class:`Stream`

    EXAMPLES::

        sage: from sage.data_structures.stream import (Stream_neg, Stream_function)
        sage: f = Stream_function(lambda n: 1, True, 1)
        sage: g = Stream_neg(f, True)
        sage: [g[i] for i in range(10)]
        [0, -1, -1, -1, -1, -1, -1, -1, -1, -1]
    """
    # TODO: maybe we should just inherit from `Stream` instead of
    # inheriting from `Stream_unary` and do not create a copy of the
    # cache
    def __init__(self, series, is_sparse):
        """
        Initialize ``self``.

        TESTS::

            sage: from sage.data_structures.stream import (Stream_neg, Stream_function)
            sage: f = Stream_function(lambda n: -1, True, 0)
            sage: g = Stream_neg(f, True)
        """
        super().__init__(series, is_sparse)
        self._true_order = self._series._true_order

    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_neg
            sage: f = Stream_function(lambda n: Zmod(6)(n), True, 2)
            sage: h = Stream_neg(f, True)
            sage: h._approximate_order
            2
            sage: [h[i] for i in range(5)]
            [0, 0, 4, 3, 2]
        """
        # this is the true order, if self._series._true_order
        return self._series._approximate_order

    def get_coefficient(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the degree for the coefficient

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_neg, Stream_function)
            sage: f = Stream_function(lambda n: n, True, 1)
            sage: g = Stream_neg(f, True)
            sage: g.get_coefficient(5)
            -5
            sage: [g.get_coefficient(i) for i in range(10)]
            [0, -1, -2, -3, -4, -5, -6, -7, -8, -9]
        """
        return -self._series[n]

    def is_nonzero(self):
        r"""
        Return ``True`` if and only if this stream is known
        to be non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_neg, Stream_function)
            sage: f = Stream_function(lambda n: n, True, 1)
            sage: g = Stream_neg(f, True)
            sage: g.is_nonzero()
            False

            sage: from sage.data_structures.stream import Stream_cauchy_invert
            sage: fi = Stream_cauchy_invert(f)
            sage: g = Stream_neg(fi, True)
            sage: g.is_nonzero()
            True
        """
        return self._series.is_nonzero()


class Stream_cauchy_invert(Stream_unary):
    """
    Operator for multiplicative inverse of the stream.

    INPUT:

    - ``series`` -- a :class:`Stream`
    - ``approximate_order`` -- ``None``, or a lower bound on the
      order of the resulting stream

    Instances of this class are always dense, because of mathematical
    necessities.

    EXAMPLES::

        sage: from sage.data_structures.stream import (Stream_cauchy_invert, Stream_function)
        sage: f = Stream_function(lambda n: 1, True, 1)
        sage: g = Stream_cauchy_invert(f)
        sage: [g[i] for i in range(10)]
        [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    """
    def __init__(self, series, approximate_order=None):
        """
        Initialize ``self``.

        TESTS::

            sage: from sage.data_structures.stream import (Stream_cauchy_invert, Stream_exact)
            sage: f = Stream_exact([1, -1])
            sage: g = Stream_cauchy_invert(f)
        """
        super().__init__(series, False)
        if approximate_order is not None:
            self._approximate_order = approximate_order
        self._zero = ZZ.zero()

    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_cauchy_invert
            sage: f = Stream_function(lambda n: GF(7)(n), True, 0)
            sage: [f[i] for i in range(5)]
            [0, 1, 2, 3, 4]
            sage: h = Stream_cauchy_invert(f)
            sage: h._approximate_order
            -1
            sage: [h[i] for i in range(-2, 5)]
            [0, 1, 5, 1, 0, 0, 0]
        """
        try:
            return -self._series.order()
        except (ValueError, RecursionError):
            raise ValueError("inverse does not exist")

    @lazy_attribute
    def _ainv(self):
        r"""
        The inverse of the leading coefficient.

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_cauchy_invert, Stream_exact)
            sage: f = Stream_exact([2, -3])
            sage: g = Stream_cauchy_invert(f)
            sage: g._ainv
            1/2

            sage: f = Stream_exact([Zmod(6)(5)], constant=2)
            sage: g = Stream_cauchy_invert(f)
            sage: g._ainv
            5
        """
        v = self._series.order()
        try:
            return ~self._series[v]
        except TypeError:
            return self._series[v].inverse_of_unit()

    def iterate_coefficients(self):
        """
        A generator for the coefficients of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_cauchy_invert, Stream_function)
            sage: f = Stream_function(lambda n: n^2, False, 1)
            sage: g = Stream_cauchy_invert(f)
            sage: n = g.iterate_coefficients()
            sage: [next(n) for i in range(10)]
            [1, -4, 7, -8, 8, -8, 8, -8, 8, -8]
        """
        yield self._ainv
        # This is the true order, which is computed in self._ainv
        v = self._approximate_order
        n = 0  # Counts the number of places from v.
        # Note that the first entry of the cache will correspond to
        # z^v, when the stream corresponds to a Laurent series.

        while True:
            n += 1
            c = self._zero
            m = min(len(self._cache), n)
            for k in range(m):
                l = self._cache[k]
                if l:
                    c += l * self._series[n - v - k]
            for k in range(v+m, v+n):
                l = self[k]
                if l:
                    c += l * self._series[n - k]
            yield -c * self._ainv

    def is_nonzero(self):
        r"""
        Return ``True`` if and only if this stream is known
        to be non-zero.

        An assumption of this class is that it is non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_cauchy_invert, Stream_function)
            sage: f = Stream_function(lambda n: n^2, False, 1)
            sage: g = Stream_cauchy_invert(f)
            sage: g.is_nonzero()
            True
        """
        return True


class Stream_dirichlet_invert(Stream_unary):
    r"""
    Operator for inverse with respect to Dirichlet convolution of the stream.

    INPUT:

    - ``series`` -- a :class:`Stream`

    EXAMPLES::

        sage: from sage.data_structures.stream import (Stream_dirichlet_invert, Stream_function)
        sage: f = Stream_function(lambda n: 1, True, 1)
        sage: g = Stream_dirichlet_invert(f, True)
        sage: [g[i] for i in range(10)]
        [0, 1, -1, -1, 0, -1, 1, -1, 0, 0]
        sage: [moebius(i) for i in range(10)]                                           # needs sage.libs.pari
        [0, 1, -1, -1, 0, -1, 1, -1, 0, 0]
    """
    def __init__(self, series, is_sparse):
        """
        Initialize.

        TESTS::

            sage: from sage.data_structures.stream import (Stream_exact, Stream_dirichlet_invert)
            sage: f = Stream_exact([0, 0], constant=1)
            sage: g = Stream_dirichlet_invert(f, True)
            sage: g[1]
            Traceback (most recent call last):
            ...
            ZeroDivisionError: the Dirichlet inverse only exists if the coefficient with index 1 is non-zero
        """
        super().__init__(series, is_sparse)
        self._zero = ZZ.zero()

    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_dirichlet_invert
            sage: f = Stream_function(lambda n: n, True, 1)
            sage: h = Stream_dirichlet_invert(f, True)
            sage: h._approximate_order
            1
            sage: [h[i] for i in range(5)]
            [0, -2, -8, -12, -48]
        """
        # this is the true order, but we want to check first
        if self._series._approximate_order > 1:
            raise ZeroDivisionError("the Dirichlet inverse only exists if the "
                                    "coefficient with index 1 is non-zero")
        self._true_order = True
        return 1

    @lazy_attribute
    def _ainv(self):
        """
        The inverse of the leading coefficient.

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_exact, Stream_dirichlet_invert)
            sage: f = Stream_exact([0, 3], constant=2)
            sage: g = Stream_dirichlet_invert(f, True)
            sage: g._ainv
            1/3

            sage: f = Stream_exact([Zmod(6)(5)], constant=2, order=1)
            sage: g = Stream_dirichlet_invert(f, True)
            sage: g._ainv
            5
        """
        try:
            return ~self._series[1]
        except TypeError:
            return self._series[1].inverse_of_unit()

    def get_coefficient(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the degree for the coefficient

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_exact, Stream_dirichlet_invert)
            sage: f = Stream_exact([0, 3], constant=2)
            sage: g = Stream_dirichlet_invert(f, True)
            sage: g.get_coefficient(6)
            2/27
            sage: [g[i] for i in range(8)]
            [0, 1/3, -2/9, -2/9, -2/27, -2/9, 2/27, -2/9]
        """
        if n == 1:
            return self._ainv
        # TODO: isn't self[k] * l and l * self[k] the same here?
        c = sum(self[k] * l for k in divisors(n)
                if (k < n
                    and (l := self._series[n // k])))
        return -c * self._ainv


class Stream_map_coefficients(Stream_unary):
    r"""
    The stream with ``function`` applied to each non-zero coefficient
    of ``series``.

    INPUT:

    - ``series`` -- a :class:`Stream`
    - ``function`` -- a function that modifies the elements of the stream

    .. NOTE::

        We assume for equality that ``function`` is a function in the
        mathematical sense.

    EXAMPLES::

        sage: from sage.data_structures.stream import (Stream_map_coefficients, Stream_function)
        sage: f = Stream_function(lambda n: 1, True, 1)
        sage: g = Stream_map_coefficients(f, lambda n: -n, True)
        sage: [g[i] for i in range(10)]
        [0, -1, -1, -1, -1, -1, -1, -1, -1, -1]

    """
    def __init__(self, series, function, is_sparse, approximate_order=None, true_order=False):
        """
        Initialize ``self``.

        TESTS::

            sage: from sage.data_structures.stream import (Stream_map_coefficients, Stream_function)
            sage: f = Stream_function(lambda n: -1, True, 0)
            sage: g = Stream_map_coefficients(f, lambda n: n + 1, True)
            sage: TestSuite(g).run(skip="_test_pickling")
        """
        self._function = function
        super().__init__(series, is_sparse, true_order)
        if approximate_order is not None:
            self._approximate_order = approximate_order

    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_map_coefficients
            sage: f = Stream_function(lambda n: Zmod(6)(n), True, 2)
            sage: h = Stream_map_coefficients(f, lambda c: 3*c, True)
            sage: h._approximate_order
            2
            sage: [h[i] for i in range(5)]
            [0, 0, 0, 3, 0]
        """
        # this is not the true order
        return self._series._approximate_order

    def get_coefficient(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        INPUT:

        - ``n`` -- integer; the degree for the coefficient

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_map_coefficients, Stream_function)
            sage: f = Stream_function(lambda n: n, True, -1)
            sage: g = Stream_map_coefficients(f, lambda n: n^2 + 1, True)
            sage: g.get_coefficient(5)
            26
            sage: [g.get_coefficient(i) for i in range(-1, 10)]
            [2, 0, 2, 5, 10, 17, 26, 37, 50, 65, 82]

            sage: R.<x,y> = ZZ[]
            sage: f = Stream_function(lambda n: n, True, -1)
            sage: g = Stream_map_coefficients(f, lambda n: R(n).degree() + 1, True)
            sage: [g.get_coefficient(i) for i in range(-1, 3)]
            [1, 0, 1, 1]
        """
        c = self._series[n]
        if c:
            return self._function(c)
        return c

    def __hash__(self):
        """
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_map_coefficients, Stream_function)
            sage: f = Stream_function(lambda n: -1, True, 0)
            sage: g = Stream_map_coefficients(f, lambda n: n + 1, True)
            sage: hash(g) == hash(g)
            True
        """
        # We don't hash the function as it might not be hashable.
        return hash((type(self), self._series))

    def __eq__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be equal.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_map_coefficients, Stream_function)
            sage: f = Stream_function(lambda n: -1, True, 0)
            sage: def plus_one(n): return n + 1
            sage: g = Stream_map_coefficients(f, plus_one, True)
            sage: g == f
            False
            sage: g == Stream_map_coefficients(f, lambda n: n + 1, True)
            False
        """
        return (isinstance(other, type(self)) and self._series == other._series
                and self._function == other._function)


class Stream_shift(Stream):
    """
    Operator for shifting a non-zero, non-exact stream.

    Instances of this class share the cache with its input stream.

    INPUT:

    - ``series`` -- a :class:`Stream`
    - ``shift`` -- an integer
    """
    def __init__(self, series, shift):
        """
        Initialize ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_shift
            sage: from sage.data_structures.stream import Stream_function
            sage: h = Stream_function(lambda n: n, True, -5)
            sage: M = Stream_shift(h, 2)
            sage: TestSuite(M).run(skip="_test_pickling")
        """
        self._series = series
        self._shift = shift
        super().__init__(series._true_order)

    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_shift
            sage: f = Stream_function(lambda n: Zmod(6)(n), True, 2)
            sage: h = Stream_shift(f, -2)
            sage: h._approximate_order
            0
            sage: [h[i] for i in range(5)]
            [2, 3, 4, 5, 0]
        """
        # this is the true order, if self._series._true_order
        return self._series._approximate_order + self._shift

    def order(self):
        r"""
        Return the order of ``self``, which is the minimum index
        ``n`` such that ``self[n]`` is non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_shift
            sage: s = Stream_shift(Stream_function(lambda n: n, True, 0), 2)
            sage: s.order()
            3
        """
        return self._series.order() + self._shift

    def __getitem__(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_shift
            sage: from sage.data_structures.stream import Stream_function
            sage: F = Stream_function(lambda n: n, False, 1)
            sage: M = Stream_shift(F, 2)
            sage: [F[i] for i in range(6)]
            [0, 1, 2, 3, 4, 5]
            sage: [M[i] for i in range(6)]
            [0, 0, 0, 1, 2, 3]
        """
        return self._series[n - self._shift]

    def __hash__(self):
        """
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_shift
            sage: from sage.data_structures.stream import Stream_function
            sage: F = Stream_function(lambda n: n, False, 1)
            sage: M = Stream_shift(F, 2)
            sage: hash(M) == hash(M)
            True
        """
        return hash((type(self), self._series))

    def __eq__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be equal.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_shift
            sage: from sage.data_structures.stream import Stream_function
            sage: F = Stream_function(lambda n: 1, False, 1)
            sage: M2 = Stream_shift(F, 2)
            sage: M3 = Stream_shift(F, 3)
            sage: M2 == M3
            False
            sage: M2 == Stream_shift(F, 2)
            True
        """
        return (isinstance(other, type(self))
                and self._shift == other._shift
                and self._series == other._series)

    def is_nonzero(self):
        r"""
        Return ``True`` if and only if this stream is known
        to be non-zero.

        An assumption of this class is that it is non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import (Stream_cauchy_invert, Stream_function)
            sage: f = Stream_function(lambda n: n^2, False, 1)
            sage: g = Stream_cauchy_invert(f)
            sage: g.is_nonzero()
            True
        """
        return self._series.is_nonzero()

    def is_uninitialized(self):
        """
        Return ``True`` if ``self`` is an uninitialized stream.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_uninitialized, Stream_shift
            sage: C = Stream_uninitialized(0)
            sage: S = Stream_shift(C, 5)
            sage: S.is_uninitialized()
            True
        """
        return self._series.is_uninitialized()


class Stream_truncated(Stream_unary):
    """
    Operator for shifting a non-zero, non-exact stream that has
    been shifted below its minimal valuation.

    Instances of this class share the cache with its input stream.

    INPUT:

    - ``series`` -- a :class:`Stream_inexact`
    - ``shift`` -- an integer
    - ``minimal_valuation`` -- an integer; this is also the approximate order
    """
    def __init__(self, series, shift, minimal_valuation):
        """
        Initialize ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_truncated
            sage: def fun(n): return 1 if ZZ(n).is_power_of(2) else 0
            sage: s = Stream_truncated(Stream_function(fun, True, 0), -5, 0)
            sage: TestSuite(s).run(skip="_test_pickling")
            sage: s = Stream_truncated(Stream_function(fun, False, 0), -5, 0)
            sage: TestSuite(s).run(skip="_test_pickling")

        Verify that we have used the cache to see if we can get the
        true order at initialization::

            sage: f = Stream_function(fun, True, 0)
            sage: [f[i] for i in range(0, 10)]
            [0, 1, 1, 0, 1, 0, 0, 0, 1, 0]
            sage: f._cache
            {1: 1, 2: 1, 3: 0, 4: 1, 5: 0, 6: 0, 7: 0, 8: 1, 9: 0}
            sage: s = Stream_truncated(f, -5, 0)
            sage: s._true_order
            True
            sage: s._approximate_order
            3
            sage: f = Stream_function(fun, False, 0)
            sage: [f[i] for i in range(0, 10)]
            [0, 1, 1, 0, 1, 0, 0, 0, 1, 0]
            sage: f._cache
            [1, 1, 0, 1, 0, 0, 0, 1, 0]
            sage: s = Stream_truncated(f, -5, 0)
            sage: s._true_order
            True
            sage: s._approximate_order
            3
        """
        super().__init__(series, series._is_sparse, False)
        assert isinstance(series, Stream_inexact)
        # We share self._series._cache but not self._series._approximate order
        # self._approximate_order cannot be updated by self._series.__getitem__
        self._cache = series._cache
        self._shift = shift
        ao = minimal_valuation
        # Try to find the true order based on the values already computed
        if self._is_sparse:
            ao -= shift
            while ao in self._cache:
                if self._cache[ao]:
                    self._true_order = True
                    break
                ao += 1
            ao += shift
        else:
            start = ao - (series._approximate_order + shift)
            for val in self._cache[start:]:
                if val:
                    self._true_order = True
                    break
                ao += 1
        self._approximate_order = ao

    def __getitem__(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_truncated
            sage: def fun(n): return 1 if ZZ(n).is_power_of(2) else 0
            sage: s = Stream_truncated(Stream_function(fun, True, 0), -5, 0)
            sage: [s[i] for i in range(10)]
            [0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
            sage: s._approximate_order
            3
            sage: s._true_order
            True
            sage: s = Stream_truncated(Stream_function(fun, False, 0), -5, 0)
            sage: s[10]
            0
            sage: s._approximate_order
            3
            sage: s._true_order
            True
        """
        if n < self._approximate_order:
            return ZZ.zero()
        ret = self._series[n-self._shift]
        if not self._true_order:
            if self._is_sparse:
                ao = self._approximate_order - self._shift
                while ao in self._cache:
                    if self._cache[ao]:
                        self._true_order = True
                        break
                    ao += 1
                self._approximate_order = ao + self._shift
            else:  # dense case
                offset = self._series._approximate_order + self._shift
                start = self._approximate_order - offset
                for val in self._cache[start:]:
                    if val:
                        self._true_order = True
                        break
                    self._approximate_order += 1
        return ret

    def __hash__(self):
        """
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_truncated
            sage: def fun(n): return 1 if ZZ(n).is_power_of(2) else 0
            sage: s = Stream_truncated(Stream_function(fun, True, 0), -5, 0)
            sage: hash(s) == hash(s)
            True
        """
        return hash((type(self), self._series))

    def __eq__(self, other):
        """
        Test equality.

        INPUT:

        - ``other`` -- a stream of coefficients

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_truncated
            sage: def fun(n): return 1 if ZZ(n).is_power_of(2) else 0
            sage: f = Stream_function(fun, True, 0)
            sage: sm5 = Stream_truncated(f, -5, 0)
            sage: sm2 = Stream_truncated(f, -2, 0)
            sage: sm2 == sm5
            False
            sage: sm5 == Stream_truncated(f, -5, 0)
            True
        """
        # We assume that comparisons of this class are done only by elements in
        #    a common ring; in particular, the minimum order will be the same.
        return (isinstance(other, type(self)) and self._shift == other._shift
                and self._series == other._series)

    def order(self):
        """
        Return the order of ``self``, which is the minimum index ``n`` such
        that ``self[n]`` is non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_truncated
            sage: def fun(n): return 1 if ZZ(n).is_power_of(2) else 0
            sage: s = Stream_truncated(Stream_function(fun, True, 0), -5, 0)
            sage: s.order()
            3
            sage: s = Stream_truncated(Stream_function(fun, False, 0), -5, 0)
            sage: s.order()
            3

        Check that it also worked properly with the cache partially filled::

            sage: f = Stream_function(fun, True, 0)
            sage: dummy = [f[i] for i in range(10)]
            sage: s = Stream_truncated(f, -5, 0)
            sage: s.order()
            3
            sage: f = Stream_function(fun, False, 0)
            sage: dummy = [f[i] for i in range(10)]
            sage: s = Stream_truncated(f, -5, 0)
            sage: s.order()
            3
        """
        if self._true_order:
            return self._approximate_order
        if self._is_sparse:
            n = self._approximate_order
            cache = self._series._cache
            while True:
                if n - self._shift in cache:
                    if cache[n-self._shift]:
                        self._approximate_order = n
                        self._true_order = True
                        return n
                elif self[n]:
                    return n
                n += 1
        # dense case
        return super().order()

    def is_nonzero(self):
        r"""
        Return ``True`` if and only if this stream is known
        to be non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_truncated
            sage: def fun(n): return 1 if ZZ(n).is_power_of(2) else 0
            sage: f = Stream_function(fun, False, 0)
            sage: [f[i] for i in range(0, 4)]
            [0, 1, 1, 0]
            sage: f._cache
            [1, 1, 0]
            sage: s = Stream_truncated(f, -5, 0)
            sage: s.is_nonzero()
            False
            sage: [f[i] for i in range(7,10)]  # updates the cache of s
            [0, 1, 0]
            sage: s.is_nonzero()
            True

            sage: f = Stream_function(fun, True, 0)
            sage: [f[i] for i in range(0, 4)]
            [0, 1, 1, 0]
            sage: f._cache
            {1: 1, 2: 1, 3: 0}
            sage: s = Stream_truncated(f, -5, 0)
            sage: s.is_nonzero()
            False
            sage: [f[i] for i in range(7,10)]  # updates the cache of s
            [0, 1, 0]
            sage: s.is_nonzero()
            True
        """
        if self._is_sparse:
            return any(c for n, c in self._series._cache.items()
                       if n + self._shift >= self._approximate_order)
        offset = self._series._approximate_order + self._shift
        start = self._approximate_order - offset
        return any(self._cache[start:])


class Stream_derivative(Stream_unary):
    """
    Operator for taking derivatives of a non-exact stream.

    INPUT:

    - ``series`` -- a :class:`Stream`
    - ``shift`` -- a positive integer
    - ``is_sparse`` -- boolean
    """
    def __init__(self, series, shift, is_sparse):
        """
        Initialize ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact, Stream_derivative
            sage: f = Stream_exact([1,2,3])
            sage: f2 = Stream_derivative(f, 2, True)
            sage: TestSuite(f2).run()
        """
        self._shift = shift
        super().__init__(series, is_sparse, False)

    @lazy_attribute
    def _approximate_order(self):
        """
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_derivative
            sage: f = Stream_function(lambda n: Zmod(6)(n), True, 2)
            sage: h = Stream_derivative(f, 3, True)
            sage: h._approximate_order
            0
            sage: [h[i] for i in range(5)]
            [0, 0, 0, 0, 0]
        """
        # this is not the true order, unless multiplying by an
        # integer cannot give 0
        if 0 <= self._series._approximate_order <= self._shift:
            return 0
        return self._series._approximate_order - self._shift

    def __getitem__(self, n):
        """
        Return the ``n``-th coefficient of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function, Stream_derivative
            sage: f = Stream_function(lambda n: 1/n if n else 0, True, -2)
            sage: [f[i] for i in range(-5, 3)]
            [0, 0, 0, -1/2, -1, 0, 1, 1/2]
            sage: f2 = Stream_derivative(f, 2, True)
            sage: [f2[i] for i in range(-5, 3)]
            [0, -3, -2, 0, 0, 1, 2, 3]

            sage: f = Stream_function(lambda n: 1/n, True, 2)
            sage: [f[i] for i in range(-1, 4)]
            [0, 0, 0, 1/2, 1/3]
            sage: f2 = Stream_derivative(f, 3, True)
            sage: [f2[i] for i in range(-1, 4)]
            [0, 2, 6, 12, 20]
        """
        return (prod(n + k for k in range(1, self._shift + 1))
                * self._series[n + self._shift])

    def __hash__(self):
        """
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function
            sage: from sage.data_structures.stream import Stream_derivative
            sage: a = Stream_function(lambda n: 2*n, False, 1)
            sage: f = Stream_derivative(a, 1, True)
            sage: g = Stream_derivative(a, 2, True)
            sage: hash(f) == hash(f)
            True
            sage: hash(f) == hash(g)
            False
        """
        return hash((type(self), self._series, self._shift))

    def __eq__(self, other):
        """
        Return whether ``self`` and ``other`` are known to be equal.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_function
            sage: from sage.data_structures.stream import Stream_derivative
            sage: a = Stream_function(lambda n: 2*n, False, 1)
            sage: f = Stream_derivative(a, 1, True)
            sage: g = Stream_derivative(a, 2, True)
            sage: f == g
            False
            sage: f == Stream_derivative(a, 1, True)
            True
        """
        return (isinstance(other, type(self))
                and self._shift == other._shift
                and self._series == other._series)

    def is_nonzero(self):
        r"""
        Return ``True`` if and only if this stream is known
        to be non-zero.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_exact, Stream_derivative
            sage: f = Stream_exact([1,2])
            sage: Stream_derivative(f, 1, True).is_nonzero()
            True
            sage: Stream_derivative(f, 2, True).is_nonzero() # it might be nice if this gave False
            True
        """
        return self._series.is_nonzero()


class Stream_infinite_operator(Stream):
    r"""
    Stream defined by applying an operator an infinite number of times.

    The ``iterator`` returns elements `s_i` to compute an infinite operator.
    The valuation of `s_i` is weakly increasing as we iterate over `I` and
    there are only finitely many terms with any fixed valuation.
    In particular, this *assumes* the result is nonzero.

    .. WARNING::

        This does not check that the input is valid.

    INPUT:

    - ``iterator`` -- the iterator for the factors
    """
    def __init__(self, iterator):
        r"""
        Initialize ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_sum
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: it = (t^n / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_sum(it)
        """
        self._op_iter = iterator
        self._cur = None
        self._cur_order = -infinity
        super().__init__(False)

    @lazy_attribute
    def _approximate_order(self):
        r"""
        Compute and return the approximate order of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_sum, Stream_infinite_product
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: it = (t^n / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_sum(it)
            sage: f._approximate_order
            1
            sage: it = (t^n for n in PositiveIntegers())
            sage: f = Stream_infinite_product(it)
            sage: f._approximate_order
            0
            sage: it = (t^(n-10) for n in PositiveIntegers())
            sage: f = Stream_infinite_product(it)
            sage: f._approximate_order
            -45
        """
        if self._cur is None:
            self._advance()
        while self._cur_order <= 0:
            self._advance()
        return self._cur._coeff_stream._approximate_order

    def _advance(self):
        r"""
        Advance the iterator so that the approximate order increases
        by at least one.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_sum
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: it = (n * t^n for n in range(10))
            sage: f = Stream_infinite_sum(it)
            sage: f._cur is None
            True
            sage: f._advance()
            sage: f._cur
            t + 2*t^2
            sage: f._cur_order
            2
            sage: for _ in range(20):
            ....:     f._advance()
            sage: f._cur
            t + 2*t^2 + 3*t^3 + 4*t^4 + 5*t^5 + 6*t^6 + 7*t^7 + 8*t^8 + 9*t^9
            sage: f._cur_order
            +Infinity

            sage: it = (t^(n//3) / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_sum(it)
            sage: f._advance()
            sage: f._cur
            2 + 3*t + 3*t^2 + 3*t^3 + O(t^4)
            sage: f._advance()
            sage: f._cur
            2 + 5*t + 6*t^2 + 6*t^3 + 6*t^4 + O(t^5)
        """
        if self._cur is None:
            temp = next(self._op_iter)
            if isinstance(temp._coeff_stream, Stream_zero):
                self._advance()
                return
            self.initial(temp)
            self._cur_order = temp._coeff_stream._approximate_order

        order = self._cur_order
        while order == self._cur_order:
            try:
                next_factor = next(self._op_iter)
            except StopIteration:
                self._cur_order = infinity
                return
            if isinstance(next_factor._coeff_stream, Stream_zero):
                continue
            coeff_stream = next_factor._coeff_stream
            while coeff_stream._approximate_order < order:
                # This check also updates the next_factor._approximate_order
                if coeff_stream[coeff_stream._approximate_order]:
                    order = coeff_stream._approximate_order
                    raise ValueError(f"invalid product computation with invalid order {order} < {self._cur_order}")
            self.apply_operator(next_factor)
            order = coeff_stream._approximate_order
            # We check to see if we need to increment the order
            if order == self._cur_order and not coeff_stream[order]:
                order += 1
        self._cur_order = order

    def __getitem__(self, n):
        r"""
        Return the ``n``-th coefficient of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_sum
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: it = (t^n / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_sum(it)
            sage: f[2]
            2
            sage: f[5]
            5
        """
        while n >= self._cur_order:
            self._advance()
        return self._cur[n]

    def order(self):
        r"""
        Return the order of ``self``, which is the minimum index ``n`` such
        that ``self[n]`` is nonzero.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_sum
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: it = (t^(5+n) / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_sum(it)
            sage: f.order()
            6
        """
        return self._approximate_order

    def __hash__(self):
        r"""
        Return the hash of ``self``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_sum
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: it = (t^n / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_sum(it)
            sage: hash(f) == hash((type(f), f._op_iter))
            True
        """
        return hash((type(self), self._op_iter))

    def __ne__(self, other):
        r"""
        Return whether ``self`` and ``other`` are known to be equal.

        INPUT:

        - ``other`` -- a stream

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_sum
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: itf = (t^n / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_sum(itf)
            sage: itg = (t^(2*n-1) / (1 - t) for n in PositiveIntegers())
            sage: g = Stream_infinite_sum(itg)
            sage: f != g
            False
            sage: f[10]
            10
            sage: g[10]
            5
            sage: f != g
            True
        """
        if not isinstance(other, type(self)):
            return True
        ao = min(self._approximate_order, other._approximate_order)
        if any(self[i] != other[i] for i in range(ao, min(self._cur_order, other._cur_order))):
            return True
        return False

    def is_nonzero(self):
        r"""
        Return ``True`` if and only if this stream is known
        to be nonzero.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_sum
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: it = (t^n / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_sum(it)
            sage: f.is_nonzero()
            True
        """
        return True


class Stream_infinite_sum(Stream_infinite_operator):
    r"""
    Stream defined by an infinite sum.

    The ``iterator`` returns elements `s_i` to compute the product
    `\sum_{i \in I} s_i`. See :class:`Stream_infinite_operator`
    for restrictions on the `s_i`.

    INPUT:

    - ``iterator`` -- the iterator for the factors
    """
    def initial(self, obj):
        r"""
        Set the initial data.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_sum
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: it = (t^n / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_sum(it)
            sage: f._cur is None
            True
            sage: f._advance()  # indirect doctest
            sage: f._cur
            t + 2*t^2 + 2*t^3 + 2*t^4 + O(t^5)
        """
        self._cur = obj

    def apply_operator(self, next_obj):
        r"""
        Apply the operator to ``next_obj``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_sum
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: it = (t^(n//2) / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_sum(it)
            sage: f._advance()
            sage: f._advance()  # indirect doctest
            sage: f._cur
            1 + 3*t + 4*t^2 + 4*t^3 + 4*t^4 + O(t^5)
        """
        self._cur += next_obj


class Stream_infinite_product(Stream_infinite_operator):
    r"""
    Stream defined by an infinite product.

    The ``iterator`` returns elements `p_i` to compute the product
    `\prod_{i \in I} (1 + p_i)`. See :class:`Stream_infinite_operator`
    for restrictions on the `p_i`.

    INPUT:

    - ``iterator`` -- the iterator for the factors
    """
    def initial(self, obj):
        r"""
        Set the initial data.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_product
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: it = (t^n / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_product(it)
            sage: f._cur is None
            True
            sage: f._advance()  # indirect doctest
            sage: f._cur
            1 + t + 2*t^2 + 3*t^3 + 4*t^4 + 5*t^5 + 6*t^6 + O(t^7)
        """
        self._cur = obj + 1

    def apply_operator(self, next_obj):
        r"""
        Apply the operator to ``next_obj``.

        EXAMPLES::

            sage: from sage.data_structures.stream import Stream_infinite_product
            sage: L.<t> = LazyLaurentSeriesRing(QQ)
            sage: it = (t^n / (1 - t) for n in PositiveIntegers())
            sage: f = Stream_infinite_product(it)
            sage: f._advance()
            sage: f._advance()  # indirect doctest
            sage: f._cur
            1 + t + 2*t^2 + 4*t^3 + 6*t^4 + 9*t^5 + 13*t^6 + O(t^7)
        """
        self._cur = self._cur + self._cur * next_obj
