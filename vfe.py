import struct
from collections import namedtuple


class DecodeError(Exception):
    pass


class Context:
    def __init__(self, byteorder, size_of_int, size_of_real):
        self.bo = byteorder
        self.size_of_int = size_of_int
        self.size_of_real = size_of_real
        if size_of_int == 4:
            self.i = "i"
        elif size_of_int == 8:
            self.i = "q"
        else:
            raise DecodeError("size_of_int must be 4 or 8", size_of_int)
        if size_of_real == 4:
            self.r = "f"
        elif size_of_int == 8:
            self.r = "d"
        else:
            raise DecodeError("size_of_real must be 4 or 8", size_of_real)

    def next_record(self, f):
        size_decoder = self.create("i")
        buflen = f.read(self.size_of_int)
        if len(buflen) == 0:
            return None
        l, = size_decoder.unpack(buflen)
        buf = f.read(l)
        ll, = size_decoder.unpack(f.read(self.size_of_int))
        if l != ll:
            raise DecodeError("record length not match", l, ll)
        return buflen + buf + buflen

    def unwrap_record(self, buf):
        return buf[self.size_of_int:-self.size_of_int]

    def wrap_record(self, buf):
        size_encoder = self.create("i")
        buflen = size_encoder.pack(len(buf))
        return buflen + buf + buflen

    def create(self, fmt):
        fmt = fmt.replace("i", self.i)
        fmt = fmt.replace("f", self.r)
        fmt = fmt.replace("I", 'i')
        return struct.Struct(self.bo + fmt)


def decode_list(ctx, buf, formats):
    size_decoder = ctx.create("i")
    n, = size_decoder.unpack_from(buf, 0)
    fmt, model = formats[0]

    i = size_decoder.size
    dec = ctx.create(fmt)
    formats = formats[1:]
    models = []
    for _ in range(n):
        m = model._make(dec.unpack_from(buf, i))
        i += dec.size
        if len(formats) > 0:
            ii, ms2 = decode_list(ctx, buf[i:], formats)
            i += ii
            m = (m, ms2)
        models.append(m)
    return (i, models)


def encode_list(ctx, formats, values):
    size_encoder = ctx.create("i")
    fmt = formats[0]
    formats = formats[1:]
    encoder = ctx.create(fmt)

    buf = size_encoder.pack(len(values))
    for v in values:
        if len(formats) == 0:
            buf += encoder.pack(*v)
        else:
            v2, vals2 = v
            buf += encoder.pack(*v2)
            buf += encode_list(ctx, formats, vals2)
    return buf


def decode_recid(ctx, buf):
    recid_decoder = ctx.create("i")
    recid, = recid_decoder.unpack_from(buf, 0)
    return recid


# ================================
# ヘッダブロック
# ================================

#
# フォーマット
#
HeaderFormat = 'BBx??Bxiiii8x'
Header = namedtuple('Header', [
    # 整数データ長
    'size_of_int',

    # 実数データ長
    'size_of_real',

    # S版フォーマット
    'is_s',

    # P版フォーマット
    'is_p',

    # 作成プログラム
    'prog',

    # 断面種類
    'kind_section',

    # 断面位置
    'loc_section',

    # プログラムバージョン番号
    'version',

    # プログラムリビジョン番号
    'revision',
])

#
# バージョン
#
VersionFormat = 'ii'
Version = namedtuple('Version', [
    # バージョン番号
    'version',

    # リビジョン番号
    'revision',
])


def decode_header(f):
    buf = f.read(5)
    if buf[4] == 0:
        byteorder = ">"
    elif buf[4] == 1:
        byteorder = "<"
    else:
        raise DecodeError("byteorder must 0 or 1", buf[4])
    l, = struct.unpack(byteorder + "i", buf[0:4])
    buf = f.read(l - 1)
    ll, = struct.unpack(byteorder + "i", f.read(4))
    if l != ll:
        raise DecodeError("record length not match", l, ll)
    # parse header
    header = Header._make(struct.unpack(byteorder + HeaderFormat, buf))

    # parse version
    l, = struct.unpack(byteorder + "i", f.read(4))
    buf = f.read(l)
    ll, = struct.unpack(byteorder + "i", f.read(4))
    if l != ll:
        raise DecodeError("record length not match", l, ll)
    version = Version._make(struct.unpack(byteorder + VersionFormat, buf))
    return (byteorder, header, version)


def encode_header(ctx, header, version):
    if ctx.bo == '>':
        byteorder = 0
    else:
        byteorder = 1
    bufheader = struct.pack(ctx.bo + 'b' + HeaderFormat, byteorder, ctx.size_of_int, ctx.size_of_real, header.is_p,
                            header.prog, header.version, header.revision)
    bufreclen = struct.pack(ctx.bo + 'i', len(bufheader))
    bufversion = struct.pack(ctx.bo + VersionFormat, *version)
    bufverlen = struct.pack(ctx.bo + 'i', len(bufversion))
    return bufreclen + bufheader + bufreclen + bufverlen + bufversion + bufverlen


# ================================
# 解析パラメータブロック
# ================================

#
# タイトル
#
TitleId = 11
TitleFormat = 'i16si256si256s'
Title = namedtuple('Title', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # 解析条件ID
    'analysis_cond_id',

    # 解析条件名
    'analysis_cond_label',

    # 解析モデルID
    'analysis_model_id',

    # 解析モデル名
    'analysis_model_label',
])


def decode_title(ctx, buf):
    title_decoder = ctx.create(TitleFormat)
    return Title._make(title_decoder.unpack(buf))


def encode_title(ctx, title):
    return ctx.create(TitleFormat).pack(*title)


#
# パラメータ
#
ParamId = 12
ParamFormat = 'i16siiififfiffffffffffffff'
Param = namedtuple('Param', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # 解析種別
    'analysis_type',

    # 解析方法
    'analysis_method',

    # マトリクスソルバー
    'matrix_solver',

    # 収束判定誤差
    'cg_tol',

    # 求める固有値の数
    'num_eigenvalue',

    # 求める周波数の下限
    'lower_freq',

    # 求める周波数の上限
    'upper_freq',

    # 最適化繰り返し数
    'num_iter',

    # 目標ボリューム
    'target_volume',

    # ムーブリミット
    'move_limit',

    # マクロひずみX
    'macro_strain_x',

    # マクロひずみY
    'macro_strain_y',

    # マクロひずみZ
    'macro_strain_z',

    # マクロひずみYZ
    'macro_strain_yz',

    # マクロひずみZX
    'macro_strain_zx',

    # マクロひずみXY
    'macro_strain_xy',

    # マクロ温度差/粘性係数
    'macro_temp_diff',

    # マクロ温度勾配/圧力勾配X
    'macro_temp_grad_x',

    # マクロ温度勾配/圧力勾配Y
    'macro_temp_grad_y',

    # マクロ温度勾配/圧力勾配Z
    'macro_temp_grad_z',

    # 解析時間
    'end_time',

    # 時間増分
    'dtime',
])


def decode_param(ctx, buf):
    param_decoder = ctx.create(ParamFormat)
    if len(buf) > param_decoder.size:
        buf = buf[:param_decoder.size]
        print('param buffer is longer than expected')
    return Param._make(param_decoder.unpack(buf))


def encode_param(ctx, param):
    return ctx.create(ParamFormat).pack(*param)


#
# サブケース
#
SubcaseId = 21
SubcaseFormat = 'i16s'
Subcase = namedtuple('Subcase', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # サブケース数
])
# サブケース本体
SSubcaseFormat = 'i256siii'
SSubcase = namedtuple('SSubcase', [
    # サブケースID
    'id',

    # 名称
    'label',

    # ボクセル／STLモデルID
    'basemodel_id',

    # 拘束セットID
    'constset_id',

    # 荷重セットID
    'loadset_id',
])


def decode_subcase(ctx, buf):
    subcase_decoder = ctx.create(SubcaseFormat)
    subcase = Subcase._make(subcase_decoder.unpack_from(buf, 0))
    n, ssubcases = decode_list(ctx, buf[subcase_decoder.size:], [
        (SSubcaseFormat, SSubcase),
    ])
    if len(buf) - subcase_decoder.size - n > 0:
        raise DecodeError("subcase is too long")
    return (subcase, ssubcases)


def encode_subcase(ctx, subcase):
    return ctx.create(SubcaseFormat).pack(*subcase[0]) \
           + encode_list(ctx, [SSubcaseFormat], subcase[1])


#
# ボクセル要素
#
ElementId = 111
ElementFormat = 'i16s'
Element = namedtuple('Element', [
    # ID
    'id',

    # 名称
    'idstr',
])
# ボクセル要素数
VoxcelFormat = 'IIIIiiiiIIII'
Voxcel = namedtuple('Voxcel', [
    # プロパティID
    'prop_id',

    # 空間位置X
    'pos_x',

    # 空間位置Y
    'pos_y',

    # 空間位置Z
    'pos_z',

    # 節点ID1
    'node_1',

    # 節点ID2
    'node_2',

    # 節点ID3
    'node_3',

    # 節点ID4
    'node_4',

    # 節点ID差分1
    'node_diff_1',

    # 節点ID差分2
    'node_diff_2',

    # 節点ID差分3
    'node_diff_3',

    # 節点ID差分4
    'node_diff_4',
])


def decode_element(ctx, buf):
    element_decoder = ctx.create(ElementFormat)
    element = Element._make(element_decoder.unpack_from(buf, 0))
    n, voxcels = decode_list(ctx, buf[element_decoder.size:], [
        (VoxcelFormat, Voxcel),
    ])
    if len(buf) - element_decoder.size - n > 0:
        raise DecodeError("element is too long")
    return (element, voxcels)


def encode_element(ctx, element):
    return ctx.create(ElementFormat).pack(*element[0]) \
           + encode_list(ctx, [VoxcelFormat], element[1])


#
# 拘束セット
#
ConstSetId = 201
ConstSetFormat = 'i16s'
ConstSet = namedtuple('ConstSet', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # 拘束セット数
])
# 拘束セット本体
ConstFormat = 'i256s'
Const = namedtuple('Const', [
    # 拘束セットID
    'id',

    # 名称
    'label',
])
# 含まれる節点拘束定義
ConstSetNodeFormat = 'i'
ConstSetNode = namedtuple('ConstSetNode', [
    # 節点拘束ID
    'id',
])
# 含まれる温度拘束定義
ConstSetTempFormat = 'i'
ConstSetTemp = namedtuple('ConstSetTemp', [
    # 温度拘束ID
    'id',
])


def decode_constset(ctx, buf):
    constset_decoder = ctx.create(ConstSetFormat)
    constset = ConstSet._make(constset_decoder.unpack_from(buf, 0))
    size_decoder = ctx.create("i")
    size, = size_decoder.unpack_from(buf[constset_decoder.size:], 0)
    n = constset_decoder.size + size_decoder.size
    consts = []
    for i in range(size):
        nn, const = decode_const(ctx, buf[n:])
        n += nn
        consts.append(const)
    if len(buf) - constset_decoder.size - n > 0:
        raise DecodeError("constset is too long")
    return (constset, consts)


def decode_const(ctx, buf):
    const_decoder = ctx.create(ConstFormat)
    const = Const._make(const_decoder.unpack_from(buf, 0))
    n, node_consts = decode_list(ctx, buf[const_decoder.size:], [
        (ConstSetNodeFormat, ConstSetNode),
    ])
    nn, temp_consts = decode_list(ctx, buf[const_decoder.size + n:], [
        (ConstSetTempFormat, ConstSetTemp),
    ])
    return const_decoder.size + n + nn, (const, node_consts, temp_consts)


def encode_const(ctx, const):
    return ctx.create(ConstFormat).pack(*const[0]) \
           + encode_list(ctx, [ConstSetNodeFormat], const[1]) \
           + encode_list(ctx, [ConstSetTempFormat], const[2])


def encode_constset(ctx, constset):
    return ctx.create(ConstSetFormat).pack(*constset[0]) + b''.join([encode_const(ctx, c) for c in constset[1]])


#
# 節点拘束
#
ConstNodeId = 211
ConstNodeFormat = 'i16s'
ConstNode = namedtuple('ConstNode', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # 節点拘束定義数
])
# 節点拘束定義本体
ConstNodeDefFormat = 'i256siiiiiiiffffff'
ConstNodeDef = namedtuple('ConstNodeDef', [
    # 節点拘束ID
    'id',

    # 名称
    'label',

    # 局所座標系ID
    'lcoord_id',

    # 拘束X
    'fixed_x',

    # 拘束Y
    'fixed_y',

    # 拘束Z
    'fixed_z',

    # 拘束RX
    'fixed_rx',

    # 拘束RY
    'fixed_ry',

    # 拘束RZ
    'fixed_rz',

    # 強制変位量X
    'constdisp_x',

    # 強制変位量Y
    'constdisp_y',

    # 強制変位量Z
    'constdisp_z',

    # 強制変位量RX
    'constdisp_rx',

    # 強制変位量RY
    'constdisp_ry',

    # 強制変位量RZ
    'constdisp_rz',

    # 節点数
])
# 含まれる節点
ConstNodeNodeFormat = 'i'
ConstNodeNode = namedtuple('ConstNodeNode', [
    # 節点ID
    'id',
])


def decode_constnode(ctx, buf):
    constnode_decoder = ctx.create(ConstNodeFormat)
    constnode = ConstNode._make(constnode_decoder.unpack_from(buf, 0))
    n, constnodedefs = decode_list(ctx, buf[constnode_decoder.size:], [
        (ConstNodeDefFormat, ConstNodeDef),
        (ConstNodeNodeFormat, ConstNodeNode),
    ])
    if len(buf) - constnode_decoder.size - n > 0:
        raise DecodeError("constnode is too long")
    return (constnode, constnodedefs)


def encode_constnode(ctx, constnode):
    return ctx.create(ConstNodeFormat).pack(*constnode[0]) \
           + encode_list(ctx, [ConstNodeFormat, ConstNodeNodeFormat], constnode[1])


if __name__ == '__main__':
    f = open("./tmp/test.vfe", "rb")
    byteorder, header, version = decode_header(f)
    ctx = Context(byteorder, header.size_of_int, header.size_of_real)

    print('byteorder', byteorder)
    print('header', header)
    print('version', version)

    buf = ctx.next_record(f)
    while buf is not None:
        recid = decode_recid(ctx, ctx.unwrap_record(buf))
        if recid == TitleId:
            title = decode_title(ctx, ctx.unwrap_record(buf))
            print('title', title)
        elif recid == ParamId:
            param = decode_param(ctx, ctx.unwrap_record(buf))
            print('param', param)
        elif recid == SubcaseId:
            subcase = decode_subcase(ctx, ctx.unwrap_record(buf))
            # print('subcase', subcase)
            print('succase count', len(subcase[1]))
        elif recid == 22:
            print("skip OUTPUT")
        elif recid == 23:
            print("skip COORD")
        elif recid == 24:
            print("skip MATERIAL")
        elif recid == 25:
            print("skip MODELNUM")
        elif recid == 26:
            print("skip FUNCTION")
        elif recid == 101:
            print("skip MODELPRP")
        elif recid == 102:
            print("skip PROP")
        elif recid == ElementId:
            element = decode_element(ctx, ctx.unwrap_record(buf))
            # print('element', element)
            print("element count", len(element[1]))
        elif recid == 121:
            print("skip MASS")
        elif recid == 122:
            print("skip RIGID")
        elif recid == 123:
            print("skip SPRING")
        elif recid == ConstSetId:
            constset = decode_constset(ctx, ctx.unwrap_record(buf))
            print('constset', constset)
        elif recid == ConstNodeId:
            constnode = decode_constnode(ctx, ctx.unwrap_record(buf))
            (_constnode, constnodedefs) = constnode
            print('constnode', _constnode)
            print('len constnodedefs', len(constnodedefs))
            for nodedef in constnodedefs:
                _nodedef, nodes = nodedef
                print('nodedef', _nodedef)
                print('len nodes', len(nodes))
        elif recid == 221:
            print("skip TEMPC")
        elif recid == 231:
            print("skip FXHED")
        elif recid == 301:
            print("skip LOADSET")
        elif recid == 311:
            print("skip FORCE")
        elif recid == 312:
            print("skip PRESS")
        elif recid == 313:
            print("skip TEMP")
        elif recid == 314:
            print("skip BODYF")
        elif recid == 321:
            print("skip HFLUX")
        elif recid == 322:
            print("skip HFLUXC")
        elif recid == 323:
            print("skip CONV")
        elif recid == 324:
            print("skip QVOL")
        elif recid == 315:
            print("skip FACE_VOXEL")
        elif recid == 316:
            print("skip CUR_DENSITY")
        elif recid == 401:
            print("skip NDRESVAL")
        elif recid == 501:
            print("skip SIMPLE_VOXEL")
        elif recid == 502:
            print("skip RESULT_AREA")
        elif recid == 30001:
            print("skip SIMIZU")
        elif recid == 1101:
            print("skip S_MODELPRP")
        elif recid == 1102:
            print("skip S_PROP")
        elif recid == 1110:
            print("skip S_VERTEX")
        elif recid == 1111:
            print("skip S_FACET")
        elif recid == 1201:
            print("skip S_CONSTSET")
        elif recid == 1211:
            print("skip S_CONST")
        elif recid == 1221:
            print("skip S_TEMPC")
        elif recid == 1301:
            print("skip S_LOADSET")
        elif recid == 1312:
            print("skip S_PRESS")
        elif recid == 1313:
            print("skip S_TEMP")
        elif recid == 1314:
            print("skip S_BODYF")
        elif recid == 1321:
            print("skip S_HFLUX")
        elif recid == 1323:
            print("skip S_CONV")
        elif recid == 1324:
            print("skip S_QVOL")
        elif recid == 1315:
            print("skip S_FACE_VOXEL")
        else:
            print("unknown recid :", recid)
        buf = ctx.next_record(f)

    f.close()
    print('decode done')
