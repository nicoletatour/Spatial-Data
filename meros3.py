#TOUROUNOGLOU NIKOLETA AM:5106
import sys, heapq
from pathlib import Path


class MBR:
    def __init__(self, xmin, xmax, ymin, ymax):
        self.xmin = xmin; self.xmax = xmax
        self.ymin = ymin; self.ymax = ymax

    def mindistance(self, x, y):
        dx = 0.0
        if   x < self.xmin: dx = self.xmin - x
        elif x > self.xmax: dx = x - self.xmax

        dy = 0.0
        if   y < self.ymin: dy = self.ymin - y
        elif y > self.ymax: dy = y - self.ymax

        return dx*dx + dy*dy

class Entry:
    def __init__(self, eid, mbr, is_leaf_entry):
        self.id        = eid         
        self.mbr       = mbr
        self.is_leaf_entry = is_leaf_entry  

class Node:
    def __init__(self, is_leaf, node_id):
        self.is_leaf = is_leaf
        self.id      = node_id
        self.entries = []
    def add(self, entry): 
        self.entries.append(entry)


def load_rtree(path):
    nodes = {}
    with Path(path).open() as f:
        for line in f:
            if not (line := line.strip()): 
                continue
            isnonleaf, node_id, raw = eval(line)
            nd = Node(isnonleaf == 0, node_id)  
            for eid, box in raw:
                mbr = MBR(*box)
                nd.add(Entry(eid, mbr, nd.is_leaf))  
            nodes[node_id] = nd
    return nodes


def knn_query(root, nodes, qx, qy, k):
    heap = []                        
    counter = 0                  
    for e in root.entries:         
        d2 = e.mbr.mindistance(qx, qy)
        heapq.heappush(heap, (d2, counter, e))
        counter += 1

    result = []
    while heap and len(result) < k:
        d2, _, entry = heapq.heappop(heap)
        if entry.is_leaf_entry:     
            result.append(entry.id)
        else:                      
            child = nodes[entry.id]
            for ch in child.entries:
                d2c = ch.mbr.mindistance(qx, qy)
                heapq.heappush(heap, (d2c, counter, ch))
                counter += 1
    return result


def main(argv):
    if len(argv) != 4:
        sys.exit(1)

    rtree_file, nn_file, k_str = argv[1:]
    k = int(k_str)

    nodes = load_rtree(rtree_file)
    root  = nodes[max(nodes)]       

    idx = 0
    with Path(nn_file).open() as f:
        for line in f:
            line = line.strip()
            if not line:
                idx += 1
                continue
            parts = line.split()
            qx = float(parts[0])
            qy = float(parts[1])

            ids = knn_query(root, nodes, qx, qy, k)

            id_strs = []
            for i in ids:
                id_strs.append(str(i))
            print(f"{idx}: " + ",".join(id_strs))

            idx += 1

if __name__ == "__main__":
    main(sys.argv)

