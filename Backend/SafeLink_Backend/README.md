# SafeLink Backend

Backend components for detecting ARP spoofing attempts using a hybrid DFA and ANN pipeline.

## Structure

- `main.py`: Application bootstrap and lifecycle management
- `config/`: Static configuration values and logging setup
- `core/`: Detection modules (packet sniffer, DFA engine, ANN classifier, alerting)
- `models/`: Stored machine learning assets and training notebook
- `data/`: Datasets and SQLite storage artifacts
- `logs/`: Runtime and alert logs
- `tests/`: Unit tests covering each major module

## Getting Started

1. Create and activate a Python 3.11 virtual environment.
2. Install dependencies using `pip install -r requirements.txt`.
3. Configure `config/settings.py` for your network interface and storage preferences.
4. Run `python main.py` to start the backend service (implementation pending).

## Testing

Execute `pytest` from the repository root to run unit tests.
