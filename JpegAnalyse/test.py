from struct import unpack
import math


def Clamp(col):
    col = 255 if col > 255 else col
    col = 0 if col < 0 else col
    return int(col)


def ColorConversion(Y, Cr, Cb):
    R = Cr * (2 - 2 * 0.299) + Y
    B = Cb * (2 - 2 * 0.114) + Y
    G = (Y - 0.114 * B - 0.299 * R) / 0.587
    return (Clamp(R + 128), Clamp(G + 128), Clamp(B + 128))


def DrawMatrix(x, y, matL, matCb, matCr):
    for yy in range(8):
        for xx in range(8):
            c = "#%02x%02x%02x" % ColorConversion(
                matL[yy][xx], matCb[yy][xx], matCr[yy][xx]
            )
            x1, y1 = (x * 8 + xx) * 1, (y * 8 + yy) * 1
            x2, y2 = (x * 8 + (xx + 1)) * 1, (y * 8 + (yy + 1)) * 1
            w.create_rectangle(x1, y1, x2, y2, fill=c, outline=c)


class IDCT:
    """
    An inverse Discrete Cosine Transformation Class
    """

    def __init__(self):
        self.base = [0] * 64
        self.zigzag = [
            [0, 1, 5, 6, 14, 15, 27, 28],
            [2, 4, 7, 13, 16, 26, 29, 42],
            [3, 8, 12, 17, 25, 30, 41, 43],
            [9, 11, 18, 24, 31, 40, 44, 53],
            [10, 19, 23, 32, 39, 45, 52, 54],
            [20, 22, 33, 38, 46, 51, 55, 60],
            [21, 34, 37, 47, 50, 56, 59, 61],
            [35, 36, 48, 49, 57, 58, 62, 63],
        ]
        self.idct_precision = 8
        self.idct_table = [
            [
                (self.NormCoeff(u) * math.cos(((2.0 * x + 1.0) * u * math.pi) / 16.0))
                for x in range(self.idct_precision)
            ]
            for u in range(self.idct_precision)
        ]

    def NormCoeff(self, n):
        if n == 0:
            return 1.0 / math.sqrt(2.0)
        else:
            return 1.0

    def rearrange_using_zigzag(self):
        for x in range(8):
            for y in range(8):
                self.zigzag[x][y] = self.base[self.zigzag[x][y]]
        return self.zigzag

    def perform_IDCT(self):
        out = [list(range(8)) for i in range(8)]

        for x in range(8):
            for y in range(8):
                local_sum = 0
                for u in range(self.idct_precision):
                    for v in range(self.idct_precision):
                        local_sum += (
                            self.zigzag[v][u]
                            * self.idct_table[u][x]
                            * self.idct_table[v][y]
                        )
                out[y][x] = local_sum // 4
        self.base = out


def DecodeNumber(code, bits):
    l = 2 ** (code - 1)
    if bits >= l:
        return bits
    else:
        return bits - (2 * l - 1)


def RemoveFF00(data):
    datapro = []
    i = 0
    while i + 2 < len(data):
        b, bnext = unpack("BB", data[i : i + 2])
        if b == 0xFF:
            if bnext != 0:
                print(f'0xff{hex(bnext)}')
                # break
            datapro.append(data[i])
            i += 2
        else:
            datapro.append(data[i])
            i += 1
    return datapro, i


def GetArray(type, l, length):
    s = ""
    for i in range(length):
        s = s + type
    return list(unpack(s, l[:length]))


class Stream:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def GetBit(self):
        b = self.data[self.pos >> 3]
        s = 7 - (self.pos & 0x7)
        self.pos += 1
        return (b >> s) & 1

    def GetBitN(self, l):
        val = 0
        for i in range(l):
            val = (val << 1) + self.GetBit()
        return val


class HuffmanTable:
    def __init__(self):
        self.root = []
        self.elements = []

    def BitsFromLengths(self, root, element, pos):
        if isinstance(root, list):
            if pos == 0:
                if len(root) < 2:
                    root.append(element)
                    return True
                return False
            for i in [0, 1]:
                if len(root) == i:
                    root.append([])
                if self.BitsFromLengths(root[i], element, pos - 1) == True:
                    return True
        return False

    def GetHuffmanBits(self, lengths, elements):
        self.elements = elements
        ii = 0
        for i in range(len(lengths)):
            for j in range(lengths[i]):
                self.BitsFromLengths(self.root, elements[ii], i)
                ii += 1

    def Find(self, st):
        r = self.root
        s = ''
        try:
            while isinstance(r, list):
                t = st.GetBit()
                s += str(t)
                r = r[t]
        except Exception as e:
            print(self.root)
            print(s)
            print(st.pos)
            print(hex(st.pos >> 3))
            r = 0
            # raise e
        return r

    def GetCode(self, st):
        while True:
            res = self.Find(st)
            if res == 0:
                return 0
            elif res != -1:
                return res


marker_mapping = {
    0xFFD8: "Start of Image",
    0xFFE0: "Application Default Header",
    0xFFE1: "APP1",
    0xFFDB: "Quantization Table",
    0xFFC0: "Start of Frame",
    0xFFC4: "Define Huffman Table",
    0xFFDA: "Start of Scan",
    0xFFD9: "End of Image",
}


class JPEG:
    def __init__(self, image_file):
        self.huffman_tables = {}
        self.quant = {}
        self.quantMapping = []
        self.sampMapping = []
        with open(image_file, "rb") as f:
            self.img_data = f.read()

    def DefineQuantizationTables(self, data):
        while len(data) > 0:
            (hdr,) = unpack("B", data[0:1])
            self.quant[hdr] = GetArray("B", data[1 : 1 + 64], 64)
            print(f"\nQuantizationTable[{hdr}]: {self.quant[hdr]}")

            data = data[65:]

    def decodeHuffman(self, data):

        while len(data) > 0:
            offset = 0
            (header,) = unpack("B", data[offset : offset + 1])
            offset += 1

            # Extract the 16 bytes containing length data
            lengths = unpack("BBBBBBBBBBBBBBBB", data[offset : offset + 16])
            offset += 16

            # Extract the elements after the initial 16 bytes
            elements = []
            for i in lengths:
                elements += GetArray("B", data[offset : offset + i], i)
                offset += i

            print("\nHeader: ", header)
            print("lengths: ", lengths)
            print("Elements: ", elements)
            print("Elements_len: ", len(elements))

            hf = HuffmanTable()
            hf.GetHuffmanBits(lengths, elements)
            self.huffman_tables[header] = hf

            data = data[offset:]

    def BaselineDCT(self, data):
        hdr, self.height, self.width, components = unpack(">BHHB", data[0:6])
        print(f"Data precision: {hdr}")
        print(f"Height: {self.height}, Width: {self.width}")
        print(f"Number of components: {components}")

        print("Component list:")
        for i in range(components):
            id, samp, QtbId = unpack("BBB", data[6 + i * 3 : 9 + i * 3])
            print(f"\tid: {id}, samp: {hex(samp)}, QuantizationTableId: {QtbId}")
            self.quantMapping.append(QtbId)
            self.sampMapping.append((samp >> 4, samp & 0x0f))
        print(self.sampMapping)

    def BuildMatrix(self, st, idx, quant, olddccoeff):
        i = IDCT()

        try:
            code = self.huffman_tables[0 + idx].GetCode(st)
        except:
            code = 0
            st.pos -= 8
        bits = st.GetBitN(code)
        dccoeff = DecodeNumber(code, bits) + olddccoeff

        i.base[0] = (dccoeff) * quant[0]
        l = 1
        while l < 64:
            code = self.huffman_tables[16 + idx].GetCode(st)
            if code == 0:
                break

            # The first part of the AC quantization table
            # is the number of leading zeros
            if code > 15:
                l += code >> 4
                code = code & 0x0F

            bits = st.GetBitN(code)

            if l < 64:
                coeff = DecodeNumber(code, bits)
                i.base[l] = coeff * quant[l]
                l += 1

        i.rearrange_using_zigzag()
        i.perform_IDCT()

        return i, dccoeff

    def StartOfScan(self, data, hdrlen):
        data, lenchunk = RemoveFF00(data[hdrlen:])
        print(f'scan_data_size: {hex(lenchunk)}')
        st = Stream(data)
        oldlumdccoeff, oldCbdccoeff, oldCrdccoeff = 0, 0, 0
        for y in range(math.ceil(self.height / 8)):
            if y > 4:
                break
            for x in range(math.ceil(self.width / 16)):
                matLs = [[None, None],[None, None]]
                for v in range(self.sampMapping[0][1]):
                    for h in range(self.sampMapping[0][0]):
                        matL, oldlumdccoeff = self.BuildMatrix(
                            st, 0, self.quant[self.quantMapping[0]], oldlumdccoeff
                        )
                        matLs[v][h] = matL
                matCr, oldCrdccoeff = self.BuildMatrix(
                    st, 1, self.quant[self.quantMapping[1]], oldCrdccoeff
                )
                matCb, oldCbdccoeff = self.BuildMatrix(
                    st, 1, self.quant[self.quantMapping[2]], oldCbdccoeff
                )

                for v in range(self.sampMapping[0][1]):
                    for h in range(self.sampMapping[0][0]):
                        DrawMatrix(2*x + h, y + v, matLs[v][h].base, matCb.base, matCr.base)

        return lenchunk + hdrlen

    def decode(self):
        data = self.img_data
        cur_offset = 0
        while True:
            (marker,) = unpack(">H", data[0:2])
            if marker in marker_mapping:
                print(
                    "-" * 50 + "\n",
                    hex(cur_offset),
                    hex(marker),
                    marker_mapping.get(marker),
                )
            if marker == 0xFFD8:
                data = data[2:]
                cur_offset += 2
            elif marker == 0xFFD9:
                return
            else:
                (lenchunk,) = unpack(">H", data[2:4])
                chunk = data[4 : 4 + lenchunk - 2]

                if marker == 0xFFC4:
                    self.decodeHuffman(chunk)
                elif marker == 0xFFDB:
                    self.DefineQuantizationTables(chunk)
                elif marker == 0xFFC0:
                    self.BaselineDCT(chunk)
                elif marker == 0xFFDA:
                    lenchunk = self.StartOfScan(data[2:], lenchunk)
                    return
                data = data[lenchunk + 2 :]
                cur_offset += lenchunk + 2

            if len(data) == 0:
                break


if __name__ == "__main__":
    from tkinter import *

    master = Tk()
    w = Canvas(master, width=800, height=800)
    w.pack()

    # img = JPEG(r"E:\Project\JupyterNotebook\JpegAnalyse\data\profile.jpg")
    # img = JPEG(r"E:\Project\JupyterNotebook\JpegAnalyse\data\test.jpg")
    # img = JPEG(r"E:\Project\JupyterNotebook\JpegAnalyse\data\incomplete.jpg")
    img = JPEG(r"E:\Project\JupyterNotebook\JpegAnalyse\data\Raw00190.jpg")
    img.decode()

    mainloop()
