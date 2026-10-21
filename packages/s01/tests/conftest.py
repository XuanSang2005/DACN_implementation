"""Select and observe the real simplejson encoder backend in each test process."""

import simplejson
import simplejson.encoder as encoder


def pytest_addoption(parser):
    parser.addoption("--encoder-backend", choices=("c", "python"), default="c")


def pytest_configure(config):
    mode = config.getoption("--encoder-backend")
    simplejson._toggle_speedups(mode == "c")
    if mode == "c" and encoder.c_make_encoder is None:
        raise RuntimeError("C encoder requested but unavailable; do not claim C coverage")
    counts = {"c": 0, "python": 0}
    if mode == "c":
        original = encoder.c_make_encoder

        def observed_c(*args, **kwargs):
            counts["c"] += 1
            return original(*args, **kwargs)

        encoder.c_make_encoder = observed_c
    original_python = encoder._make_iterencode

    def observed_python(*args, **kwargs):
        counts["python"] += 1
        return original_python(*args, **kwargs)

    encoder._make_iterencode = observed_python
    config.encoder_counts = counts


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.write_line(
        f"Observed real encoder factory calls: {config.encoder_counts}; "
        f"selected={config.getoption('--encoder-backend')}"
    )
