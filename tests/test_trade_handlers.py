import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from handlers.trade_handlers import (
    start_buy, start_sell, execute_trade, cancel_trade,
    handle_sell_percentage, handle_sell_amount_option,
    TRADE_AMOUNT, TRADE_PERCENTAGE
)

class TestTradeHandlers(unittest.TestCase):
    def setUp(self):
        self.update = MagicMock(spec=Update)
        self.context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        self.context.user_data = {}
        
    async def test_start_buy(self):
        # Mock the callback query
        self.update.callback_query = MagicMock()
        self.update.callback_query.data = "buy_BTC"
        self.update.callback_query.edit_message_text = AsyncMock()
        self.update.callback_query.answer = AsyncMock()

        result = await start_buy(self.update, self.context)

        self.assertEqual(result, TRADE_AMOUNT)
        self.assertEqual(self.context.user_data['trade_coin'], "BTC")
        self.assertEqual(self.context.user_data['trade_type'], "buy")
        self.update.callback_query.edit_message_text.assert_called_once()

    async def test_start_sell(self):
        self.update.callback_query = MagicMock()
        self.update.callback_query.data = "sell_ETH"
        self.update.callback_query.edit_message_text = AsyncMock()
        self.update.callback_query.answer = AsyncMock()

        result = await start_sell(self.update, self.context)

        self.assertEqual(result, TRADE_PERCENTAGE)
        self.assertEqual(self.context.user_data['trade_coin'], "ETH")
        self.assertEqual(self.context.user_data['trade_type'], "sell")
        self.update.callback_query.edit_message_text.assert_called_once()

    @patch('handlers.trade_handlers.get_selected_api')
    @patch('handlers.trade_handlers.get_spot_holdings')
    @patch('handlers.trade_handlers.sell_spot')
    async def test_handle_sell_percentage(self, mock_sell_spot, mock_get_holdings, mock_get_api):
        # Mock API and holdings data
        mock_get_api.return_value = {'api_key': 'test_key', 'api_secret': 'test_secret'}
        mock_get_holdings.return_value = {
            'account1': {
                'holdings': [
                    {'currency': 'BTC', 'total': 1.0}
                ]
            }
        }
        mock_sell_spot.return_value = {'order_id': '12345', 'status': 'success'}

        self.update.callback_query = MagicMock()
        self.update.callback_query.data = "sellpct_BTC_50"
        self.update.callback_query.edit_message_text = AsyncMock()
        self.update.callback_query.answer = AsyncMock()

        result = await handle_sell_percentage(self.update, self.context)

        self.assertEqual(result, ConversationHandler.END)
        mock_sell_spot.assert_called_once_with(
            api_key='test_key',
            api_secret='test_secret',
            currency='BTC',
            amount=0.5  # 50% of 1.0
        )

    @patch('handlers.trade_handlers.get_selected_api')
    @patch('handlers.trade_handlers.buy_spot')
    async def test_execute_trade_buy(self, mock_buy_spot, mock_get_api):
        mock_get_api.return_value = {'api_key': 'test_key', 'api_secret': 'test_secret'}
        mock_buy_spot.return_value = {'order_id': '12345', 'status': 'success'}

        self.context.user_data['trade_type'] = 'buy'
        self.context.user_data['trade_coin'] = 'BTC'
        self.update.message = MagicMock()
        self.update.message.text = "100.0"  # Buy for 100 USDT
        self.update.message.reply_text = AsyncMock()

        result = await execute_trade(self.update, self.context)

        self.assertEqual(result, ConversationHandler.END)
        mock_buy_spot.assert_called_once_with(
            api_key='test_key',
            api_secret='test_secret',
            currency='BTC',
            amount=100.0
        )

    async def test_cancel_trade(self):
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()

        result = await cancel_trade(self.update, self.context)

        self.assertEqual(result, ConversationHandler.END)
        self.update.message.reply_text.assert_called_once_with("Trade cancelled.")

    async def test_handle_sell_amount_option(self):
        self.update.callback_query = MagicMock()
        self.update.callback_query.data = "sellamt_BTC"
        self.update.callback_query.edit_message_text = AsyncMock()
        self.update.callback_query.answer = AsyncMock()

        result = await handle_sell_amount_option(self.update, self.context)

        self.assertEqual(result, TRADE_AMOUNT)
        self.assertEqual(self.context.user_data['trade_coin'], "BTC")

if __name__ == '__main__':
    import asyncio
    # Run async tests
    async def run_tests():
        test_loader = unittest.TestLoader()
        test_suite = test_loader.loadTestsFromTestCase(TestTradeHandlers)
        runner = unittest.TextTestRunner()
        runner.run(test_suite)

    asyncio.run(run_tests())
