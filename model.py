import vfe, vre


class VoxelElement:
    """
    The node labeling of voxel

    upper nodes
    p__o
    /__/
    m  n

    lower nodes
    l__k
    /__/
    i  j

    axis direction
    _ x
    | z
    / y

    i : (0, 0, 0)
    j : (1, 0, 0)
    k : (1, 1, 0)
    l : (0, 1, 0)
    m : (0, 0, 1)
    n : (1, 0, 1)
    o : (1, 1, 1)
    p : (0, 1, 1)

    node id is sampled in order (... i m .... l p ... j n ... k o ...) starting from 1
    """

    def __init__(self, id, elem):
        self._elem = elem
        self.id = id
        self.pos = (elem.pos_x, elem.pos_y, elem.pos_z)
        self.node_ids = [elem.node_1, elem.node_2, elem.node_3, elem.node_4,
                         elem.node_1 + elem.node_diff_1, elem.node_2 + elem.node_diff_2,
                         elem.node_3 + elem.node_diff_3,
                         elem.node_4 + elem.node_diff_4]

    def node_pos(self, size):
        p = self.pos
        x, y, z = size
        return [
            (p[0], p[1], p[2]),
            (p[0] + x, p[1], p[2]),
            (p[0] + x, p[1] + y, p[2]),
            (p[0], p[1] + y, p[2]),
            (p[0], p[1], p[2] + z),
            (p[0] + x, p[1], p[2] + z),
            (p[0] + x, p[1] + y, p[2] + z),
            (p[0], p[1] + y, p[2] + z),
        ]

    def __str__(self):
        return 'v({}, {})'.format(self.id, self.pos)

    def __repr__(self):
        return self.__str__()


class VoxelMap:
    def __init__(self, modelprp, voxels):
        self._modelprp = modelprp
        self.num_node = modelprp.num_node
        self.size = (modelprp.size_x, modelprp.size_y, modelprp.size_z)
        self.num = (modelprp.num_x, modelprp.num_y, modelprp.num_z)
        self.elems = [VoxelElement(i, elem) for i, elem in enumerate(voxels)]
        self.elems_map = {elem.pos: elem for elem in self.elems}


class Node:
    def __init__(self, idx):
        self.idx = idx
        self.pos = None

    @property
    def id(self):
        return self.idx + 1

    def save(self, pos):
        if self.pos is None:
            self.pos = pos
            return
        if self.pos != pos:
            raise Exception("pos is not match", self.id, self.pos, pos)

    def __str__(self):
        return 'n({}, {})'.format(self.id, self.pos)

    def __repr__(self):
        return self.__str__()


class NodeMap:
    def __init__(self, voxelmap):
        self.num_node = voxelmap.num_node
        self.nodes = [Node(i) for i in range(self.num_node)]
        for elem in voxelmap.elems:
            for id, pos in zip(elem.node_ids, elem.node_pos(voxelmap.size)):
                self.nodes[id - 1].save(pos)
        self.nodes_map = {node.pos: node for node in self.nodes}


def load_voxel_map(vfe_filename):
    with open(vfe_filename, "rb") as f:
        byteorder, header, version = vfe.decode_header(f)
        ctx = vfe.Context(byteorder, header.size_of_int, header.size_of_real)
        buf = ctx.next_record(f)
        modelprp, element, voxels = None, None, None
        while buf is not None:
            recid = vfe.decode_recid(ctx, ctx.unwrap_record(buf))
            if recid == vfe.ModelPrpId:
                modelprp = vfe.decode_modelprp(ctx, ctx.unwrap_record(buf))
            elif recid == vfe.ElementId:
                element, voxels = vfe.decode_element(ctx, ctx.unwrap_record(buf))
            buf = ctx.next_record(f)
    voxelmap = VoxelMap(modelprp, voxels)
    return voxelmap


class OutputValue:
    def __init__(self, type, value, origin):
        self.type = type
        self.value = value.value
        self.pos = origin.pos
        self.origin = origin

    def __str__(self):
        return 'o({}, {}, {})'.format(self.value, self.pos, self.type)

    def __repr__(self):
        return self.__str__()


def load_outputs(vre_filename, voxelmap, nodemap):
    node_outputs = {}
    voxel_outputs = {}
    with open(vre_filename, "rb") as f:
        byteorder, header, version = vre.decode_header(f)
        ctx = vre.Context(byteorder, header.size_of_int, header.size_of_real)
        buf = ctx.next_record(f)
        while buf is not None:
            recid = vre.decode_recid(ctx, ctx.unwrap_record(buf))
            if recid == vre.NodeValId:
                _, outputs = vre.decode_nodeval(ctx, ctx.unwrap_record(buf))
                for output, values in outputs:
                    node_outputs[output.type] = [OutputValue(output.type, value, node) for value, node in
                                                 zip(values, nodemap.nodes)]
            elif recid == vre.ElemValId:
                _, outputs = vre.decode_elemval(ctx, ctx.unwrap_record(buf))
                for output, values in outputs:
                    voxel_outputs[output.type] = [OutputValue(output.type, value, elem) for value, elem in
                                                  zip(values, voxelmap.elems)]
            buf = ctx.next_record(f)
    return voxel_outputs, node_outputs
