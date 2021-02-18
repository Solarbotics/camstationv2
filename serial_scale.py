#From https://github.com/zmitchell/async-serial/blob/master/async_serial_protocol.py

import asyncio
import serial_asyncio


class Reader(asyncio.Protocol):
    def connection_made(self, transport):
        """Store the serial transport and prepare to receive data.
        """
        self.transport = transport
        self.buf = bytes()
        self.msgs_recvd = 0
        print('Reader connection created')

    def data_received(self, data):
        """Store characters until a 'kg' is received.
        """
        self.buf += data
        if b'kg,\r' in self.buf:
            # print(self.buf)
            if b'Readings:' in self.buf: # Reset the buffer to zero for the post-boot message filtering
                self.buf = b'0.000,kg\r\n'
                print('gotcha')

            lines = self.buf.split(b'\n')
            #lines = self.buf.split(b',')
            self.buf = lines[-1]  # whatever was left over

            # print('selfbuf:',self.buf)
            # for line in lines[:-1]:
            #     print(f'Reader received: {line.decode()}')
            #     self.msgs_recvd += 1
            print('Lines:',lines)
            print("Reader:",lines[0].decode('ascii').split(',')[0])
        if self.msgs_recvd == 8:
            self.transport.close()

    def connection_lost(self, exc):
        print('Reader closed')


class Writer(asyncio.Protocol):
    def connection_made(self, transport):
        """Store the serial transport and schedule the task to send data.
        """
        self.transport = transport
        print('Writer connection created')
        asyncio.ensure_future(self.send())
        print('Writer.send() scheduled')

    def connection_lost(self, exc):
        print('Writer closed')

    async def send(self):
        """Send four newline-terminated messages, one byte at a time.
        """
        message = b'r\n'
        for b in message:
            await asyncio.sleep(0.5)
            self.transport.serial.write(bytes([b]))
            print(f'Writer sent: {bytes([b])}')
        self.transport.close()


loop = asyncio.get_event_loop()
# reader = serial_asyncio.create_serial_connection(loop, Reader, 'reader', baudrate=9600)
# writer = serial_asyncio.create_serial_connection(loop, Writer, 'writer', baudrate=9600)
reader = serial_asyncio.create_serial_connection(loop, Reader, '/dev/ttyUSB0', baudrate=9600)
# writer = serial_asyncio.create_serial_connection(loop, Writer, '/dev/ttyUSB0', baudrate=9600)
asyncio.ensure_future(reader)
print('Reader scheduled')
# asyncio.ensure_future(writer)
print('Writer scheduled')
loop.call_later(10, loop.stop)
loop.run_forever()
print('Done')