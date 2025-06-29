# -*- coding: utf-8 -*-
"""
Meta-Policy Optimization Framework for Battery Energy Management using LLMs

This script simulates an adaptive decision-making process in a simplified energy system 
where a controller manages battery charge/discharge actions based on electricity price data. 

Key features:
- Implements a hierarchical decision structure using a meta-policy and a base policy.
- Leverages Large Language Models (LLMs) to iteratively generate, evaluate, and refine base policies.
- Uses simulation feedback (e.g., battery state of charge, cost, action history) to guide improvements.
- Automatically handles code generation and correction for policy controllers via OpenAI API.
- Tracks performance improvement over iterations.

Usage Notes:
- Ensure that the working directory includes required prompt templates and price data files.
- Set `KEY_PATH` and `FOLDER_PATH` appropriately for your environment.
- Designed for research and experimentation in sequential decision-making and LLM planning.

Author: Kai-Wen Tien
Last Updated: 2025/06/29
"""
# %%

from openai import OpenAI
import csv

KEY_PATH = "G:/My Drive/00_Temp Workspace/250622_研究_LLM_SDM"
FOLDER_PATH = "C:/Users/USER/OneDrive/Documents/GitHub/sequential_decision_anlytics"
with open(KEY_PATH + "/OPENAI_API_KEY.txt", newline='', encoding='utf-8') as f:
    OPENAI_API_KEY = f.read()
    
client = OpenAI(api_key=OPENAI_API_KEY)

# loading all templates

def load_market_data():
    second_column = []
    with open(FOLDER_PATH + "/data/market_price.csv", newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            second_column.append(float(row[1]))  # Get the 2nd column (index 1)
    
    return second_column

class MetaPolicy():
    def __init__(self):
        # Load prompt templates from local files
        self.task_template = self._load_template("prompts/prompt_task_generator.txt")
        self.policy_signature = self._load_template("policies/policy_signature.py")
        self.code_template = self._load_template("prompts/prompt_code_generator.txt")
        self.corrector_template = self._load_template("prompts/prompt_error_corrector.txt")
        
    def _load_template(self, filename):
        with open(FOLDER_PATH + f"/{filename}", "r", encoding="utf-8") as f:
            return f.read()
    
    def generate_task(self, history, base_policy_code):
        battery_level_record = [h['battery_level_record'] for h in history]
        action_record = [h['action_record'] for h in history]
        cost_per_time_record = [h['cost_per_time_record'] for h in history]
        total_cost_record = [h['total_cost'] for h in history]
        
        # Analyze last result, return new task prompt
        task_generator = self.task_template.format(
            code = base_policy_code,
            battery_level_record = battery_level_record, 
            action_record = action_record, 
            cost_per_time_record = cost_per_time_record,
            total_cost = 'None' if not total_cost_record else total_cost_record[-1], 
            total_cost_record = total_cost_record
        )
        
        task_description = client.responses.create(
            model = "gpt-4.1-mini",
            input = task_generator
        )
        return task_description.output_text
        
    def generate_base_policy_code(self, task_description):
        # Send prompt to OpenAI to get code
        code_generator = self.code_template.format(
            policy_signature = self.policy_signature, 
            task_description = task_description
        )       
        
        base_policy_code = client.responses.create(
            model = "gpt-4.1-mini",
            input = code_generator
        )
        return base_policy_code.output_text
    
    def correct_code(self, failed_code, error_message):
        # correct the code
        corrector_prompt = self.corrector_template.format(
            error_message = error_message,
            code = failed_code,
            policy_signature = self.policy_signature
        )
        
        corrected_code = client.responses.create(
            model = "gpt-4.1-mini", 
            input = corrector_prompt
            )
        return corrected_code.output_text
        
class BasePolicyExecutor():
    def __init__(self, code_text):
        self.namespace = {}   #isolate the variables
        exec(code_text, self.namespace)
    def take_action(self,  state_of_charge, imported_energy, market_price, cost):
        temp_policy = self.namespace['Policy'](imported_energy, market_price=market_price, cost=cost)
        return temp_policy.take_action(state_of_charge, imported_energy, market_price, cost) ## check imported energy

class EnergySystemSimulator():
    def __init__(self):
        self.state_of_charge = 50
        self.price = load_market_data()
        self.demand = 5
    
    def reset(self):
        self.state_of_charge = 50
        
    def run(self, controller):
        cost = 0
        soc_record = []
        action_record = []
        cost_per_time_record = []
        imported_energy = 0
        
        for t in range(len(self.price)):
            price = self.price[t]
            demand = self.demand

            # controller suggests how much to draw from battery or buy
            action = controller.take_action(self.state_of_charge, imported_energy, price, cost)
            
            # clip actions (aoviding overcharge or overdischarge)
            # if trying to charge
            if action > 0:
                battery_charge = min(action, 100 - self.state_of_charge)
                battery_discharge = 0
            else:
                battery_discharge = min(-action, self.state_of_charge, demand)
                battery_charge = 0
    
            market_contrib = demand - battery_discharge + battery_charge
            imported_energy = market_contrib
    
            self.state_of_charge = self.state_of_charge - battery_discharge + battery_charge
            self.state_of_charge = max(0, min(100, self.state_of_charge))
    
            cost_per_time = price * market_contrib
            cost += cost_per_time
            
            soc_record.append(self.state_of_charge)
            action_record.append(battery_charge - battery_discharge) # record the real action
            cost_per_time_record.append(cost_per_time)
            
        return {'battery_level_record': soc_record, 
                'action_record': action_record,
                'cost_per_time_record': cost_per_time_record, 
                'total_cost': cost}
        

# %% the hierarchical decison structure

# initial setup
meta_policy = MetaPolicy()
simulator = EnergySystemSimulator()
history = []

#save the initial base policy (without battery)
with open(FOLDER_PATH + "/policies/baseline_policy.py", "r", encoding="utf-8") as f:
    base_policy_code = f.read()

controller = BasePolicyExecutor(base_policy_code)
result = simulator.run(controller)
history.append(result)

# Planning horizon
NUM_META_ITERATIONS = 10

for i in range(NUM_META_ITERATIONS):
    print(f"\n--- Meta Decision Loop {i+1} ---")
    
    simulator.reset()      #reset the simulator
    
    #Step 1: Generate or update task (prompt) using meta-policy
    task_prompt = meta_policy.generate_task(history, base_policy_code)
    print('task prompt generated...')
    
    #Step 2: Generate new base-policy (controller code)
    base_policy_code = meta_policy.generate_base_policy_code(task_prompt)
    print('base policy code generated...')
    #Step 3: Simulate the controller in the enviroment
    try:
        controller = BasePolicyExecutor(base_policy_code)
        result = simulator.run(controller)
    except Exception as e:
        print(f"[ERROR] BasePolicy Executor filed: {e}")
        
        # Apply error correction here
        base_policy_code = meta_policy.correct_code(base_policy_code, str(e))
        print('base policy code generated...')        
        
        # Retry
        controller = BasePolicyExecutor(base_policy_code)
        result = simulator.run(controller)
    
    print('simulation finished...')
    
    #Step 4: Collect performance
    history.append(result)
    
    
# %% plot the total costs
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

total_cost = [h['total_cost'] for h in history] 
improvement = [(total_cost[0] - tc)/total_cost[0] for tc in total_cost]

plt.plot(range(len(improvement)), improvement, marker='s')
plt.gca().yaxis.set_major_formatter(PercentFormatter(xmax=1.0))  # Format as percentage
plt.xlabel("Meta Iteration")
plt.ylabel("Improvement (%)")
plt.title("Cost Improvement over Meta-Iterations")
plt.grid(True)
plt.show()
   
    
    
    
    
    
    
    
    
    


