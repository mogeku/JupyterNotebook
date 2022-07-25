import os
from construct import *

class NALU:
    def __init__(self, data):
        self.data = data
        self.fmt = Struct(
            "header"
            / BitStruct(
                "forbidden_zero_bit" / Flag,
                "nal_ref_idc" / BitsInteger(2),
                "nal_util_type"
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

    def __str__(self):
        return self.info.__str__()

    def cvt_ebsp_to_rbsp(self):
        self.info.payload = self.info.payload.replace(b'\x00\x00\x03', b'\x00\x00')

class H264:
    def __init__(self, path):
        self.path = path
        self.data = None
        with open(path, 'rb') as f:
            self.data = f.read()
        self.cur_offset = 0
        self.start_code = [b'\x00\x00\x01', b'\x00\x00\x00\x01']

    def _read_nalu(self):
        data = self.data[self.cur_offset:]
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
        return data[beg:end]



    def decode(self):
        nalu_raw = self._read_nalu()
        while nalu_raw != None:
            nalu = NALU(nalu_raw)
            # 去除 ebsp 中的防竞争字节 0x03
            nalu.cvt_ebsp_to_rbsp()

            print(nalu)

            if self.cur_offset > 30000: break

            nalu_raw = self._read_nalu()




if __name__ == '__main__':
    print(os.path.abspath(os.curdir))

    h264_file = './data/data1.h264'

    h264 = H264(h264_file)
    h264.decode()

