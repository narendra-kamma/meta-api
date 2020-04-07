import os
import struct

def float2date(date):
    """Convert a float to a string containig a date"""
    date = int(date)
    year = 1900 + (date / 10000)
    month = (date % 10000) / 100
    day = date % 100
    return '%04d%02d%02d' % (year, month, day)

def fmsbin2ieee(bytes):
    """Convert an array of 4 bytes containing Microsoft Binary floating point
    number to IEEE floating point format (which is used by Python)"""
    as_int = struct.unpack("i", bytes)
    if not as_int:
        return 0.0
    man = long(struct.unpack('H', bytes[2:])[0])
    exp = (man & 0xff00) - 0x0200
    if (exp & 0x8000 != man & 0x8000):
        return 1.0
	#raise ValueError('exponent overflow')
    man = man & 0x7f | (man << 8) & 0x8000
    man |= exp >> 1
    bytes2 = bytes[:2]
    bytes2 += chr(man & 255)
    bytes2 += chr((man >> 8) & 255)
    return struct.unpack("f", bytes2)[0]

def ieee2fmsbin(f):
    """
    Convert an IEEE floating point format (4 Bytes in Python) value to 
    Microsoft Binary floating point
    """
    ie = struct.pack('f', f)
    ieee = []
    ieee.append(struct.unpack("B", ie[0])[0])
    ieee.append(struct.unpack("B", ie[1])[0])
    ieee.append(struct.unpack("B", ie[2])[0])
    ieee.append(struct.unpack("B", ie[3])[0])
    msbin = [0] * 4
    sign = ieee[3] & 0x80

    msbin_exp = (ieee[3] << 1) | (ieee[2] >> 7)
    # how do you want to treat too-large exponents...?
    if msbin_exp == 0xfe:
        raise OverflowError
    msbin_exp += 2
    msbin[3] = msbin_exp
    msbin[2] = sign | (ieee[2] & 0x7f)
    msbin[:2] = ieee[:2]
    st = ''
    st += struct.pack('B',msbin[0])
    st += struct.pack('B',msbin[1])
    st += struct.pack('B',msbin[2])
    st += struct.pack('B',msbin[3])
    return st

def date2float(date):
    """Convert a date to float
       expected date format = "YYYYMMDD"
    """
    date = str(date)
    y = int(date[:4]) - 1900
    final = str(y) + date[4:]
    return int(final) + 0.0


class MetaRecord():
    """
    holds header details of a symbol
    """
    def __init__(self):
        """
        initializes the instance
        """
        self.start_date = 0
        self.end_date = 0
        self.file_num = 0
        self.name = ""
        self.code = 0
        
    def parse_master_type(self, raw_string):
        """
        parses master type header record
        updates instance accordingly
        """
        unpacked = struct.unpack("<B6s16s2s4s4s1s2s16s1s", raw_string)
        self.file_num = unpacked[0]
        self.name = unpacked[2].split('\x00')[0].split('  ')[0]
        self.start_date = float2date(fmsbin2ieee(unpacked[4]))
        self.end_date = float2date(fmsbin2ieee(unpacked[5]))
        self.code = unpacked[8].split('\x00')[0].split('  ')[0]
        return

    def parse_emaster_type(self, raw_string):
        """
        parses xmaster type header record
        updates instance accordingly
        """
        unpacked = struct.unpack("<2sB8s21s28s1s3sf4sf50s4s62s", raw_string)
        self.file_num = unpacked[1]
        self.name = unpacked[4].split('\x00')[0].split('  ')[0]
        self.start_date = float2date(unpacked[7])
        self.end_date = float2date(unpacked[9])
        self.code = unpacked[3].split('\x00')[0].split('  ')[0]
        return

    def parse_xmaster_type(self, raw_string):
        """
        parses xmaster type header record
        updates instance accordingly
        """
        unpacked = struct.unpack("<1s15s46s3sBB4s9sI20sII4sI30s", raw_string)
        self.code = unpacked[1].split('\x00')[0]
        self.name = unpacked[2].split('\x00')[0]
        self.file_num = unpacked[4] + (unpacked[5] * 256)
        self.start_date = unpacked[8]
        self.end_date = unpacked[13]
        return

class TickRecord():
    """
    represents a single details
    tick can be for any frequency
    """
    def __init__(self, name, code, tdate, topen, thigh, tlow, tclose, tvolume):
        """
        initializes tick record with supplied values
        """
        self.name = name
        self.code = code
        self.date = int(tdate)
        self.open = float(topen)
        self.high = float(thigh)
        self.low = float(tlow)
        self.close = float(tclose)
        self.volume = float(tvolume)
        
class Manager():
    """
    represents all headers information
    maintains in-memory representation of all headers
    """

    def __init__(self, path):
        """
        initializes header instance.
        loads all header data in to memory
        """
        self.copyright = "www.kakup.com"
        self.pad = '\x00'
        self.path = path
        self.meta_records = []
        self.data_records = {}
        
        # read master and list out meta records
        """if (os.path.exists(path + "MASTER")):
            m_file = open(path + "MASTER", 'rb')
            count = struct.unpack("B", m_file.read(1))
            m_file.seek(0)
            m_file.seek(53) # skip intro part
            # now we know that, there are "count" meta records
            for i in range(1, count[0]+1):
                mr = MetaRecord()
                mr.parse_master_type(m_file.read(53))
                self.meta_records.append(mr)
            m_file.close()"""

        # read emaster and list out meta records
        if (os.path.exists(path + "EMASTER")):
            m_file = open(path + "EMASTER", 'rb')
            count = struct.unpack("B", m_file.read(1))
            m_file.seek(0)
            m_file.seek(192) # skip intro part
            # now we know that, there are "count" meta records
            for i in range(1, count[0]+1):
                mr = MetaRecord()
                mr.parse_emaster_type(m_file.read(192))
                self.meta_records.append(mr)
            m_file.close()

            
        # read Xmaster and list out meta records
        if (os.path.exists(self.path + "XMASTER")):
            m_file = open(self.path + "XMASTER", 'rb')
            m_file.seek(10) #jump unwanted
            count = struct.unpack("H", m_file.read(2))
            m_file.seek(0)
            m_file.seek(150) # skip intro part
            # now we know that, there are "count" meta records
            for i in range(1, count[0]+1):
                mr = MetaRecord()
                mr.parse_xmaster_type(m_file.read(150))
                self.meta_records.append(mr)
            m_file.close()
        # done
        return


    def list_out(self):

        m_file = open("C:/Users/naren/Desktop/data test/All/3I 0210 0211/" + "MASTER", 'rb')
        print m_file.read(53)
        a= m_file.read(53)
        print a
        x= struct.unpack("25s4s24s",a)
        print x
        print fmsbin2ieee(x[1])
        print float2date(fmsbin2ieee(x[1])) # master date reading
        m_file.close()

        m_file = open("C:/Users/naren/Desktop/data test/All/3I 0210 0211/" + "EMASTER", 'rb')
        print m_file.read(192)
        a= m_file.read(130)
        print a
        x= struct.unpack("64s4s4s4s50s4s",a)
        print x
        print float2date(struct.unpack("f",x[1])[0])
        m_file.close()

    def get_meta_record_by_code(self, code):
        """
        returns meta record if exists, by matching code
        """
        # check for code in meta_records
        for meta_record in self.meta_records:
            if meta_record.code == code:
                return meta_record

    def update_meta_record_by_code(self, code, mr):
        """
        updates meta record entry by matching code
        """
        # check for code in meta_records
        for meta_record in self.meta_records:
            if meta_record.code == code:
                ind = self.meta_records.index(meta_record)
                self.meta_records[ind] = mr
                return
        # seems not existing upto now
        # add a new meta record and return
        self.meta_records.append(mr)
        return
        
    
    def add_record(self, tick_record):
        """
        add tick details to appropriate file and updates headers
        make sure that symbol got added to headers, if new.

        assumes that tick_records contain one or more entrties
        related to the same symbol. otheriwse, corrupts data.

        this method perform actions only on in-memory data.
        actual file writing happens while conclusion.
        """
        
        mr = self.get_meta_record_by_code(tick_record.code)

        # does meta record found?
        if not mr:
            # lets create one
            mr = MetaRecord()
            mr.file_num = len(self.meta_records) + 1
            mr.code = tick_record.code
            mr.name = tick_record.name
            mr.start_date = tick_record.date
            mr.end_date = tick_record.date

        # check whether we need to update start or end date
        if float(mr.start_date) > float(tick_record.date):
            # user is adding old entry than repository
            mr.start_date = tick_record.date
        elif float(mr.end_date) < float(tick_record.date):
            # user is adding new data
            mr.end_date = tick_record.date

        # update modified meta record
        # it will also care about new meta record
        self.update_meta_record_by_code(tick_record.code, mr)

        # store tick details for conclusion
        if not mr.file_num in self.data_records:
            self.data_records[mr.file_num] = []
        # obtain pending writing records of this data file
        pending_list = self.data_records[mr.file_num]
        pending_list.append(tick_record)
        # update pending list with new records
        self.data_records[mr.file_num] = pending_list


    def write_masters(self):
        """
        re-writes master files basing on information
        available in in-memory database.

        effects master, emaster, xmaster
        """
        #==================================MASTER===============================
        # prepare header information
        part_1 = struct.pack("<B1sB46s4s",
                             len(self.meta_records[:255]),
                             self.pad, len(self.meta_records[:255]),
                             self.pad * 46, self.pad * 4)
        part_2 = ""
        # prepare each records meta information
        for each_rec in self.meta_records[:255]:
            part_2 += struct.pack("<B4s2s16s2s4s4s1s2s16s1s",
                                  each_rec.file_num,
                                  "e\x00\x1c\x07", #FLAGS?, May be no. of fields 
                                  self.pad * 2, each_rec.name,
                                  self.pad * 2,
                                  ieee2fmsbin(date2float(each_rec.start_date)),
                                  ieee2fmsbin(date2float(each_rec.end_date)),
                                  'D', self.pad * 2,
                                  each_rec.code, self.pad)
                
        # write to file
        f = open(self.path + "MASTER", 'wb')
        f.write(part_1)
        f.write(part_2)
        f.close()

        #==================================EMASTER==============================
        
        part_1 = ""
        part_2 = ""
        part_1 = struct.pack("<B1sB46s4s43s96s",
                             len(self.meta_records[:255]) ,
                             self.pad, len(self.meta_records[:255]) ,
                             self.pad * 46, self.pad * 4,
                             self.pad * 43,
                             self.pad * 96 
                             )
        
        # prepare each records meta information
        for each_rec in self.meta_records[:255]:
            part_2 += struct.pack("<2sB8s21s28s1s3sf4sf50s4s62s",
                                  "66", each_rec.file_num,
                                  "\x00\x00\x00\x07\x7f\x00 \x00", # DONT REMOVE SPACE IN STRING
                                  each_rec.code.ljust(21,'\x00'),
                                  each_rec.name.ljust(28,'\x00'),
                                  "D", self.pad * 3,
                                  date2float(each_rec.start_date),
                                  self.pad * 4,
                                  date2float(each_rec.end_date),
                                  self.pad * 50, self.pad * 4, self.pad * 62)
                                
        
        # write to file
        f = open(self.path + "EMASTER", 'wb')
        f.write(part_1)
        f.write(part_2)        
        f.close()
        
        #=================================XMASTER===============================

        if not self.meta_records[255:]:
            return
        
        part_1 = ""
        part_2 = ""
        part_1 = struct.pack("6s3sH2sH2sH2s128s",
                             "]\xfeXM\x02\x02", # CONSTANT. ALTERED. ACTUAL: "]\xfeXM\x8b\x02"
                             self.pad * 3, # CLEANED: "h5M"
                             len(self.meta_records[255:]), self.pad * 2,
                             len(self.meta_records[255:]), self.pad * 2,
                             len(self.meta_records[255:]) + 255, self.pad * 2,
                             self.copyright.ljust(128, self.pad))
        
        # prepare each records meta information
        for each_rec in self.meta_records[255:]:
            part_2 += struct.pack("<1s15s46s1s2sBB4s9sI4s16sII4sI30s",
                                  "\x01", each_rec.code.ljust(15,'\x00'),
                                  each_rec.name.ljust(46,'\x00'),
                                  "D", self.pad * 2,
                                  each_rec.file_num % 256, each_rec.file_num/256,
                                  "\x00\x00\x00\x7f", # UNKNOWN. CONSTANT
                                  self.pad * 9, each_rec.start_date,
                                  self.pad * 4, # CLEANED: b\x8d2\x00
                                  self.pad * 16, 
                                  each_rec.start_date, each_rec.start_date,
                                  self.pad * 4,
                                  each_rec.end_date,
                                  self.pad * 30)
        # write to file
        f = open(self.path + "XMASTER", 'wb')
        f.write(part_1)
        f.write(part_2)        
        f.close()
        
    def write_data_file(self, file_num):
        """
        updates data files with added tick records
        creates data file, if new.

        1. load existing data if available
        2. add pending data to existing data
        3. re-write everything
        """
        pending_records = self.data_records[file_num]
        existing_records = {}
        file_path = "%sF%s.%s"%(self.path, file_num, "DAT" if file_num <=255 else "MWD")
        
        # try to load existing data
        if os.path.exists(file_path):
            
            data_file = open(file_path, "rb")
            data_file.seek(2) # skip two chars to find out length
            count = struct.unpack("H", data_file.read(2))[0]
            data_file.seek(28) # skip header part
            
            # read chunks. of each 24 bytes
            for i in range(count-1):
                the_chunk = data_file.read(28)
                # dictionary key is nothing but date
                existing_records[float2date(fmsbin2ieee(the_chunk[:4]))] = the_chunk
            data_file.close()

        # add pending records data to existing records in format
        # remember, we didn't unpack existing data.
        # just to be uniform and ease in soring, pack new data
        for pending_record in pending_records:
            packed_newdata = struct.pack("4s4s4s4s4s4s4s",
                                         ieee2fmsbin(date2float(pending_record.date)),
                                         ieee2fmsbin(pending_record.open),
                                         ieee2fmsbin(pending_record.high),
                                         ieee2fmsbin(pending_record.low),
                                         ieee2fmsbin(pending_record.close),
                                         ieee2fmsbin(pending_record.volume),
                                         self.pad * 4)
            existing_records[str(pending_record.date)] = packed_newdata
    
        # time for writing.
        part_1 = struct.pack("2sH24s",
                             self.pad * 2,
                             len(existing_records) + 1, self.pad * 4)
        part_2 = ""
        for key in sorted(existing_records):
            part_2 += existing_records[key] # already packed
            
        # write to file
        f = open(file_path, 'wb')
        f.write(part_1)
        f.write(part_2)        
        f.close()
           
            
    def conclude(self):
        """
        concludes all actions performed so far on in-memory data
        re-writes header files and effected data files.

        responsible for real file writing operations
        """
        
        # let's update master files. real files.
        self.write_masters()
        # let's update individual data files
        for file_num in self.data_records:
            self.write_data_file(file_num)
            

if __name__ == "__main__":
    h = Manager("C:/Users/naren/Desktop/data test/All/output1/")
    #h.list_out()
    tick_recs = []
    for i in range(1000):
        i = i + 1
        tick_recs.append(TickRecord("A" + str(i), str(i), 20100205, 453.1, 480.5, 430.0, 450.2, 20000000))
    for each in tick_recs:                         
        h.add_record(each)
    h.conclude()
