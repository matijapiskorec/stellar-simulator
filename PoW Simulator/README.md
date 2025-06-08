# Proof-of-Work (PoW) simulator

Implementation of Proof-of-Work (PoW) simulator using Gillespie algorithm.

Install Python virtual environment:
```
python3 -m venv env/stellar
source env/stellar/bin/activate
pip install -r requirements.txt
```

Or you can run it with Docker file:
```
docker-compose up -d --build
docker-compose exec pow bash
```

There is also a Makefile which makes it easier to manage Docker, with few targets `build`, `start`, `bash`, `ls`, `kill`, `simulator` and `test`.

All output is through Python's logging to standard error, so if you want to pipe the output (for example, to a file) you need:
```
python src/simulator.py > output.txt 2>&1
```

## Bibliography

[1] Satoshi Nakamoto, Bitcoin: A Peer-to-Peer Electronic Cash System, https://bitcoin.org/bitcoin.pdf
