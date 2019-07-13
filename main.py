import struct
from collections import namedtuple


class DecodeError(Exception):
    pass


class Decoder:
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

    def next_block(self, f):
        buf = f.read(self.size_of_int)
        if len(buf) == 0:
            return None
        l, = struct.unpack(self.bo + self.i, buf)
        buf = f.read(l)
        ll, = struct.unpack(self.bo + self.i, f.read(self.size_of_int))
        if l != ll:
            raise DecodeError("record length not match", l, ll)
        return buf

    def create(self, fmt):
        fmt = fmt.replace("i", self.i)
        fmt = fmt.replace("f", self.r)
        return struct.Struct(self.bo + fmt)


def decode_list(decoder, buf, formats):
    size_decoder = decoder.create("i")
    n, = size_decoder.unpack_from(buf, 0)
    fmt, model = formats[0]

    i = size_decoder.size
    dec = decoder.create(fmt)
    formats = formats[1:]
    models = []
    for _ in range(n):
        m = model._make(dec.unpack_from(buf, i))
        i += dec.size
        if len(formats) > 0:
            ii, ms2 = decode_list(decoder, buf[i:], formats)
            i += ii
            m = (m, ms2)
        models.append(m)
    return (i, models)


def decode_recid(decoder, buf):
    recid_decoder = decoder.create("i")
    recid, = recid_decoder.unpack_from(buf, 0)
    return recid


# ================================
# ヘッダブロック
# ================================

#
# フォーマット
#
Header = namedtuple('Header', [
    # 整数データ長
    'size_of_int',

    # 実数データ長
    'size_of_real',

    # P版フォーマット
    'is_p',

    # 作成プログラム
    'prog',

    # プログラムバージョン番号
    'version',

    # プログラムリビジョン番号
    'revision',
])

#
# バージョン
#
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
    header = Header._make(struct.unpack(byteorder + "BB?2xB9xii8x", buf))

    # parse version
    l, = struct.unpack(byteorder + "i", f.read(4))
    buf = f.read(l)
    ll, = struct.unpack(byteorder + "i", f.read(4))
    if l != ll:
        raise DecodeError("record length not match", l, ll)
    version = Version._make(struct.unpack(byteorder + "ii", buf))
    return (byteorder, header, version)


# ================================
# サマリーブロック
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


def decode_title(decoder, buf):
    title_decoder = decoder.create(TitleFormat)
    return Title._make(title_decoder.unpack(buf))


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


def decode_param(decoder, buf):
    param_decoder = decoder.create(ParamFormat)
    return Param._make(param_decoder.unpack(buf))


#
# 基本情報
#
BaseinfoId = 31
BaseinfoFormat = 'i16si256s'
Baseinfo = namedtuple('Baseinfo', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # データブロック数
    'num_data_block',

    # femファイル名
    'vfe_filename',
])


def decode_baseinfo(decoder, buf):
    baseinfo_decoder = decoder.create(BaseinfoFormat)
    return Baseinfo._make(baseinfo_decoder.unpack(buf))


#
# 結果サブケース
#
RSCaseId = 32
RSCaseFormat = 'i16sii'
RSCase = namedtuple('RSCase', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # 位相最適化サブケースID
    'topology_id',

    # 均質化材料定数サブケースID
    'material_id',

    # サブケース数
])
# サブケース
RSSubCaseFormat = 'i256s'
RSSubCase = namedtuple('RSSubCase', [
    # サブケースID
    'id',

    # 名称
    'idstr',

    # 固有モード数
])
# 固有モード
RSModeFormat = 'if'
RSMode = namedtuple('RSMode', [
    # 固有モードID
    'id',

    # 固有値
    'value',
])


def decode_rscase(decoder, buf):
    rscase_decoder = decoder.create(RSCaseFormat)
    rscase = RSCase._make(rscase_decoder.unpack_from(buf, 0))
    n, rssubcases = decode_list(decoder, buf[rscase_decoder.size:], [
        (RSSubCaseFormat, RSSubCase),
        (RSModeFormat, RSMode),
    ])
    if len(buf) - rscase_decoder.size - n > 0:
        raise DecodeError("rscase is too long")
    return (rscase, rssubcases)


#
# モデル情報
#
ModelinfId = 33
ModelinfFormat = 'i16s'
Modelinf = namedtuple('Modelinf', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # ボクセルモデル数
    # STLモデル数
])
# ボクセルモデル
VoxcelModelFormat = 'i256sii'
VoxcelModel = namedtuple('VoxcelModel', [
    # ボクセルモデルID
    'id',

    # ボクセルモデル名
    'idstr',

    # 節点数
    'n_node',

    # ボクセル要素数
    'size',
])
# STLモデル
STLModelFormat = 'i256sii'
STLModel = namedtuple('STLModel', [
    # STLモデルID
    'id',

    # STLモデル名
    'idstr',

    # 頂点数
    'n_vertex',

    # パッチ数
    'n_patch',
])


def decode_modelinf(decoder, buf):
    modelinf_decoder = decoder.create(ModelinfFormat)
    modelinf = Modelinf._make(modelinf_decoder.unpack_from(buf, 0))
    i = modelinf_decoder.size
    j, voxcel_models = decode_list(decoder, buf[i:], [
        (VoxcelModelFormat, VoxcelModel),
    ])
    i += j
    j, stl_models = decode_list(decoder, buf[i:], [(STLModelFormat, STLModel)])
    i += j
    if len(buf) - i > 0:
        raise DecodeError("modelinf is too long")
    return (modelinf, voxcel_models, stl_models)


#
# 簡易モデル結果出力
#
SimpleResultId = 34
SimpleResultFormat = 'i16s'
SimpleResult = namedtuple('SimpleResult', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # ボクセルモデル数
])
# ボクセルモデル
SimpleVoxcelModelFormat = 'ifffiiii'
SimpleVoxcelModel = namedtuple('SimpleVoxcelModel', [
    # ボクセルモデルID
    'id',

    # ボクセルサイズX
    'size_x',

    # ボクセルサイズY
    'size_y',

    # ボクセルサイズZ
    'size_z',

    # ボクセル数X
    'n_x',

    # ボクセル数Y
    'n_y',

    # ボクセル数Z
    'n_z',

    # ボクセル要素数
    'voxelem_size',

    # 出力範囲数
])
# 出力範囲
DetailAreaFormat = 'i256siiiiii'
DetailArea = namedtuple('DetailArea', [
    # ID
    'id',

    # 名称
    'idstr',

    # X開始位置
    'start_pos_x',
    # X空間数
    'nvox_x',

    # Y開始位置
    'start_pos_y',

    # Y空間数
    'nvox_y',

    # Z開始位置
    'start_pos_z',

    # Z空間数
    'nvox_z',
])


def decode_simple_result(decoder, buf):
    simple_result_decoder = decoder.create(SimpleResultFormat)
    simple_result = SimpleResult._make(simple_result_decoder.unpack_from(buf, 0))
    i = simple_result_decoder.size
    j, voxcel_models = decode_list(decoder, buf[i:], [
        (SimpleVoxcelModelFormat, SimpleVoxcelModel),
        (DetailAreaFormat, DetailArea),
    ])
    i += j
    if len(buf) - i > 0:
        raise DecodeError("simple_result is too long")
    return (simple_result, voxcel_models)


# ================================
# データブロック
# ================================

#
# データ属性
#
DataPropId = 101
DataPropFormat = 'i16siif256sii'
DataProp = namedtuple('DataProp', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # サブケースID
    'subcase_id',

    # ステップ数
    'i_step',

    # 時刻
    'time',

    # 名称
    'label',

    # 固有モードID
    'mode_id',

    # ボクセル／STLモデルID
    'voxmodel_id',
])


def decode_dataprop(decoder, buf):
    dataprop_decoder = decoder.create(DataPropFormat)
    return DataProp._make(dataprop_decoder.unpack(buf))


#
# データセット
#
OutputFormat = 'i256si'
Output = namedtuple('Output', [
    # タイプ
    'type',

    # タイトル
    'title',

    # 実数データ長
    'size_of_real'

    # 節点数
])
# 値
OutputValueFormat = 'f'
OutputValue = namedtuple('OutputValue', [
    # 値
    'value'
])


def decode_outputs(decoder, buf):
    size_decoder = decoder.create("i")
    output_decoder = decoder.create(OutputFormat)

    n, = size_decoder.unpack_from(buf, 0)
    i = size_decoder.size

    outputs = []
    for _ in range(n):
        output = Output._make(output_decoder.unpack_from(buf, i))
        i += output_decoder.size

        value_decoder = Decoder(decoder.bo, decoder.size_of_int, output.size_of_real).create(OutputValueFormat)
        n2, = size_decoder.unpack_from(buf, i)
        i += size_decoder.size

        values = []
        for _ in range(n2):
            value = OutputValue._make(value_decoder.unpack_from(buf, i))
            i += value_decoder.size
            values.append(value)

        outputs.append((output, values))
    return (i, outputs)


#
# 節点データ
#
NodeValId = 111
NodeValFormat = 'i16s'
NodeVal = namedtuple('NodeVal', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # データセット数
])


def decode_nodalval(decoder, buf):
    nodalval_decoder = decoder.create(NodeValFormat)
    nodalval = NodeVal._make(nodalval_decoder.unpack_from(buf, 0))
    i = nodalval_decoder.size
    j, outputs = decode_outputs(decoder, buf[i:])
    i += j
    if len(buf) - i > 0:
        raise DecodeError("nodalval is too long")
    return (nodalval, outputs)


#
# 要素データ
#
ElemValId = 121
ElemValFormat = 'i16s'
ElemVal = namedtuple('ElemVal', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # データセット数
])


def decode_elemval(decoder, buf):
    elemval_decoder = decoder.create(ElemValFormat)
    elemval = ElemVal._make(elemval_decoder.unpack_from(buf, 0))
    i = elemval_decoder.size
    j, outputs = decode_outputs(decoder, buf[i:])
    i += j
    if len(buf) - i > 0:
        raise DecodeError("elemval is too long")
    return (elemval, outputs)


#
# 最適化履歴
#
OptHistId = 201
OptHistFormat = 'i16s'
OptHist = namedtuple('OptHist', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # ステップ数
])
# ステップ
OptHistValueFormat = 'f'
OptHistValue = namedtuple('OptHistValue', [
    # 目的関数の初期形状比
    'value',
])


def decode_opthist(decoder, buf):
    opthist_decoder = decoder.create(OptHistFormat)
    opthist = OptHist._make(opthist_decoder.unpack_from(buf, 0))
    i = opthist_decoder.size
    j, steps = decode_list(decoder, buf[i:], [
        (OptHistValueFormat, OptHistValue),
    ])
    i += j
    if len(buf) - i > 0:
        raise DecodeError("opthist is too long")
    return (opthist, steps)


#
# TODO: 均質化材料定数
#
HomoMatId = 401

#
# 粗いボクセルモデルの要素データ
#
SimpleEValId = 501
SimpleEValFormat = 'i16s'
SimpleEVal = namedtuple('SimpleEVal', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # データセット数
])


def decode_simpleeval(decoder, buf):
    simpleeval_decoder = decoder.create(SimpleEValFormat)
    eval = SimpleEVal._make(simpleeval_decoder.unpack_from(buf, 0))
    i = simpleeval_decoder.size
    j, outputs = decode_outputs(decoder, buf[i:])
    i += j
    if len(buf) - i > 0:
        raise DecodeError("simpleeval is too long")
    return (eval, outputs)


#
# 詳細解析範囲の節点データ
#
NodeValHeatId = 502
NodeValHeatFormat = 'i16s'
NodeValHeat = namedtuple('NodeValHeat', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # 出力範囲数
])
# 詳細解析範囲ID
AreaIdFormat = 'i'
AreaId = namedtuple('AreaId', [
    # 詳細解析範囲ID
    'id',
])


def decode_nodeval_heat(decoder, buf):
    nodeval_heat_decoder = decoder.create(NodeValHeatFormat)
    nodeval_heat = NodeValHeat._make(nodeval_heat_decoder.unpack_from(buf, 0))
    i = nodeval_heat_decoder.size

    values = []
    if nodeval_heat.id == NodeValHeatId:
        size_decoder = decoder.create("i")
        area_id_decoder = decoder.create(AreaIdFormat)
        n, = size_decoder.unpack_from(buf, i)
        i += size_decoder.size
        for _ in range(n):
            area_id = AreaId._make(area_id_decoder.unpack_from(buf, i))
            i += area_id_decoder.size

            j, outputs = decode_outputs(decoder, buf[i:])
            i += j
            values.append((area_id, outputs))
    else:
        j, outputs = decode_outputs(decoder, buf[i:])
        i += j
        values = outputs

    if len(buf) - i > 0:
        raise DecodeError("nodeval_heat is too long")
    return (nodeval_heat, values)


#
# 詳細解析範囲の要素データ
#
ElemValHeatId = 503
ElemValHeatFormat = 'i16s'
ElemValHeat = namedtuple('ElemValHeat', [
    # レコードID
    'id',

    # 識別子
    'idstr',

    # 出力範囲数
])


def decode_elemval_heat(decoder, buf):
    elemval_heat_decoder = decoder.create(ElemValHeatFormat)
    elemval_heat = ElemValHeat._make(elemval_heat_decoder.unpack_from(buf, 0))
    i = elemval_heat_decoder.size

    values = []
    if elemval_heat.id == ElemValHeatId:
        size_decoder = decoder.create("i")
        area_id_decoder = decoder.create(AreaIdFormat)
        n, = size_decoder.unpack_from(buf, i)
        i += size_decoder.size
        for _ in range(n):
            area_id = AreaId._make(area_id_decoder.unpack_from(buf, i))
            i += area_id_decoder.size

            j, outputs = decode_outputs(decoder, buf[i:])
            i += j
            values.append((area_id, outputs))
    else:
        j, outputs = decode_outputs(decoder, buf[i:])
        i += j
        values = outputs

    if len(buf) - i > 0:
        raise DecodeError("elemval_heat is too long")
    return (elemval_heat, values)


if __name__ == '__main__':
    f = open("./tmp/test.vre", "rb")
    byteorder, header, version = decode_header(f)
    decoder = Decoder(byteorder, header.size_of_int, header.size_of_real)

    buf = decoder.next_block(f)
    title = decode_title(decoder, buf)

    buf = decoder.next_block(f)
    param = decode_param(decoder, buf)

    buf = decoder.next_block(f)
    baseinfo = decode_baseinfo(decoder, buf)

    buf = decoder.next_block(f)
    rscase = decode_rscase(decoder, buf)

    buf = decoder.next_block(f)
    modelinf = decode_modelinf(decoder, buf)

    buf = decoder.next_block(f)
    if decode_recid(decoder, buf) == SimpleResultId:
        simple_result = decode_simple_result(decoder, buf)
        buf = decoder.next_block(f)

    while True:
        if buf is None:
            break
        dataprop = decode_dataprop(decoder, buf)

        buf = decoder.next_block(f)
        if decode_recid(decoder, buf) == NodeValId:
            nodalval = decode_nodalval(decoder, buf)

            buf = decoder.next_block(f)
            elemval = decode_elemval(decoder, buf)
            buf = decoder.next_block(f)
        elif decode_recid(decoder, buf) == SimpleEValId:
            simple_eval = decode_simpleeval(decoder, buf)

            buf = decoder.next_block(f)
            if decode_recid(decoder, buf) == SimpleEValId:
                nodeval_heat = decode_nodeval_heat(decoder, buf)

                buf = decoder.next_block(f)
                elemval_heat = decode_elemval_heat(decoder, buf)
                buf = decoder.next_block(f)

    f.close()
