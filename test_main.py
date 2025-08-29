
import unittest
from unittest.mock import MagicMock, patch, call
import main
import oci

class TestMain(unittest.TestCase):

    @patch('main.time.sleep', return_value=None)
    @patch('main.send_discord_message')
    def test_execute_oci_command_success(self, mock_send_discord_message, mock_sleep):
        client = MagicMock()
        client.some_method.return_value = MagicMock(data="Success")
        
        result = main.execute_oci_command(client, 'some_method')
        
        self.assertEqual(result, "Success")
        client.some_method.assert_called_once()
        mock_send_discord_message.assert_not_called()

    @patch('main.time.sleep', return_value=None)
    @patch('main.send_discord_message')
    def test_execute_oci_command_connection_error_retry(self, mock_send_discord_message, mock_sleep):
        client = MagicMock()
        client.some_method.side_effect = [
            oci.exceptions.RequestException("Connection error"),
            MagicMock(data="Success")
        ]
        
        result = main.execute_oci_command(client, 'some_method')
        
        self.assertEqual(result, "Success")
        self.assertEqual(client.some_method.call_count, 2)
        mock_send_discord_message.assert_called_once_with("⏳ Connection issue while executing some_method. Retrying... Details: Connection error")

    @patch('main.time.sleep', return_value=None)
    @patch('main.send_discord_message')
    def test_execute_oci_command_service_error_default_handler(self, mock_send_discord_message, mock_sleep):
        client = MagicMock()
        service_error = oci.exceptions.ServiceError(status=500, code="InternalServerError", message="Server error", headers={})
        client.some_method.side_effect = [
            service_error,
            MagicMock(data="Success")
        ]
        
        result = main.execute_oci_command(client, 'some_method')
        
        self.assertEqual(result, "Success")
        self.assertEqual(client.some_method.call_count, 2)
        mock_send_discord_message.assert_called_once()

    @patch('main.time.sleep', return_value=None)
    @patch('main.send_discord_message')
    def test_execute_oci_command_service_error_custom_handler(self, mock_send_discord_message, mock_sleep):
        client = MagicMock()
        service_error = oci.exceptions.ServiceError(status=429, code="LimitExceeded", message="Limit exceeded", headers={})
        client.some_method.side_effect = [
            service_error,
            MagicMock(data="Success")
        ]
        
        custom_handler = MagicMock()
        
        result = main.execute_oci_command(client, 'some_method', custom_error_handler=custom_handler)
        
        self.assertEqual(result, "Success")
        self.assertEqual(client.some_method.call_count, 2)
        custom_handler.assert_called_once_with(service_error)
        mock_send_discord_message.assert_not_called()

    @patch('main.time.sleep', return_value=None)
    @patch('main.send_discord_message')
    def test_execute_oci_command_service_error_custom_handler_raise(self, mock_send_discord_message, mock_sleep):
        client = MagicMock()
        service_error = oci.exceptions.ServiceError(status=429, code="LimitExceeded", message="Limit exceeded", headers={})
        client.some_method.side_effect = service_error
        
        custom_handler = MagicMock()
        custom_handler.side_effect = service_error
        
        with self.assertRaises(oci.exceptions.ServiceError):
            main.execute_oci_command(client, 'some_method', custom_error_handler=custom_handler)
        
        self.assertEqual(client.some_method.call_count, 1)
        custom_handler.assert_called_once_with(service_error)
        mock_send_discord_message.assert_not_called()

if __name__ == '__main__':
    # OCI clients are initialized in main, we need to mock them for tests
    main.iam_client = MagicMock()
    main.network_client = MagicMock()
    main.compute_client = MagicMock()
    main.OCI_USER_ID = "test_user"
    unittest.main()
