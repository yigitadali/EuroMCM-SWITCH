# EuroMCM 2026 - SWITCH (Problem λ)

This repository contains our team's solution and modeling study for the EuroMCM 2026 Lambda Problem. We built a simulation tool named **SWITCH** to analyze and optimize adaptive LLM routing techniques, focusing on accuracy, compute costs, and carbon scenarios.

## Project Structure

* `simulate_switch.py` - Core simulation logic for the routing mechanism.
* `data/` - Benchmark datasets (Mixtral/GPT-4 GSM8K samples used for validation).
* `scripts/reproduce.py` - Script to rerun experiments and verify results.
* `figures/ & results/` - Generated plots and data outputs from the test runs.

## Prerequisites & Installation
The project requires Python 3.9

1. Clone the repository and navigate inside:
   ```bash
   git clone https://github.com
   cd EuroMCM-2026-SWITCH
   ```

2. Setup virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## How to Run

To execute the core simulation and verify the baseline results, run:

```bash
python3 scripts/reproduce.py --verify
```

The `--verify` flag checks the generated output files against our committed results to ensure reproducibility. Yo
