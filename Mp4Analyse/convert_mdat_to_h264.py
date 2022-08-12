from construct import *
import enum

base_offset = 0

class Box:
    def __init__(self, name=""):
        if not hasattr(self, "body_fmt"):
            self.body_fmt = IfThenElse(
                this.size == 1,
                GreedyBytes,
                Bytes(
                    this.size - 8 if this.large_size == None else this.large_size - 16
                ),
            )

        self.struct = None
        self.size = None
        self.body = None
        self.box_name = name

        self.fmt = Struct(
            "size" / Int32ub,
            "type" / PaddedString(4, "ascii"),
            "large_size" / Optional(If(this.size == 0, Int64ub)),
            "extended_type" / Optional(If(this.type == "uuid", Bytes(16))),
            "body" / self.body_fmt,
        )

    def __str__(self):
        ret = f"box_name: {self.box_name}\nNormal Box " + self.struct.__str__()
        return ret

    def init(self, data):
        try:
            self.struct = self.fmt.parse(data)
            self.size = (
                self.struct.size
                if self.struct.large_size == None
                else self.struct.large_size
            )
            if self.box_name == "":
                self.box_name = self.struct.type
            self.body = self.struct.body
        except Exception as e:
            print(e)

    @staticmethod
    def getBoxList(data):
        cur_offset = 0
        boxes = []
        data_len = len(data)

        while cur_offset < data_len:
            tmp = Box(data[cur_offset:])

            # print(f"Current pos is {cur_offset}/{data_len}")

            box = None
            if tmp.box_name == "avc1":
                box = VisualSampleEntry(data[cur_offset:])
            else:
                box = tmp

            boxes.append(box)
            cur_offset += box.size

        return boxes


class NALU_TYPE(enum.IntEnum):
    non_IDR = (1,)
    coded_slice_data_partition_a = (2,)
    coded_slice_data_partition_b = (3,)
    coded_slice_data_partition_c = (4,)
    IDR = (5,)
    SEI = (6,)
    SPS = (7,)
    PPS = (8,)
    access_unit_delimiter = (9,)
    end_of_seq = (10,)
    end_of_stream = (11,)
    filler_data = (12,)


class NALU:
    def __init__(self, data):
        self.data = data
        self.fmt = Struct(
            "Header"
            / BitStruct(
                "forbidden_zero_bit" / Flag,
                "nal_ref_idc" / BitsInteger(2),
                "nal_unit_type" / BitsInteger(5),
            ),
            "Payload" / GreedyBytes,
        )

        self.struct = self.fmt.parse(self.data)
        self.type = self.struct.Header.nal_unit_type
        self.ref_idc = self.struct.Header.nal_ref_idc
        self.forbidden_zero_bit = self.struct.Header.forbidden_zero_bit
        self.payload = self.struct.Payload

    def __str__(self):
        return self.struct.__str__()

class AVCConfigurationBox(Box):
    def __init__(self):
        self.body_fmt = Struct(
            "configurationVersion" / Int8ub,
            "AVCProfileIndication" / Int8ub,
            "profile_compatibility" / Int8ub,
            "AVCLevelIndication" / Int8ub,
            "lengthSizeMinusOne" / BitStruct(Padding(6), "value" / BitsInteger(2)),
            "numOfSequenceParameterSets"
            / BitStruct(Padding(3), "value" / BitsInteger(5)),
            "sps_list"
            / Array(
                this.numOfSequenceParameterSets.value,
                Struct(
                    "sps_len" / Int16ub,
                    "sps" / Bytes(this.sps_len),
                ),
            ),
            "numOfPictureParameterSets" / Int8ub,
            "pps_list"
            / Array(
                this.numOfPictureParameterSets,
                Struct(
                    "pps_len" / Int16ub,
                    "pps" / Bytes(this.pps_len),
                ),
            ),
        )

        super().__init__("avcC")

    def init(self, data):
        super().init(data)

        self.sps_list = [sps.sps for sps in self.body.sps_list]
        self.pps_list = [pps.pps for pps in self.body.pps_list]

class MediaDataBox(Box):
    def __init__(self):
        self.body_fmt = Struct("data" / GreedyBytes)

        super().__init__("mdat")

    def _get_nalu(self, offset):
        data = self.body.data[offset:]
        nalu_len = Int32ub.parse(data)
        if nalu_len not in range(len(data)):
            raise StreamError('')
        nalu_data = data[4 : 4 + nalu_len]
        return nalu_len, nalu_data

    def _find_AUD(self, offset):
        while True:
            if offset >= len(self.body.data):
                return -1

            try:
                # print(offset)
                nalu_len, nalu_data = self._get_nalu(offset)
            except StreamError:
                offset += 1
                continue
            # print(nalu_data)

            if nalu_len != 2:
                offset += 1
                continue

            try:
                nalu = NALU(nalu_data)
            except StreamError:
                offset += 1
                continue
            # print(nalu)

            if (
                nalu.forbidden_zero_bit != 0
                or nalu.type != NALU_TYPE.access_unit_delimiter
                or nalu.ref_idc != 0
            ):
                offset += 1
                continue

            aud_payload_fmt = BitStruct('primary_pic_type' / BitsInteger(3), 'alignment_bit' / BitsInteger(5))
            aud_payload = aud_payload_fmt.parse(nalu.payload)
            if aud_payload.primary_pic_type not in range(7) or aud_payload.alignment_bit != 0b10000:
                offset += 1
                continue

            return offset

    def get_nalu_list(self):

        nalu_list = []
        offset = 0

        while True:
            offset = self._find_AUD(offset)
            print('-----AUD offset:', offset + base_offset + 8)
            if offset == -1:
                break

            while True:
                try:
                    nalu_len, nalu_data = self._get_nalu(offset)
                    print(NALU(nalu_data))
                    print(f'nalu data offset: {offset + base_offset + 8}')
                    offset += nalu_len + 4
                except StreamError:
                    break

                nalu_list.append(nalu_data)

            if len(nalu_list) > 100:
                break

        print(f'nalu count: {len(nalu_list)}')
        return nalu_list

    def convert_to_h264(self, h264_path, sps_list, pps_list):
        nalu_list = self.get_nalu_list()

        kStartCode = b"\x00\x00\x00\x01"
        kAUD = b"\x09\x10"

        f = open(h264_path, "wb")
        for sps in sps_list:
            f.write(kStartCode)
            f.write(kAUD)
            f.write(kStartCode)
            f.write(sps)

        for pps in pps_list:
            f.write(kStartCode)
            f.write(kAUD)
            f.write(kStartCode)
            f.write(pps)

        for nalu in nalu_list:
            f.write(kStartCode)
            f.write(nalu)
        f.close()


data = None
# f = open(r"D:\Users\Desktop\hero8.mp4", "rb")
f = open(r"D:\Users\Desktop\#X012514_1.mp4", "rb")

data = f.read()

f.seek(283089136)
data = f.read(1024*100)

avcC_offset = data.find(b"avcC") - 4
if avcC_offset >= 0:
    avcC = AVCConfigurationBox()
    avcC.init(data[avcC_offset:])
    print(avcC)

f.seek(47939584)
data = f.read(1024*1000)

base_offset = 47939584
mdat_offset = data.find(b"mdat") - 4
base_offset += mdat_offset
if mdat_offset >= 0:
    mdat = MediaDataBox()
    mdat.init(data[mdat_offset:])
    print(mdat)

    mdat.convert_to_h264(r'D:\Users\Desktop\hero8.h264', avcC.sps_list, avcC.pps_list)
    # mdat.get_nalu_list()
