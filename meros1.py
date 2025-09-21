#TOUROUNOGLOU NIKOLETA AM:5106
import sys
from pathlib import Path
from typing import List, Tuple
from pymorton import interleave_latlng

M = 20   
m = 8    

class MBR:

    def __init__(self, xmin, xmax, ymin, ymax):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax

    @staticmethod
    def union(a, b):
        
        if a is None:
            return MBR(b.xmin, b.xmax, b.ymin, b.ymax)

        new_xmin = min(a.xmin, b.xmin)
        new_xmax = max(a.xmax, b.xmax)
        new_ymin = min(a.ymin, b.ymin)
        new_ymax = max(a.ymax, b.ymax)

        return MBR(new_xmin, new_xmax, new_ymin, new_ymax)

    def to_list(self):
        return [self.xmin, self.xmax, self.ymin, self.ymax]


class Entry:
    def __init__(self, eid, mbr):
        self.id = eid
        self.mbr = mbr


class Node:
    _next_id = 0

    def __init__(self, is_leaf):
        self.id = Node._next_id
        Node._next_id += 1

        self.is_leaf = is_leaf
        self.entries: List[Entry] = []
        self.mbr = None 

    def add(self, entry: Entry):
        self.entries.append(entry)
        self.mbr = MBR.union(self.mbr, entry.mbr)



def read_coords(filepath: str) -> List[Tuple[float, float]]:
    coords: List[Tuple[float, float]] = []
    path = Path(filepath)

    f = path.open()
    for line in f:
        line = line.strip()

        if line == "":
            continue
        else:
            parts = line.split(",")
            x_str = parts[0]
            y_str = parts[1]

            x = float(x_str)
            y = float(y_str)

            coords.append((x, y))
           
    f.close()

    return coords


def read_offsets(filepath: str, coords: List[Tuple[float, float]]):
    objects = []
    gxmin = gxmax = gymin = gymax = None

    with Path(filepath).open() as f:
        for line in f:
            line = line.strip()
            if line == "":
                continue

            parts = line.split(",")
            oid = int(parts[0])
            start = int(parts[1])
            end   = int(parts[2])

            first_x, first_y = coords[start]
            xmin = xmax = first_x
            ymin = ymax = first_y

            for idx in range(start + 1, end + 1):
                x, y = coords[idx]
                if x < xmin:
                    xmin = x
                if x > xmax:
                    xmax = x
                if y < ymin:
                    ymin = y
                if y > ymax:
                    ymax = y

            mbr = MBR(xmin, xmax, ymin, ymax)
            objects.append({"id": oid, "mbr": mbr})

            if gxmin is None or xmin < gxmin:
                gxmin = xmin
            if gxmax is None or xmax > gxmax:
                gxmax = xmax
            if gymin is None or ymin < gymin:
                gymin = ymin
            if gymax is None or ymax > gymax:
                gymax = ymax

    return objects, (gxmin, gxmax, gymin, gymax)


def morton_sort(objects, extents):
    (gxmin, gxmax, gymin, gymax) = extents

    for obj in objects:
        cx = (obj["mbr"].xmin + obj["mbr"].xmax) / 2.0
        cy = (obj["mbr"].ymin + obj["mbr"].ymax) / 2.0

        code = interleave_latlng(cy, cx)
        obj["code"] = code

    objects.sort(key=lambda o: o["code"])


def recompute(node: Node) -> MBR:
    box = None
    for entry in node.entries:
        box = MBR.union(box, entry.mbr)
    return box


def build_leaves(objects):
    leaves = []         
    i = 0
    total = len(objects)

    while i < total:
        grouplist = objects[i:i + M]  
        block_objs = list(grouplist)

        if len(block_objs) < m:
            if len(leaves) > 0:
                previous = leaves[-1]
                need = m - len(block_objs)

                while need > 0 and len(previous.entries) > m:
                    borrowed = previous.entries.pop()
                    previous.mbr = recompute(previous)
                    block_objs.insert(0, {"id": borrowed.id, "mbr": borrowed.mbr})
                    need -= 1

                if len(block_objs) < m:
                    for r in block_objs:
                        entry = Entry(r["id"], r["mbr"])
                        previous.add(entry)
                    i += len(block_objs)
                    continue

        leaf = Node(is_leaf=True)
        for rec in block_objs:
            entry = Entry(rec["id"], rec["mbr"])
            leaf.add(entry)
        leaves.append(leaf)

        i += len(block_objs)

    return leaves

def build_levels(bottom):

    levels = [bottom]        
    current = bottom           

    while True:
        if len(current) == 1:       
            break

        if len(current) <= M:        
            root = Node(is_leaf=False)
            for child in current:
                root.add(Entry(child.id, child.mbr))
            levels.append([root])   
            break

        groups = []
        idx = 0
        while idx < len(current):
            groups.append(current[idx:idx + M])
            idx += M

        if len(groups[-1]) < m:
            prev  = groups[-2]
            last  = groups[-1]
            need  = m - len(last)
            while need > 0 and len(prev) > m:
                last.insert(0, prev.pop())  
                need -= 1
            if len(last) < m:              
                prev.extend(last)
                groups.pop()

        next_level = []
        for grp in groups:
            parent = Node(is_leaf=False)
            for child in grp:
                entry = Entry(child.id, child.mbr)
                parent.add(entry)
            next_level.append(parent)

        levels.append(next_level)  
        current = next_level       

    return levels


def node_as_string(node: Node) -> str:
    if node.is_leaf:
        kind_flag = 0
    else:
        kind_flag = 1

    parts = []
    for ent in node.entries:
        parts.append(f"[{ent.id}, {ent.mbr.to_list()}]")

    joined = ", ".join(parts)
    return f"[{kind_flag}, {node.id}, [{joined}]]"


def main(argv):

    if len(argv) != 3:
        sys.exit(1)

    coords_file = argv[1]
    offsets_file = argv[2]

    coords = read_coords(coords_file)
    objects, extents = read_offsets(offsets_file, coords)

    morton_sort(objects, extents)

    leaves = build_leaves(objects)

    levels = build_levels(leaves)

    depth = 0
    for lvl in levels:
        count = len(lvl)
        if count == 1:
            ending = ""
        else:
            ending = "s"

        print(f"{count} node{ending} at level {depth}")
        depth += 1

    out_path = Path("Rtree.txt")
    out_file = out_path.open("w")

    all_nodes = []
    for lvl in levels:
        for nd in lvl:
            all_nodes.append(nd)

    all_nodes.sort(key=lambda n: n.id)

    for node in all_nodes:
        line = node_as_string(node)
        out_file.write(line + "\n")

    out_file.close()


if __name__ == '__main__':
    main(sys.argv)
