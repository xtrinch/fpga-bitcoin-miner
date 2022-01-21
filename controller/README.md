# Mining controller

This is the part that connects to the pool and gives work to the miner.

It supports the following scenarios:

```
Miner (V2) ----> pool (V2)
```

# Running

Create virtualenv with `python3 -m venv env`.
Run `source env/bin/activate`.
Run `pip install -r requirements.txt`.

Run pool with `python3 simulate-pool.py` and miner with `python3 mine.py`.

# Overview

The protocol used is **Stratum V2**. The basis for this repository is https://github.com/braiins/braiins/tree/bos-devel/open/protocols/stratum/sim.

# Features

- pool rejects stale shares since it simulates finding new blocks
- miners simulate finding shares based exponential distribution
- plot results of series of simulations


## Install

Requires Python 3.7.