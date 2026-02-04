# Wraps DBC load and registers decoder into runtime
from app.core.decoder.dbc_decoder import DbcDecoder

def import_dbc(runtime, dbc_path: str):
    dec = DbcDecoder(dbc_path)
    runtime.decoders.insert(0, dec)
