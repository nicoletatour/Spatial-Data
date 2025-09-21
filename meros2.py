#TOUROUNOGLOU NIKOLETA AM:5106
import sys
from pathlib import Path

class MBR:
    def __init__(self, xmin, xmax, ymin, ymax):
        self.xmin = xmin 
        self.xmax = xmax
        self.ymin = ymin 
        self.ymax = ymax

    def intersects(self, other):
        return not (self.xmax < other.xmin or self.xmin > other.xmax or
                    self.ymax < other.ymin or self.ymin > other.ymax)

class Entry:
    def __init__(self, eid, mbr):
        self.id = eid
        self.mbr = mbr

class Node:
    def __init__(self, is_leaf, node_id):
        self.is_leaf = is_leaf
        self.id = node_id
        self.entries = []
    def add(self, entry):
        self.entries.append(entry)

def load_rtree(path):
    nodes = {}
    with Path(path).open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

           
            isnonleaf, node_id, entries_temp = eval(line) 

            nd = Node(isnonleaf == 0, node_id)
            for eid, mlist in entries_temp:
                nd.add(Entry(eid, MBR(*mlist)))
            nodes[node_id] = nd
    return nodes


def range_query(root, nodes, win):
    w = MBR(win[0], win[1], win[2], win[3])
    out = []

    def dfs(node):
        for e in node.entries:
            if not e.mbr.intersects(w):
                continue
            if node.is_leaf:              
                out.append(e.id)
            else:                         
                dfs(nodes[e.id])

    dfs(root)
    return out

def main(argv):
    if len(argv) != 3:
        sys.exit(1)

    nodes = load_rtree(argv[1])
    root = nodes[max(nodes)] 

    with Path(argv[2]).open() as f:
           
        idx = 0
        for line in f:

            current_idx = idx

            line = line.strip()
            if not line:
                idx += 1
                continue

            parts = line.split()
            x_low  = float(parts[0])
            y_low  = float(parts[1])
            x_high = float(parts[2])
            y_high = float(parts[3])

            hits = range_query(root, nodes, [x_low, x_high, y_low, y_high])
            hits.sort()

            hit_strs = []
            for h in hits:
                hit_strs.append(str(h))

            print(f"{current_idx} ({len(hits)}): " + ",".join(hit_strs))

            idx += 1


if __name__ == "__main__":
    main(sys.argv)
