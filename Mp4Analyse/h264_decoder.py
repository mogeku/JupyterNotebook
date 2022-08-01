import os
import math
import enum
from construct import *
from bitstream import BitStream
from numpy import uint8

class SE_TYPE(enum.Enum):
    MB_TYPE = enum.auto()

class Cabac:
    def __init__(self, slice, se_type:SE_TYPE, stream):
        self.slice = slice
        self.se_type = se_type
        self.stream = stream


    # 9.3.3.2 Arithmetic decoding process
    def DecodeBin(self, bypassFlag, ctxIdx):
        pass

    def get_m_n(self, ctxIdx):
        pass

    # 9.3.3.1.1.3 Derivation process of ctxIdxInc for the syntax element mb_type
    def Derivation_process_of_ctxIdxInc_for_the_syntax_element_mb_type(self, ctxIdxOffset):
        pass

    def Decode_mb_type_I_slice(self):
        # Table 9-34 – Syntax elements and associated types of binarization, maxBinIdxCtx, and ctxIdxOffset
        maxBinIdxCtx = 6
        ctxIdxOffset = 3
        bypassFlag = 0

        # 参考 Table 9-39, 处理每一位的 binIdx

        # 获取 binIdx = 0 的 binVal
        ctxIdxInc = self.Derivation_process_of_ctxIdxInc_for_the_syntax_element_mb_type(ctxIdxOffset)
        # 9.3.3.1 Derivation process for ctxIdx
        ctxIdx = ctxIdxOffset + ctxIdxInc
        binVal = self.DecodeBin(bypassFlag, ctxIdx)

        # Table 9-36 – Binarization for macroblock types in I slices
        if binVal == 0: # b(0)
            return MB_TYPE_I.I_NxN  # Bin string: 0


    def Decode_mb_type(self):
        if self.slice.slice_type % 5 == SLICE_TYPE.I:
            return self.Decode_mb_type_I_slice()


    # 9.3.1.2 Initialization process for the arithmetic decoding engine
    def Initialization_process_for_the_arithmetic_decoding_engine(self):
        pass

    # 9.3.1.1 Initialization process for context variables
    def Initialization_process_for_context_variables(self):
        pass

    # 9.3 CABAC parsing process for slice data
    def CABAC_parsing_process_for_slice_data(self):
        if self.se_type == SE_TYPE.MB_TYPE:
            return self.Decode_mb_type()

class MyBitStream(BitStream):
    def __init__(self, data: bytes, bit_len):
        super().__init__(data)
        self.bit_len = bit_len
        self._readed_bit = 0

    def byte_aligned(self):
        return self._readed_bit % 8 == 0

    def more_data(self):
        return self._readed_bit < self.bit_len

    def next_bits(self, n):
        state = self.save()
        ret = 0
        while n > 0:
            ret = ret << 1
            ret |= self.read(bool)
            n -= 1
        self.restore(state)
        return ret

    def read_bit(self):
        if not self.more_data():
            return None

        self._readed_bit += 1
        return int(self.read(bool))

    def read_nbit(self, n):
        ret = 0
        while n > 0:
            ret = ret << 1
            ret |= self.read_bit()
            n -= 1
        return ret

    def read_ue(self):
        n = 0
        while True:
            bit = self.read_bit()
            if bit == None:
                return None

            if bit == 0:
                n += 1
            else:
                break

        return self.read_nbit(n) + (1 << n) - 1

    def read_se(self):
        ue = self.read_ue()
        if ue == None:
            return None

        ue += 1
        if ue & 1:
            return -(ue >> 1)
        else:
            return ue >> 1

    def read_ae(self, slice, se_type):
        cabac = Cabac(slice, se_type, self)
        return cabac.CABAC_parsing_process_for_slice_data()

    def read_me(self):
        # TODO: read_me
        pass

    def read_te(self):
        # TODO: read_te
        pass


class NALU_Payload:
    def __init__(self, nal_header, data, bit_len, type_name):
        self.stream = MyBitStream(data, bit_len)
        self.type = type_name
        self.nal_unit_type = nal_header.nal_unit_type
        self.nal_ref_idc = nal_header.nal_ref_idc

    def __str__(self):
        ret = f"{self.type} info:\n"
        skip_list = ["stream", "sps_list", "pps_list", "pps", "sps"]
        for key, value in self.__dict__.items():
            if key in skip_list:
                continue
            ret += f"\t{key} = {value}\n"
        return ret

    def more_rbsp_data(self):
        return self.stream.more_data()

    def scaling_list(self):
        # TODO: scaling_list
        pass

    def ref_pic_list_mvc_modification(self):
        # TODO: ref_pic_list_modification
        pass

    def ref_pic_list_modification(self):
        # TODO: ref_pic_list_modification
        pass

    def pred_weight_table(self):
        # TODO: pred_weight_table
        pass

    def vui_parameters(self):
        # TODO: vui_parameters
        pass

    def dec_ref_pic_marking(self):
        if self.IdrPicFlag:
            self.no_output_of_prior_pics_flag = self.stream.read_bit()
            self.long_term_reference_flag = self.stream.read_bit()
        else:
            self.adaptive_ref_pic_marking_mode_flag = self.stream.read_bit()
            if self.adaptive_ref_pic_marking_mode_flag:
                while True:
                    self.memory_management_control_operation = self.stream.read_ue()
                    if self.memory_management_control_operation in [1, 3]:
                        self.difference_of_pic_nums_minus1 = self.stream.read_ue()
                    if self.memory_management_control_operation == 2:
                        self.long_term_pic_num = self.stream.read_ue()
                    if self.memory_management_control_operation in [3, 6]:
                        self.long_term_frame_idx = self.stream.read_ue()
                    if self.memory_management_control_control == 4:
                        self.max_long_term_frame_idx_plus1 = self.stream.read_ue()
                    if self.memory_management_control_operation == 0:
                        break


class SPS(NALU_Payload):
    def __init__(self, nal_header, data, bit_len):
        super().__init__(nal_header, data, bit_len, "Sequence parameter set")

        # 参考下面 itu 标准中的 7.3.2.1.1  Sequence parameter set data syntax 进行解析
        # https://www.itu.int/rec/dologin_pub.asp?lang=e&id=T-REC-H.264-201304-S!!PDF-E&type=items
        self.profile_idc = self.stream.read(uint8)
        self.constraint_set0_flag = self.stream.read_bit()
        self.constraint_set1_flag = self.stream.read_bit()
        self.constraint_set2_flag = self.stream.read_bit()
        self.constraint_set3_flag = self.stream.read_bit()
        self.constraint_set4_flag = self.stream.read_bit()
        self.constraint_set5_flag = self.stream.read_bit()
        self.reserved_zero_2bits = self.stream.read_nbit(2)
        self.level_idc = self.stream.read(uint8)
        self.seq_parameter_set_id = self.stream.read_ue()

        if self.profile_idc in [100, 110, 122, 244, 44, 83, 86, 118, 128, 138]:
            # 0: 单色, 1: YUV 4:2:0, 2: YUV 4:2:2, 3: YUV 4:4:4 (默认值为 1)
            self.chroma_format_idc = self.stream.read_ue()
            self.separate_colour_plane_flag = 0
            if self.chroma_format_idc == 3:
                # 是否将 UV 分量独立出来, 变成 YYY UUU VVV 的存储方式
                self.separate_colour_plane_flag = self.stream.read_bit()
            self.bit_depth_luma_minus8 = self.stream.read_ue()
            self.bit_depth_chroma_minus8 = self.stream.read_ue()
            self.qpprime_y_zero_transform_bypass_flag = self.stream.read_bit()
            self.seq_scaling_matrix_present_flag = self.stream.read_bit()

            if self.seq_scaling_matrix_present_flag:
                self.seq_scaling_list_present_flag = []
                for i in range(8 if self.chroma_format_idc != 3 else 12):
                    self.seq_scaling_list_present_flag.append(self.stream.read_bit())
                    if self.seq_scaling_list_present_flag[i]:
                        if i < 6:
                            pass  # TODO: scaling_list( ScalingList4x4[ i ], 16, UseDefaultScalingMatrix4x4Flag[ i ] )
                        else:
                            pass  # TODO: scaling_list( ScalingList8x8[ i − 6 ], 64, UseDefaultScalingMatrix8x8Flag[ i − 6 ] )
            self.log2_max_frame_num_minus4 = self.stream.read_ue()
            self.pic_order_cnt_type = self.stream.read_ue()
            if self.pic_order_cnt_type == 0:
                self.log2_max_pic_order_cnt_lsb_minus4 = self.stream.read_ue()
            elif self.pic_order_cnt_type == 1:
                self.delta_pic_order_always_zero_flag = self.stream.read_bit()
                self.offset_for_non_ref_pic = self.stream.read_se()
                self.offset_for_top_to_bottom_field = self.stream.read_se()
                self.num_ref_frames_in_pic_order_cnt_cycle = self.stream.read_ue()
                self.offset_for_ref_frame = []
                for i in range(self.num_ref_frames_in_pic_order_cnt_cycle):
                    self.offset_for_ref_frame.append(self.stream.read_se())
            self.max_num_ref_frames = self.stream.read_ue()
            self.gaps_in_frame_num_value_allowed_flag = self.stream.read_bit()
            # 横向宏块个数 - 1
            self.pic_width_in_mbs_minus1 = self.stream.read_ue()
            # 纵向宏块个数 - 1
            self.pic_height_in_map_units_minus1 = self.stream.read_ue()
            # 1为帧编码
            self.frame_mbs_only_flag = self.stream.read_bit()
            self.mb_adaptive_frame_field_flag = 0
            if not self.frame_mbs_only_flag:
                # 1为帧场自适应编码, 0为场编码
                self.mb_adaptive_frame_field_flag = self.stream.read_bit()
            self.direct_8x8_inference_flag = self.stream.read_bit()
            # 图像宽高是否有裁剪
            self.frame_cropping_flag = self.stream.read_bit()
            if self.frame_cropping_flag:
                self.frame_crop_left_offset = self.stream.read_ue()
                self.frame_crop_right_offset = self.stream.read_ue()
                self.frame_crop_top_offset = self.stream.read_ue()
                self.frame_crop_bottom_offset = self.stream.read_ue()
            self.vui_parameters_present_flag = self.stream.read_bit()
            if self.vui_parameters_present_flag:
                self.vui_parameters()

        # 通过上面读取的参数推导出下面的参数

        # 像素编码的格式, 0: 单色或 YUV444 分离模式, 1: YUV420, 2: YUV422, 3: YUV444
        if self.chroma_format_idc == 3:
            self.ChromaArrayType = 3 if self.separate_colour_plane_flag == 0 else 0
        else:
            self.ChromaArrayType = self.chroma_format_idc

        # SubWidthC 和 SubHeightC 代表 YUV 分量中, Y 分量和 UV(Chroma) 分量在水平和竖直方向上的比值
        if self.ChromaArrayType == 1:  # YUV420
            self.SubWidthC = 2
            self.SubHeightC = 2
        elif self.ChromaArrayType == 2:  # YUV422
            self.SubWidthC = 2
            self.SubHeightC = 1
        elif self.ChromaArrayType == 3:  # YUV444
            self.SubWidthC = 1
            self.SubHeightC = 1
        else:  # 单色或 YUV444 分离模式
            pass

        # 指定一个宏块(Macroblock) UV(Chroma) 分量的宽高
        if self.ChromaArrayType != 0:
            self.MbWidthC = 16 / self.SubWidthC
            self.MbHeightC = 16 / self.SubHeightC
        else:  # 单色或 YUV444 分离模式
            self.MbWidthC = 0
            self.MbHeightC = 0

        # 计算实际的宽高
        self.width = (self.pic_width_in_mbs_minus1 + 1) * 16
        # 2 - frame_mbs_only_flag 表示若为场编码, 则高度需要 * 2
        self.height = (
            (2 - self.frame_mbs_only_flag)
            * (self.pic_height_in_map_units_minus1 + 1)
            * 16
        )
        # 宽高是否正好为 16 的倍数
        if self.frame_cropping_flag:
            crop_unit_x = 0
            crop_unit_y = 0
            if self.ChromaArrayType == 0:
                crop_unit_x = 1
                crop_unit_y = 2 - self.frame_mbs_only_flag
            elif self.ChromaArrayType in [1, 2, 3]:
                crop_unit_x = self.SubWidthC
                crop_unit_y = self.SubHeightC * (2 - self.frame_mbs_only_flag)

            self.width -= crop_unit_x * (
                self.frame_crop_left_offset + self.frame_crop_right_offset
            )
            self.height -= crop_unit_y * (
                self.frame_crop_top_offset + self.frame_crop_bottom_offset
            )

        self.BitDepth_y = 8 + self.bit_depth_luma_minus8
        self.BitDepth_c = 8 + self.bit_depth_chroma_minus8


class PPS(NALU_Payload):
    def __init__(self, nal_header, data, bit_len, sps_list):
        super().__init__(nal_header, data, bit_len, "Picture parameter set")

        self.pic_parameter_set_id = self.stream.read_ue()
        self.seq_parameter_set_id = self.stream.read_ue()
        self.entropy_coding_mode_flag = self.stream.read_bit()
        self.bottom_field_pic_order_in_frame_present_flag = self.stream.read_bit()
        self.num_slice_groups_minus1 = self.stream.read_ue()
        if self.num_slice_groups_minus1 > 0:
            self.slice_group_map_type = self.stream.read_ue()
            if self.slice_group_map_type == 0:
                self.run_length_minus1 = []
                for iGroup in range(self.num_slice_groups_minus1):
                    self.run_length_minus1.append(self.stream.read_ue())
            elif self.slice_group_map_type == 2:
                self.top_left = []
                self.bottom_right = []
                for iGroup in range(self.num_slice_groups_minus1):
                    self.top_left.append(self.stream.read_ue())
                    self.bottom_right.append(self.stream.read_ue())
            elif self.slice_group_map_type in [3, 4, 5]:
                self.slice_group_change_direction_flag = self.stream.read_bit()
                self.slice_group_change_rate_minus1 = self.stream.read_ue()
                self.SliceGroupChangeRate = self.slice_group_change_rate_minus1 + 1
            elif self.slice_group_map_type == 6:
                self.pic_size_in_map_units_minus1 = self.stream.read_ue()
                self.PicSizeInMapUnits = self.pic_size_in_map_units_minus1 + 1
                self.slice_group_id = []
                for i in range(self.num_slice_groups_minus1):
                    self.slice_group_id.append(
                        self.stream.read_nbit(
                            math.ceil(math.log2(self.num_slice_groups_minus1))
                        )
                    )
        self.num_ref_idx_l0_default_active_minus1 = self.stream.read_ue()
        self.num_ref_idx_l1_default_active_minus1 = self.stream.read_ue()
        self.weighted_pred_flag = self.stream.read_bit()
        self.weighted_bipred_idc = self.stream.read_nbit(2)
        self.pic_init_qp_minus26 = self.stream.read_se()
        self.pic_init_qs_minus26 = self.stream.read_se()
        self.chroma_qp_index_offset = self.stream.read_se()
        self.deblocking_filter_control_present_flag = self.stream.read_bit()
        self.constrained_intra_pred_flag = self.stream.read_bit()
        self.redundant_pic_cnt_present_flag = self.stream.read_bit()
        if self.more_rbsp_data():
            self.transform_8x8_mode_flag = self.stream.read_bit()
            self.pic_scaling_matrix_present_flag = self.stream.read_bit()
            if self.pic_scaling_matrix_present_flag:
                self.pic_scaling_list_present_flag = []
                for i in range(
                    6
                    + (
                        2
                        if sps_list[self.seq_parameter_set_id].chroma_format_idc != 3
                        else 6
                    )
                    * self.transform_8x8_mode_flag
                ):
                    self.pic_scaling_list_present_flag.append(self.stream.read_bit())
                    if self.pic_scaling_list_present_flag[i]:
                        if i < 6:
                            self.scaling_list()
                        else:
                            self.scaling_list()
            self.second_chroma_qp_index_offset = self.stream.read_se()


class SEI(NALU_Payload):
    def __init__(self, nal_header, data, bit_len):
        super().__init__(
            nal_header, data, bit_len, "Supplemental enhancement information"
        )

        while True:
            self.sei_message()
            if not self.more_rbsp_data():
                break

    def sei_message(self):
        self.stream.read_bit()
        # TODO: sei_message
        pass


class AUD(NALU_Payload):
    def __init__(self, nal_header, data, bit_len):
        super().__init__(nal_header, data, bit_len, "Access unit delimiter")

        # 指定 slice_type 可能的值
        # 参考 itu 标准中的 Table 7-5 - Meaning of primary_pic_type
        self.primary_pic_type = self.stream.read_nbit(3)


class EndOfSeq(NALU_Payload):
    def __init__(self, nal_header, data, bit_len):
        super().__init__(nal_header, data, bit_len, "End of sequence")


class EndOfStream(NALU_Payload):
    def __init__(self, nal_header, data, bit_len):
        super().__init__(nal_header, data, bit_len, "End of stream")


class FillerData(NALU_Payload):
    def __init__(self, nal_header, data, bit_len):
        super().__init__(nal_header, data, bit_len, "Filler data")

        self.ff_byte = b""
        while self.stream.next_bits(8) == 0xFF:
            self.ff_byte += self.stream.read_nbit(8).to_bytes(1, "big")


class MB_TYPE_I(enum.IntEnum):
    I_NxN = 0
    I_16x16_0_0_0 = 1
    I_16x16_1_0_0 = 2
    I_16x16_2_0_0 = 3
    I_16x16_3_0_0 = 4
    I_16x16_0_1_0 = 5
    I_16x16_1_1_0 = 6
    I_16x16_2_1_0 = 7
    I_16x16_3_1_0 = 8
    I_16x16_0_2_0 = 9
    I_16x16_1_2_0 = 10
    I_16x16_2_2_0 = 11
    I_16x16_3_2_0 = 12
    I_16x16_0_0_1 = 13
    I_16x16_1_0_1 = 14
    I_16x16_2_0_1 = 15
    I_16x16_3_0_1 = 16
    I_16x16_0_1_1 = 17
    I_16x16_1_1_1 = 18
    I_16x16_2_1_1 = 19
    I_16x16_3_1_1 = 20
    I_16x16_0_2_1 = 21
    I_16x16_1_2_1 = 22
    I_16x16_2_2_1 = 23
    I_16x16_3_2_1 = 24
    I_PCM = 25


class MB_TYPE_B(enum.IntEnum):
    B_Direct_16x16 = 0
    B_L0_16x16 = 1
    B_L1_16x16 = 2
    B_Bi_16x16 = 3
    B_L0_L0_16x8 = 4
    B_L0_L0_8x16 = 5
    B_L1_L1_16x8 = 6
    B_L1_L1_8x16 = 7
    B_L0_L1_16x8 = 8
    B_L0_L1_8x16 = 9
    B_L1_L0_16x8 = 10
    B_L1_L0_8x16 = 11
    B_L0_Bi_16x8 = 12
    B_L0_Bi_8x16 = 13
    B_L1_Bi_16x8 = 14
    B_L1_Bi_8x16 = 15
    B_Bi_L0_16x8 = 16
    B_Bi_L0_8x16 = 17
    B_Bi_L1_16x8 = 18
    B_Bi_L1_8x16 = 19
    B_Bi_Bi_16x8 = 20
    B_Bi_Bi_8x16 = 21
    B_8x8 = 22
    B_Skip = -1


class MB_TYPE_P_SP(enum.IntEnum):
    P_L0_16x16 = 0
    P_L0_L0_16x8 = 1
    P_L0_L0_8x16 = 2
    P_8x8 = 3
    P_8x8ref0 = 4
    P_Skip = -1


class MB_TYPE_SI(enum.IntEnum):
    SI = 0


class MB_PART_PRED_MODE(enum.IntEnum):
    Intra_4x4 = 0
    Intra_8x8 = 1
    Intra_16x16 = 2
    Pred_L0 = 3
    Pred_L1 = 4
    BiPred = 5
    Direct = 6


class SLICE_TYPE(enum.IntEnum):
    P = 0
    B = 1
    I = 2
    SP = 3
    SI = 4


class Slice(NALU_Payload):
    def __init__(self, nal_header, data, bit_len, type_name, sps_list, pps_list):
        super().__init__(nal_header, data, bit_len, type_name)
        self.sps_list = sps_list
        self.pps_list = pps_list
        self.IdrPicFlag = self.nal_unit_type == 5

    def slice_header(self):
        self.first_mb_in_slice = self.stream.read_ue()
        self.slice_type = self.stream.read_ue()
        self.pic_parameter_set_id = self.stream.read_ue()
        self.pps: PPS = self.pps_list[self.pic_parameter_set_id]
        self.sps: SPS = self.sps_list[self.pps.seq_parameter_set_id]
        if self.sps.separate_colour_plane_flag == 1:
            self.colour_plane_id = self.stream.read_nbit(2)
        self.frame_num = self.stream.read_nbit(self.sps.log2_max_frame_num_minus4 + 4)
        # 判断是否为场编码
        if not self.sps.frame_mbs_only_flag:
            self.field_pic_flag = self.stream.read_bit()
            if self.field_pic_flag:
                # 判断是底场还是顶场
                self.bottom_field_flag = self.stream.read_bit()
        if self.IdrPicFlag:
            self.idr_pic_id = self.stream.read_ue()
        if self.sps.pic_order_cnt_type == 0:
            self.pic_order_cnt_lsb = self.stream.read_nbit(
                self.sps.log2_max_pic_order_cnt_lsb_minus4 + 4
            )
            if (
                self.pps.bottom_field_pic_order_in_frame_present_flag
                and not self.field_pic_flag
            ):
                self.delta_pic_order_cnt_bottom = self.stream.read_se()

        self.delta_pic_order_cnt = []
        if (
            self.sps.pic_order_cnt_type == 1
            and not self.sps.delta_pic_order_always_zero_flag
        ):
            self.delta_pic_order_cnt.append(self.stream.read_se())
            if (
                self.pps.bottom_field_pic_order_in_frame_present_flag
                and not self.field_pic_flag
            ):
                self.delta_pic_order_cnt.append(self.stream.read_se())
        if self.pps.redundant_pic_cnt_present_flag:
            self.redundant_pic_cnt = self.stream.read_ue()
        if self.slice_type % 5 == SLICE_TYPE.B:  # B帧
            self.direct_spatial_mv_pred_flag = self.stream.read_bit()
        if self.slice_type % 5 in [
            SLICE_TYPE.P,
            SLICE_TYPE.SP,
            SLICE_TYPE.B,
        ]:  # P帧, SP帧, B帧
            self.num_ref_idx_active_override_flag = self.stream.read_bit()
            if self.num_ref_idx_active_override_flag:
                self.num_ref_idx_l0_active_minus1 = self.stream.read_ue()
                if self.slice_type % 5 == SLICE_TYPE.B:  # B帧
                    self.num_ref_idx_l1_active_minus1 = self.stream.read_ue()
        if self.nal_unit_type in [20, 21]:
            self.ref_pic_list_mvc_modification()  # specified in AnnexH
        else:
            self.ref_pic_list_modification()
        if self.pps.weighted_pred_flag and (
            self.slice_type % 5 in [SLICE_TYPE.P, SLICE_TYPE.SP]
            or self.pps.weighted_bipred_idc == 1
            and self.slice_type % 5 == SLICE_TYPE.B
        ):
            self.pred_weight_table()
        if self.nal_ref_idc != 0:
            self.dec_ref_pic_marking()
        if self.pps.entropy_coding_mode_flag and self.slice_type % 5 not in [
            SLICE_TYPE.I,  # I
            SLICE_TYPE.SI,  # SI
        ]:
            self.cabac_init_idc = self.stream.read_ue()
        self.slice_qp_delta = self.stream.read_se()
        if self.slice_type % 5 in [SLICE_TYPE.SP, SLICE_TYPE.SI]:  # SP, SI
            if self.slice_type % 5 == SLICE_TYPE.SP:  # SP
                self.sp_for_switch_flag = self.stream.read_bit()
            self.slice_qs_delta = self.stream.read_se()
        if self.pps.deblocking_filter_control_present_flag:
            self.disable_deblocking_filter_idc = self.stream.read_ue()
            if self.disable_deblocking_filter_idc != 1:
                self.slice_alpha_c0_offset_div2 = self.stream.read_se()
                self.slice_beta_offset_div2 = self.stream.read_se()
        if (
            self.pps.num_slice_groups_minus1 > 0
            and self.pps.slice_group_map_type in range(3, 6)
        ):
            self.slice_group_change_cycle = self.stream.read_nbit(
                math.ceil(
                    math.log2(
                        self.pps.PicSizeInMapUnits / self.pps.SliceGroupChangeRate + 1
                    )
                )
            )

    def NextMbAddress(self, CurrMbAddr):
        # TODO: NextMbAddress
        pass

    def MbPartPredMode(self, mb_type, zero_or_one):
        if self.slice_type % 5 == SLICE_TYPE.I:
            if mb_type == MB_TYPE_I.I_NxN:
                if self.pps.transform_8x8_mode_flag == 0:
                    return MB_PART_PRED_MODE.Intra_4x4
                elif self.pps.transform_8x8_mode_flag == 1:
                    return MB_PART_PRED_MODE.Intra_8x8
            elif mb_type == MB_TYPE_I.I_PCM:
                return None
            else:
                return MB_PART_PRED_MODE.Intra_16x16

        elif self.slice_type % 5 in [SLICE_TYPE.P, SLICE_TYPE.SP]:
            if zero_or_one == 0:
                if mb_type in [
                    MB_TYPE_P_SP.P_L0_16x16,
                    MB_TYPE_P_SP.P_L0_L0_16x8,
                    MB_TYPE_P_SP.P_L0_L0_8x16,
                    MB_TYPE_P_SP.P_Skip,
                ]:
                    return MB_PART_PRED_MODE.Pred_L0
                else:
                    return None
            elif zero_or_one == 1:
                if mb_type in [MB_TYPE_P_SP.P_L0_L0_16x8, MB_TYPE_P_SP.P_L0_L0_8x16]:
                    return MB_PART_PRED_MODE.Pred_L0
                else:
                    return None

        elif self.slice_type % 5 == SLICE_TYPE.B:
            if zero_or_one == 0:
                if mb_type in [MB_TYPE_B.B_Direct_16x16, MB_TYPE_B.B_Skip]:
                    return MB_PART_PRED_MODE.Direct
                elif mb_type in [
                    MB_TYPE_B.B_L0_16x16,
                    MB_TYPE_B.B_L0_L0_16x8,
                    MB_TYPE_B.B_L0_L0_8x16,
                    MB_TYPE_B.B_L0_L1_16x8,
                    MB_TYPE_B.B_L0_L1_8x16,
                    MB_TYPE_B.B_L0_Bi_16x8,
                    MB_TYPE_B.B_L0_Bi_8x16,
                ]:
                    return MB_PART_PRED_MODE.Pred_L0
                elif mb_type in [
                    MB_TYPE_B.B_L1_16x16,
                    MB_TYPE_B.B_L1_L1_16x8,
                    MB_TYPE_B.B_L1_L1_8x16,
                    MB_TYPE_B.B_L1_L0_16x8,
                    MB_TYPE_B.B_L1_L0_8x16,
                    MB_TYPE_B.B_L1_Bi_16x8,
                    MB_TYPE_B.B_L1_Bi_8x16,
                ]:
                    return MB_PART_PRED_MODE.Pred_L1
                elif mb_type == MB_TYPE_B.B_8x8:
                    return None
                else:
                    return MB_PART_PRED_MODE.BiPred
            if zero_or_one == 1:
                if mb_type in [
                    MB_TYPE_B.B_Direct_16x16,
                    MB_TYPE_B.B_L0_16x16,
                    MB_TYPE_B.B_L1_16x16,
                    MB_TYPE_B.B_Bi_16x16,
                    MB_TYPE_B.B_8x8,
                    MB_TYPE_B.B_Skip,
                ]:
                    return None
                elif mb_type in [
                    MB_TYPE_B.B_L0_L0_16x8,
                    MB_TYPE_B.B_L0_L0_8x16,
                    MB_TYPE_B.B_L1_L0_16x8,
                    MB_TYPE_B.B_L1_L0_8x16,
                    MB_TYPE_B.B_Bi_L0_16x8,
                    MB_TYPE_B.B_Bi_L0_8x16,
                    MB_TYPE_B.B_L1_Bi_8x16,
                ]:
                    return MB_PART_PRED_MODE.Pred_L0
                elif mb_type in [
                    MB_TYPE_B.B_L1_L1_16x8,
                    MB_TYPE_B.B_L1_L1_8x16,
                    MB_TYPE_B.B_L0_L1_16x8,
                    MB_TYPE_B.B_L0_L1_8x16,
                    MB_TYPE_B.B_Bi_L1_16x8,
                    MB_TYPE_B.B_Bi_L1_8x16,
                ]:
                    return MB_PART_PRED_MODE.Pred_L1
                else:
                    return MB_PART_PRED_MODE.BiPred

        if self.slice_type % 5 == SLICE_TYPE.SI:
            if mb_type == MB_TYPE_SI.SI:
                return MB_PART_PRED_MODE.Intra_4x4

    def NumMbPart(self, mb_type):
        if self.slice_type % 5 in [SLICE_TYPE.P, SLICE_TYPE.SP]:
            if mb_type in [MB_TYPE_P_SP.P_L0_16x16, MB_TYPE_P_SP.P_Skip]:
                return 1
            elif mb_type in [MB_TYPE_P_SP.P_L0_L0_16x8, MB_TYPE_P_SP.P_L0_16x16]:
                return 2
            else:
                return 4

        if self.slice_type % 5 in [SLICE_TYPE.B]:
            if mb_type in [MB_TYPE_B.B_Direct_16x16, MB_TYPE_B.B_Skip]:
                return None
            elif mb_type in [
                MB_TYPE_B.B_L0_16x16,
                MB_TYPE_B.B_L1_16x16,
                MB_TYPE_B.B_Bi_16x16,
            ]:
                return 1
            elif mb_type in [MB_TYPE_B.B_8x8]:
                return 4
            else:
                return 2

    def mb_pred(self, mb_type):
        if self.MbPartPredMode(mb_type, 0) in [
            MB_PART_PRED_MODE.Intra_4x4,
            MB_PART_PRED_MODE.Intra_8x8,
            MB_PART_PRED_MODE.Intra_16x16,
        ]:
            if self.MbPartPredMode(mb_type, 0) == MB_PART_PRED_MODE.Intra_4x4:
                self.prev_intra4x4_pred_mode_flag = []
                self.rem_intra4x4_pred_mode = []
                for luma4x4BlkIdx in range(16):
                    self.prev_intra4x4_pred_mode_flag.append(
                        self.stream.read_ae()
                        if self.pps.entropy_coding_mode_flag
                        else self.stream.read_bit()
                    )
                    if not self.prev_intra4x4_pred_mode_flag[luma4x4BlkIdx]:
                        self.rem_intra4x4_pred_mode.append(
                            self.stream.read_ae()
                            if self.pps.entropy_coding_mode_flag
                            else self.stream.read_nbit(3)
                        )
            if self.MbPartPredMode(mb_type, 0) == MB_PART_PRED_MODE.Intra_8x8:
                self.prev_intra8x8_pred_mode_flag = []
                self.rem_intra8x8_pred_mode = []
                for luma8x8BlkIdx in range(16):
                    self.prev_intra8x8_pred_mode_flag.append(
                        self.stream.read_ae()
                        if self.pps.entropy_coding_mode_flag
                        else self.stream.read_bit()
                    )
                    if not self.prev_intra8x8_pred_mode_flag[luma8x8BlkIdx]:
                        self.rem_intra8x8_pred_mode.append(
                            self.stream.read_ae()
                            if self.pps.entropy_coding_mode_flag
                            else self.stream.read_nbit(3)
                        )
            if self.sps.ChromaArrayType in [1, 2]:
                self.intra_chroma_pred_mode = (
                    self.stream.read_ae()
                    if self.pps.entropy_coding_mode_mode
                    else self.stream.read_ue()
                )
        elif self.MbPartPredMode(mb_type, 0) != MB_PART_PRED_MODE.Direct:
            self.ref_idx_l0 = []
            for mbPartIdx in range(self.NumMbPart(mb_type)):
                if (
                    (
                        self.num_ref_idx_l0_active_minus1 > 0
                        or self.mb_field_decoding_flag != self.field_pic_flag
                    )
                    and self.MbPartPredMode(mb_type, mbPartIdx)
                    != MB_PART_PRED_MODE.Pred_L1
                ):
                    self.ref_idx_l0.append(
                        self.stream.read_ae()
                        if self.pps.entropy_coding_mode_flag
                        else self.stream.read_te()
                    )
            self.ref_idx_l1 = []
            for mbPartIdx in range(self.NumMbPart(mb_type)):
                if (
                    (
                        self.num_ref_idx_l1_active_minus1 > 0
                        or self.mb_field_decoding_flag != self.field_pic_flag
                    )
                    and self.MbPartPredMode(mb_type, mbPartIdx)
                    != MB_PART_PRED_MODE.Pred_L0
                ):
                    self.ref_idx_l1.append(
                        self.stream.read_ae()
                        if self.pps.entropy_coding_mode_flag
                        else self.stream.read_te()
                    )
            self.mvd_l0 = []
            for mbPartIdx in range(self.NumMbPart(mb_type)):
                if self.MbPartPredMode(mb_type, mbPartIdx) != MB_PART_PRED_MODE.Pred_L1:
                    self.mvd_l0.append([[]])
                    for compIdx in range(2):
                        self.mvd_l0[mbPartIdx][0].append(
                            self.stream.read_ae()
                            if self.pps.entropy_coding_mode_flag
                            else self.stream.read_se()
                        )
            self.mvd_l1 = []
            for mbPartIdx in range(self.NumMbPart(mb_type)):
                if self.MbPartPredMode(mb_type, mbPartIdx) != MB_PART_PRED_MODE.Pred_L0:
                    self.mvd_l1.append([[]])
                    for compIdx in range(2):
                        self.mvd_l1[mbPartIdx][0].append(
                            self.stream.read_ae()
                            if self.pps.entropy_coding_mode_flag
                            else self.stream.read_se()
                        )

    def sub_mb_pred(self, mb_type):
        # TODO: sub_mb_pred
        pass

    def residual_block_cavlc(self, startIdx, endIdx, maxNumCoeff):
        pass

    def residual_block_cabac(self, startIdx, endIdx, maxNumCoeff):
        coeffLevel = []
        if maxNumCoeff != 64 or self.sps.ChromaArrayType == 3:
            self.coded_block_flag = self.stream.read_ae()
        for i in range(maxNumCoeff):
            coeffLevel.append(0)
        if self.coded_block_flag:
            numCoeff = endIdx + 1
            i = startIdx
            self.significant_coeff_flag = []
            self.last_significant_coeff_flag = []
            while i < numCoeff - 1:
                self.significant_coeff_flag.append(self.stream.read_ae())
                if self.significant_coeff_flag[i]:
                    self.last_significant_coeff_flag.append(self.stream.read_ae())
                    if self.last_significant_coeff_flag[i]:
                        numCoeff = i + 1
                i += 1
            self.coeff_abs_level_minus1 = [0 for i in range(numCoeff)]
            self.coeff_abs_level_minus1[-1] = self.stream.read_ae()
            self.coeff_sign_flag = [0 for i in range(numCoeff)]
            self.coeff_sign_flag[-1] = self.stream.read_ae()
            coeffLevel[numCoeff - 1] = (
                self.coeff_abs_level_minus1[numCoeff - 1] + 1
            ) * (1 - 2 * self.coeff_sign_flag[numCoeff - 1])
            for i in range(numCoeff - 2, startIdx - 1, -1):
                if self.significant_coeff_flag[i]:
                    self.coeff_abs_level_minus1[i] = self.stream.read_ae()
                    self.coeff_sign_flag[i] = self.stream.read_ae()
                    coeffLevel[i] = (self.coeff_abs_level_minus1[i] + 1) * (
                        1 - 2 * self.coeff_sign_flag[i]
                    )

    def residual_luma(self, startIdx, endIdx):
        i16x16DClevel = []
        i16x16AClevel = []
        level4x4 = []
        level8x8 = []
        if (
            startIdx == 0
            and self.MbPartPredMode(self.mb_type, 0) == MB_PART_PRED_MODE.Intra_16x16
        ):
            i16x16DClevel = self.residual_block(0, 15, 16)
        for i8x8 in range(4):
            if (
                not self.pps.transform_8x8_mode_flag
                or not self.pps.entropy_coding_mode_flag
            ):
                temp_8x8 = [0 for i in range(64)]
                for i4x4 in range(4):
                    if self.CodedBlockPatternLuma & (1 << i8x8):
                        if (
                            self.MbPartPredMode(self.mb_type, 0)
                            == MB_PART_PRED_MODE.Intra_16x16
                        ):
                            i16x16AClevel.append(
                                self.residual_block(
                                    max(0, startIdx - 1, endIdx - 1, 15)
                                )
                            )
                        else:
                            level4x4.append(self.residual_block(startIdx, endIdx, 16))
                    elif (
                        self.MbPartPredMode(self.mb_type, 0)
                        == MB_PART_PRED_MODE.Intra_16x16
                    ):
                        temp = []
                        for i in range(15):
                            temp.append(0)
                        i16x16AClevel.append(temp)
                    else:
                        temp = []
                        for i in range(16):
                            temp.append(0)
                        level4x4.append(temp)
                    if (
                        not self.pps.entropy_coding_mode_flag
                        and self.pps.transform_8x8_mode_flag
                    ):
                        for i in range(16):
                            temp_8x8[4 * i + i4x4] = level4x4[i8x8 * 4 + i4x4][i]
                level8x8.append(temp_8x8)
            elif self.CodedBlockPatternLuma & (1 << i8x8):
                level8x8.append(self.residual_block(4 * startIdx, 4 * endIdx + 3, 64))
            else:
                temp = []
                for i in range(64):
                    temp.append(0)
                level8x8.append(temp)

        return i16x16DClevel, i16x16AClevel, level4x4, level8x8

    def residual(self, startIdx, endIdx):
        if not self.pps.entropy_coding_mode_flag:
            self.residual_block = self.residual_block_cavlc
        else:
            self.residual_block = self.residual_block_cabac
        (
            self.Intra16x16DCLevel,
            self.Intra16x16ACLevel,
            self.LumaLevel4x4,
            self.LumaLevel8x8,
        ) = self.residual_luma(startIdx, endIdx)
        if self.sps.ChromaArrayType in [1, 2]:
            NumC8x8 = 4 // (self.sps.SubWidthC * self.sps.SubHeightC)
            self.ChromaDCLevel = []
            for iCbCr in range(2):
                if (self.CodedBlockPatternChroma & 3) and startIdx == 0:
                    self.ChromaDCLevel.append(
                        (self.residual_block(0, 4 * NumC8x8 - 1, 4 * NumC8x8))
                    )
                else:
                    temp = []
                    for i in range(4 * NumC8x8):
                        temp.append(0)
                    self.ChromaDCLevel.append(temp)
            self.ChromaACLevel = []
            for iCbCr in range(2):
                self.ChromaACLevel.append([])
                for i8x8 in range(NumC8x8):
                    for i4x4 in range(4):
                        if self.CodedBlockPatternChroma & 2:
                            self.ChromaACLevel[iCbCr].append(
                                (
                                    self.residual_block(
                                        max(0, startIdx - 1), endIdx - 1, 15
                                    )
                                )
                            )
                        else:
                            temp = []
                            for i in range(15):
                                temp.append(0)
                            self.ChromaACLevel[iCbCr].append(temp)
        elif self.sps.ChromaArrayType == 3:
            (
                self.CbIntra16x16DCLevel,
                self.CbIntra16x16ACLevel,
                self.CbLevel4x4,
                self.CbLevel8x8,
            ) = self.residual_luma(startIdx, endIdx)
            (
                self.CrIntra16x16DCLevel,
                self.CrIntra16x16ACLevel,
                self.CrLevel4x4,
                self.CrLevel8x8,
            ) = self.residual_luma(startIdx, endIdx)

    def macroblock_layer(self):
        self.mb_type = (
            self.stream.read_ae()
            if self.pps.entropy_coding_mode_flag
            else self.stream.read_ue()
        )
        if self.mb_type == MB_TYPE_I.I_PCM:
            self.pcm_alignment_zero_bit = []
            while not self.stream.byte_aligned():
                self.pcm_alignment_zero_bit.append(self.stream.read_bit())
            self.pcm_sample_luma = []
            for i in range(256):
                self.pcm_sample_luma.append(self.stream.read_nbit(self.sps.BitDepth_y))
            self.pcm_sample_chroma = []
            for i in range(2 * self.sps.MbWidthC * sps.MbHeightC):
                self.pcm_sample_chroma.append(
                    self.stream.read_nbit(self.sps.BitDepth_c)
                )
        else:
            noSubMbPartSizeLessThan8x8Flag = 1
            if (
                self.mb_type != MB_TYPE_I.I_NxN
                and self.MbPartPredMode_I(self.mb_type, 0)
                != MB_PART_PRED_MODE.Intra_16x16
                and self.NumMbPart(self.mb_type) == 4
            ):
                # TODO: sub_mb_pred(mb_type)
                pass
            else:
                if self.pps.transform_8x8_mode_flag and self.mb_type == MB_TYPE_I.I_NxN:
                    self.transform_size_8x8_flag = (
                        self.stream.read_ae()
                        if self.pps.entropy_coding_mode_flag
                        else self.stream.read_bit()
                    )
                self.mb_pred(mb_type)
            if self.MbPartPredMode(self.mb_type, 0) != MB_PART_PRED_MODE.Intra_16x16:
                self.coded_block_pattern = (
                    self.stream.read_ae()
                    if self.pps.entropy_coding_mode_flag
                    else self.stream.read_me()
                )
                self.CodedBlockPatternLuma = self.coded_block_pattern % 16
                self.CodedBlockPatternChroma = self.coded_block_pattern // 16
                if (
                    self.CodedBlockPatternLuma > 0
                    and self.pps.transform_8x8_mode_flag
                    and self.mb_type != MB_TYPE_I.I_NxN
                    and noSubMbPartSizeLessThan8x8Flag
                    and (
                        self.mb_type != MB_TYPE_B.B_Direct_16x16
                        or self.sps.direct_8x8_inference_flag
                    )
                ):
                    self.transform_size_8x8_flag = (
                        self.stream.read_ae()
                        if self.pps.entropy_coding_mode_flag
                        else self.stream.read_bit()
                    )
                if (
                    self.CodedBlockPatternLuma > 0
                    or self.CodedBlockPatternChroma > 0
                    or self.MbPartPredMode(mb_type, 0) == MB_PART_PRED_MODE.Intra_16x16
                ):
                    self.mb_qp_delta = (
                        self.stream.read_ae()
                        if self.pps.entropy_coding_mode_flag
                        else self.stream.read_se()
                    )
                    self.residual(0, 15)

    def slice_data(self):
        if self.pps.entropy_coding_mode_flag:
            self.cabac_alignment_one_bit = []
            while not self.stream.byte_aligned():
                self.cabac_alignment_one_bit.append(self.stream.read_bit())
        # 该宏块是否为自适应编码
        MbaffFrameFlag = (
            self.sps.mb_adaptive_frame_field_flag and not self.field_pic_flag
        )
        # 当前宏块在宏块序列中的索引
        CurrMbAddr = self.first_mb_in_slice * (1 + MbaffFrameFlag)
        moreDataFlag = 1
        prevMbSkipped = 0
        while True:
            if self.slice_type % 5 not in [SLICE_TYPE.I, SLICE_TYPE.SI]:  # I, SI
                if not self.pps.entropy_coding_mode_flag:
                    self.mb_skip_run = self.stream.read_ue()
                    prevMbSkipped = self.mb_skip_run > 0
                    for i in range(self.mb_skip_run):
                        CurrMbAddr = self.NextMbAddress(CurrMbAddr)
                    if self.mb_skip_run > 0:
                        moreDataFlag = self.stream.more_data()
                else:
                    self.mb_skip_flag = self.stream.read_ae()
                    moreDataFlag = not self.mb_skip_flag
            if moreDataFlag:
                if MbaffFrameFlag and (
                    CurrMbAddr % 2 == 0 or (CurrMbAddr % 2 == 1 and prevMbSkipped)
                ):
                    self.mb_field_decoding_flag = (
                        self.stream.read_ae()
                        if self.pps.entropy_coding_mode_flag
                        else self.stream.read_bit()
                    )
                self.macroblock_layer()
            if not self.pps.entropy_coding_mode_flag:
                moreDataFlag = self.stream.more_data()
            else:
                if self.slice_type % 5 not in [SLICE_TYPE.I, SLICE_TYPE.SI]:  # I, SI
                    prevMbSkipped = self.mb_skip_flag
                if MbaffFrameFlag and CurrMbAddr % 2 == 0:
                    moreDataFlag = 1
                else:
                    self.end_of_slice_flag = self.stream.read_ae()
                    moreDataFlag = not self.end_of_slice_flag
            CurrMbAddr = self.NextMbAddress(CurrMbAddr)

            if not moreDataFlag:
                break

    def slice_layer_without_partitioning(self):
        self.slice_header()
        self.slice_data()

    def slice_data_partition_a_layer(self):
        self.slice_header()
        self.slice_id = self.stream.read_ue()
        self.slice_data()

    def slice_data_partition_b_layer(self):
        self.slice_id = self.stream.read_ue()
        if self.sps.separate_colour_plane_flag == 1:
            self.colour_plane_id = self.stream.read_nbit(2)
        if self.pps.redundant_pic_cnt_present_flag:
            self.redundant_pic_cnt = self.stream.read_ue()
        self.slice_data()

    def slice_data_partition_c_layer(self):
        self.slice_id = self.stream.read_ue()
        if self.sps.separate_colour_plane_flag == 1:
            self.colour_plane_id = self.stream.read_nbit(2)
        if self.pps.redundant_pic_cnt_present_flag:
            self.redundant_pic_cnt = self.stream.read_ue()
        self.slice_data()


class IDR(Slice):
    def __init__(self, nal_header, data, bit_len, sps_list, pps_list):
        super().__init__(nal_header, data, bit_len, "IDR", sps_list, pps_list)

        self.slice_layer_without_partitioning()


class NALU_TYPE(enum.IntEnum):
    non_IDR = (1,)
    coded_slice_data_partition_a = (2,)
    coded_slice_data_partition_b = (3,)
    coded_slice_data_partition_c = (4,)
    IDR = (5,)
    SEI = (6,)
    SPS = (7,)
    PPS = (8,)
    AUD = (9,)
    end_of_seq = (10,)
    end_of_stream = (11,)
    filler_data = (12,)


class NALU:
    def __init__(self, data):
        self.data = data
        self.fmt = Struct(
            "header"
            / BitStruct(
                "forbidden_zero_bit" / Flag,
                "nal_ref_idc" / BitsInteger(2),
                "nal_unit_type" / BitsInteger(5),
            ),
            "payload" / GreedyBytes,
        )

        self.info = self.fmt.parse(self.data)
        self.header = self.info.header
        self.type = NALU_TYPE(self.header.nal_unit_type)
        self.ebsp = self.info.payload
        # 去除防竞争字节 0x03
        self.rbsp = self.ebsp.replace(b"\x00\x00\x03", b"\x00\x00")
        # 去除补齐的位数, 获取原始数据的位数
        self.sodb_bit_len = self._get_sodb_bit_len()

    def __str__(self):
        return f"{self.type.__str__()} {self.info.__str__()}\n"

    def _get_sodb_bit_len(self):
        # 获取补齐的bit数
        last_byte = self.rbsp[-1]
        trailing_bits_len = 0
        for i in range(8):
            trailing_bits_len += 1
            if (last_byte >> i) & 1:
                break
        return len(self.rbsp) * 8 - trailing_bits_len


class H264:
    def __init__(self, path):
        self.path = path
        self.data = None
        with open(path, "rb") as f:
            self.data = f.read()
        self.cur_offset = 0
        self.start_code = [b"\x00\x00\x01", b"\x00\x00\x00\x01"]
        self.sps_list = {}
        self.pps_list = {}

    def _read_nalu(self):
        data = self.data[self.cur_offset :]
        if len(data) == 0:
            return None

        beg = 3 if data[:3] == self.start_code[0] else 4
        end = -1
        for s in self.start_code:
            offset = data.find(s, beg)
            if end == -1:
                end = offset
            elif end > offset:
                end = offset

        if end == -1:
            end = len(data)

        self.cur_offset += end
        return NALU(data[beg:end])

    def decode(self):
        while True:
            nalu = self._read_nalu()

            if nalu == None:
                break

            print(nalu)

            payload = None
            if nalu.type == NALU_TYPE.SPS:
                payload = SPS(nalu.header, nalu.rbsp, nalu.sodb_bit_len)
                self.sps_list[payload.seq_parameter_set_id] = payload
            elif nalu.type == NALU_TYPE.PPS:
                payload = PPS(nalu.header, nalu.rbsp, nalu.sodb_bit_len, self.sps_list)
                self.pps_list[payload.pic_parameter_set_id] = payload
            elif nalu.type == NALU_TYPE.AUD:
                payload = AUD(nalu.header, nalu.rbsp, nalu.sodb_bit_len)
            elif nalu.type == NALU_TYPE.SEI:
                payload = SEI(nalu.header, nalu.rbsp, nalu.sodb_bit_len)
            elif nalu.type == NALU_TYPE.IDR:
                payload = IDR(
                    nalu.header,
                    nalu.rbsp,
                    nalu.sodb_bit_len,
                    self.sps_list,
                    self.pps_list,
                )
            elif nalu.type == NALU_TYPE.non_IDR:
                pass
            elif nalu.type == NALU_TYPE.end_of_seq:
                payload = EndOfSeq(nalu.header, nalu.rbsp, nalu.sodb_bit_len)
            elif nalu.type == NALU_TYPE.end_of_stream:
                payload = EndOfStream(nalu.header, nalu.rbsp, nalu.sodb_bit_len)
            elif nalu.type == NALU_TYPE.filler_data:
                payload = FillerData(nalu.header, nalu.rbsp, nalu.sodb_bit_len)

            print(payload)
            print("-" * 50)

            if self.cur_offset > 1000:
                break


if __name__ == "__main__":
    print(os.path.abspath(os.curdir))

    # h264_file = "./data/data1.h264"
    h264_file = r"D:\Project\work\git\mp4repair\temp\out.h264"

    h264 = H264(h264_file)
    h264.decode()
