import os
import queue
import signal
import sys
import threading
from threading import Timer

import yaml

from google_assistant import GoogleAssistant
from rotary_phone import RotaryDial
from ringtone import Ringtone

callback_queue = queue.Queue()


class TelephoneDaemon:
    # Number to be dialed
    dial_number = ""

    # On/off hook state
    offHook = False

    # Off hook timeout
    offHookTimeoutTimer = None

    RotaryDial = None

    config = None

    assistant = GoogleAssistant()

    def __init__(self):
        print("[STARTUP]")

        with open("configuration.yml", 'r') as f:
            self.config = yaml.load(f)

        signal.signal(signal.SIGINT, self.OnSignal)

        # Ring tone
        self.Ringtone = Ringtone(self.config)

        # This is to indicate boot complete. Not very realistic, but fun.
        self.Ringtone.playfile(self.config["soundfiles"]["startup"])

        # Rotary dial
        self.RotaryDial = RotaryDial()
        self.RotaryDial.RegisterCallback(NumberCallback=self.GotDigit, OffHookCallback=self.OffHook,
                                         OnHookCallback=self.OnHook, OnVerifyHook=self.OnVerifyHook)

    def OnHook(self):
        print("[PHONE] On hook")
        self.offHook = False
        self.Ringtone.stophandset()

    def OffHook(self):
        print("[PHONE] Off hook")
        self.offHook = True
        # Reset current number when off hook
        self.dial_number = ""

        self.offHookTimeoutTimer = Timer(5, self.OnOffHookTimeout)
        self.offHookTimeoutTimer.start()

        # TODO: State for ringing, don't play tone if ringing :P
        print("Try to start dialtone")
        self.Ringtone.starthandset(self.config["soundfiles"]["dialtone"])

        self.Ringtone.stop()

    def OnVerifyHook(self, state):
        if not state:
            self.offHook = False
            self.Ringtone.stophandset()

    def OnIncomingCall(self):
        print("[INCOMING]")
        self.Ringtone.start()

    def OnOutgoingCall(self):
        print("[OUTGOING] ")

    def OnRemoteHungupCall(self):
        print("[HUNGUP] Remote disconnected the call")
        # Now we want to play busy-tone..
        self.Ringtone.starthandset(self.config["soundfiles"]["busytone"])

    def OnSelfHungupCall(self):
        print("[HUNGUP] Local disconnected the call")

    def OnOffHookTimeout(self):
        print("[OFFHOOK TIMEOUT]")

        # TODO: Add "short circuit" to perform an action based on the number entered

        self.Ringtone.stophandset()
        self.Ringtone.starthandset(self.config["soundfiles"]["timeout"])

    def GotDigit(self, digit):
        print("[DIGIT] Got digit: %s" % digit)
        self.Ringtone.stophandset()
        self.dial_number += str(digit)
        print("[NUMBER] We have: %s" % self.dial_number)

        if self.dial_number == "0":
            self.assistant.assist()

        # TODO: Handle known "codes" for specific commands

        # Shutdown command, since our filesystem isn't read only (yet?)
        # This hopefully prevents dataloss.
        # TODO: stop rebooting..
        if self.dial_number == "0666":
            self.Ringtone.playfile(self.config["soundfiles"]["shutdown"])
            os.system("halt")

        if len(self.dial_number) == 8:
            if self.offHook:
                print("[PHONE] Dialing number: %s" % self.dial_number)
                self.dial_number = ""

    def OnSignal(self, signal, frame):
        print("[SIGNAL] Shutting down on %s" % signal)
        self.RotaryDial.StopVerifyHook()
        sys.exit(0)


def main():
    TDaemon = TelephoneDaemon()


if __name__ == "__main__":
    main()
