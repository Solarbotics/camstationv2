import serial, time, threading

class Scale:

    def __init__(self, port, limiters=True):
        self.scale = serial.Serial(port=port, baudrate=9600, timeout=1)
        self.weight = 0
        self.Ready = False
        self.limiters = limiters
        self.__exit__ = False
        self.__stop__ = False
        self.__done__ = True
        tf = threading.Thread(target=self.__Run__, daemon=True)
        tf.start()
        print("init Tare")
        self.Tare()

    def __Run__(self):
        print("Connecting to scale\n")
        self.scale.flush()
        while self.__stop__ == False:
            try:
                raw = self.scale.readline()
                data = raw.decode()
                if ",lbs" in data or ",kg" in data:
                    self.Ready = True
                    self.weight = float(data.split(",")[0])
                    if self.weight < 0.05 and self.limiters:
                        self.weight = 0
                else:
                    
                    if "Exiting" in data:
                        self.__exit__ = True
                    if len(data) > 4:
                        print(data.replace("\r", "").replace("\n", ""))
                        self.__done__ = False
                    else:
                        if '>' in data:
                            self.__done__ = True

            except Exception as e:
                print(raw, data, e)
                pass

    def Stop(self):
        """Use this to close the thread running the scale"""
        self.__stop__ = True

    def AutoMenu(self, *args):
        """Write your controls so you can programmatically use the menu. AutoMenu('3', '1')"""
        print("AutoDef")
        while self.Ready == False:
            time.sleep(0.1)
        time.sleep(1)
        self.scale.write("x".encode())
        time.sleep(1)
        for item in args:
            self.scale.write(str(item).encode())
            time.sleep(1)
            while self.__done__ == False:
                time.sleep(0.1)
        time.sleep(1)
        self.scale.write("x".encode())

    def InteractiveMenu(self):
        print("Imenu")
        """Use the menu in console"""

        while self.Ready == False:
            time.sleep(0.1)
        time.sleep(1)
        self.scale.write("x".encode())
        time.sleep(1)
        while self.__exit__ == False:
            self.scale.write(input("Option: ").encode())
            time.sleep(1)
            while self.__done__ == False:
                time.sleep(0.1)
        self.__exit__ == True
        time.sleep(0.5)

    def Tare(self):
        """Tare the scale without having to use the menus"""
        while self.Ready == False:
            time.sleep(0.1)
        print("Performing Auto Tare")
        time.sleep(1)
        self.scale.write("x".encode())
        time.sleep(1)
        self.scale.write("1".encode())
        time.sleep(3)
        while self.__done__ == False:
            time.sleep(0.1)
        self.scale.write("x".encode())
        time.sleep(1)

    def TargetWeight(self, weight, tolerance, timeout=-1):
        """Keeps running, yeilding current weight, until the weight is achieved"""
        while (self.weight < weight-tolerance or self.weight > weight+tolerance) and (timeout > 0 or timeout == -1):
            yield self.weight, weight - self.weight
            if timeout != -1:
                timeout = timeout - 0.5
            time.sleep(0.5)


