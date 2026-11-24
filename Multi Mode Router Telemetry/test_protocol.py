#This file will verify that struct packing, length checks and bit-corruption checks behave reliably under edge cases.
import unittest
from protocol import (
    pack_packet,
    unpack_packet,
    PKT_ACK,
    PKT_DATA,
    PKT_FIN,
    HEADER_SIZE
)

class TestBinaryProtocol(unittest.TestCase):
    def test_valid_data_packet_roundtrip(self):
        payload=b"Telemetry payload 12345"
        raw=pack_packet(seq_num=42,pkt_type=PKT_DATA,payload_bytes=payload)
        self.assertEqual(len(raw),HEADER_SIZE+len(payload))

        seq,ptype,unpacked_payload,is_valid=unpack_packet(raw)
        self.assertTrue(is_valid)
        self.assertEqual(seq,42)
        self.assertEqual(ptype,PKT_DATA)
        self.assertEqual(unpacked_payload,payload)

    def test_empty_ack_and_fin_packets(self):
        for ptype in (PKT_ACK,PKT_FIN):
            raw=pack_packet(seq_num=7,pkt_type=ptype)
            seq,unpacked_type,payload,is_valid=unpack_packet(raw)
            self.assertTrue(is_valid)
            self.assertEqual(seq,7)
            self.assertEqual(unpacked_type,ptype)
            self.assertEqual(payload,b"")

    def test_single_bit_flip_detected_by_crc32(self):
        raw=bytearray(pack_packet(seq_num=10,pkt_type=PKT_DATA,payload_bytes=b"Critical frame"))
        #Flip one bit in the last byte of the payload.
        raw[-1]^=0x01
        _,_,_,is_valid=unpack_packet(bytes(raw))
        self.assertFalse(is_valid)

    def test_header_bit_flip_detected_by_crc32(self):
        raw=bytearray(pack_packet(seq_num=10,pkt_type=PKT_DATA,payload_bytes=b"Critical Frame"))
        #Flip 1 bit inside the sequence number field (byte3)
        raw[3]^=0x01
        _,_,_,is_valid=unpack_packet(bytes(raw))
        self.assertFalse(is_valid)

    def test_truncated_packet_rejected(self):
        raw=pack_packet(seq_num=1,pkt_type=PKT_DATA,payload_bytes=b"Hello")
        _,_,_,is_valid=unpack_packet(raw[:-2])
        self.assertFalse(is_valid)

if __name__=="__main__":
    unittest.main(verbosity=2)