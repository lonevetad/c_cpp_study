import csv
import io
import json
from pathlib import Path
from typing import Any, Union

from .output_channel import OutputChannel


class FileOutputChannel(OutputChannel):
    """Output channel that writes JSON or CSV lines to a file or stream.

    Parameters
    ----------
    path_or_stream:
        A file path (``str`` or :class:`pathlib.Path`) opened in append mode,
        or an already-open text stream.  When a path is given this channel
        owns the stream and closes it in :meth:`close`.
    format:
        ``"json"`` (default) writes ``{"name": …, "payload": …}\\n`` per call.
        ``"csv"`` writes ``name,payload\\n`` per call.
    """

    def __init__(
        self,
        path_or_stream: Union[str, Path, io.IOBase],
        format: str = "json",
    ) -> None:
        self._format = format.lower()
        if isinstance(path_or_stream, (str, Path)):
            self._stream = open(path_or_stream, "a")
            self._owns_stream = True
        else:
            self._stream = path_or_stream
            self._owns_stream = False
        if self._format == "csv":
            self._csv_writer = csv.writer(self._stream)
        else:
            self._csv_writer = None

    def send(self, name: str, payload: Any) -> None:
        if self._format == "json":
            self._stream.write(
                json.dumps({"name": name, "payload": payload}) + "\n"
            )
        else:
            self._csv_writer.writerow([name, payload])
        self._stream.flush()

    def close(self) -> None:
        if self._owns_stream:
            self._stream.close()

    def clone(self) -> "FileOutputChannel":
        c = FileOutputChannel.__new__(FileOutputChannel)
        c._format = self._format
        c._stream = self._stream
        c._owns_stream = False  # clone never owns the stream
        c._csv_writer = csv.writer(c._stream) if c._format == "csv" else None
        return c
