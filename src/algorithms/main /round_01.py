import json
from _dep.datamodel import OrderDepth, UserId, TradingState, Order, ProsperityEncoder


MM_SYMBOL = ["INTARIAN_PEPPER_ROOT", "ASH_COATED_OSMIUM"]
POS_LIMITS = {"INTARIAN_PEPPER_ROOT": 80, "ASH_COATED_OSMIUM": 80}


class Product:
    def __init__(self, name, state, new_trader_data) -> None:
        
        self.state = state
       
        self.name = name
        
        self.new_trader_data = new_trader_data
        self.last_traderData = self.get_last_traderData()
               
        self.buy_order_depth, self.sell_order_depth = self.get_order_depths()
        self.wall_mid, self.wall_ceiling, self.wall_floor  = self.get_wall()
        self.highest_bid, self.lowest_ask = self.best_offers()
        
        self.position_limit = POS_LIMITS.get(self.name, 0)
        self.initial_position = self.state.position.get(self.name, 0)
        self.buy_available_volume, self.sell_available_volume = None

        
    def get_last_traderData(self):
                        
        last_traderData = {}
        try:
            if self.state.traderData != '':
                last_traderData = json.loads(self.state.traderData)
        except: self.log("ERROR", 'td')

        return last_traderData
    
    def log(self):
        pass
        
    
    def available_volume(self):
        pass
        
    def best_offers(self):
        buy_orders, sell_orders = self.buy_order_depth, self.sell_order_depth
        highest_bid, lowest_ask = None, None
        
        highest_bid = max(buy_orders)
        lowest_ask = min(sell_orders)
        
        return highest_bid, lowest_ask
         
        
    def get_wall(self):
        
        buy_orders, sell_orders = self.buy_order_depth, self.sell_order_depth
        mid, ceiling, floor = None, None, None
        
        try: ceiling = max(buy_orders, key=buy_orders.get)
        except: pass
        try: floor = max(sell_orders, key=sell_orders.get)
        except: pass
        
        try: mid = (ceiling + floor) / 2
        except: pass
        
        return mid, ceiling, floor

        
        
    def get_order_depths(self):
        order_depths, buy_orders, sell_orders = {}, {}, {}
        
        try: order_depths: OrderDepth = self.state.order_depths.get(self.name)
        except: pass
        
        try: buy_orders = {bp: bv for bp, bv in sorted(order_depths.buy_orders.items(), key=lambda x:x[0], reverse = True)}
        except: pass
        
        try: sell_orders = {sp: abs(sv) for sp, sv in sorted(order_depths.sell_orders.items(), key=lambda x:x[0], reverse = True)}
        except: pass

        return buy_orders, sell_orders
    
    
            
        
        
        



class Trader:

    def run(self, state: TradingState):
        text = json.dumps(state, cls=ProsperityEncoder, indent=2, sort_keys=True)
        print(text, flush=True)
        result = {}
        traderData = "SAMPLE" 
        conversions = 1
        return result, conversions, traderData





if __name__ == "__main__":
    # demo with a fake empty state is awkward; just shows API
    logger.info("logging is configured — use logger.info/debug/warning/error in your code")
