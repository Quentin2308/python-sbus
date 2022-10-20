#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Based on:
	Sokrates80/sbus_driver_micropython git hub
	https://os.mbed.com/users/Digixx/code/SBUS-Library_16channel/file/83e415034198/FutabaSBUS/FutabaSBUS.cpp/
	https://os.mbed.com/users/Digixx/notebook/futaba-s-bus-controlled-by-mbed/
	https://www.ordinoscope.net/index.php/Electronique/Protocoles/SBUS
"""

import asyncio
#from periphery import Serial
import serial
import serial_asyncio


import bitarray as ba
import bitarray.util as bau
#used to check packets for validity
_UART_FRAME_CONFORMANCE_BITMASK = ba.bitarray('100000000011')
#used to check failsafe status
_FAILSAFE_STATUS_BITMASK = ba.bitarray('000000001100')
#_PACKET_LENGTH = 298
_UART_FRAME_LENGTH = 12

class SBUSReceiver:
    class SBUSFramer(asyncio.Protocol):

        START_BYTE = 0x00
        END_BYTE = 0xf8
        SBUS_FRAME_LEN = 22
        #SBUS_FRAME_LEN = 22
	#\xf8.\x00

        def __init__(self):
            super().__init__()
            self._in_frame = False
            self.transport = None
            self._frame = bytearray()
            self.frames = asyncio.Queue()

        def connection_made(self, transport):
            self.transport = transport

        def data_received(self, data):
            long = len(data)
            #print(long)
            #print(data)
            channel_data = ba.bitarray(long*12)
            channel_data.setall(0)
            channel_data_ptr = 0

            data_int = int.from_bytes(data, byteorder="big")
            data_bin_b = bin(data_int)[2::]
            #print (data_bin_b)
            data_bin_12 = ba.bitarray(data_bin_b)
            #print ("data_bin_12 : ", data_bin_12)
            for packet_data in range (0,12+25*12,12):
                channel_data[channel_data_ptr:channel_data_ptr+8]=data_bin_12[packet_data+1:packet_data+9]
                channel_data_ptr += 8
            print ("Channel data : ", channel_data) 
            channel_data_hex = []
            for i,ch in enumerate(channel_data) :
                channel_data_hex.append(ch[0:7])
            print ("Channel data hex : ", channel_data_hex)
            for b in channel_data:
                if self._in_frame:
                    self._frame.append(b)
                    if len(self._frame) == SBUSReceiver.SBUSFramer.SBUS_FRAME_LEN:
                        decoded_frame = SBUSReceiver.SBUSFrame(self._frame)
                        print(decoded_frame)
                        asyncio.run_coroutine_threadsafe(self.frames.put(decoded_frame), asyncio.get_running_loop())
                        self._in_frame = False
                else:
                    if b == SBUSReceiver.SBUSFramer.START_BYTE:
                        self._in_frame = True
                        self._frame.clear()
                        #self._frame.append(b)

        def connection_lost(self, exc):
            asyncio.get_event_loop().stop()

    class SBUSFrame:
        OUT_OF_SYNC_THD = 10
        SBUS_NUM_CHANNELS = 16
        SBUS_SIGNAL_OK = 0
        SBUS_SIGNAL_LOST = 1
        SBUS_SIGNAL_FAILSAFE = 2

        def __init__(self, frame):
            self.sbusChannels = [None] * SBUSReceiver.SBUSFrame.SBUS_NUM_CHANNELS
            channel_bits = ba.bitarray(176) #holds the bits of the 16 11-bit channel values
            #print(channel_bits)
            channel_bits.setall(0)
            #print(channel_bits)
            channel_bits_ptr = 0
            toto3 = frame[0:23]
            #print (toto3)
            toto4 = int.from_bytes(toto3, byteorder="big") 
            #print (toto4)
            toto5 = bin(toto4)[2::]
            #print (toto5)
            #print (len(toto5))
            toto6 = ba.bitarray(toto5)
            #print (toto6)
            #print (len(toto6))
		
            for packet_bits_ptr in range (0,_UART_FRAME_LENGTH+22*_UART_FRAME_LENGTH,_UART_FRAME_LENGTH):
                #extract from UART frame and invert each byte
                #print (toto6[packet_bits_ptr+1:packet_bits_ptr+9])
                channel_bits[channel_bits_ptr:channel_bits_ptr+8]=~toto6[packet_bits_ptr:packet_bits_ptr+8]
                #print (channel_bits[channel_bits_ptr:channel_bits_ptr+8])
                #print (channel_bits)
                channel_bits_ptr += 8
            ret_list = []
            #print (channel_bits)
            #print (len(channel_bits))

            for channel_ptr in range(0,16*11,11):
                #iterate through 11-bit numbers, converting them to ints. Note little endian.
                ret_list.append(bau.ba2int(ba.bitarray(channel_bits[channel_ptr:channel_ptr+11],endian='little')))
            #print (ret_list[4::])

            # Failsafe
            self.failSafeStatus = SBUSReceiver.SBUSFrame.SBUS_SIGNAL_OK
            if (frame[SBUSReceiver.SBUSFramer.SBUS_FRAME_LEN - 2]) & (1 << 2):
                self.failSafeStatus = SBUSReceiver.SBUSFrame.SBUS_SIGNAL_LOST
            if (frame[SBUSReceiver.SBUSFramer.SBUS_FRAME_LEN - 2]) & (1 << 3):
                self.failSafeStatus = SBUSReceiver.SBUSFrame.SBUS_SIGNAL_FAILSAFE

        def get_rx_channels(self):
            """
            Used to retrieve the last SBUS channels values reading
            :return:  an array of 18 unsigned short elements containing 16 standard channel values + 2 digitals (ch 17 and 18)
            """

            return self.sbusChannels

        def get_rx_channel(self, num_ch):
            """
            Used to retrieve the last SBUS channel value reading for a specific channel
            :param: num_ch: the channel which to retrieve the value for
            :return:  a short value containing
            """

            return self.sbusChannels[num_ch]

        def get_failsafe_status(self):
            """
            Used to retrieve the last FAILSAFE status
            :return:  a short value containing
            """

            return self.failSafeStatus

        def __repr__(self):
            #return ",".join(str(ch) for ch in self.sbusChannels)
            toto=""
            for i,ch in enumerate(self.sbusChannels):
            	#if i != 1 and i != 2 and i != 3:
            		#toto += str(ch) + "	"
            	toto += str(ch) + "	"
            return toto
            
    def __init__(self):
        self._transport = None
        self._protocol = None

    @staticmethod
    async def create(port='/dev/ttyS1'):
        receiver = SBUSReceiver()
        receiver._transport, receiver._protocol = await serial_asyncio.create_serial_connection(
            asyncio.get_running_loop(),
            SBUSReceiver.SBUSFramer,
            port,
            baudrate=100000)#,
            #parity=serial.PARITY_EVEN,
            #stopbits=serial.STOPBITS_TWO,
            #bytesize=serial.EIGHTBITS)
        return receiver
	
    async def get_frame(self):
        return await self._protocol.frames.get()


async def main():
    sbus = await SBUSReceiver.create("/dev/ttyS1")
    while True:
        frame = await sbus.get_frame()
        #print(frame)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
    loop.close()
