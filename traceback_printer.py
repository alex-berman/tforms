import traceback, sys

def print_traceback():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    print >> sys.stderr, "".join(
        traceback.format_exception(exc_type, exc_value, exc_traceback))
