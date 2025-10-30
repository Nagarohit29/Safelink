import numpy as np
import pandas as pd
import time
from sklearn.preprocessing import StandardScaler
import pickle
from config import settings

SCALER_PATH = settings.MODELS_DIR / "scaler.pkl"

def load_dataset(csv_path):
    df = pd.read_csv(csv_path)
    return df

def prepare_features_and_labels(df, label_col="Label"):
    # Use numeric columns only as features
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    X = df[numeric_cols].fillna(0).astype(float).values
    y = df[label_col].astype(str).apply(lambda s: 1 if s.lower().strip().startswith("arp_spoof") or "spoof" in s.lower() else 0).values
    return X, y, numeric_cols

def get_or_train_scaler(X_train):
    if SCALER_PATH.exists():
        with open(SCALER_PATH, "rb") as f:
            scaler = pickle.load(f)
    else:
        scaler = StandardScaler()
        scaler.fit(X_train)
        with open(SCALER_PATH, "wb") as f:
            pickle.dump(scaler, f)
    return scaler

def scale_features(X, scaler):
    return scaler.transform(X)

def ip_to_int(ip_str):
    # Convert IPv4 string to int; if not IPv4, return 0
    try:
        parts = ip_str.split(".")
        parts = [int(p) for p in parts]
        val = 0
        for p in parts:
            val = (val << 8) + p
        return val
    except Exception:
        return 0

def mac_to_int(mac_str):
    # Convert MAC to int
    try:
        s = mac_str.replace(":", "").replace("-", "").lower()
        return int(s, 16)
    except Exception:
        return 0

# For live packet -> feature vector mapping
_last_seen = {}  # track last-time per source
_counter_window = {}  # track packet counts per source in window

def features_from_packet(pkt, numeric_columns):
    """
    Attempt to produce a numeric-vector compatible with the model features
    numeric_columns: list of column names used during training (order matters)
    This function maps available ARP or IP packet properties to those numeric columns.
    For fields we cannot compute, we place zeros.
    IMPORTANT: For production, adapt this mapping to match actual feature extraction used to create dataset.
    """
    vec = np.zeros(len(numeric_columns), dtype=float)
    # try to extract common numeric features if present
    now = time.time()
    src = None
    try:
        # ARP
        if pkt.haslayer("ARP"):
            arp = pkt.getlayer("ARP")
            opcode = int(arp.op)  # 1 request, 2 reply
            # Map some generic columns if present
            if "protocol" in numeric_columns:
                vec[numeric_columns.index("protocol")] = 0  # ARP protocol code placeholder
            if "src_port" in numeric_columns:
                vec[numeric_columns.index("src_port")] = 0
            # map opcode to a column if it exists
            for candidate in ["arp_opcode", "opcode", "arp_op"]:
                if candidate in numeric_columns:
                    vec[numeric_columns.index(candidate)] = opcode
            src = arp.psrc if hasattr(arp, "psrc") else None
            src_mac = arp.hwsrc if hasattr(arp, "hwsrc") else None
        # IP packet fallback
        elif pkt.haslayer("IP"):
            ip = pkt.getlayer("IP")
            src = ip.src
            if "protocol" in numeric_columns:
                vec[numeric_columns.index("protocol")] = int(ip.proto)
    except Exception:
        pass

    # inter-arrival and frequency
    if src:
        last = _last_seen.get(src, None)
        if last is None:
            inter = 0.0
        else:
            inter = now - last
        _last_seen[src] = now

        # sliding window count
        win = 1.0  # 1s window
        arr = _counter_window.get(src, [])
        arr = [t for t in arr if now - t <= win]
        arr.append(now)
        _counter_window[src] = arr
        freq = len(arr) / (win if win>0 else 1)

        # place into numeric fields if exist
        for c in ["bidirectional_packets", "bidirectional_bytes", "src2dst_packets"]:
            if c in numeric_columns:
                vec[numeric_columns.index(c)] = freq

    return vec
