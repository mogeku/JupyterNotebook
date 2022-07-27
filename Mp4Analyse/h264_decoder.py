import os
import math
from construct import *
from bitstream import BitStream
from numpy import uint8


class MyBitStream(BitStream):
    def __init__(self, data: bytes, bit_len):
        super().__init__(data)
        self.bit_len = bit_len
        self._readed_bit = 0

    def more_data(self):
        return self._readed_bit < self.bit_len

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


class NALU_Payload:
    def __init__(self, data, bit_len, type_name):
        self.stream = MyBitStream(data, bit_len)
        self.type = type_name

    def __str__(self):
        ret = f"{self.type} info:\n"
        skip_list = ["stream"]
        for key, value in self.__dict__.items():
            if key in skip_list:
                continue
            ret += f"\t{key} = {value}\n"
        return ret

    def more_rbsp_data(self):
        return self.stream.more_data()

    def scaling_list(self):
        pass


class SPS(NALU_Payload):
    def __init__(self, data, bit_len):
        super().__init__(data, bit_len, "Sequence parameter set")

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
                            pass  # scaling_list 含义暂时不知道
                        else:
                            pass  # scaling_list 含义暂时不知道
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
                pass  # vui_parameters 的解析暂时不知道

        # 通过上面读取的参数推导出下面的参数

        # 像素编码的格式, 0: 单色或 YUV444 分离模式, 1: YUV420, 2: YUV422, 3: YUV444
        if self.chroma_format_idc == 3:
            self.ChromaArrayType = 3 if self.separate_colour_plane_flag == 0 else 0
        else:
            self.ChromaArrayType = self.chroma_format_idc

        # SubWidthC 和 SubHeightC 代表 YUV 分量中, Y 分量和 UV 分量在水平和竖直方向上的比值
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
            self.SubWidthC = 1
            self.SubHeightC = 1

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


class PPS(NALU_Payload):
    def __init__(self, data, bit_len, sps:SPS):
        super().__init__(data, bit_len, "Picture parameter set")

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
            elif self.slice_group_map_type == 6:
                self.pic_size_in_map_units_minus1 = self.stream.read_ue()
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
                for i in range(6 + (2 if sps.chroma_format_idc != 3 else 6) * self.transform_8x8_mode_flag):
                    self.pic_scaling_list_present_flag.append(self.stream.read_bit())
                    if self.pic_scaling_list_present_flag[i]:
                        if i < 6:
                            self.scaling_list()
                        else:
                            self.scaling_list()
            self.second_chroma_qp_index_offset = self.stream.read_se()


class NALU:
    def __init__(self, data):
        self.data = data
        self.fmt = Struct(
            "header"
            / BitStruct(
                "forbidden_zero_bit" / Flag,
                "nal_ref_idc" / BitsInteger(2),
                "nal_unit_type"
                / Enum(
                    BitsInteger(5),
                    non_IDR=1,
                    coded_slice_data_partition_a=2,
                    coded_slice_data_partition_b=3,
                    coded_slice_data_partition_c=4,
                    IDR=5,
                    SEI=6,
                    SPS=7,
                    PPS=8,
                    access_unit_delimiter=9,
                    end_of_seq=10,
                    end_of_stream=11,
                    filler_data=12,
                ),
            ),
            "payload" / GreedyBytes,
        )

        self.info = self.fmt.parse(self.data)
        self.type = self.info.header.nal_unit_type
        self.ebsp = self.info.payload
        # 去除防竞争字节 0x03
        self.rbsp = self.ebsp.replace(b"\x00\x00\x03", b"\x00\x00")
        # 去除补齐的位数, 获取原始数据的位数
        self.sodb_bit_len = self._get_sodb_bit_len()

    def __str__(self):
        return self.info.__str__()

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
        self.sps = None
        self.pps = None

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
            print(nalu.info.header)
            if nalu.type == "SPS":
                payload = SPS(nalu.rbsp, nalu.sodb_bit_len)
                self.sps = payload
            elif nalu.type == "PPS":
                payload = PPS(nalu.rbsp, nalu.sodb_bit_len, self.sps)
                self.pps = payload

            print(payload)

            if self.cur_offset > 1000:
                break


if __name__ == "__main__":
    print(os.path.abspath(os.curdir))

    h264_file = "./data/data1.h264"

    h264 = H264(h264_file)
    h264.decode()

