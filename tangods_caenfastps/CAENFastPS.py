#!/usr/bin/python3 -u
# coding: utf8
from tango import AttrWriteType, DevState, DispLevel, AttReqType
from tango.server import Device, attribute, command, device_property

import socket
from enum import IntEnum


class LoopMode(IntEnum):
    Current = 0
    Voltage = 1

class UpMode(IntEnum):
    ANALOG = 0
    NORMAL = 1
    WAVEFORM = 2

class CAENFastPS(Device):
    """CAENFastPS

    This controls a CAEN FastPS Power Supply

    """

    IPaddress = device_property(dtype=str)
    Port = device_property(dtype=int, default_value=10001)

    current = attribute(
        label="current",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        unit="A",
    )

    ramp_current = attribute(
        label="ramp current",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        unit="A/s",
        min_value=0,
    )

    voltage = attribute(
        label="voltage",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        unit="V",
    )

    ramp_voltage = attribute(
        label="ramp voltage",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        unit="V/s",
        min_value=0,
    )

    power = attribute(
        label="power",
        dtype=float,
        access=AttrWriteType.READ,
        unit="W",
    )

    loop_mode = attribute(
        label="loop mode",
        dtype=LoopMode,
        access=AttrWriteType.READ,
        doc="mode of the loop control, either constant voltage or constant current",
    )

    enabled = attribute(
        label="enabled",
        dtype=bool,
        access=AttrWriteType.READ,
    )

    ramping = attribute(
        label="ramping",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
    )

    fault = attribute(
        label="fault",
        dtype=bool,
        access=AttrWriteType.READ,
    )

    def init_device(self):
        super().init_device()
        try:
            self.info_stream(
                "Trying to connect to {:s}:{:d}".format(self.IPaddress, self.Port)
            )
            self.con = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP
            )
            self.con.connect((self.IPaddress, self.Port))
            self.con.settimeout(5)
            self.con.setblocking(True)
            idn = self.write_read("VER")
            self.info_stream("Connection established for {:s}".format(idn))
        except:
            self.error_stream("Error on initialization!")

        self.set_state(DevState.STANDBY)
        self.__ramping = False
        self.__waveform = []

    def delete_device(self):
        self.set_state(DevState.OFF)
        self.info_stream("A device was deleted!")

    def always_executed_hook(self):
        status = self.write_read("MST")
        number, pad, rjust, size, kind = int(status, 16), "0", ">", 32, "b"
        bin_status = f"{number:{pad}{rjust}{size}{kind}}"
        self.debug_stream(bin_status)
        self.__enabled = bool(int(bin_status[-1]))
        self.__isramping = bool(int(bin_status[-13]))
        if not self.__enabled:
            self.set_state(DevState.STANDBY)
        else:
            if self.__isramping:
                self.set_state(DevState.MOVING)
            else:
                self.set_state(DevState.ON)

        self.__fault = bool(int(bin_status[-2]))
        if self.__fault:
            self.set_state(DevState.FAULT)

        self.__loop_mode = int(bin_status[-6])

    def read_current(self):
        return float(self.write_read("MRI"))

    def write_current(self, value):
        if self.__ramping:
            self.write_read("MWIR:{:f}".format(value))
        else:
            self.write_read("MWI:{:f}".format(value))
    
    def is_current_allowed(self, req_type):
        if req_type == AttReqType.WRITE_REQ:
            return self.__enabled
        else:
            return True

    def read_ramp_current(self):
        return float(self.write_read("MSRI:?"))

    def write_ramp_current(self, value):
        self.write_read("MSRI:{:f}".format(value))

    def read_voltage(self):
        return float(self.write_read("MRV"))

    def write_voltage(self, value):
        if self.__ramping:
            self.write_read("MWVR:{:f}".format(value))
        else:
            self.write_read("MWV:{:f}".format(value))

    def is_voltage_allowed(self, req_type):
        if req_type == AttReqType.WRITE_REQ:
            return self.__enabled
        else:
            return True

    def read_ramp_voltage(self):
        return float(self.write_read("MSRV:?"))

    def write_ramp_voltage(self, value):
        self.write_read("MSRV:{:f}".format(value))

    def read_power(self):
        return float(self.write_read("MRW"))

    def read_loop_mode(self):
        return self.__loop_mode

    def read_enabled(self):
        return self.__enabled

    def read_ramping(self):
        return self.__ramping

    def write_ramping(self, value):
        self.__ramping = bool(value)

    def read_fault(self):
        return self.__fault
    
    @attribute(access=AttrWriteType.READ_WRITE)
    def update_mode(self) -> UpMode:
        ans = self.write_read("UPMODE:?")
        return UpMode[ans]
    
    @update_mode.setter
    def update_mode(self, mode: UpMode):
        mode_str = UpMode(mode).name
        self.write_read(f"UPMODE:{mode_str}")
    
    @attribute(access=AttrWriteType.READ_WRITE, max_dim_x=500_000)
    def waveform(self) -> list[float]:
        return self.__waveform

    @waveform.setter
    def waveform(self, wave: list[float]):
        if len(wave) >= 100:
            wave_str = ":".join([f"{value:.3f}" for value in wave])
            ans = self.write_read(f"WAVE:POINTS: {wave_str}")
            if ans == 0:
                self.__waveform = wave
    
    @waveform.is_allowed
    def waveform(self, req_type):
        if req_type == AttReqType.WRITE_REQ:
            return (not self.__fault) and (not self.__enabled)
        else:
            return True
    
    @attribute(access=AttrWriteType.READ_WRITE)
    def waveform_periods(self) -> int:
        ans = self.write_read("WAVE:N_PERIODS:?")
        return int(ans)
    
    @waveform_periods.setter
    def waveform_periods(self, num: int):
        return self.write_read("WAVE:N_PERIODS:{:d}".format(num))

    @command
    def enable(self):
        self.write_read("MON")

    @command
    def disable(self):
        self.write_read("MOFF")
        self.set_state(DevState.ON)

    @command
    def current_mode(self):
        self.write_read("LOOP:I")

    @command
    def voltage_mode(self):
        self.write_read("LOOP:V")

    @command
    def start_waveform(self) -> None:
        self.write_read("WAVE:START")
    
    @command
    def stop_waveform(self) -> None:
        self.write_read("WAVE:STOP")

    @command(dtype_in=str, doc_in="command", dtype_out=str, doc_out="response")
    def write_read(self, cmd):
        try:
            self.con.send("{:s}\r".format(cmd).encode("utf8"))
            ret = self.con.recv(1024).decode("utf8")
            while ret.find("\r\n") == -1:
                ret += self.con.recv(1024).decode("utf8")
        except socket.timeout:
            self.warning_stream("Socket timeout")
            return [-2, ""]
        except socket.error:
            self.error_stream("Socket error")
            return [-2, ""]
        # evaluate the response

        ret_cmd = "#{:s}:".format(cmd.rstrip(":?"))
        self.debug_stream("{:s} - {:s}".format(ret_cmd, ret))

        if "#AK" in ret:
            # write command acknowledged - nothing to return
            self.info_stream("write command acknowledged")
            return 0
        elif "#NAK" in ret:
            # write command not acknowledged - nothing to return
            msg = ret[5:].strip()
            self.warn_stream(
                "write command not acknowledged with error: {}".format(msg)
            )
            return -1
        elif ret_cmd in ret:
            # read command acknowledged - return value
            res = ret[len(ret_cmd): -2]
            return res
        else:
            i = ret.find(":")
            return ret[i + 1 : -2]


# start the server
if __name__ == "__main__":
    CAENFastPS.run_server()
