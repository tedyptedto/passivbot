from typing import List, Tuple

from numba.experimental import jitclass

from definitions.order import Order
from definitions.order_list import OrderList, empty_order_list
from definitions.position_list import PositionList


@jitclass([])
class StrategyConfig:
    """
    Base strategy config. Needs to be implemented by every strategy.
    DO NOT INHERIT FROM IT!
    """

    def __init__(self):
        pass


def convert_dict_to_config(config: dict) -> StrategyConfig:
    """
    Converts the strategy config from a dictionary to a specific strategy config.
    Needs to be implemented by every strategy.
    :param config: The strategy part of the config.
    :return: A jitclass StrategyConfig implemented by the strategy.
    """
    strategy_config = StrategyConfig()
    for key, item in config.items():
        pass
    return strategy_config


class Strategy:
    """
    Base strategy class specifying base functionality like updating values.
    """

    def __init__(self, config: StrategyConfig):
        """
        Initializes a base strategy with Strategy config and empty values for balance, position, open orders, qty step,
        and price step.
        :param config: Containing the content for the strategy in form of a StrategyConfig.
        """
        self.config = config
        self.balance = 0
        self.position = PositionList()
        self.open_orders = OrderList()
        self.qty_step = None
        self.price_step = None

    def precompile(self):
        """
        Dummy function that should call all functions in a strategy, including external function to force numba to
        compile them. Avoids compilation at first use, which can be during execution of trade logic.
        :return:
        """
        pass

    def update_steps(self, qty_step, price_step):
        """
        Assigns the qty and price step to the strategy. Depending on pair and exchange.
        :param qty_step: The step size of the quantity of an order for this pair and exchange.
        :param price_step: The step size of the price of an order for this pair and exchange.
        :return:
        """
        self.qty_step = qty_step
        self.price_step = price_step

    def update_balance(self, balance: float):
        """
        Updates the balance of the strategy. Is called in the bot when the balance changes.
        :param balance: The new balance.
        :return:
        """
        self.balance = balance

    def update_position(self, position: PositionList):
        """
        Updates the positions of the strategy. Is called in the bot when the position changes.
        :param position: New positions.
        :return:
        """
        self.position.update_long(position.long)
        self.position.update_short(position.short)

    def update_orders(self, orders: OrderList):
        """
        Updates the orders of the strategy. Is called in the bot when the orders change.
        :param orders: New orders.
        :return:
        """
        self.open_orders.update_long(orders.long)
        self.open_orders.update_short(orders.short)

    def update_values(self, balance: float, position: PositionList, orders: OrderList):
        """
        Updates all value of the strategy (balance, positions, orders) at once.
        :param balance: New balance.
        :param position: New positions.
        :param orders: New orders.
        :return:
        """
        self.update_balance(balance)
        self.update_position(position)
        self.update_orders(orders)

    def make_decision(self, balance: float, position: PositionList, orders: OrderList, price: float) -> Tuple[
        List[Order], List[Order]]:
        """
        Base function to make a decision on a price update.
        :param balance: Current balance.
        :param position: Current position.
        :param orders: Current orders.
        :param price: Current price.
        :return: Two typed lists of orders, orders to add and orders to delete.
        """
        add_orders = empty_order_list()
        delete_orders = empty_order_list()
        return add_orders, delete_orders

    def on_update(self, position: PositionList, last_filled_order: Order) -> Tuple[List[Order], List[Order]]:
        """
        Base function to call when there is an order and position update. Waits until both events arrived.
        :param position: The new position.
        :param last_filled_order: The last filled order.
        :return: Two typed lists of orders, orders to add and orders to delete.
        """
        add_orders = empty_order_list()
        delete_orders = empty_order_list()
        return add_orders, delete_orders
