import signal
import time
from pathlib import Path


output_path = Path(str(snakemake.output[0]))
signal_path = output_path.with_suffix(output_path.suffix + ".signal")
signal_received = False


def handle_signal(signum, _frame):
    global signal_received
    signal_received = True
    signal_path.write_text(f"{signal.Signals(signum).name}\n")


signal.signal(signal.SIGUSR1, handle_signal)

for _ in range(45):
    time.sleep(1)

status = "python-finished-with-signal\n" if signal_received else "python-finished\n"
output_path.write_text(status)