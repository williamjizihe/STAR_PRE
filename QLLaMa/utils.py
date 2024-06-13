class Interval:
    """
    Class that represents a single interval [inf, sup].
    """
    def __init__(self, inf, sup):
        if inf > sup:
            raise ValueError("Lower bound must not be greater than upper bound.")
        self.inf = inf
        self.sup = sup

    def __contains__(self, item):
        return self.inf <= item <= self.sup
    
    def strict_contains(self, item):
        return self.inf < item < self.sup

    def __repr__(self):
        return f"[{self.inf}, {self.sup}]"

class ndInterval:
    """
    Class that creates arrays of intervals and extends interval methods across the array.
    """

    def __init__(self, n, inf=None, sup=None):
        self.n = n
        self.inf = inf if inf is not None else [float('-inf')] * n
        self.sup = sup if sup is not None else [float('inf')] * n
        if len(self.inf) != n or len(self.sup) != n:
            raise ValueError("The length of inf and sup must match n.")
        self.intervals = [Interval(self.inf[i], self.sup[i]) for i in range(n)]

    def __contains__(self, item):
        if len(item) != self.n:
            raise ValueError("Dimension mismatch: item length must match the number of intervals.")
        return all(item[i] in self.intervals[i] for i in range(self.n))

    def strict_contains(self, item):
        if len(item) != self.n:
            raise ValueError("Dimension mismatch: item length must match the number of intervals.")
        return all(self.intervals[i].strict_contains(item[i]) for i in range(self.n))
    
    def __repr__(self):
        return f"ndInterval({self.intervals})"

# Example usage:
if __name__ == '__main__':
    nd_interval = ndInterval(2, [1, 2], [3, 4])
    print(nd_interval)  # Output: ndInterval([[1, 3], [2, 4]])

    point = [2, 3]
    print(point in nd_interval)  # Output: True

    point = [4, 3]
    print(point in nd_interval)  # Output: False
