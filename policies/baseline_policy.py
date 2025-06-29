class Policy:
    def __init__(self, imported_energy, market_price, cost):
        """
        Initialize policy parameters and state variables.
        Parameters:
        - imported_energy (float): Total energy imported so far [kWh]
        - market_price (float): Current or average market price [€/kWh]
        - cost (float): Accumulated energy cost [€]
        """
        self.imported_energy = imported_energy
        self.market_price = market_price
        self.cost = cost

    def take_action(
        self,
        state_of_charge: float,      # Current battery charge [kWh]
        imported_energy: float,      # Current energy import [kWh]
        market_price: float,         # Current market price [€/kWh]
        cost: float                  # Current total cost [€]
    ) -> float:
        """
        Determine optimal energy trading action based on current state.

        Returns:
        float: Action for battery [kWh]
               Positive → charge
               Negative → discharge
        """
        action = 0 # no battary, just buy from market
        
        return action