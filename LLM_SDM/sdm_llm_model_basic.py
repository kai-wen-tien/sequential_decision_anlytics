# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
Make sure the execution directory to the same folder.

"""
# %%
OPENAI_API_KEY = "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"
FOLDER_PATH = "G:/My Drive/00_Temp Workspace/250622_研究_LLM_SDM"
from openai import OpenAI
import csv
client = OpenAI(api_key=OPENAI_API_KEY)

def load_market_data():
    second_column = []
    with open(FOLDER_PATH + "/market price.csv", newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            second_column.append(float(row[1]))  # Get the 2nd column (index 1)
    
    return second_column

class MetaPolicy():
    
    def generate_task(self, history, base_policy_code):
        battery_level_record = [h['battery_level_record'] for h in history]
        action_record = [h['action_record'] for h in history]
        cost_per_time_record = [h['cost_per_time_record'] for h in history]
        total_cost_record = [h['total_cost'] for h in history]
        # Analyze last result, return new task prompt
        with open(FOLDER_PATH + "/task_generator.txt", "r", encoding="utf-8") as f:
            task_generator = f.read()
            task_generator = task_generator.format(code = base_policy_code,
                                                   battery_level_record = battery_level_record, 
                                                   action_record = action_record, 
                                                   cost_per_time_record = cost_per_time_record,
                                                   total_cost = 'None' if not total_cost_record else total_cost_record[-1], 
                                                   total_cost_record = total_cost_record)
            task_description = client.responses.create(
                model = "gpt-4.1",
                input = task_generator
            )
            return task_description.output_text
        
    def generate_base_policy_code(self, task_description):
        # Send prompt to OpenAI to get code
        with open(FOLDER_PATH + "/Policy.py", "r", encoding="utf-8") as f:
            policy_signature = f.read()
            
        with open(FOLDER_PATH + "/code_generator.txt", "r", encoding="utf-8") as f:
            code_generator = f.read()
            code_generator = code_generator.format(policy_signature = policy_signature, 
                                                   task_description = task_description)       
            base_policy_code = client.responses.create(
                model = "gpt-4.1",
                input = code_generator
            )
            return base_policy_code.output_text
    
    def correct_code(self, failed_code, error_message):
        with open(FOLDER_PATH + "/Policy.py", "r", encoding="utf-8") as f:
            policy_signature = f.read()

        with open(FOLDER_PATH + "/error_corrector.txt", "r", encoding="utf-8") as f:
            corrector_prompt = f.read().format(
                error_message = error_message,
                code = failed_code,
                policy_signature = policy_signature
            )
        
        corrected_code = client.responses.create(
            model = "gpt-4.1", 
            input = corrector_prompt
            )
        return corrected_code
        
class BasePolicyExecutor():
    def __init__(self, code_text):
        self.namespace = {}   #isolate the variables
        exec(code_text, self.namespace)
    def take_action(self,  state_of_charge, market_price, cost):
        temp_policy = self.namespace['Policy'](0, market_price, cost)
        return temp_policy.take_action(state_of_charge, 0, market_price, cost) ## check imported energy

class EnergySystemSimulator():
    def __init__(self):
        self.state_of_charge = 50
        self.price = load_market_data()
        
    def run(self, controller, start_index, end_index):
        cost = 0
        soc_record = []
        action_record = []
        cost_per_time_record = []

        
        for t in range(end_index - start_index + 1):
            price = self.price[t]
            demand = 5              # constant demand per time step

            # controller suggests how much to draw from battery or buy
            # action = controller.take_action(self.state_of_charge, price, cost)
            action = 5
            
            # total supply = battery discharge + market buy
            battery_contrib = min(max(-action, 0), self.state_of_charge)
            market_contrib = max(action, 0)     # buy only when action > 0
            total_supply = battery_contrib + market_contrib
            
            # ensure demand is met (for realism)
            if total_supply < demand:
                # buy the rest from market
                deficit = demand - total_supply
                market_contrib += deficit
                total_supply = demand
                cost += price*deficit
            
            # update battery state of charge
            self.state_of_charge = max(0, min(100, 
                                              self.state_of_charge 
                                              - battery_contrib
                                              + market_contrib))
            
            cost_per_time = price * market_contrib #pay only when buying
            cost += cost_per_time
            
            soc_record.append(self.state_of_charge)
            action_record.append(action)
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

with open(FOLDER_PATH + "/Policy0.py", "r", encoding="utf-8") as f:
    base_policy_code = f.read()

# Planning horizon
NUM_META_ITERATIONS = 10
TIME_PER_META = 15

for i in range(NUM_META_ITERATIONS):
    print(f"\n--- Meta Interation {i+1} ---")
    
    #Step 1: Generate or update task (prompt) using meta-policy
    task_prompt = meta_policy.generate_task(history, base_policy_code)
    print('task prompt generated...')
    
    #Step 2: Generate new base-policy (controller code)
    base_policy_code = meta_policy.generate_base_policy_code(task_prompt)
    print('base policy code generated...')
    try:
        controller = BasePolicyExecutor(base_policy_code)
    except Exception as e:
        print(f"[ERROR] BasePolicy Executor filed: {e}")
        
        # Apply error correction here
        base_policy_code = meta_policy.correct_code(base_policy_code, str(e))
        
        # Retry
        controller = BasePolicyExecutor(base_policy_code)
        print('base policy code generated...')
    
    #Step 3: Simulate the controller in the enviroment
    result = simulator.run(controller, i, i*TIME_PER_META + TIME_PER_META - 1)
    print('simulation finished...')
    
    #Step 4: Collect performance
    history.append(result)
    
    
    
    
    
    
    
    
    
    
    
    


