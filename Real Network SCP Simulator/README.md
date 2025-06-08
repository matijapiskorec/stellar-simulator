# Stellar Consensus Protocol (SCP) simulator

Implementation of Stellar Consensus Protocol (SCP) simulator using Gillespie algorithm. Stellar uses Federated Byzantine Agreement (FBA) to reach consensus.

Install Python virtual environment:
```
python3 -m venv env/stellar
source env/stellar/bin/activate
pip install -r requirements.txt
```

Or you can run it with Docker file:
```
docker-compose up -d --build
docker-compose exec stellar bash
```

There is also a Makefile which makes it easier to manage Docker, with few targets `build`, `start`, `bash`, `ls`, `kill`, `simulator` and `test`.

All output is through Python's logging to standard error, so if you want to pipe the output (for example, to a file) you need:
```
python src/simulator.py > output.txt 2>&1
```

## Bibliography

[1] David Maziers, The Stellar Consensus Protocol: A Federated Model for Internet-level Consensus, https://www.stellar.org/papers/stellar-consensus-protocol

[2] Nicolas Barry and Giuliano Losa and David Mazieres and Jed McCaleb and Stanislas Polu, The Stellar Consensus Protocol (SCP) - technical implementation draft, https://datatracker.ietf.org/doc/draft-mazieres-dinrg-scp/05/
