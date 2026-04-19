import json
import math

from datamodel import OrderDepth, UserId, TradingState, Order, ProsperityEncoder


MM_SYMBOL = ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]
POS_LIMITS = {"ASH_COATED_OSMIUM": 80, "INTARIAN_PEPPER_ROOT": 80}
WALL_MINS = {"ASH_COATED_OSMIUM": 20,"INTARIAN_PEPPER_ROOT": 15}
WALL_WINDOW = 1
LOWASK_WINDOW = 5

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
        self.wall_mid, self.wall_floor, self.wall_ceiling  = self.get_wall(WALL_MINS.get(self.name, 15))
        self.highest_bid, self.lowest_ask = self.best_offers()
        
        self.position_limit = POS_LIMITS.get(self.name, 0)
        self.initial_position = self.state.position.get(self.name, 0)
        self.available_buy, self.available_sell = self.available_size()
        
        self.bwap, self.awap = self.wall_history(WALL_WINDOW)
        self.wall_vwap = self.calc_wall_vwap(WALL_WINDOW)

    def get_last_traderData(self):
                        
        last_traderData = {}
        try:
            if self.state.traderData != '':
                last_traderData = json.loads(self.state.traderData)
        except: self.log("ERROR", 'td')

        return last_traderData
    
    
    def bid(self, price, volume, logging=True):
        int_price = int(price)          # truncate: never bid above intended price
        abs_volume = min(abs(int(volume)), self.available_buy)
        if abs_volume <= 0: return
        order = Order(self.name, int_price, abs_volume)
        if logging: self.log("BUYO", {"p":int_price, "s":self.name, "v":int(volume)}, product_group='ORDERS')
        self.available_buy -= abs_volume
        self.orders.append(order)

    def ask(self, price, volume, logging=True):
        int_price = math.ceil(price)     # ceil: never ask below intended price
        abs_volume = min(abs(int(volume)), self.available_sell)
        if abs_volume <= 0: return
        order = Order(self.name, int_price, -abs_volume)
        if logging: self.log("SELLO", {"p":int_price, "s":self.name, "v":int(volume)}, product_group='ORDERS')
        self.available_sell -= abs_volume
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
        available_sell = self.position_limit + self.initial_position
        return available_buy, available_sell
        
    def best_offers(self):
        buy_orders, sell_orders = self.buy_order_depth, self.sell_order_depth
        highest_bid, lowest_ask = None, None
        
        if buy_orders: 
            try: highest_bid = max(buy_orders)
            except: pass
            
        if sell_orders:
            try: lowest_ask = min(sell_orders)
            except: pass
        
        return highest_bid, lowest_ask
        
    def get_wall(self, volume_min):
        
        buy_orders, sell_orders = self.buy_order_depth, self.sell_order_depth
        mid, ceiling, floor = None, None, None
        
        if buy_orders:
            try:
                bp = max(buy_orders, key=buy_orders.get)
                floor = bp if buy_orders[bp] >= volume_min else None
            except: pass

        if sell_orders:
            try:
                sp = max(sell_orders, key=sell_orders.get)
                ceiling = sp if sell_orders[sp] >= volume_min else None
            except: pass
        
        if floor and ceiling:
            mid = (floor + ceiling) / 2
        
        return mid, floor, ceiling

        
        
    def get_order_depths(self):
        od = self.state.order_depths.get(self.name)
        if od is None:
            return {}, {}
        buy_orders, sell_orders = {}, {}
        if od.buy_orders:
            try: buy_orders = {bp: bv for bp, bv in sorted(od.buy_orders.items(), key=lambda x:x[0], reverse = True)}
            except: pass
        if od.sell_orders:
            try: sell_orders = {sp: abs(sv) for sp, sv in sorted(od.sell_orders.items(), key=lambda x:x[0])}
            except: pass

        return buy_orders, sell_orders
    
    def _wall_keys(self):
        return f"{self.name}_BWAP", f"{self.name}_AWAP"
  
    def wall_history(self, window):
        
        bk, ak = self._wall_keys()
        bwap = list(self.last_traderData.get(bk, []))
        awap = list(self.last_traderData.get(ak, []))
        
        if window < 1:
            window = 1
            
        if self.wall_floor is not None:
            bwap.append(int(self.wall_floor))
            
        if self.wall_ceiling is not None:
            awap.append(int(self.wall_ceiling))
            
        while len(bwap) > window:
            bwap.pop(0)
        while len(awap) > window:
            awap.pop(0)
            
        self.new_trader_data[bk] = bwap
        self.new_trader_data[ak] = awap
        return bwap, awap
    
    def calc_wall_vwap(self, window):
        if len(self.bwap) != window or len(self.awap) != window:
            return None
        return (sum(self.bwap) + sum(self.awap)) / (2 * window)

    
class StaticTrader(Product):
    def __init__(self, state, prints, new_trader_data):
        super().__init__(MM_SYMBOL[0], state, prints, new_trader_data)

        self.anchor_mid = 10000
        self.variable_mid = self.wall_vwap
        

    def get_orders(self):
        # taking
 #       if not self.buy_order_depth:
        if self.wall_vwap:
            for sp, sv in self.sell_order_depth.items():
                ev = ((self.anchor_mid - sp) + (self.variable_mid - sp) * 3) / 4
                if ev > 0:
                    self.bid(sp, sv, logging=False)
                elif sp <= self.variable_mid and sp < self.anchor_mid:
                    self.bid(sp, min(sv, abs(self.initial_position)), logging=False)

            for bp, bv in self.buy_order_depth.items():
                ev = ((bp - self.anchor_mid) + (bp - self.variable_mid) * 3) / 4
                if ev > 0:
                    self.ask(bp, bv, logging=False)
                elif bp >= (self.variable_mid) and bp > self.anchor_mid:
                    self.ask(bp, min(bv, self.initial_position), logging=False)
        
        if self.wall_vwap:
            bid_price = self.variable_mid - 95
            for bp, bv in self.buy_order_depth.items():
                overbidding_price = bp + 1
                ev = ((self.anchor_mid - overbidding_price) + (self.variable_mid - overbidding_price) * 3) / 4
                if bv > 1 and ev > 0:
                    bid_price = max(bid_price, overbidding_price)
                    break
                elif bp < self.variable_mid and bp < self.anchor_mid:
                    bid_price = max(bid_price, bp)
                    break
                
            self.bid(bid_price, self.available_buy)
            
        if self.wall_vwap:
            ask_price = self.variable_mid + 95
            for sp, sv in self.sell_order_depth.items():
                underbidding_price = sp - 1
                ev = ((underbidding_price - self.anchor_mid) + (underbidding_price - self.variable_mid) * 3) / 4
                if sv > 1 and ev > 0:
                    ask_price = min(ask_price, underbidding_price)
                    break
                elif sp > self.variable_mid and sp > self.anchor_mid:
                    ask_price = min(ask_price, sp)
                    break

            self.ask(ask_price, self.available_sell)            
        
        return {self.name: self.orders}
    

class DriftTrader(Product):
    def __init__(self, state, prints, new_trader_data):
        super().__init__(MM_SYMBOL[1], state, prints, new_trader_data)
        self.drift_mid = state.timestamp * .001 + 13000     
        self.dynamic_mid = self.safe_mid()
        self.a_floor = self.ask_floor(LOWASK_WINDOW)

    def safe_mid(self):
        residual_max = 1
        if self.wall_vwap is None:
            return None
        if abs(self.drift_mid - self.wall_vwap) < residual_max:
            return self.drift_mid
        return self.wall_vwap
    
    def ask_floor(self, window):
        
        ask_floor = list(self.last_traderData.get("ASK_FLOOR", []))
        
        if window < 1:
            window = 1
            
        if self.wall_ceiling is not None and self.dynamic_mid is not None:
            ask_floor.append(self.wall_ceiling - self.dynamic_mid)

        while len(ask_floor) > window:
            ask_floor.pop(0)

        self.new_trader_data["ASK_FLOOR"] = ask_floor
        return min(ask_floor) if ask_floor else None
            

    
    def get_orders(self):
        
        if self.dynamic_mid:
            if self.initial_position < 80 and self.state.timestamp < 10000:
                for sp, sv in self.sell_order_depth.items():
                    if self.a_floor is not None and sp < (self.dynamic_mid + self.a_floor - 2):
                        self.bid(sp, sv, logging=False)
                    
        if self.dynamic_mid:
            for sp, sv in self.sell_order_depth.items():
                if sp < self.dynamic_mid + 1:
                    self.bid(sp, sv, logging=False)

        
        if self.dynamic_mid:
            bid_price = self.dynamic_mid - 95
            for bp, bv in self.buy_order_depth.items():
                overbidding_price = bp + 1
                if bv > 1 and overbidding_price < self.dynamic_mid:
                    bid_price = max(bid_price, overbidding_price)
                    break
                elif bp < self.dynamic_mid:
                    bid_price = max(bid_price, bp)
                    break
                
            self.bid(bid_price, self.available_buy)
            
        if self.dynamic_mid:
            ask_price = self.dynamic_mid + 95
            for sp, sv in self.sell_order_depth.items():
                underbidding_price = sp - 1
                if self.a_floor is not None and sv > 1 and underbidding_price > (self.dynamic_mid + self.a_floor - 4) and self.initial_position > 79:
                    ask_price = min(ask_price, underbidding_price)
                    break

            self.ask(ask_price, 5)       

        return {self.name: self.orders}
    

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
            MM_SYMBOL[1]: DriftTrader,

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