import asyncio
import serial
import serial_asyncio
import bitarray as ba
import bitarray.util as bau




class SBUSReceiver:
    
    class SBUSFramer(asyncio.Protocol):
		
        START_BYTE = 0xf8
        #END_BYTE = 0x00
        SBUS_FRAME_LEN = 25

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
            #print("longueur : ",long)
            #print("data : ",data)
            data_int = int.from_bytes(data, byteorder="big")
            data_bin_b = bin(data_int)[2::]
            #print (data_bin_b)
            for b in data:
                if self._in_frame:
                    self._frame.append(b)
                    if len(self._frame) == SBUSReceiver.SBUSFramer.SBUS_FRAME_LEN:
                        #decoded_frame = SBUSReceiver.SBUSFrame(self._frame)
                        print("longueur :", len(self._frame))
                        print("frame complétée : ", self._frame)
                        #asyncio.run_coroutine_threadsafe(self.frames.put(decoded_frame), asyncio.get_running_loop())
                        self._in_frame = False
                else:
                    if b == SBUSReceiver.SBUSFramer.START_BYTE:
                        self._in_frame = True
                        self._frame.clear()
                        self._frame.append(b)


    class SBUSFrame:
        OUT_OF_SYNC_THD = 10
        SBUS_NUM_CHANNELS = 16
        SBUS_SIGNAL_OK = 0
        SBUS_SIGNAL_LOST = 1
        SBUS_SIGNAL_FAILSAFE = 2
	
        def get_rx_channels(self):
            return self.sbusChannels

        def get_rx_channel(self, num_ch):
            return self.sbusChannels[num_ch]

        def get_failsafe_status(self):
            return self.failSafeStatus
        
        def __init__(self, frame):
            self.sbusChannels = [None] * SBUSReceiver.SBUSFrame.SBUS_NUM_CHANNELS
            print ("frame transférée:", frame)
            channel_sum = int.from_bytes(frame[0:23], byteorder="little")
            #print (channel_sum)

            #for ch in range(0, SBUSReceiver.SBUSFrame.SBUS_NUM_CHANNELS):
                #self.sbusChannels[ch] = channel_sum & 0x7ff
                #channel_sum = channel_sum >> 12
            # Failsafe
            self.failSafeStatus = SBUSReceiver.SBUSFrame.SBUS_SIGNAL_OK
            if (frame[SBUSReceiver.SBUSFramer.SBUS_FRAME_LEN - 2]) & (1 << 2):
                self.failSafeStatus = SBUSReceiver.SBUSFrame.SBUS_SIGNAL_LOST
            if (frame[SBUSReceiver.SBUSFramer.SBUS_FRAME_LEN - 2]) & (1 << 3):
                self.failSafeStatus = SBUSReceiver.SBUSFrame.SBUS_SIGNAL_FAILSAFE
                
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
            #parity=serial.PARITY_ODD,
            #stopbits=serial.STOPBITS_ONE,
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
