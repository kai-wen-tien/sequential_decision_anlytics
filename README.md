# Sequential Decision Anlytics
## Introduction
Meta-Policy Optimization Framework for Battery Energy Management using LLMs

This script simulates an adaptive decision-making process in a simplified energy system 
where a controller manages battery charge/discharge actions based on electricity price data. 

**Key features:**
- Implements a hierarchical decision structure using a meta-policy and a base policy.
- Leverages Large Language Models (LLMs) to iteratively generate, evaluate, and refine base policies.
- Uses simulation feedback (e.g., battery state of charge, cost, action history) to guide improvements.
- Automatically handles code generation and correction for policy controllers via OpenAI API.
- Tracks performance improvement over iterations.

**Usage Notes:**
- Ensure that the working directory includes required prompt templates and price data files.
- Set `KEY_PATH` and `FOLDER_PATH` appropriately for your environment.
- Designed for research and experimentation in sequential decision-making and LLM planning.
