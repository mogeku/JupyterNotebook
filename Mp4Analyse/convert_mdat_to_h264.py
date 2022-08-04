from construct import *

class Box:
    def __init__(self, name=''):
        if not hasattr(self, 'body_fmt'):
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
            if self.box_name == '':
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

class MediaDataBox(Box):
    def __init__(self):
        self.body_fmt = Struct("data" / GreedyBytes)

        super().__init__('mdat')

    def get_nalu_list(self):
        nalu_fmt = Struct(
            "nalu_len" / Int32ub,
            "nalu_data" / Bytes(this.nalu_len),
        )

        nalu_list_fmt = GreedyRange(nalu_fmt)

        nalu_list = [nalu.nalu_data for nalu in nalu_list_fmt.parse(self.body.data)]

        return nalu_list

    def convert_to_h264(self, h264_path):
        nalu_list = self.get_nalu_list()

        kStartCode = b'\x00\x00\x00\x01'

        f = open(h264_path, 'wb')
        for nalu in nalu_list:
            f.write(kStartCode)
            f.write(nalu)
        f.close()


data = None
with open(r"D:\Users\Desktop\MP4_72042229760.mp4", 'rb') as f:
    data = f.read()

mdat_offset = data.find(b'mdat') - 4
if mdat_offset >= 0:
    mdat = MediaDataBox()
    mdat.init(data[mdat_offset:])
    print(mdat)

    mdat.convert_to_h264(r'D:\Users\Desktop\MP4_72042229760.h264')

