import json
from _dep.datamodel import OrderDepth, UserId, TradingState, Order, ProsperityEncoder


MM_SYMBOL = ["INTARIAN_PEPPER_ROOT", "ASH_COATED_OSMIUM"]
POS_LIMITS = {"INTARIAN_PEPPER_ROOT": 80, "ASH_COATED_OSMIUM": 80}


class Product:
    def __init__(self, name, state, prints, new_trader_data, product_group=None) -> None:
        
        self.orders = []
        
        self.state = state
        self.prints = prints
       
        self.name = name
        self.product_group = name if product_group is None else product_group
        
        self.new_trader_data = new_trader_data
        self.last_traderData = self.get_last_traderData()
               
        self.buy_order_depth, self.sell_order_depth = self.get_order_depths()
        self.wall_mid, self.wall_ceiling, self.wall_floor  = self.get_wall()
        self.highest_bid, self.lowest_ask = self.best_offers()
        
        self.position_limit = POS_LIMITS.get(self.name, 0)
        self.initial_position = self.state.position.get(self.name, 0)
        self.buy_available_volume, self.sell_available_volume = None
        self.available_buy, self.available_sell = self.available_size()

        
    def get_last_traderData(self):
                        
        last_traderData = {}
        try:
            if self.state.traderData != '':
                last_traderData = json.loads(self.state.traderData)
        except: self.log("ERROR", 'td')

        return last_traderData
    
    
    def bid(self, price, volume, logging=True):
        abs_volume = min(abs(int(volume)), self.max_allowed_buy_volume)
        order = Order(self.name, int(price), abs_volume)
        if logging: self.log("BUYO", {"p":price, "s":self.name, "v":int(volume)}, product_group='ORDERS')
        self.max_allowed_buy_volume -= abs_volume
        self.orders.append(order)

    def ask(self, price, volume, logging=True):
        abs_volume = min(abs(int(volume)), self.max_allowed_sell_volume)
        order = Order(self.name, int(price), -abs_volume)
        if logging: self.log("SELLO", {"p":price, "s":self.name, "v":int(volume)}, product_group='ORDERS')
        self.max_allowed_sell_volume -= abs_volume
        self.orders.append(order)

    def log(self, kind, message, product_group=None):
        if product_group is None: product_group = self.product_group

        if product_group == 'ORDERS':
            group = self.prints.get(product_group, [])
            group.append({kind: message})
        else:
            group = self.prints.get(product_group, {})
            group[kind] = message

        self.prints[product_group] = group
        
    
    def available_size(self):
        available_buy = self.position_limit - self.initial_position 
        available_sell = self.initial_position + self.initial_position
        return available_buy, available_sell
        
    def best_offers(self):
        buy_orders, sell_orders = self.buy_order_depth, self.sell_order_depth
        highest_bid, lowest_ask = None, None
        
        try: highest_bid = max(buy_orders)
        except: pass
        try: lowest_ask = min(sell_orders)
        except: pass
        
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
    
class StaticTrader(Product):
    def __init__(self, state, prints, new_trader_data):
        super().__init__(MM_SYMBOL[0], state, prints, new_trader_data)
        
    def get_orders(self):
        # taking
        for bo, bv in self.buy_order_depth.items():
            draw = max(bv, self.available_sell)
            if self.highest_bid > 10000:
                self.ask(bo, draw)
                self.available_sell - draw
                break
                
        for so, sv in self.sell_order_depth.items():
            draw = max(sv, self.available_buy)
            if self.lowest_ask < 10000:
                self.ask(so, draw)
                self.available_buy - draw
                break
        
        # making
        buffer = 1
        for bo, bv in self.buy_order_depth.items():
            if self.highest_bid < 10000:
                bid_price = bo + buffer
                break
                
        for so, sv in self.sell_order_depth.items():
            if self.lowest_ask > 10000:
                ask_price = so - buffer
                break
                
        self.ask(ask_price, self.available_sell)
        self.bid(bid_price, self.available_buy)
        
        return {self.name: self.orders}
        
        
        


class DriftTrader(Product):
    def __init__(self, state, prints, new_trader_data):
        super().__init__(MM_SYMBOL[1], state, prints, new_trader_data)
        
    def get_orders(self):
        pass
        
    
    
    
            
        
        
        



class Trader:
    
    def run(self, state: TradingState):
        result:dict[str,list[Order]] = {}
        new_trader_data = {}
        prints = {
            "GENERAL": {
                "TIMESTAMP": state.timestamp,
                "POSITIONS": state.position
            },
        }

        def export(prints):
            try: print(json.dumps(prints))
            except: pass


        product_traders = {
            MM_SYMBOL[0]: StaticTrader,
            #MM_SYMBOL[1]: DriftTrader,

        }

        result, conversions = {}, 0
        for symbol, product_trader in product_traders.items():
            if symbol in state.order_depths:

                try:
                    trader = product_trader(state, prints, new_trader_data)
                    result.update(trader.get_orders())

                    #if symbol == COMMODITY_SYMBOL:
                        #conversions = trader.get_conversions()
                except: pass


        try: final_trader_data = json.dumps(new_trader_data)
        except: final_trader_data = ''


        export(prints)
        return result, conversions, final_trader_data
