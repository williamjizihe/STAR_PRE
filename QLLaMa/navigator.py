import numpy as np

class Boss:
    def __init__(self, G: list):
        # G is a list of ndIntervals
        self.G = G
        self.visit_matrix = np.zeros((len(G), len(G)))
        
    def identify_partition(self, state):
        """Identify the partition of the state"""
        start_partition = -1
        for i in range(len(self.G)):
            if state in self.G[i]:
                start_partition = i
                break
        return start_partition

    def strict_identify_partition(self, state):
        """Identify the partition of the state"""
        start_partition = -1
        for i in range(len(self.G)):
            if self.G[i].strict_contains(state):
                start_partition = i
                break
        return start_partition
    
    def count_visits(self, state, next_state):
        """Count the number of visits from start_partition to end_partition"""
        start_partition = self.strict_identify_partition(state)
        end_partition = self.strict_identify_partition(next_state)
        if start_partition != -1 and end_partition != -1 and start_partition != end_partition:
            self.visit_matrix[start_partition][end_partition] += 1