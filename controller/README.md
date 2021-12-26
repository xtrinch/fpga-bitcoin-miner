# Mining controller

This is the part that connects to the pool and gives work to the miner.

# Running

Create virtualenv with `python3 -m venv env`.
Run `source env/bin/activate`.
Run `pip install -r requirements.txt`.

Run pool with `python3 simulate-pool.py` and miner with `python3 mine.py`.

# Overview

The intention is to verify the design of **Stratum V2**. At the same time, the platform can serve as a testbed for various network latency scenarios.

Last but not least, the idea is to have a reference implementation of both protocols that serves the blueprint specification of the messages.


# Features

- test network latency issues
- complete definition of protocol messages
- pool rejects stale shares since it simulates finding new blocks
- miners simulate finding shares based exponential distribution
- plot results of series of simulations


## Install

Simulation requires Python 3.7.

The easiest way to run the simulation is to use python `virtualenvwrapper`


### The `virtualenvwrapper` way

```
mkvirtualenv --python=/usr/bin/python3.7 stratum-sim
pip install -r ./requirements.txt
```


# Future Work

The simulation is far from complete. Currently, it supports the following
 scenarios:

```
2xminer (V1) ----> pool (V1)
2xminer (V2) ----> pool (V2)
miner (V2) ----> proxy (translating) ---> pool (V1)
```


The current simulation output is very basic, and we know that it could be extended much further. Below are a few points that could be covered in future iterations:
- implement BDD scenarios using gherkin language to run a full set of simulation scenarios
- provide more advanced statistics with chart plotting
