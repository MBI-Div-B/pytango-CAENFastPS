from .CAENFastPS import CAENFastPS


def main():
    import sys
    import tango.server

    args = ["CAENFastPS"] + sys.argv[1:]
    tango.server.run((CAENFastPS,), args=args)
