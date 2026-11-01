import json
from typing import ClassVar
from unittest.mock import ANY, patch

import pytest

from app import DYNAMODB_TABLE_NAME, SQS_QUEUE_URL, app, process_message


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data == {"status": "ok"}


class TestProcessMessage:
    VALID_MESSAGE: ClassVar[dict] = {
        'MessageId': 'msg-123',
        'Body': json.dumps({
            'user_id': 'user-1',
            'flag_name': 'dark_mode',
            'result': True,
            'timestamp': '2026-09-05T12:00:00'
        }),
        'ReceiptHandle': 'handle-abc'
    }

    @patch('app.dynamodb_client')
    @patch('app.sqs_client')
    def test_process_message_success(self, mock_sqs_client, mock_dynamodb_client):
        process_message(self.VALID_MESSAGE)

        mock_dynamodb_client.put_item.assert_called_once_with(
            TableName=DYNAMODB_TABLE_NAME,
            Item={
                'event_id': {'S': ANY},
                'user_id': {'S': 'user-1'},
                'flag_name': {'S': 'dark_mode'},
                'result': {'BOOL': True},
                'timestamp': {'S': '2026-09-05T12:00:00'}
            }
        )
        mock_sqs_client.delete_message.assert_called_once_with(
            QueueUrl=SQS_QUEUE_URL,
            ReceiptHandle='handle-abc'
        )

    @patch('app.dynamodb_client')
    @patch('app.sqs_client')
    def test_process_message_invalid_json(self, mock_sqs_client, mock_dynamodb_client):
        message = {
            'MessageId': 'msg-456',
            'Body': 'invalid json',
            'ReceiptHandle': 'handle-xyz'
        }

        process_message(message)

        mock_dynamodb_client.put_item.assert_not_called()
        mock_sqs_client.delete_message.assert_not_called()

    @patch('app.dynamodb_client')
    @patch('app.sqs_client')
    def test_process_message_missing_fields(self, mock_sqs_client, mock_dynamodb_client):
        message = {
            'MessageId': 'msg-789',
            'Body': json.dumps({'user_id': 'user-1'}),
            'ReceiptHandle': 'handle-def'
        }

        process_message(message)

        mock_dynamodb_client.put_item.assert_not_called()
        mock_sqs_client.delete_message.assert_not_called()
