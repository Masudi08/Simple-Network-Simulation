import struct
import zlib

#Network byte order (Big-Endian'!'):
#I=4-Byte unsigned int(seq_num)
#B=1-Byte unsigned char(pkt_type)
#H=2-Byte unsigned short (payload_len)
#I=4-Byte unsigned int(crc32 checksum)
HEADER_FORMAT="!IBHI"
HEADER_SIZE=struct.calcsize(HEADER_FORMAT)

PKT_DATA=0
PKT_ACK=1
PKT_FIN=2

def pack_packet(seq_num:int,pkt_type:int,payload_bytes:bytes=b"")->bytes:
    """Packs header fields and payload into a raw binary datagram with crc32."""
    payload_len=len(payload_bytes)

    #Pack header with placeholder checksum=0 to compute the crc32
    temp_header=struct.pack(HEADER_FORMAT,seq_num,pkt_type,payload_len,0)
    checksum=zlib.crc32(temp_header+payload_bytes)& 0xFFFFFFFF

    #Repack with real checksum
    final_header = struct.pack(HEADER_FORMAT,seq_num,pkt_type,payload_len,checksum)
    return final_header+payload_bytes
def unpack_packet(raw_bytes:bytes):
    """Unpacks raw bytes into (seq_num,pkt_type,payload_bytes,is_valid)
    Returns is_valid=False if the packet is truncated or fails CRC32 check.
    """
    if len(raw_bytes)<HEADER_SIZE:
        return None,None,b"",False
    header_bytes=raw_bytes[:HEADER_SIZE]
    payload_bytes=raw_bytes[HEADER_SIZE:]

    seq_num,pkt_type,payload_len,received_crc =struct.unpack(HEADER_FORMAT,header_bytes)

    #Verify declared length matches actual payload length
    if len(payload_bytes) != payload_len:
        return seq_num,pkt_type,payload_bytes,False
    
    #Recomputation of CRC32 with checksum zeroed out and comparing.
    verify_header=struct.pack(HEADER_FORMAT,seq_num,pkt_type,payload_len,0)
    calculated_crc =zlib.crc32(verify_header+payload_bytes)&0xFFFFFFFF

    is_valid=(received_crc ==calculated_crc)
    return seq_num,pkt_type,payload_bytes,is_valid
