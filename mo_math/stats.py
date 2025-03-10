# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#


import math
import sys
from math import sqrt

from mo_dots import Data, Null, coalesce
from mo_future import text, zip_longest
from mo_imports import delay_import

from mo_math import OR, almost_equal
from mo_math.vendor import strangman

logger = delay_import("mo_logs.Log")

DEBUG = False
DEBUG_STRANGMAN = False
EPSILON = 0.000000001
ABS_EPSILON = sys.float_info.min * 2  # *2 FOR SAFETY

if DEBUG_STRANGMAN:
    try:
        import numpy as np
        from scipy import stats
        import scipy
    except Exception as e:
        DEBUG_STRANGMAN = False


def chisquare(f_obs, f_exp):
    try:
        py_result = strangman.stats.chisquare(f_obs, f_exp)
    except Exception as e:
        logger.error("problem with call", e)

    if DEBUG_STRANGMAN:
        from mo_testing.fuzzytestcase import assertAlmostEqualValue

        sp_result = scipy.stats.chisquare(np.frum(f_obs), f_exp=np.frum(f_exp))
        if not assertAlmostEqualValue(sp_result[0], py_result[0], digits=9) and assertAlmostEqualValue(
            sp_result[1], py_result[1], delta=1e-8
        ):
            logger.error("problem with stats lib")

    return py_result


def Stats2ZeroMoment(stats):
    # MODIFIED FROM http://statsmodels.sourceforge.net/devel/_modules/statsmodels/stats/moment_helpers.html
    # ADDED count
    mc0, mc1, mc2, skew, kurt = (
        stats.count,
        coalesce(stats.mean, 0),
        coalesce(stats.variance, 0),
        coalesce(stats.skew, 0),
        coalesce(stats.kurtosis, 0),
    )

    mz0 = mc0
    mz1 = mc1 * mc0
    mz2 = (mc2 + mc1 * mc1) * mc0
    mc3 = coalesce(skew, 0) * (mc2 ** 1.5)  # 3rd central moment
    mz3 = (mc3 + 3 * mc1 * mc2 + mc1 ** 3) * mc0  # 3rd non-central moment
    mc4 = (coalesce(kurt, 0) + 3.0) * (mc2 ** 2.0)  # 4th central moment
    mz4 = (mc4 + 4 * mc1 * mc3 + 6 * mc1 * mc1 * mc2 + mc1 ** 4) * mc0

    m = ZeroMoment(mz0, mz1, mz2, mz3, mz4)
    if DEBUG:
        from mo_testing.fuzzytestcase import assertAlmostEqualValue

        globals()["DEBUG"] = False
        try:
            v = ZeroMoment2Stats(m)
            assertAlmostEqualValue(v.count, stats.count, places=10)
            assertAlmostEqualValue(v.mean, stats.mean, places=10)
            assertAlmostEqualValue(v.variance, stats.variance, places=10)
            assertAlmostEqualValue(v.skew, stats.skew, places=10)
            assertAlmostEqualValue(v.kurtosis, stats.kurtosis, places=10)
        except Exception as e:
            v = ZeroMoment2Stats(m)
            logger.error("programmer error")
        globals()["DEBUG"] = True
    return m


def ZeroMoment2Stats(z_moment):
    Z = z_moment.S
    if not Z:
        return Stats()
    N = Z[0]
    if N == 0:
        return Stats()

    mean = Z[1] / N
    Z2 = Z[2] / N
    Z3 = Z[3] / N
    Z4 = Z[4] / N

    if N == 1:
        variance = None
        skew = None
        kurtosis = None
    else:
        if almost_equal(Z2, mean * mean, digits=9):
            variance = 0
            skew = None
            kurtosis = None
        else:
            variance = Z2 - mean * mean
            mc3 = Z3 - (3 * mean * variance + mean ** 3)  # 3rd central moment
            mc4 = Z4 - (4 * mean * mc3 + 6 * mean * mean * variance + mean ** 4)
            skew = mc3 / (variance ** 1.5)
            kurtosis = (mc4 / (variance ** 2.0)) - 3.0

    stats = Stats(count=N, mean=mean, variance=variance, skew=skew, kurtosis=kurtosis)

    if DEBUG:
        from mo_testing.fuzzytestcase import assertAlmostEqualValue

        globals()["DEBUG"] = False
        v = Null
        try:
            v = Stats2ZeroMoment(stats)
            for i in range(5):
                assertAlmostEqualValue(v.S[i], Z[i], places=7)
        except Exception as e:
            logger.error(
                "Conversion failed.  Programmer error:\nfrom={{from|indent}},\nresult"
                " stats={{stats|indent}},\nexpected param={{expected|indent}}",
                {"from": Z},
                stats=stats,
                expected=v.S,
                cause=e,
            )
        globals()["DEBUG"] = True

    return stats


class Stats(Data):
    def __init__(self, **kwargs):
        Data.__init__(self)

        self.count = 0
        self.mean = None
        self.variance = None
        self.skew = None
        self.kurtosis = None

        if "samples" in kwargs:
            s = ZeroMoment2Stats(ZeroMoment.new_instance(kwargs["samples"]))
            self.count = s.count
            self.mean = s.mean
            self.variance = s.variance
            self.skew = s.skew
            self.kurtosis = s.kurtosis
            return

        if "count" not in kwargs:
            self.count = 0
            self.mean = None
            self.variance = None
            self.skew = None
            self.kurtosis = None
        elif "mean" not in kwargs:
            self.count = kwargs["count"]
            self.mean = None
            self.variance = None
            self.skew = None
            self.kurtosis = None
        elif "variance" not in kwargs and "std" not in kwargs:
            self.count = kwargs["count"]
            self.mean = kwargs["mean"]
            self.variance = 0
            self.skew = None
            self.kurtosis = None
        elif "skew" not in kwargs:
            self.count = kwargs["count"]
            self.mean = kwargs["mean"]
            self.variance = kwargs["variance"] if "variance" in kwargs else kwargs["std"] ** 2
            self.skew = None
            self.kurtosis = None
        elif "kurtosis" not in kwargs:
            self.count = kwargs["count"]
            self.mean = kwargs["mean"]
            self.variance = kwargs["variance"] if "variance" in kwargs else kwargs["std"] ** 2
            self.skew = kwargs["skew"]
            self.kurtosis = None
        else:
            self.count = kwargs["count"]
            self.mean = kwargs["mean"]
            self.variance = kwargs["variance"] if "variance" in kwargs else kwargs["std"] ** 2
            self.skew = kwargs["skew"]
            self.kurtosis = kwargs["kurtosis"]

    @property
    def std(self):
        return sqrt(self.variance)


class ZeroMoment:
    """
    ZERO-CENTERED MOMENTS
    """

    def __init__(self, *args):
        self.S = args

    def __add__(self, other):
        output = ZeroMoment()
        output += other
        return output

    def __iadd__(self, other):
        if isinstance(other, ZeroMoment):
            return ZeroMoment(*array_add(self.S, other.S))
        elif hasattr(other, "__iter__"):
            return ZeroMoment(*array_add(self.S, ZeroMoment.new_instance(other)))
        elif other == None:
            return self
        else:
            return ZeroMoment(
                *array_add(self.S, (1, other, pow(other, 2), pow(other, 3), pow(other, 4), pow(other, 2),),)
            )

    @property
    def tuple(self):
        # RETURN AS ORDERED TUPLE
        return self.S

    def __data__(self):
        # RETURN HASH OF SUMS
        return {"s" + str(i): m for i, m in enumerate(self.S)}

    @staticmethod
    def new_instance(values=None):
        if values == None:
            return ZeroMoment()

        vals = tuple(values)
        return ZeroMoment(
            len(vals),
            sum(vals),
            sum([pow(n, 2) for n in vals]),
            sum([pow(n, 3) for n in vals]),
            sum([pow(n, 4) for n in vals]),
        )

    @property
    def stats(self):
        return ZeroMoment2Stats(self)


def array_add(A, B):
    return tuple(coalesce(a, 0) + coalesce(b, 0) for a, b in zip_longest(A, B))


def sub(a, b):
    return coalesce(a, 0) - coalesce(b, 0)


def ZeroMoment2dict(z):
    # RETURN HASH OF SUMS
    return {"s" + str(i): m for i, m in enumerate(z.S)}


def median(values, simple=True, mean_weight=0.0):
    """
    RETURN MEDIAN VALUE

    IF simple=False THEN IN THE EVENT MULTIPLE INSTANCES OF THE
    MEDIAN VALUE, THE MEDIAN IS INTERPOLATED BASED ON ITS POSITION
    IN THE MEDIAN RANGE

    mean_weight IS TO PICK A MEDIAN VALUE IN THE ODD CASE THAT IS
    CLOSER TO THE MEAN (PICK A MEDIAN BETWEEN TWO MODES IN BIMODAL CASE)
    """

    if OR(v == None for v in values):

        logger.error("median is not ready to handle None")

    try:
        if not values:
            return Null

        l = len(values)
        _sorted = sorted(values)

        middle = int(l / 2)
        _median = float(_sorted[middle])

        if len(_sorted) == 1:
            return _median

        if simple:
            if l % 2 == 0:
                return (_sorted[middle - 1] + _median) / 2
            return _median

        # FIND RANGE OF THE median
        start_index = middle - 1
        while start_index > 0 and _sorted[start_index] == _median:
            start_index -= 1
        start_index += 1
        stop_index = middle + 1
        while stop_index < l and _sorted[stop_index] == _median:
            stop_index += 1

        num_middle = stop_index - start_index

        if l % 2 == 0:
            if num_middle == 1:
                return (_sorted[middle - 1] + _median) / 2
            else:
                return (_median - 0.5) + (middle - start_index) / num_middle
        else:
            if num_middle == 1:
                return (1 - mean_weight) * _median + mean_weight * (_sorted[middle - 1] + _sorted[middle + 1]) / 2
            else:
                return (_median - 0.5) + (middle + 0.5 - start_index) / num_middle
    except Exception as e:
        logger.error("problem with median of {values}", values=values, cause=e)


def percentile(values, percent):
    """
    PERCENTILE WITH INTERPOLATION
    RETURN VALUE AT, OR ABOVE, percentile OF THE VALUES

    snagged from http://code.activestate.com/recipes/511478-finding-the-percentile-of-the-values/
    """
    N = sorted(values)
    if not N:
        return None
    k = (len(N) - 1) * percent
    f = int(math.floor(k))
    c = int(math.ceil(k))
    if f == c:
        return N[int(k)]
    d0 = N[f] * (c - k)
    d1 = N[c] * (k - f)
    return d0 + d1


zero = Stats()
